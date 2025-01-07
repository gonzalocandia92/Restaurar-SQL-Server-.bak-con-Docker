FROM mcr.microsoft.com/mssql/server:2019-latest
USER root
ENV DEFAULT_MSSQL_SA_PASSWORD=myStrongDefault!Password
ENV ACCEPT_EULA=Y

# Instalar mssql-tools y unixodbc-dev
RUN apt-get update && apt-get install -y mssql-tools unixodbc-dev

COPY restore-db.sh entrypoint.sh /opt/mssql/bin/
RUN chmod +x /opt/mssql/bin/restore-db.sh /opt/mssql/bin/entrypoint.sh

# Cambiar el directorio donde se almacenan los backups
RUN mkdir -p /tmp/

# Copiar los archivos .bak directamente al directorio temporal
COPY backup/*.bak /tmp/

# Cambiar la propiedad y permisos del directorio temporal y los archivos de backup
RUN chown -R mssql:root /tmp && \
    chmod 0755 /tmp && \
    chmod -R 0650 /tmp/*

USER mssql

# CMD ya no ejecuta el script de restauración, lo hará el entrypoint cuando el contenedor inicie
CMD [ "/opt/mssql/bin/sqlservr" ]
ENTRYPOINT [ "/opt/mssql/bin/entrypoint.sh" ]
