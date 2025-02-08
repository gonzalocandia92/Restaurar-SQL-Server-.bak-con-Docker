-- Verificar si el login global ya existe
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'sudata_reader')
BEGIN
    CREATE LOGIN sudata_reader WITH PASSWORD = 'myStrongDefault!Password';
    PRINT 'Login "sudata_reader" creado.';
END
ELSE
BEGIN
    PRINT 'Login "sudata_reader" ya existe.';
END

-- Verificar si el usuario ya existe en la base de datos
USE parino_backup_temp;
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'sudata_reader')
BEGIN
    CREATE USER sudata_reader FOR LOGIN sudata_reader;
    PRINT 'Usuario "sudata_reader" creado en la base de datos "parino_backup_temp".';
END
ELSE
BEGIN
    PRINT 'Usuario "sudata_reader" ya existe en la base de datos "parino_backup_temp".';
END

-- Verificar si el rol de solo lectura ya ha sido asignado
IF NOT EXISTS (SELECT * FROM sys.database_role_members 
               WHERE member_principal_id = USER_ID('sudata_reader') 
               AND role_principal_id = USER_ID('db_datareader'))
BEGIN
    ALTER ROLE db_datareader ADD MEMBER sudata_reader;
    PRINT 'Rol "db_datareader" asignado al usuario "sudata_reader".';
END
ELSE
BEGIN
    PRINT 'El usuario "sudata_reader" ya tiene el rol "db_datareader".';
END

-- Verificar que el rol fue asignado correctamente
SELECT * FROM sys.database_role_members WHERE member_principal_id = USER_ID('sudata_reader');
