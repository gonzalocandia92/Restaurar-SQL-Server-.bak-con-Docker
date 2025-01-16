#!/bin/bash

# Directorios de logs
CONTAINER_LOG="/mnt/external_logs/container.log"
SQL_LOG_DIR="/var/opt/mssql/log"
EXTERNAL_SQL_LOG_DIR="/mnt/external_logs/sql_logs"

# Crear directorios externos si no existen
mkdir -p $(dirname $CONTAINER_LOG)
mkdir -p $EXTERNAL_SQL_LOG_DIR

# Redirigir stdout y stderr del contenedor a un archivo de log externo
exec > >(tee -a "$CONTAINER_LOG") 2>&1

echo "Iniciando contenedor y configurando logs externos..."

# Iniciar SQL Server en segundo plano
/opt/mssql/bin/sqlservr --accept-eula &

# Esperar que SQL Server esté listo
echo "Esperando que SQL Server esté listo..."
until /opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P $MSSQL_SA_PASSWORD -Q "SELECT 1" > /dev/null 2>&1; do
    sleep 5
    echo "Esperando SQL Server..."
done

echo "SQL Server está listo para aceptar conexiones."

# Mover los logs de SQL Server al directorio externo
echo "Moviendo logs de SQL Server al volumen externo..."
mv $SQL_LOG_DIR/* $EXTERNAL_SQL_LOG_DIR/

# Limpiar los logs de SQL Server dentro del contenedor
echo "Limpiando logs de SQL Server en el contenedor..."
> $SQL_LOG_DIR/errorlog
> $SQL_LOG_DIR/errorlog.1

# Ejecutar el script de monitoreo de Google Drive en segundo plano
python3 /opt/mssql/scripts/monitor-drive.py &

echo "Monitoreando Google Drive y esperando archivos de respaldo..."

# Mantener el contenedor en ejecución
wait
