CREATE OR ALTER VIEW dbo.vw_sud_Activo AS
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
    a.Tipo AS Tipo,
    ast.Codigo AS Subtipo_Codigo,
    ast.Nombre AS SubTipo_Nombre,
    cl.Codigo AS Clasificacion_Codigo,
    cl.Nombre AS Clasificacion_Nombre,
    a.FechaDeModificacion,
    a.FechaDeAlta,
    (SELECT COUNT(1) 
     FROM Activo h 
     WHERE h.GCRecord IS NULL AND h.ActivoPadre = a.Oid
    ) AS TieneHijos,
    CASE 
        WHEN  
         	(SELECT COUNT(1) 
    		FROM Activo h 
     		WHERE h.GCRecord IS NULL AND h.ActivoPadre = a.Oid) > 0
        THEN CAST(1 AS BIT) 
        ELSE CAST(0 AS BIT) 
    END AS EsPadre,
    REPLACE(a.Etiquetas, ',', ', ') AS Etiquetas,
    a.EnServicio AS EnServicio,
    a.Cliente AS ClienteOid
FROM dbo.Activo a
LEFT JOIN ActivoSubTipo ast ON ast.Oid = a.SubTipo
LEFT JOIN ActivoClasificacion cl ON cl.Oid = a.Clasificacion

