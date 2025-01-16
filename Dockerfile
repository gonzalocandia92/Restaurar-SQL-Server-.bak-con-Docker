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
RUN mkdir -p /tmp/ /opt/mssql/scripts /tmp/credentials /mnt/external_logs

# Copiar todos los archivos desde ./scripts/ al contenedor
COPY ./scripts/* /opt/mssql/scripts/

# Copiar los scripts personalizados
COPY entrypoint.sh monitor-drive.py /opt/mssql/scripts/

# Copiar las credenciales de la API de Google Drive
COPY credentials.json /tmp/credentials/

# Dar permisos de ejecución a los scripts
RUN chmod +x /opt/mssql/scripts/*.sh /opt/mssql/scripts/*.py

# Cambiar la propiedad y permisos de los directorios necesarios
RUN chown -R mssql:root /tmp /opt/mssql/scripts /mnt/external_logs && \
    chmod 0755 /tmp /opt/mssql/scripts /mnt/external_logs

# Configurar un volumen para los logs externos
VOLUME /mnt/external_logs

# Cambiar al usuario mssql
USER mssql

# Configurar el entrypoint personalizado
ENTRYPOINT [ "/opt/mssql/scripts/entrypoint.sh" ]
