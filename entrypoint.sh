#!/bin/bash

# Ejecutar SQL Server en segundo plano
/opt/mssql/bin/sqlservr --accept-eula &

# Esperar que SQL Server esté listo para aceptar conexiones
echo "Esperando que SQL Server esté listo..."
/opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P $MSSQL_SA_PASSWORD -Q "WAITFOR DELAY '00:00:10'"

# Ejecutar el script de restauración
/opt/mssql/bin/restore-db.sh

# Esperar a que el servidor SQL termine su ejecución (es la última línea, el contenedor permanecerá corriendo)
wait
