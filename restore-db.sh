#!/bin/bash

export MSSQL_SA_PASSWORD=$DEFAULT_MSSQL_SA_PASSWORD

# Esperar a que SQL Server esté listo para aceptar conexiones
echo "Esperando a que SQL Server esté listo..."
/opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P $MSSQL_SA_PASSWORD -Q "SELECT 1" > /dev/null 2>&1
while [ $? -ne 0 ]; do
    echo "Esperando..."
    sleep 5
    /opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P $MSSQL_SA_PASSWORD -Q "SELECT 1" > /dev/null 2>&1
done

for restoreFile in /tmp/backup/*.bak  # Asegúrate de que el path sea el correcto
do
    fileName=${restoreFile##*/}
    base=${fileName%.bak}
    
    # Rutas a donde se deben mover los archivos .mdf y .ldf en el contenedor
    mdfFile="/var/opt/mssql/data/${base}.mdf"
    ldfFile="/var/opt/mssql/data/${base}_log.ldf"
    
    # Realizar la restauración de la base de datos especificando las rutas de los archivos
    /opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P $MSSQL_SA_PASSWORD -Q "RESTORE DATABASE [$base] FROM DISK = '$restoreFile' WITH MOVE '${base}' TO '$mdfFile', MOVE '${base}_log' TO '$ldfFile'"

    # Eliminar el archivo .bak después de la restauración
    rm -rf $restoreFile
done
