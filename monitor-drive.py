import time
import os
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
import subprocess
from googleapiclient.errors import HttpError
from datetime import datetime

# Configuración de las credenciales y el ID de la carpeta
SERVICE_ACCOUNT_FILE = '/tmp/credentials/credentials.json'  # Ruta del archivo de credenciales
FOLDER_ID = '1f-9DReeCRVVWX9toD6k4nZBUMCbJt-y-'  # ID de la carpeta en Google Drive
DOWNLOAD_PATH = '/tmp/backup/parino_backup_temp.bak'  # Ruta donde se guardará el archivo descargado
LAST_MODIFIED_FILE = '/tmp/backup/last_modified.txt'  # Archivo para guardar la última fecha de modificación

# Configuración de logging para mostrar el monitoreo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Función para obtener la última fecha de modificación guardada
def get_last_modified_time():
    if os.path.exists(LAST_MODIFIED_FILE):
        with open(LAST_MODIFIED_FILE, 'r') as f:
            last_modified = f.read().strip()
            return datetime.strptime(last_modified, '%Y-%m-%d %H:%M:%S')
    return None

# Función para guardar la fecha de la última modificación
def save_last_modified_time():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LAST_MODIFIED_FILE, 'w') as f:
        f.write(now)

# Función para listar y descargar archivos de Google Drive
def list_and_download_files():
    logger.info("Conectando a Google Drive y descargando el archivo .bak...")

    # Asegurarse de que el directorio de destino exista
    os.makedirs(os.path.dirname(DOWNLOAD_PATH), exist_ok=True)
    
    # Autenticación con la API de Google Drive
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
    service = build('drive', 'v3', credentials=creds)

    while True:
        try:
            # Listar archivos en la carpeta
            results = service.files().list(
                q=f"'{FOLDER_ID}' in parents and trashed=false",
                fields="files(id, name, modifiedTime)"
            ).execute()
            items = results.get('files', [])

            if not items:
                logger.info("No se encontraron archivos en la carpeta.")
            else:
                logger.info("Archivos en la carpeta:")
                for item in items:
                    logger.info(f"Nombre: {item['name']} - ID: {item['id']} - Última modificación: {item['modifiedTime']}")

                    # Si el archivo es el .bak y ha cambiado desde la última restauración
                    if item['name'] == 'parino_backup_temp.bak':
                        # Verificar si el archivo ha sido modificado después de la última restauración
                        last_modified = get_last_modified_time()
                        file_modified_time = datetime.strptime(item['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')

                        if not last_modified or file_modified_time > last_modified:
                            logger.info("Nuevo archivo o archivo modificado, iniciando descarga...")

                            file_id = item['id']
                            request = service.files().get_media(fileId=file_id)
                            with open(DOWNLOAD_PATH, 'wb') as fh:
                                downloader = MediaIoBaseDownload(fh, request)
                                done = False
                                while not done:
                                    status, done = downloader.next_chunk()
                                    logger.info(f"Descargando: {int(status.progress() * 100)}%")
                            
                            logger.info(f"Archivo descargado correctamente a {DOWNLOAD_PATH}")
                            
                            # Llamar a la función de restauración
                            restore_database(DOWNLOAD_PATH)
                            # Guardar la nueva fecha de modificación
                            save_last_modified_time()
                            logger.info("Esperando nuevos archivos en Google Drive...")
                        else:
                            logger.info("El archivo no ha cambiado desde la última restauración. No es necesario restaurar.")

        except HttpError as error:
            logger.error(f"Error al conectar con Google Drive: {error}")
            # Reintentar después de un intervalo de tiempo si hay un error de conexión
            logger.info("Reintentando la conexión en 30 segundos...")
            time.sleep(30)  # Esperar 30 segundos antes de intentar nuevamente

        # Esperar un minuto antes de revisar nuevamente
        logger.info("Monitoreo en ejecución... Esperando un minuto para la siguiente comprobación.")
        time.sleep(60)  # Espera de 1 minuto

# Función para restaurar la base de datos
def restore_database(backup_file_path):
    logger.info(f"Iniciando restauración con el archivo {backup_file_path}...")
    
    # Nombre base de la base de datos (aquí se puede personalizar si se quiere)
    db_name = os.path.basename(backup_file_path).replace('.bak', '')
    
    # Comando para eliminar la base de datos si ya existe
    delete_db_command = f"/opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P $MSSQL_SA_PASSWORD -Q \"IF EXISTS (SELECT name FROM sys.databases WHERE name = '{db_name}') BEGIN DROP DATABASE [{db_name}] END\""
    
    # Ejecutar el comando para eliminar la base de datos
    delete_result = subprocess.run(delete_db_command, shell=True, capture_output=True, text=True)
    
    if delete_result.returncode == 0:
        logger.info(f"Base de datos {db_name} eliminada si existía.")
    else:
        logger.error(f"Error al intentar eliminar la base de datos {db_name}: {delete_result.stderr}")

    # Rutas a donde se deben mover los archivos .mdf y .ldf en el contenedor
    mdf_file = f"/var/opt/mssql/data/{db_name}.mdf"
    ldf_file = f"/var/opt/mssql/data/{db_name}_log.ldf"

    # Realizar la restauración de la base de datos especificando las rutas de los archivos
    restore_command = f"""/opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P $MSSQL_SA_PASSWORD -Q "RESTORE DATABASE [{db_name}] FROM DISK = '{backup_file_path}' WITH MOVE 'parino.cmms.express' TO '{mdf_file}', MOVE 'parino.cmms.express_log' TO '{ldf_file}'" > /tmp/restore_output.log 2>&1"""
    
    # Ejecutar el comando de restauración
    result = subprocess.run(restore_command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info(f"Restauración completada exitosamente para la base de datos: {db_name}")
        execute_ddl_scripts(db_name)
    else:
        logger.error(f"Error durante la restauración de la base de datos: {result.stderr}")
    
    # Eliminar el archivo .bak después de la restauración
    os.remove(backup_file_path)
    logger.info(f"Archivo {backup_file_path} eliminado después de la restauración.")

# Nueva función para ejecutar los scripts DDL de vistas
def execute_ddl_scripts(db_name):
    logger.info(f"Ejecutando scripts de DDL para las vistas en la base de datos {db_name}...")
    
    # Rutas a los archivos .sql
    views_sql_files = [
        '/opt/mssql/scripts/vw_sud_Activo.sql',
        '/opt/mssql/scripts/vw_sud_Cliente.sql'
    ]
    
    for sql_file in views_sql_files:
        sqlcmd_command = f"""
        /opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P $MSSQL_SA_PASSWORD -d {db_name} -i {sql_file}
        """
        # Ejecutar cada script de vista
        sqlcmd_result = subprocess.run(sqlcmd_command, shell=True, capture_output=True, text=True)
        if sqlcmd_result.returncode == 0:
            logger.info(f"Vista de {sql_file} ejecutada exitosamente.")
        else:
            logger.error(f"Error al ejecutar el script de {sql_file}: {sqlcmd_result.stderr}")

    
if __name__ == '__main__':
    list_and_download_files()
