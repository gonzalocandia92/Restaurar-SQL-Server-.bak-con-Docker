CREATE OR ALTER VIEW dbo.vw_sud_Cliente AS
SELECT 
    cli.Oid,
    ter.Codigo AS CUIT,
    cli.RazonSocial,
    cli.FechaDeAlta,
    ter.Calle,
    ter.Localidad,
    ter.CodigoPostal,
    prov.Nombre AS Provincia,
    pais.Nombre AS Pais,  
    ter.EstaActivo, 
    CASE 
        WHEN ter.GCRecord IS NOT NULL THEN 1 
        ELSE 0 
    END AS EstaEliminado
FROM dbo.Cliente AS cli
INNER JOIN dbo.Tercero AS ter ON cli.Oid = ter.Oid
LEFT JOIN dbo.Provincia AS prov ON ter.Provincia = prov.Oid
LEFT JOIN dbo.Pais AS pais ON ter.Pais = pais.Oid AND prov.Pais = pais.Oid;
