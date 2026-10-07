"""Extracción de red → ``data/raw/`` (Paso 1).

Solo se usa si el organizador no entrega el snapshot común (ADR 0002 D6).
Guarda cada respuesta tal cual y un registro ``extraccion.json`` con URL,
parámetros, estado HTTP y SHA-256 para reproducibilidad. Una fuente que falla
queda registrada; nunca aborta las demás.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from senal import catalogo

log = logging.getLogger(__name__)

AGENTE = "senal-hackiathon/0.1 (+https://github.com/BryR0/HackIAthon)"
TIEMPO_ESPERA_SEGUNDOS = 60.0
FORMATO_GDELT = "%Y%m%d%H%M%S"


@dataclass(frozen=True)
class Solicitud:
    fuente: str
    url: str
    params: Mapping[str, str]
    estado: int | None
    archivo: str | None
    sha256: str | None
    error: str | None = None


def tramos(desde: datetime, hasta: datetime, dias: int) -> list[tuple[datetime, datetime]]:
    """Divide ``[desde, hasta)`` en tramos contiguos de a lo sumo ``dias``."""
    resultado: list[tuple[datetime, datetime]] = []
    inicio = desde
    while inicio < hasta:
        fin = min(inicio + timedelta(days=dias), hasta)
        resultado.append((inicio, fin))
        inicio = fin
    return resultado


def obtener_con_reintentos(
    cliente: httpx.Client,
    url: str,
    params: Mapping[str, str],
    *,
    intentos: int = 4,
    espera_base: float = catalogo.GDELT_PAUSA_SEGUNDOS,
    dormir: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    """GET con backoff exponencial ante 429/5xx. Devuelve la última respuesta, sin lanzar."""
    respuesta = cliente.get(url, params=dict(params))
    for intento in range(1, intentos):
        if respuesta.status_code != 429 and respuesta.status_code < 500:
            break
        dormir(espera_base * 2 ** (intento - 1))
        respuesta = cliente.get(url, params=dict(params))
    return respuesta


def _guardar(destino: Path, nombre: str, contenido: bytes) -> str:
    ruta = destino / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)
    return hashlib.sha256(contenido).hexdigest()


def _solicitar(
    cliente: httpx.Client,
    destino: Path,
    fuente: str,
    url: str,
    params: Mapping[str, str],
    archivo: str,
) -> Solicitud:
    try:
        respuesta = obtener_con_reintentos(cliente, url, params)
    except httpx.HTTPError as error:
        log.warning("Fallo de red en %s: %s", fuente, error)
        return Solicitud(fuente, url, params, None, None, None, type(error).__name__)

    if respuesta.status_code != 200:
        log.warning("%s respondió %s", fuente, respuesta.status_code)
        return Solicitud(fuente, url, params, respuesta.status_code, None, None, "estado_http")

    digesto = _guardar(destino, archivo, respuesta.content)
    return Solicitud(fuente, url, params, 200, archivo, digesto)


def _extraer_gdelt(
    cliente: httpx.Client, destino: Path, corte: datetime, dormir: Callable[[float], None]
) -> list[Solicitud]:
    desde = corte - timedelta(days=catalogo.VENTANA_NOTICIAS_DIAS)
    solicitudes: list[Solicitud] = []
    for clave, consulta in catalogo.GDELT_CONSULTAS.items():
        for inicio, fin in tramos(desde, corte, catalogo.TRAMO_GDELT_DIAS):
            params = {
                "query": consulta,
                "mode": "ArtList",
                "format": "json",
                "maxrecords": str(catalogo.GDELT_MAX_REGISTROS),
                "startdatetime": inicio.strftime(FORMATO_GDELT),
                "enddatetime": fin.strftime(FORMATO_GDELT),
            }
            archivo = f"gdelt_{clave}_{inicio:%Y%m%d}.json"
            solicitudes.append(
                _solicitar(
                    cliente, destino, f"gdelt:{clave}", catalogo.GDELT_DOC_URL, params, archivo
                )
            )
            dormir(catalogo.GDELT_PAUSA_SEGUNDOS)
    return solicitudes


def _extraer_worldbank(cliente: httpx.Client, destino: Path) -> list[Solicitud]:
    paises = ";".join(catalogo.PAISES)
    anios = f"{catalogo.ANIOS.start}:{catalogo.ANIOS.stop - 1}"
    return [
        _solicitar(
            cliente,
            destino,
            f"worldbank:{indicador}",
            catalogo.WORLDBANK_URL.format(paises=paises, indicador=indicador),
            {"date": anios, "format": "json", "per_page": "1000"},
            f"worldbank_{indicador}.json",
        )
        for indicador in catalogo.INDICADORES
    ]


def _extraer_sbp(cliente: httpx.Client, destino: Path) -> list[Solicitud]:
    """Fuente D: un PDF por mes; los PDFs quedan en ``raw/sbp/`` y fuera de git (ADR 0003)."""
    anio = catalogo.SBP_ANIO % 100
    return [
        _solicitar(
            cliente,
            destino,
            f"sbp:{catalogo.SBP_ANIO}-{mes:02d}",
            catalogo.SBP_IAB_URL.format(mes=mes, anio=anio),
            {},
            f"sbp/IAB-{mes:02d}{anio:02d}.pdf",
        )
        for mes in catalogo.SBP_MESES
    ]


def _cliente(transporte: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": AGENTE},
        timeout=TIEMPO_ESPERA_SEGUNDOS,
        follow_redirects=True,
        transport=transporte,
    )


def _escribir_registro(destino: Path, registro: Mapping[str, object]) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "extraccion.json").write_text(
        json.dumps(registro, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def agregar_sbp(
    destino: Path, *, transporte: httpx.BaseTransport | None = None
) -> dict[str, object]:
    """Descarga solo la fuente D y la agrega a un ``extraccion.json`` existente.

    No vuelve a pedir noticias: el corpus editorial y su fecha de corte no cambian.
    Una corrida previa de SBP se reemplaza, no se duplica.
    """
    registro: dict[str, object] = json.loads((destino / "extraccion.json").read_text("utf-8"))
    previas = registro["solicitudes"]
    assert isinstance(previas, list)
    with _cliente(transporte) as cliente:
        nuevas = [asdict(s) for s in _extraer_sbp(cliente, destino)]
    registro = {
        **registro,
        "solicitudes": [s for s in previas if not str(s["fuente"]).startswith("sbp:")] + nuevas,
    }
    _escribir_registro(destino, registro)
    return registro


def extraer_todo(
    destino: Path,
    corte: datetime | None = None,
    *,
    incluir_gdelt: bool = True,
    incluir_sbp: bool = True,
    dormir: Callable[[float], None] = time.sleep,
) -> dict[str, object]:
    """Descarga todas las fuentes y escribe ``extraccion.json``. Devuelve el registro."""
    corte = (corte or datetime.now(UTC)).replace(microsecond=0)
    with _cliente() as cliente:
        solicitudes = [
            _solicitar(cliente, destino, "tvn_rss", catalogo.TVN_RSS_URL, {}, "tvn_rss.xml"),
            *_extraer_worldbank(cliente, destino),
            _solicitar(
                cliente,
                destino,
                "usgs",
                catalogo.USGS_URL,
                catalogo.USGS_PARAMETROS,
                "usgs_2024.geojson",
            ),
        ]
        if incluir_sbp:
            solicitudes.extend(_extraer_sbp(cliente, destino))
        if incluir_gdelt:
            solicitudes.extend(_extraer_gdelt(cliente, destino, corte, dormir))

    registro: dict[str, object] = {
        "version": catalogo.VERSION_PAQUETE,
        "fecha_corte_utc": corte.isoformat(),
        "solicitudes": [asdict(s) for s in solicitudes],
    }
    _escribir_registro(destino, registro)
    return registro
