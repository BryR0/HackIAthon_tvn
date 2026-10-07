"""Etapa 3 · Contextualizar: noticia ↔ dato oficial pertinente (reto §3, T04).

Reglas:
- Solo se enlaza si hay relación léxica explícita con el indicador; nunca se fuerza.
- Se cita el último año con valor; los nulos no se rellenan.
- Toda cifra anual lleva su año, unidad y la advertencia de que no es un dato de hoy.
- USGS solo respalda hechos sísmicos y la caja regional no es el territorio de Panamá.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from senal.catalogo import INDICADORES
from senal.ingest import Indicador, parsear_fecha
from senal.organize import normalizar_texto

PALABRAS_POR_INDICADOR: Mapping[str, tuple[str, ...]] = {
    "FP.CPI.TOTL.ZG": ("inflacion", "precios", "costo de vida", "canasta basica", "inflation"),
    "SL.UEM.TOTL.ZS": ("desempleo", "empleo", "desocupacion", "unemployment", "jobs"),
    "NY.GDP.MKTP.KD.ZG": ("pib", "crecimiento economico", "economia crece", "gdp", "recesion"),
    "NE.EXP.GNFS.ZS": ("exportaciones", "exporta", "exportadores", "exports"),
    "SP.POP.TOTL": ("poblacion", "habitantes", "censo", "population"),
    "IT.NET.USER.ZS": ("internet", "conectividad", "banda ancha", "brecha digital"),
}
PAISES_POR_NOMBRE: Mapping[str, str] = {
    "costa rica": "CRI",
    "colombia": "COL",
    "republica dominicana": "DOM",
    "mexico": "MEX",
    "guatemala": "GTM",
}
PAIS_POR_DEFECTO = "PAN"
PALABRAS_SISMICAS = ("sismo", "sismos", "temblor", "terremoto", "earthquake", "sismico")
VENTANA_SISMO = timedelta(days=2)


@dataclass(frozen=True)
class EnlaceIndicador:
    id_evidencia: str
    pais_iso3: str
    indicador_id: str
    nombre: str
    anio: int
    valor: float
    unidad: str | None
    fuente_url: str | None
    licencia: str | None
    limitacion: str


@dataclass(frozen=True)
class EnlaceSismo:
    id_evidencia: str
    id: str
    magnitude: float | None
    time: str
    place: str | None
    url: str | None
    limitacion: str


def _menciona(texto_normalizado: str, terminos: Iterable[str]) -> bool:
    relleno = f" {texto_normalizado} "
    return any(f" {t} " in relleno for t in terminos)


def _paises(texto_normalizado: str) -> list[str]:
    mencionados = [
        iso for nombre, iso in PAISES_POR_NOMBRE.items() if _menciona(texto_normalizado, [nombre])
    ]
    return [PAIS_POR_DEFECTO, *mencionados]


def _ultimo_con_valor(
    indicadores: Sequence[Indicador], pais: str, indicador_id: str
) -> Indicador | None:
    candidatos = [
        i
        for i in indicadores
        if i.pais_iso3 == pais and i.indicador_id == indicador_id and i.valor is not None
    ]
    return max(candidatos, key=lambda i: i.anio, default=None)


def enlazar_indicadores(texto: str, indicadores: Sequence[Indicador]) -> list[EnlaceIndicador]:
    normalizado = " ".join(normalizar_texto(texto).split())
    enlaces: list[EnlaceIndicador] = []
    for indicador_id, palabras in PALABRAS_POR_INDICADOR.items():
        if not _menciona(normalizado, palabras):
            continue
        for pais in _paises(normalizado):
            dato = _ultimo_con_valor(indicadores, pais, indicador_id)
            if dato is None or dato.valor is None:
                continue
            enlaces.append(
                EnlaceIndicador(
                    id_evidencia=f"WB:{pais}:{indicador_id}:{dato.anio}",
                    pais_iso3=pais,
                    indicador_id=indicador_id,
                    nombre=INDICADORES.get(indicador_id, indicador_id),
                    anio=dato.anio,
                    valor=dato.valor,
                    unidad=dato.unidad,
                    fuente_url=dato.fuente_url,
                    licencia=dato.licencia,
                    limitacion=(
                        f"Dato anual {dato.anio} del Banco Mundial "
                        f"({dato.unidad or 'sin unidad'}); "
                        "no describe la situación actual ni la fecha de la noticia."
                    ),
                )
            )
    return enlaces


def enlazar_sismos(
    texto: str, fecha: datetime, eventos: Iterable[Mapping[str, Any]]
) -> list[EnlaceSismo]:
    if not _menciona(" ".join(normalizar_texto(texto).split()), PALABRAS_SISMICAS):
        return []
    enlaces: list[EnlaceSismo] = []
    for evento in eventos:
        momento = parsear_fecha(str(evento["time"]))
        if abs(momento - fecha) > VENTANA_SISMO:
            continue
        enlaces.append(
            EnlaceSismo(
                id_evidencia=f"USGS:{evento['id']}",
                id=str(evento["id"]),
                magnitude=evento.get("magnitude"),
                time=str(evento["time"]),
                place=evento.get("place"),
                url=evento.get("url"),
                limitacion=(
                    "Evento del catálogo USGS en la caja regional lat 5–12, lon −86 a −76, "
                    "que no equivale al territorio de Panamá. Solo respalda hechos sísmicos."
                ),
            )
        )
    return enlaces
