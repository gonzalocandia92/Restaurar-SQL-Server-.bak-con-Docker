#!/bin/bash

# Ejecutar SQL Server en segundo plano
/opt/mssql/bin/sqlservr --accept-eula &

# Esperar que SQL Server esté listo para aceptar conexiones
echo "Esperando que SQL Server esté listo..."
until /opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P $MSSQL_SA_PASSWORD -Q "SELECT 1" > /dev/null 2>&1; do
    sleep 5
    echo "Esperando SQL Server..."
done

echo "SQL Server está listo para aceptar conexiones."

# Ejecutar el script para monitorear Google Drive en segundo plano
python3 /opt/mssql/scripts/monitor-drive.py &

echo "Monitoreando Google Drive y esperando archivos de respaldo..."

# Esperar a que el servidor SQL termine su ejecución (es la última línea, el contenedor permanecerá corriendo)
wait
