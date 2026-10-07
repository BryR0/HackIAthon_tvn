"""Contradicciones dentro de un evento (reto CU-04, T05).

Determinista: extrae cifras con unidad y marca la unidad cuando las fuentes
dan valores distintos. No escoge una versión: muestra todas como
``revision_pendiente``. La persona revisora decide.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

UNIDADES: dict[str, str] = {
    "%": "%",
    "por ciento": "%",
    "muertos": "muertos",
    "muertes": "muertos",
    "fallecidos": "muertos",
    "heridos": "heridos",
    "lesionados": "heridos",
    "desaparecidos": "desaparecidos",
    "familias": "familias",
    "personas": "personas",
    "viviendas": "viviendas",
    "millones": "millones",
    "transitos": "tránsitos",
    "tránsitos": "tránsitos",
    "buques": "buques",
}
_PATRON = re.compile(
    r"(?P<num>\d{1,3}(?:\.\d{3})+|\d+(?:[.,]\d+)?)\s*(?P<unidad>"
    + "|".join(sorted(map(re.escape, UNIDADES), key=len, reverse=True))
    + r")",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Afirmacion:
    id_fuente: str
    texto: str


@dataclass(frozen=True)
class Version:
    id_fuente: str
    valor: float
    fragmento: str


@dataclass(frozen=True)
class Contradiccion:
    unidad: str
    versiones: tuple[Version, ...]
    estado: str = "revision_pendiente"


def normalizar_numero(texto: str) -> float:
    """``1.350`` → 1350 (miles es-PA); ``2,5`` y ``2.5`` → 2.5."""
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", texto):
        return float(texto.replace(".", ""))
    return float(texto.replace(",", "."))


def extraer_cifras(afirmacion: Afirmacion) -> list[tuple[str, Version]]:
    cifras: list[tuple[str, Version]] = []
    for m in _PATRON.finditer(afirmacion.texto):
        unidad = UNIDADES[m.group("unidad").lower()]
        cifras.append(
            (unidad, Version(afirmacion.id_fuente, normalizar_numero(m.group("num")), m.group(0)))
        )
    return cifras


def detectar_contradicciones(afirmaciones: Sequence[Afirmacion]) -> list[Contradiccion]:
    por_unidad: dict[str, list[Version]] = {}
    for afirmacion in afirmaciones:
        for unidad, version in extraer_cifras(afirmacion):
            por_unidad.setdefault(unidad, []).append(version)

    return [
        Contradiccion(unidad, tuple(versiones))
        for unidad, versiones in sorted(por_unidad.items())
        if len({round(v.valor, 3) for v in versiones}) > 1
    ]
