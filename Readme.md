# SQL Server Backup Restoration from Google Drive

Este proyecto permite la restauración automática de bases de datos en un servidor SQL Server a partir de un archivo de respaldo `.bak` almacenado en una carpeta de Google Drive. El sistema monitorea continuamente la carpeta de Google Drive para detectar nuevos archivos de respaldo o modificaciones en archivos existentes y realiza la restauración cuando sea necesario.

## Características

- **Monitoreo continuo**: El sistema verifica la carpeta de Google Drive cada minuto para ver si el archivo de respaldo ha sido modificado.
- **Restauración automática**: Si se detecta un archivo `.bak` nuevo o modificado, el sistema descarga el archivo y restaura la base de datos correspondiente en SQL Server.
- **Eliminación de la base de datos anterior**: Antes de realizar la restauración, si ya existe una base de datos con el mismo nombre, esta será eliminada para evitar conflictos.
- **Configuración flexible**: Las credenciales de Google Drive y otros parámetros son fácilmente configurables a través de variables en el código.

## Requisitos

Para ejecutar este proyecto, necesitas:

- **Docker** (para contenedores)
- **SQL Server** (contenedor o instalación local)
- **Google Cloud Service Account** con acceso a la API de Google Drive
- **Python 3.x** y las bibliotecas correspondientes:
    - `google-api-python-client`
    - `google-auth`
    - `google-auth-httplib2`
    - `google-auth-oauthlib`
    - `google-cloud`
    - `subprocess`
  
## Uso

- **Monitoreo**: El script `monitor-drive.py` se ejecutará en un bucle infinito, verificando la carpeta de Google Drive cada minuto para detectar archivos nuevos o modificados.

- **Restauración**: Si se encuentra un archivo `.bak` nuevo o modificado, el sistema lo descargará y lo usará para restaurar la base de datos en el servidor SQL Server. La base de datos existente se eliminará antes de la restauración.

## Estructura del Proyecto

