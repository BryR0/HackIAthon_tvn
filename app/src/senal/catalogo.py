"""Catálogo de fuentes del paquete "Panamá · Señales y Evidencias v1" (reto §6, §12).

Única fuente de verdad para extracción, snapshot y la página "Catálogo de datos"
de Notion. Las URLs [1]–[9] vienen del PDF del reto; los endpoints son derivados.
Las fuentes SBP [8]–[9] alimentan la extensión bancaria (ADR 0003).
"""

from __future__ import annotations

from dataclasses import dataclass

VERSION_PAQUETE = "panama-senales-evidencias-v1"

PAISES = ("PAN", "CRI", "COL", "DOM", "MEX", "GTM")
ANIOS = range(2010, 2025)
INDICADORES = {
    "NY.GDP.MKTP.KD.ZG": "crecimiento del PIB",
    "FP.CPI.TOTL.ZG": "inflación",
    "SL.UEM.TOTL.ZS": "desempleo",
    "SP.POP.TOTL": "población",
    "IT.NET.USER.ZS": "uso de internet",
    "NE.EXP.GNFS.ZS": "exportaciones/PIB",
}

TVN_RSS_URL = "https://www.tvn-2.com/rss/"
# Reto §6 A: en TVN usar inicialmente metadatos; extractos solo con autorización
# explícita del patrocinador (pregunta 13 al organizador). Mientras sea False,
# la descripción del RSS queda en raw/ y no entra al snapshot.
USAR_EXTRACTOS_TVN = False
GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
WORLDBANK_URL = "https://api.worldbank.org/v2/country/{paises}/indicator/{indicador}"
USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
# Fuente D (§6): Informe de Actividad Bancaria mensual de la SBP, 12 meses de 2024.
SBP_IAB_URL = (
    "https://www.superbancos.gob.pa/documentos/financiera_y_estadistica/estudios/IAB/"
    "IAB-{mes:02d}{anio:02d}.pdf"
)
SBP_ANIO = 2024
SBP_MESES = range(1, 13)
AVISO_SBP = (
    "Datos agregados de la Superintendencia de Bancos de Panamá con fines informativos. "
    "El análisis es del equipo, no una opinión oficial de la SBP."
)

# Consultas GDELT por familia temática pedida en el reto (§6 A).
GDELT_CONSULTAS = {
    "panama": "Panama",
    "logistica": "(Canal OR logistica OR puerto) Panama",
    "turismo": "(turismo OR tourism) Panama",
    "economia": "(economia OR inflacion OR empleo OR economy) Panama",
    "eventos_naturales": "(inundacion OR sismo OR lluvias OR sequia OR flood) Panama",
}
GDELT_MAX_REGISTROS = 250
GDELT_PAUSA_SEGUNDOS = 6.0
VENTANA_NOTICIAS_DIAS = 90
TRAMO_GDELT_DIAS = 15

# Caja regional USGS (§6 C). No equivale al territorio de Panamá.
USGS_PARAMETROS = {
    "format": "geojson",
    "starttime": "2024-01-01",
    "endtime": "2024-12-31T23:59:59",
    "minlatitude": "5",
    "maxlatitude": "12",
    "minlongitude": "-86",
    "maxlongitude": "-76",
    "minmagnitude": "3",
}


@dataclass(frozen=True)
class FuenteCatalogo:
    ref: str
    nombre: str
    url: str
    condiciones: str


FUENTES = (
    FuenteCatalogo(
        "1", "TVN Panamá · sitio oficial", "https://www.tvn-2.com/", "Medio del patrocinador"
    ),
    FuenteCatalogo(
        "2",
        "TVN · feed RSS público",
        TVN_RSS_URL,
        "Titulares, fechas y descripciones; no implica licencia sobre artículos, videos o imágenes",
    ),
    FuenteCatalogo(
        "3",
        "GDELT · DOC 2.0 API",
        "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts",
        "Metadatos; no transfiere derechos de los medios enlazados",
    ),
    FuenteCatalogo(
        "4",
        "Banco Mundial · Indicators API v2",
        "https://datahelpdesk.worldbank.org/knowledgebase/articles/"
        "889392-about-the-indicators-api-documentation",
        "CC BY 4.0 salvo excepciones por indicador",
    ),
    FuenteCatalogo(
        "5", "Banco Mundial · Panamá", "https://data.worldbank.org/country/panama", "CC BY 4.0"
    ),
    FuenteCatalogo(
        "6",
        "Banco Mundial · términos para datasets",
        "https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets",
        "Atribución obligatoria; período de referencia ≠ año de extracción",
    ),
    FuenteCatalogo(
        "7",
        "USGS · servicio FDSN de eventos",
        "https://earthquake.usgs.gov/fdsnws/event/1",
        "Usar ID y URL del evento; solo hechos sísmicos",
    ),
    FuenteCatalogo(
        "8",
        "SBP · estadísticas financieras",
        "https://www.superbancos.gob.pa/estadisticas-financieras",
        "Uso informativo; libre acceso; citar a la SBP como fuente y ser fiel a su contenido "
        "y contexto. Solo agregados del sistema, sin datos de clientes ni por banco",
    ),
    FuenteCatalogo(
        "9",
        "SBP · estudios e informes (Informe de Actividad Bancaria)",
        "https://www.superbancos.gob.pa/estadisticas-financieras/estudios",
        "Uso informativo; citar a la SBP; el análisis del equipo no es opinión oficial de la SBP",
    ),
)
