FROM mcr.microsoft.com/mssql/server:2019-latest

USER root

# Variables de entorno para SQL Server
ENV DEFAULT_MSSQL_SA_PASSWORD=myStrongDefault!Password
ENV ACCEPT_EULA=Y

# Instalar herramientas necesarias: mssql-tools, unixodbc-dev, Python y pip
RUN apt-get update && apt-get install -y \
    mssql-tools unixodbc-dev python3 python3-pip && \
    apt-get clean

# Instalar el SDK de Google API para Python
RUN pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Crear directorios necesarios
RUN mkdir -p /tmp/ /opt/mssql/scripts /tmp/credentials

# Copiar los scripts personalizados
#COPY restore-db.sh entrypoint.sh download_from_drive.py monitor-drive.py /opt/mssql/scripts/
COPY restore-db.sh entrypoint.sh monitor-drive.py /opt/mssql/scripts/

# Copiar las credenciales de la API de Google Drive
COPY credentials.json /tmp/credentials/

# Dar permisos de ejecución a los scripts
RUN chmod +x /opt/mssql/scripts/*.sh /opt/mssql/scripts/*.py

# Cambiar la propiedad y permisos de los directorios necesarios
RUN chown -R mssql:root /tmp /opt/mssql/scripts && \
    chmod 0755 /tmp /opt/mssql/scripts

# Cambiar al usuario mssql
USER mssql

# Configurar el entrypoint personalizado
CMD [ "/opt/mssql/bin/sqlservr" ]
ENTRYPOINT [ "/opt/mssql/scripts/entrypoint.sh" ]
