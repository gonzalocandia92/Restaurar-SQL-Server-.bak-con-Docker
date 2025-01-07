#!/bin/bash

export MSSQL_SA_PASSWORD=$DEFAULT_MSSQL_SA_PASSWORD

# Iniciar el servidor SQL Server en segundo plano
(/opt/mssql/bin/sqlservr --accept-eula & ) | grep -q "Server is listening on" && sleep 2

for restoreFile in /tmp/*.bak
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
