"""Etapa 4 · Priorizar: puntaje de atención 0–100 (reto §4, plan §5).

Herramienta de ordenamiento, no probabilidad de verdad ni de pérdida.
Unidad: evento agrupado (cluster), así la duplicación no suma.
Referencia temporal: la fecha de corte del snapshot, nunca el reloj (ADR 0002 D5).
Cambiar cualquier constante exige subir ``RULES_VERSION`` y registrar la
decisión en Notion (ADR 0002 D7).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

from senal.organize import normalizar_texto

RULES_VERSION = "senal-1.1.0"

PESOS = {"R": 30, "I": 25, "U": 20, "N": 15, "E": 10}
BANDA_MEDIA = 40.0
BANDA_ALTA = 70.0

# R · afinidad del tema con la agenda editorial de TVN.
PESO_TEMA: Mapping[str, float] = {
    "economia": 1.0,
    "logistica_canal": 1.0,
    "servicios_publicos": 0.9,
    "eventos_naturales": 0.9,
    "regulacion": 0.8,
    "turismo": 0.7,
    "sin_tema": 0.3,
}
# I · alcance típico del tema (nacional/sectorial); nunca por tono.
ALCANCE_TEMA: Mapping[str, float] = {
    "logistica_canal": 0.8,
    "economia": 0.7,
    "servicios_publicos": 0.7,
    "eventos_naturales": 0.6,
    "regulacion": 0.6,
    "turismo": 0.5,
    "sin_tema": 0.2,
}
BONO_DATO_OFICIAL = 0.3
TAU_URGENCIA_DIAS = 7.0
PROCEDENCIAS_PARA_SATURAR = 3
BONO_FUENTE_OFICIAL = 0.2
# N · en e5 dos titulares no relacionados ya tienen coseno ≈0,75; sin escalar,
# 1 − coseno quedaría siempre cerca de 0,2 y N no discriminaría.
ESCALA_NOVEDAD = 0.25

GAZETTEER_PANAMA = (
    "panama", "panameno", "panamena", "panamenos", "chiriqui", "colon", "david", "veraguas",
    "herrera", "los santos", "cocle", "darien", "bocas del toro", "guna yala", "san miguelito",
    "arraijan", "la chorrera", "canal de panama", "css", "idaan", "mef", "asamblea nacional",
    "sinaproc", "autoridad del canal", "acp", "tocumen", "cortizo", "mulino",
)  # fmt: skip
GAZETTEER_REGION = (
    "costa rica", "colombia", "republica dominicana", "mexico", "guatemala", "centroamerica",
    "latinoamerica", "caribe", "america latina", "nicaragua", "honduras", "el salvador",
)  # fmt: skip
SUFIJOS_MEDIO_PANAMENO = (".pa",)
MEDIOS_PANAMENOS = (
    "tvn-2.com",
    "prensa.com",
    "laestrella.com.pa",
    "critica.com.pa",
    "telemetro.com",
)
NIVEL_PANAMA = 1.0
# 1.1.0: 0.8 -> 0.5. Un medio panameño que cubre un hecho internacional sin mención
# a Panamá (p. ej. drones en el mar Negro) llegaba al top 2 de la agenda.
NIVEL_MEDIO_PANAMENO = 0.5
NIVEL_REGION = 0.5


@dataclass(frozen=True)
class SenalesEvento:
    id_evento: str
    tema: str
    texto: str
    medios: tuple[str, ...]
    fecha_referencia: datetime
    dato_oficial_enlazado: bool
    procedencias_independientes: int
    fuente_oficial: bool
    novedad: float


@dataclass(frozen=True)
class Puntaje:
    id_evento: str
    r: float
    i: float
    u: float
    n: float
    e: float
    total: float
    banda: str
    version: str = RULES_VERSION
    # Prioridad ordena la revisión humana; nunca habilita publicación (T08).
    habilita_publicacion: bool = False

    def desglose(self) -> dict[str, dict[str, float]]:
        valores = {"R": self.r, "I": self.i, "U": self.u, "N": self.n, "E": self.e}
        return {
            clave: {
                "valor": round(v, 3),
                "peso": PESOS[clave],
                "aporte": round(PESOS[clave] * v, 1),
            }
            for clave, v in valores.items()
        }


def _contiene(texto: str, terminos: Iterable[str]) -> bool:
    relleno = f" {' '.join(normalizar_texto(texto).split())} "
    return any(f" {t} " in relleno for t in terminos)


def nivel_geografico(texto: str, medios: Iterable[str]) -> float:
    """1 Panamá explícito · 0.5 medio panameño o región · 0 ninguno."""
    if _contiene(texto, GAZETTEER_PANAMA):
        return NIVEL_PANAMA
    if any(m in MEDIOS_PANAMENOS or m.endswith(SUFIJOS_MEDIO_PANAMENO) for m in medios):
        return NIVEL_MEDIO_PANAMENO
    if _contiene(texto, GAZETTEER_REGION):
        return NIVEL_REGION
    return 0.0


def banda(total: float) -> str:
    if total >= BANDA_ALTA:
        return "alto"
    if total >= BANDA_MEDIA:
        return "medio"
    return "bajo"


def _acotar(valor: float) -> float:
    return max(0.0, min(1.0, valor))


def novedad(max_coseno_previo: float) -> float:
    """N a partir de la similitud máxima con eventos que empezaron antes."""
    return _acotar((1.0 - max_coseno_previo) / ESCALA_NOVEDAD)


def puntuar(senales: SenalesEvento, corte: datetime) -> Puntaje:
    tema = senales.tema if senales.tema in PESO_TEMA else "sin_tema"
    r = _acotar(nivel_geografico(senales.texto, senales.medios) * PESO_TEMA[tema])
    i = _acotar(ALCANCE_TEMA[tema] + (BONO_DATO_OFICIAL if senales.dato_oficial_enlazado else 0.0))
    edad_dias = max(0.0, (corte - senales.fecha_referencia).total_seconds() / 86_400)
    u = _acotar(math.exp(-edad_dias / TAU_URGENCIA_DIAS))
    n = _acotar(senales.novedad)
    e = _acotar(
        min(senales.procedencias_independientes, PROCEDENCIAS_PARA_SATURAR)
        / PROCEDENCIAS_PARA_SATURAR
        + (BONO_FUENTE_OFICIAL if senales.fuente_oficial else 0.0)
    )
    total = round(
        PESOS["R"] * r + PESOS["I"] * i + PESOS["U"] * u + PESOS["N"] * n + PESOS["E"] * e, 1
    )
    return Puntaje(senales.id_evento, r, i, u, n, e, total, banda(total))


def ordenar(puntajes: Iterable[Puntaje]) -> list[Puntaje]:
    """Mayor puntaje primero; empates por mayor urgencia y luego ID (reto §4)."""
    return sorted(puntajes, key=lambda p: (-p.total, -p.u, p.id_evento))
