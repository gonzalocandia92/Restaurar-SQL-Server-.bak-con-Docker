CREATE OR ALTER VIEW dbo.vw_sud_Equipo AS
SELECT
    a.Oid,
    a.Codigo AS Codigo, 
    a.Nombre AS Nombre,
    CASE 
        WHEN a.LocalizacionTipo = 1 THEN 
            dbo.ObtenerDireccionCompleta(a.Calle, a.Localidad, a.CodigoPostal, a.Provincia, a.Pais)
        ELSE 
            NULL
    END AS Localizacion,
    ast.Codigo AS Subtipo_Codigo,
    ast.Nombre AS SubTipo_Nombre,
    cl.Codigo AS Clasificacion_Codigo,
    cl.Nombre AS Clasificacion_Nombre,
    a.FechaDeModificacion,
    a.FechaDeAlta,
    a.ActivoPadre AS Instalacion,
    REPLACE(a.Etiquetas, ',', ', ') AS Etiquetas,
    a.EnServicio AS EnServicio,
    a.Cliente AS ClienteOid
FROM dbo.Activo a
LEFT JOIN ActivoSubTipo ast ON ast.Oid = a.SubTipo
LEFT JOIN ActivoClasificacion cl ON cl.Oid = a.Clasificacion
WHERE tipo = 0