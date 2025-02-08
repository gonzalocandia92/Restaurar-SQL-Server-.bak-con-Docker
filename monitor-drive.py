import time
import os
import logging
import zipfile
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
import subprocess
from googleapiclient.errors import HttpError
from datetime import datetime

SERVICE_ACCOUNT_FILE = '/tmp/credentials/credentials.json'
FOLDER_ID = '1Cz_yVxOwV-JYTzra6z8nWUPBHN-86w2O'
DOWNLOAD_PATH = '/tmp/backup/parino_backup_temp.bak'
LAST_MODIFIED_FILE = '/tmp/backup/last_modified.txt'
SQL_LOG_DIR = '/var/opt/mssql/log'
CONTAINER_LOG = '/mnt/external_logs/container.log'
LOG_BACKUP_DIR = '/mnt/external_logs'
SA_PASSWORD = os.environ.get('MSSQL_SA_PASSWORD')


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def execute_sql_command_with_retry(command, retries=3):
    for attempt in range(retries):
        result = subprocess.run(command, capture_output=True, text=True)
        if "Login failed" not in result.stderr:
            return result
        logger.warning(f"Login attempt {attempt + 1} failed. Retrying...")
        time.sleep(5)
    logger.error("Max retries reached for SQL command.")
    return None

def get_last_modified_time():
    if os.path.exists(LAST_MODIFIED_FILE):
        with open(LAST_MODIFIED_FILE, 'r') as f:
            last_modified = f.read().strip()
            return datetime.strptime(last_modified, '%Y-%m-%d %H:%M:%S')
    return None

def save_last_modified_time():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LAST_MODIFIED_FILE, 'w') as f:
        f.write(now)

def list_and_download_files():
    logger.info("Conectando a Google Drive y buscando archivos .bak...")
    os.makedirs(os.path.dirname(DOWNLOAD_PATH), exist_ok=True)

    while True:
        try:
            # Renovar conexión con Google Drive antes de cada verificación
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
            service = build('drive', 'v3', credentials=creds)
            
            # Obtener lista de archivos .bak en la carpeta de Drive
            results = service.files().list(
                q=f"'{FOLDER_ID}' in parents and trashed=false and name contains '.bak'",
                fields="files(id, name, modifiedTime)"
            ).execute()
            items = results.get('files', [])

            if not items:
                logger.info("No se encontraron archivos .bak en Drive.")
            else:
                # Ordenar los archivos por fecha de modificación (más reciente primero)
                items.sort(key=lambda x: x['modifiedTime'], reverse=True)
                latest_file = items[0]  # Último archivo modificado
                file_id = latest_file['id']
                file_name = latest_file['name']
                file_modified_time = datetime.strptime(latest_file['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')

                last_modified = get_last_modified_time()
                if not last_modified or file_modified_time > last_modified:
                    logger.info(f"Nuevo archivo encontrado: {file_name}. Iniciando descarga...")
                    
                    # Descargar el archivo
                    temp_download_path = os.path.join(os.path.dirname(DOWNLOAD_PATH), file_name)
                    request = service.files().get_media(fileId=file_id)
                    with open(temp_download_path, 'wb') as fh:
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                            logger.info(f"Descargando: {int(status.progress() * 100)}%")

                    # Renombrar el archivo descargado a "parino_backup_temp.bak"
                    os.rename(temp_download_path, DOWNLOAD_PATH)
                    logger.info(f"Archivo renombrado a {DOWNLOAD_PATH}")

                    # Restaurar la base de datos
                    restore_database(DOWNLOAD_PATH)

                    # Guardar la fecha de última modificación
                    save_last_modified_time()

                    # Eliminar todos los archivos de Drive excepto el último descargado
                    for item in items:
                        if item['id'] != file_id:
                            try:
                                #service.files().delete(fileId=item['id']).execute()
                                logger.info(f"Archivo {item['name']} eliminado de Google Drive.")
                            except HttpError as error:
                                logger.error(f"Error al eliminar {item['name']}: {error}")

        except HttpError as error:
            logger.error(f"Error en Google Drive: {error}")
            time.sleep(30)

        logger.info("Esperando un minuto para la siguiente verificación.")
        time.sleep(60)


def restore_database(backup_file_path):
    logger.info(f"Iniciando restauración con el archivo {backup_file_path}...")
    db_name = os.path.basename(backup_file_path).replace('.bak', '')

    # Permitir conexiones remotas
    sqlcmd_command = ["/opt/mssql-tools/bin/sqlcmd", "-S", "localhost", "-U", "SA", "-P", SA_PASSWORD, "-Q", "sp_configure 'remote access', 1; RECONFIGURE;"]
    execute_sql_command_with_retry(sqlcmd_command)
    
    # Cerrar sesiones activas y eliminar la base de datos
    close_sessions_command = [
        "/opt/mssql-tools/bin/sqlcmd", "-S", "localhost", "-U", "SA", "-P", SA_PASSWORD, "-Q",
        f"ALTER DATABASE [{db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE IF EXISTS [{db_name}];"
    ]
    execute_sql_command_with_retry(close_sessions_command)
    
    # Restaurar la base de datos
    restore_command = [
        "/opt/mssql-tools/bin/sqlcmd", "-S", "localhost", "-U", "SA", "-P", SA_PASSWORD, "-Q",
        f"RESTORE DATABASE [{db_name}] FROM DISK = '{backup_file_path}' WITH MOVE 'parino.cmms.express' TO '/var/opt/mssql/data/{db_name}.mdf', MOVE 'parino.cmms.express_log' TO '/var/opt/mssql/data/{db_name}_log.ldf'"
    ]
    subprocess.run(restore_command)

    # Verificar si la base de datos existe antes de ejecutar scripts DDL
    check_db_command = [
        "/opt/mssql-tools/bin/sqlcmd", "-S", "localhost", "-U", "SA", "-P", SA_PASSWORD, "-Q", 
        f"SELECT name FROM sys.databases WHERE name = '{db_name}';"
    ]
    result = subprocess.run(check_db_command, capture_output=True, text=True)
    if db_name not in result.stdout:
        logger.error(f"Error: La base de datos {db_name} no se restauró correctamente.")
        return

    logger.info(f"Restauración completada para {db_name}")
    if check_database_recovery(db_name):
        execute_ddl_scripts(db_name)
        enable_tde(db_name)
    else:
        logger.error(f"Database {db_name} is not fully recovered.")
    clear_logs()
    os.remove(backup_file_path)

def execute_ddl_scripts(db_name):
    logger.info(f"Ejecutando scripts DDL en {db_name}...")
    scripts = [os.path.join('/opt/mssql/scripts', f) for f in os.listdir('/opt/mssql/scripts') if f.endswith('.sql')]
    
    for script in scripts:
        sqlcmd_command = ["/opt/mssql-tools/bin/sqlcmd", "-S", "localhost", "-U", "SA", "-P", SA_PASSWORD, "-d", db_name, "-i", script]
        result = execute_sql_command_with_retry(sqlcmd_command)
        if result:
            logger.info(f"Ejecutado: {script}")
        else:
            logger.error(f"Error al ejecutar el script: {script}")

def clear_logs():
    logger.info("Comprimendo logs antes de limpiarlos...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = os.path.join(LOG_BACKUP_DIR, f'logs_{timestamp}.zip')
    
    with zipfile.ZipFile(zip_filename, 'w') as log_zip:
        for log_file in os.listdir(SQL_LOG_DIR):
            full_path = os.path.join(SQL_LOG_DIR, log_file)
            log_zip.write(full_path, arcname=log_file)
        if os.path.exists(CONTAINER_LOG):
            log_zip.write(CONTAINER_LOG, arcname='container.log')
    
    logger.info(f"Logs comprimidos en {zip_filename}")
    
    logger.info("Limpiando logs después de la restauración...")
    open(CONTAINER_LOG, 'w').close()
    clear_logs_command = ["/opt/mssql-tools/bin/sqlcmd", "-S", "localhost", "-U", "SA", "-P", SA_PASSWORD, "-Q", "EXEC sp_cycle_errorlog;"]
    result = execute_sql_command_with_retry(clear_logs_command)
    if result:
        logger.info(f"Logs limpiados exitosamente.")
    else:
        logger.error(f"Error al limpiar logs.")

def check_database_recovery(db_name):
    check_db_recovery_command = [
        "/opt/mssql-tools/bin/sqlcmd", "-S", "localhost", "-U", "SA", "-P", SA_PASSWORD, "-Q",
        f"SELECT state_desc FROM sys.databases WHERE name = '{db_name}';"
    ]
    result = subprocess.run(check_db_recovery_command, capture_output=True, text=True)
    return 'ONLINE' in result.stdout

def enable_tde(db_name):
    logger.info(f"Habilitando cifrado TDE en {db_name}...")

    # Crear la clave maestra y el certificado en master (si no existen)
    master_key_cert = """
    USE master;
    IF NOT EXISTS (SELECT * FROM sys.symmetric_keys WHERE name = '##MS_DatabaseMasterKey##')
    BEGIN
        CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'MyStrongMasterKeyPassword!';
    END
    IF NOT EXISTS (SELECT * FROM sys.certificates WHERE name = 'MyServerCert')
    BEGIN
        CREATE CERTIFICATE MyServerCert WITH SUBJECT = 'Database Encryption';
    END
    """
    execute_sql_command_with_retry(["/opt/mssql-tools/bin/sqlcmd", "-S", "localhost", "-U", "SA", "-P", SA_PASSWORD, "-Q", master_key_cert])

    # Habilitar TDE en la base de datos restaurada
    tde_command = f"""
    USE {db_name};
    CREATE DATABASE ENCRYPTION KEY WITH ALGORITHM = AES_256 ENCRYPTION BY SERVER CERTIFICATE MyServerCert;
    ALTER DATABASE {db_name} SET ENCRYPTION ON;
    """
    execute_sql_command_with_retry(["/opt/mssql-tools/bin/sqlcmd", "-S", "localhost", "-U", "SA", "-P", SA_PASSWORD, "-Q", tde_command])

    logger.info(f"Cifrado habilitado en {db_name}.")


if __name__ == '__main__':
    list_and_download_files()
