"""Parsers de fuentes públicas. Fixtures sintéticos con el formato real observado 2026-10-06."""

import json
from datetime import UTC, datetime

from senal.fuentes import (
    parsear_gdelt,
    parsear_rss_tvn,
    parsear_usgs,
    parsear_worldbank,
    unidad_desde_nombre,
)

EXTRACCION = datetime(2026, 10, 6, tzinfo=UTC)

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dcterms="http://purl.org/dc/terms/">
  <channel>
    <title><![CDATA[Tvn Panamá - Portada]]></title>
    <item>
      <title><![CDATA[Titular sintético sobre el Canal]]></title>
      <link><![CDATA[https://www.tvn-2.com/nacionales/sintetico_1_1.html]]></link>
      <description><![CDATA[Descripción sintética.
]]></description>
      <pubDate><![CDATA[Tue, 06 Oct 2026 11:50:00 +0000]]></pubDate>
    </item>
    <item>
      <title><![CDATA[Titular sin descripción]]></title>
      <link><![CDATA[https://www.tvn-2.com/economia/sintetico_1_2.html]]></link>
      <pubDate><![CDATA[Fri, 20 Sep 2024 18:19:27 +0000]]></pubDate>
    </item>
  </channel>
</rss>"""


def test_rss_tvn_produce_filas_del_contrato_con_origen_y_alcance() -> None:
    filas = parsear_rss_tvn(RSS, EXTRACCION)

    assert len(filas) == 2
    primera = filas[0]
    assert primera["titulo"] == "Titular sintético sobre el Canal"
    assert primera["medio"] == "tvn-2.com"
    assert primera["origen"] == "tvn_rss"
    assert primera["idioma"] == "es"
    assert primera["descripcion"] == "Descripción sintética."
    assert primera["alcance_texto"] == "titular_descripcion_rss"
    assert primera["fecha_extraccion"] == "2026-10-06T00:00:00+00:00"


def test_rss_sin_descripcion_declara_solo_titular_metadatos() -> None:
    filas = parsear_rss_tvn(RSS, EXTRACCION)

    assert filas[1]["descripcion"] is None
    assert filas[1]["alcance_texto"] == "titular_metadatos"


def test_rss_conserva_fecha_original_de_publicacion() -> None:
    filas = parsear_rss_tvn(RSS, EXTRACCION)

    assert filas[1]["fecha_publicacion"] == "Fri, 20 Sep 2024 18:19:27 +0000"
    assert filas[1]["fecha_deteccion"] is None


WORLDBANK = json.dumps(
    [
        {"page": 1, "pages": 1, "per_page": 1000, "total": 2, "lastupdated": "2026-07-13"},
        [
            {
                "indicator": {
                    "id": "FP.CPI.TOTL.ZG",
                    "value": "Inflation, consumer prices (annual %)",
                },
                "countryiso3code": "PAN",
                "date": "2024",
                "value": 0.7,
                "unit": "",
            },
            {
                "indicator": {
                    "id": "FP.CPI.TOTL.ZG",
                    "value": "Inflation, consumer prices (annual %)",
                },
                "countryiso3code": "CRI",
                "date": "2023",
                "value": None,
                "unit": "",
            },
        ],
    ]
)


def test_worldbank_conserva_nulos_y_deriva_unidad_del_nombre() -> None:
    filas = parsear_worldbank(WORLDBANK, EXTRACCION, "https://api.worldbank.org/v2/x")

    assert [f["valor"] for f in filas] == ["0.7", None]
    assert {f["unidad"] for f in filas} == {"annual %"}
    assert filas[0]["licencia"] == "CC BY 4.0"
    assert filas[0]["fuente_url"] == "https://api.worldbank.org/v2/x"


def test_worldbank_respuesta_de_error_devuelve_lista_vacia() -> None:
    error = json.dumps([{"message": [{"id": "120", "value": "Invalid value"}]}])

    assert parsear_worldbank(error, EXTRACCION, "https://x") == []


def test_unidad_desde_nombre() -> None:
    assert unidad_desde_nombre("Population, total") is None
    assert unidad_desde_nombre("Exports of goods and services (% of GDP)") == "% of GDP"


USGS = json.dumps(
    {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "us6000test",
                "properties": {
                    "mag": 4,
                    "place": "9 km NW of San Juan del Sur, Nicaragua",
                    "time": 1735513210566,
                    "updated": 1741473552040,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us6000test",
                    "status": "reviewed",
                },
                "geometry": {"type": "Point", "coordinates": [-85.9299, 11.3207, 100.943]},
            }
        ],
    }
)


def test_usgs_extrae_campos_del_contrato_con_tiempos_utc() -> None:
    eventos = parsear_usgs(USGS)

    assert eventos == [
        {
            "id": "us6000test",
            "magnitude": 4.0,
            "time": "2024-12-29T23:00:10.566000+00:00",
            "updated": "2025-03-08T22:39:12.040000+00:00",
            "longitude": -85.9299,
            "latitude": 11.3207,
            "depth": 100.943,
            "place": "9 km NW of San Juan del Sur, Nicaragua",
            "status": "reviewed",
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us6000test",
        }
    ]


GDELT = json.dumps(
    {
        "articles": [
            {
                "url": "https://www.prensa.com/economia/sintetico/",
                "url_mobile": "",
                "title": "Titular sintético de economía ",
                "seendate": "20260915T153000Z",
                "socialimage": "",
                "domain": "prensa.com",
                "language": "Spanish",
                "sourcecountry": "Panama",
            }
        ]
    }
)


def test_gdelt_seendate_es_deteccion_y_publicacion_queda_nula() -> None:
    filas = parsear_gdelt(GDELT, EXTRACCION, consulta="economia")

    assert filas == [
        {
            "titulo": "Titular sintético de economía",
            "url": "https://www.prensa.com/economia/sintetico/",
            "medio": "prensa.com",
            "idioma": "es",
            "fecha_publicacion": None,
            "fecha_deteccion": "20260915T153000Z",
            "fecha_extraccion": "2026-10-06T00:00:00+00:00",
            "origen": "gdelt_doc:economia",
            "descripcion": None,
            "alcance_texto": "titular_metadatos",
        }
    ]


def test_gdelt_sin_articulos_o_texto_no_json_devuelve_vacio() -> None:
    assert parsear_gdelt("{}", EXTRACCION, consulta="x") == []
    assert parsear_gdelt("Please limit requests", EXTRACCION, consulta="x") == []
