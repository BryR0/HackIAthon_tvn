"""Parsers puros de las fuentes públicas del reto (§6, §12).

No hacen red: reciben el texto de la respuesta y devuelven filas del contrato
(§7) como diccionarios de texto, listas para ``ingest.validar_*``. La red vive
en ``scripts/``, así la lógica se prueba sin internet.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from defusedxml import ElementTree

Fila = dict[str, str | None]

LICENCIA_BANCO_MUNDIAL = "CC BY 4.0"
UNIDAD_ENTRE_PARENTESIS = re.compile(r"\(([^()]+)\)\s*$")


def _limpio(texto: str | None) -> str | None:
    if texto is None:
        return None
    resultado = " ".join(texto.split())
    return resultado or None


def _hijo(item: Any, etiqueta: str) -> str | None:
    nodo = item.find(etiqueta)
    return None if nodo is None else _limpio(nodo.text)


def parsear_rss_tvn(xml: str, fecha_extraccion: datetime) -> list[Fila]:
    """Ítems del RSS de TVN. Solo titulares y metadatos: no implica licencia del artículo."""
    raiz = ElementTree.fromstring(xml)
    idioma = _limpio(raiz.findtext("channel/language")) or "es"
    filas: list[Fila] = []

    for item in raiz.iter("item"):
        url = _hijo(item, "link")
        descripcion = _hijo(item, "description")
        filas.append(
            {
                "titulo": _hijo(item, "title"),
                "url": url,
                "medio": urlsplit(url or "").netloc.removeprefix("www.") or None,
                "idioma": idioma,
                "fecha_publicacion": _hijo(item, "pubDate"),
                "fecha_deteccion": None,
                "fecha_extraccion": fecha_extraccion.isoformat(),
                "origen": "tvn_rss",
                "descripcion": descripcion,
                "alcance_texto": "titular_descripcion_rss" if descripcion else "titular_metadatos",
            }
        )
    return filas


def unidad_desde_nombre(nombre: str) -> str | None:
    """El API v2 deja ``unit`` vacío; la unidad viene entre paréntesis en el nombre."""
    coincidencia = UNIDAD_ENTRE_PARENTESIS.search(nombre)
    return coincidencia.group(1) if coincidencia else None


def parsear_worldbank(texto: str, fecha_extraccion: datetime, fuente_url: str) -> list[Fila]:
    """Observaciones del Indicators API v2. ``value`` nulo se conserva nulo."""
    carga = json.loads(texto)
    if not isinstance(carga, list) or len(carga) < 2 or not isinstance(carga[1], list):
        return []

    filas: list[Fila] = []
    for obs in carga[1]:
        indicador = obs.get("indicator") or {}
        valor = obs.get("value")
        filas.append(
            {
                "pais_iso3": obs.get("countryiso3code"),
                "indicador_id": indicador.get("id"),
                "anio": obs.get("date"),
                "valor": None if valor is None else str(valor),
                "unidad": obs.get("unit") or unidad_desde_nombre(indicador.get("value", "")),
                "fuente_url": fuente_url,
                "fecha_extraccion": fecha_extraccion.isoformat(),
                "licencia": LICENCIA_BANCO_MUNDIAL,
            }
        )
    return filas


def _epoch_ms_a_iso(milisegundos: int | None) -> str | None:
    if milisegundos is None:
        return None
    return datetime.fromtimestamp(milisegundos / 1000, tz=UTC).isoformat()


def parsear_usgs(texto: str) -> list[dict[str, Any]]:
    """Sismos del servicio FDSN en GeoJSON → campos mínimos del contrato."""
    eventos: list[dict[str, Any]] = []
    for feature in json.loads(texto).get("features", []):
        props = feature.get("properties") or {}
        lon, lat, prof = (feature.get("geometry") or {}).get("coordinates", [None, None, None])
        magnitud = props.get("mag")
        eventos.append(
            {
                "id": feature.get("id"),
                "magnitude": None if magnitud is None else float(magnitud),
                "time": _epoch_ms_a_iso(props.get("time")),
                "updated": _epoch_ms_a_iso(props.get("updated")),
                "longitude": lon,
                "latitude": lat,
                "depth": prof,
                "place": props.get("place"),
                "status": props.get("status"),
                "url": props.get("url"),
            }
        )
    return eventos


IDIOMAS_GDELT = {"spanish": "es", "english": "en", "portuguese": "pt", "french": "fr"}


def parsear_gdelt(texto: str, fecha_extraccion: datetime, consulta: str) -> list[Fila]:
    """ArtList de GDELT DOC 2.0.

    ``seendate`` es la fecha de **detección** de GDELT, no la de publicación:
    se guarda en ``fecha_deteccion`` y la publicación queda nula (reto §7).
    Una respuesta de error (texto no JSON, p. ej. límite de tasa) devuelve vacío.
    """
    try:
        carga = json.loads(texto)
    except json.JSONDecodeError:
        return []
    if not isinstance(carga, dict):
        return []

    filas: list[Fila] = []
    for articulo in carga.get("articles", []):
        idioma = (articulo.get("language") or "").strip().lower()
        filas.append(
            {
                "titulo": _limpio(articulo.get("title")),
                "url": _limpio(articulo.get("url")),
                "medio": _limpio(articulo.get("domain")),
                "idioma": IDIOMAS_GDELT.get(idioma, idioma or None),
                "fecha_publicacion": None,
                "fecha_deteccion": _limpio(articulo.get("seendate")),
                "fecha_extraccion": fecha_extraccion.isoformat(),
                "origen": f"gdelt_doc:{consulta}",
                "descripcion": None,
                "alcance_texto": "titular_metadatos",
            }
        )
    return filas
