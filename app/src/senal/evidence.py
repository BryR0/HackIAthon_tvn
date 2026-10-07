"""Procedencia independiente y estado de evidencia (reto §4, CU-03).

La circulación no es confirmación: piezas que replican la misma agencia, o
titulares casi idénticos en medios distintos, cuentan como **una** procedencia.
El estado de evidencia es independiente del puntaje y no etiqueta verdad.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from senal.organize import normalizar_texto

SUBDOMINIOS_DE_PRESENTACION = ("www.", "m.", "amp.", "mobile.")
AGENCIAS = ("EFE", "AFP", "AP", "Reuters", "Europa Press", "Xinhua", "ANSA", "DPA", "Bloomberg")
_PATRON_AGENCIA = re.compile(
    r"\((?P<entre>" + "|".join(AGENCIAS) + r")\)"
    r"|^(?P<inicio>" + "|".join(a for a in AGENCIAS if a != "AP") + r")\s*[:\-–]",
    re.IGNORECASE,
)
DOMINIOS_OFICIALES = (
    ".gob.pa",
    "worldbank.org",
    "usgs.gov",
    "pancanal.com",
    "superbancos.gob.pa",
    "inec.gob.pa",
)
SIMILITUD_TITULAR_REPLICADO = 0.9


@dataclass(frozen=True)
class Pieza:
    url: str
    titulo: str
    descripcion: str | None = None


def dominio_canonico(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    for prefijo in SUBDOMINIOS_DE_PRESENTACION:
        if host.startswith(prefijo):
            return host[len(prefijo) :]
    return host


def agencia(texto: str) -> str | None:
    """Agencia citada como fuente de la pieza, en mayúsculas; ``None`` si no hay."""
    coincidencia = _PATRON_AGENCIA.search(texto)
    if coincidencia is None:
        return None
    return (coincidencia.group("entre") or coincidencia.group("inicio")).upper()


def es_fuente_oficial(url: str) -> bool:
    """Dominio exacto o subdominio real (``data.worldbank.org``); ``evilworldbank.org`` no."""
    host = (urlsplit(url).hostname or "").lower()
    return any(
        host == base or host.endswith("." + base)
        for base in (d.lstrip(".") for d in DOMINIOS_OFICIALES)
    )


def _jaccard(a: str, b: str) -> float:
    ta, tb = set(normalizar_texto(a).split()), set(normalizar_texto(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _clave(pieza: Pieza) -> str:
    citada = agencia(pieza.titulo) or agencia(pieza.descripcion or "")
    return f"agencia:{citada}" if citada else f"dominio:{dominio_canonico(pieza.url)}"


def contar_procedencias(piezas: Sequence[Pieza]) -> int:
    """Procedencias independientes: misma agencia, mismo dominio o titular replicado = una."""
    padre = list(range(len(piezas)))

    def raiz(i: int) -> int:
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    claves = [_clave(p) for p in piezas]
    for i in range(len(piezas)):
        for j in range(i + 1, len(piezas)):
            replicado = _jaccard(piezas[i].titulo, piezas[j].titulo) >= SIMILITUD_TITULAR_REPLICADO
            if claves[i] == claves[j] or replicado:
                padre[raiz(j)] = raiz(i)
    return len({raiz(i) for i in range(len(piezas))})


def estado_evidencia(procedencias: int, *, fuente_oficial: bool) -> str:
    """0 → insuficiente · 1 → parcial · ≥2 o una oficial → suficiente para el borrador."""
    if procedencias <= 0:
        return "insuficiente"
    if procedencias >= 2 or fuente_oficial:
        return "suficiente_para_borrador"
    return "parcial"
