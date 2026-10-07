"""Etapa 2 · Organizar: clasificación temática y agrupación de eventos.

- Baseline (§8 del reto): reglas de palabras clave.
- IA: prototipos por tema sobre embeddings multilingües, con abstención por
  umbral y margen: si no hay tema claro se devuelve ``SIN_TEMA``; no se fuerza.
- Agrupación: enlace promedio sobre similitud coseno dentro de una ventana temporal,
  para que tres copias del mismo hecho cuenten como un evento (T02).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from senal.embed import Codificador, Matriz

SIN_TEMA = "sin_tema"

TEMAS = {
    "economia": "Economía",
    "logistica_canal": "Logística / Canal",
    "turismo": "Turismo",
    "servicios_publicos": "Servicios públicos",
    "eventos_naturales": "Eventos naturales",
    "regulacion": "Regulación",
}

PALABRAS_CLAVE: Mapping[str, tuple[str, ...]] = {
    "economia": (
        "economia", "inflacion", "pib", "empleo", "desempleo", "precios", "salario",
        "deuda", "fiscal", "impuesto", "mef", "inversion", "economy", "inflation",
    ),
    "logistica_canal": (
        "canal", "transito", "transitos", "buque", "buques", "puerto", "puertos",
        "naviera", "contenedor", "logistica", "esclusa", "calado", "shipping",
    ),
    "turismo": (
        "turismo", "turista", "turistas", "hotel", "hoteles", "visitantes", "aerolinea",
        "vuelos", "crucero", "atp", "tourism", "tourist",
    ),
    "servicios_publicos": (
        "agua", "idaan", "electricidad", "energia", "apagon", "css", "salud", "hospital",
        "transporte", "metro", "basura", "educacion", "meduca", "acueducto",
    ),
    "eventos_naturales": (
        "sismo", "terremoto", "temblor", "inundacion", "inundaciones", "lluvia", "lluvias",
        "sequia", "tormenta", "deslizamiento", "sinaproc", "earthquake", "flood",
    ),
    "regulacion": (
        "ley", "decreto", "regulacion", "resolucion", "asamblea", "reglamento", "norma",
        "superintendencia", "gaceta", "proyecto de ley", "regulation",
    ),
}  # fmt: skip

# Ejemplares por tema, sin "Panamá": el topónimo común dominaba la similitud y
# borraba el margen entre temas (calibración 2026-10-06 con 3049 titulares reales).
PROTOTIPOS: Mapping[str, tuple[str, ...]] = {
    "economia": (
        "inflación y precios", "crecimiento económico del PIB", "desempleo y empleo",
        "deuda pública y presupuesto del Estado", "inversión extranjera y comercio",
        "economy inflation GDP",
    ),
    "logistica_canal": (
        "tránsitos de buques por el Canal", "puertos y contenedores",
        "navieras y transporte marítimo", "esclusas y calado del Canal",
        "shipping canal transits ports",
    ),
    "turismo": (
        "llegada de turistas y visitantes", "ocupación hotelera", "vuelos y aerolíneas",
        "cruceros y destinos turísticos", "tourism travel hotels",
    ),
    "servicios_publicos": (
        "suministro de agua potable", "cortes de electricidad",
        "hospitales y Caja de Seguro Social", "transporte público y metro",
        "recolección de basura", "escuelas y educación pública",
    ),
    "eventos_naturales": (
        "sismo o terremoto", "lluvias e inundaciones", "sequía y falta de lluvia",
        "deslizamientos y tormentas", "earthquake flood storm",
    ),
    "regulacion": (
        "nueva ley aprobada por la Asamblea", "decreto ejecutivo",
        "resolución de la superintendencia", "reglamento y normativa",
        "regulation law decree",
    ),
}  # fmt: skip

# Valores iniciales; se calibran con evals/eval_organize.py sobre el set etiquetado.
UMBRAL_TEMA = 0.80
MARGEN_TEMA = 0.01


@dataclass(frozen=True)
class Documento:
    id: str
    texto: str
    fecha: datetime


@dataclass(frozen=True)
class Clasificacion:
    tema: str
    puntaje: float
    margen: float
    metodo: str


def normalizar_texto(texto: str) -> str:
    """Minúsculas sin acentos ni signos, para reglas léxicas."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", sin_acentos.lower())


def clasificar_por_palabras(texto: str) -> str:
    """Baseline: tema con más coincidencias de palabras clave; empate o cero → ``SIN_TEMA``."""
    tokens = f" {' '.join(normalizar_texto(texto).split())} "
    conteos = {
        tema: sum(f" {palabra} " in tokens for palabra in palabras)
        for tema, palabras in PALABRAS_CLAVE.items()
    }
    mejor = max(conteos.values())
    ganadores = [tema for tema, n in conteos.items() if n == mejor]
    return ganadores[0] if mejor > 0 and len(ganadores) == 1 else SIN_TEMA


class ClasificadorPrototipos:
    """Vecino más cercano entre ejemplares por tema; abstención por umbral y margen."""

    def __init__(
        self,
        codificador: Codificador,
        prototipos: Mapping[str, Sequence[str]] = PROTOTIPOS,
        *,
        umbral: float = UMBRAL_TEMA,
        margen: float = MARGEN_TEMA,
    ) -> None:
        self._codificador = codificador
        self._temas = tuple(prototipos)
        self._umbral = umbral
        self._margen = margen
        self._ejemplares = [
            codificador.codificar(list(textos), "passage") for textos in prototipos.values()
        ]

    @property
    def metodo(self) -> str:
        return f"prototipos:{self._codificador.modelo}"

    def clasificar_vectores(self, vectores: Matriz) -> list[Clasificacion]:
        similitudes = np.stack([(vectores @ m.T).max(axis=1) for m in self._ejemplares], axis=1)
        resultado: list[Clasificacion] = []
        for fila in similitudes:
            orden = np.argsort(fila)[::-1]
            mejor = float(fila[orden[0]])
            segundo = float(fila[orden[1]]) if len(orden) > 1 else 0.0
            margen = mejor - segundo
            tema = self._temas[int(orden[0])]
            if mejor < self._umbral or margen < self._margen:
                tema = SIN_TEMA
            resultado.append(Clasificacion(tema, mejor, margen, self.metodo))
        return resultado

    def clasificar(self, textos: Sequence[str]) -> list[Clasificacion]:
        return self.clasificar_vectores(self._codificador.codificar(textos, "passage"))


def agrupar_eventos(
    documentos: Sequence[Documento], vectores: Matriz, *, umbral: float, ventana_dias: float
) -> tuple[tuple[str, ...], ...]:
    """Clusters de IDs ordenados por enlace **promedio** (no encadena eventos distintos).

    Distancia = 1 − coseno; documentos fuera de la ventana temporal quedan a distancia 1.
    """
    n = len(documentos)
    if n < 2:
        return tuple((d.id,) for d in documentos)
    marcas = np.array([d.fecha.timestamp() for d in documentos])
    distancias = np.clip(1.0 - (vectores @ vectores.T), 0.0, 1.0).astype(np.float64)
    distancias[np.abs(marcas[:, None] - marcas[None, :]) > ventana_dias * 86_400] = 1.0
    np.fill_diagonal(distancias, 0.0)
    etiquetas = AgglomerativeClustering(
        n_clusters=None,
        metric="precomputed",
        linkage="average",
        distance_threshold=1.0 - umbral,
    ).fit_predict(distancias)

    grupos: dict[int, list[str]] = {}
    for etiqueta, documento in zip(etiquetas, documentos, strict=True):
        grupos.setdefault(int(etiqueta), []).append(documento.id)
    return tuple(sorted(tuple(sorted(ids)) for ids in grupos.values()))


UMBRAL_EVENTO = 0.90
VENTANA_EVENTO_DIAS = 3.0
