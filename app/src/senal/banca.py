"""Modalidad bancaria (extensión, ADR 0003): contexto sectorial para un analista.

Reglas:
- El vínculo tema → sector es una tabla versionada y **siempre una hipótesis**:
  ni el LLM ni el puntaje deciden qué sector se ve afectado.
- Se cita el último mes con valor de cada sector; los nulos no se rellenan.
- Toda cifra SBP lleva su período (``MM/AAAA``) y unidad, y la advertencia de que
  no describe la situación actual ni es opinión oficial de la SBP.
- No hay score de clientes, bancos ni riesgo de crédito (reto §2, §4 CU-05, §9.1).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from senal.ingest import SerieSBP

VERSION_BANCA = "banca-1.0.0"
MODALIDADES = ("editorial", "banca")
MODALIDAD_POR_DEFECTO = "editorial"

# Tema de la bandeja → sectores SBP potencialmente relacionados (hipótesis).
SECTORES_POR_TEMA: Mapping[str, tuple[str, ...]] = {
    "logistica_canal": ("comercio", "industria"),
    "turismo": ("comercio", "consumo_personal"),
    "economia": ("total", "consumo_personal", "hipotecario"),
    "eventos_naturales": ("agricultura", "ganaderia", "pesca", "construccion"),
    "servicios_publicos": ("industria", "sector_publico"),
    "regulacion": ("act_financieras_seguros",),
}

# Horizonte de seguimiento sugerido al analista: un supuesto, no una predicción.
HORIZONTE_SEGUIMIENTO: Mapping[str, str] = {
    "logistica_canal": "corto plazo (menos de 3 meses)",
    "turismo": "corto plazo (menos de 3 meses)",
    "eventos_naturales": "corto plazo (menos de 3 meses)",
    "economia": "mediano plazo (3 a 12 meses)",
    "servicios_publicos": "mediano plazo (3 a 12 meses)",
    "regulacion": "mediano plazo (3 a 12 meses)",
}
HORIZONTE_POR_DEFECTO = "mediano plazo (3 a 12 meses)"


@dataclass(frozen=True)
class EnlaceSBP:
    id_evidencia: str
    sector: str
    nombre: str
    periodo: str
    valor: float
    unidad: str | None
    variacion_pct: float | None
    periodo_base: str | None
    pagina_pdf: int | None
    fuente_url: str | None
    relacion: str  # siempre "hipotesis"
    limitacion: str


def normalizar_modalidad(valor: str | None) -> str:
    """Lista permitida; cualquier otro valor cae a la modalidad editorial."""
    return valor if valor in MODALIDADES else MODALIDAD_POR_DEFECTO


def es_tema_bancario(tema: str) -> bool:
    return tema in SECTORES_POR_TEMA


def periodo_texto(periodo: str) -> str:
    """``2024-12`` → ``12/2024``: la forma que el texto debe usar al citar."""
    return f"{periodo[5:7]}/{periodo[:4]}"


def horizonte_seguimiento(tema: str) -> str:
    return HORIZONTE_SEGUIMIENTO.get(tema, HORIZONTE_POR_DEFECTO)


def _ultima_con_valor(series: Iterable[SerieSBP], sector: str) -> SerieSBP | None:
    candidatas = [s for s in series if s.sector == sector and s.valor is not None]
    return max(candidatas, key=lambda s: s.periodo, default=None)


def enlazar_sbp(tema: str, series: Iterable[SerieSBP]) -> tuple[EnlaceSBP, ...]:
    """Series SBP del último mes con dato para los sectores mapeados al tema."""
    disponibles = tuple(series)
    enlaces: list[EnlaceSBP] = []
    for sector in SECTORES_POR_TEMA.get(tema, ()):
        serie = _ultima_con_valor(disponibles, sector)
        if serie is None or serie.valor is None:
            continue
        enlaces.append(
            EnlaceSBP(
                id_evidencia=serie.id_evidencia,
                sector=sector,
                nombre=serie.nombre,
                periodo=serie.periodo,
                valor=serie.valor,
                unidad=serie.unidad,
                variacion_pct=serie.variacion_pct,
                periodo_base=serie.periodo_base,
                pagina_pdf=serie.pagina_pdf,
                fuente_url=serie.fuente_url,
                relacion="hipotesis",
                limitacion=(
                    f"Saldo mensual agregado a {periodo_texto(serie.periodo)} "
                    f"({serie.unidad or 'sin unidad'}) del Informe de Actividad Bancaria de la "
                    "SBP; no describe la situación actual ni la fecha de la noticia. La relación "
                    "con el tema es una hipótesis del equipo, no una opinión de la SBP."
                ),
            )
        )
    return tuple(enlaces)
