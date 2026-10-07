"""Embeddings multilingües en proceso (ADR 0002 D2).

Un solo modelo para documentos, prototipos y consultas. Los pesos se cachean
localmente al primer uso, así la demo funciona sin red. Si el modelo no carga,
``cargar_codificador`` devuelve ``None`` y quien llama degrada a BM25/palabras
clave, rotulándolo (idea tomada de ``docversion``: fallar con ``None``, no lanzar).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from typing import Literal, Protocol

import numpy as np
import numpy.typing as npt

log = logging.getLogger(__name__)

MODELO_POR_DEFECTO = "intfloat/multilingual-e5-small"
TAMANO_LOTE = 64

TipoTexto = Literal["query", "passage"]
Matriz = npt.NDArray[np.float32]


class Codificador(Protocol):
    modelo: str

    def codificar(self, textos: Sequence[str], tipo: TipoTexto) -> Matriz: ...


class CodificadorE5:
    """``multilingual-e5`` exige prefijos ``query:``/``passage:``; vectores normalizados L2."""

    def __init__(self, modelo: str = MODELO_POR_DEFECTO) -> None:
        from sentence_transformers import SentenceTransformer

        self.modelo = modelo
        self._st = SentenceTransformer(modelo)

    def codificar(self, textos: Sequence[str], tipo: TipoTexto) -> Matriz:
        if not textos:
            return np.zeros((0, 0), dtype=np.float32)
        prefijados = [f"{tipo}: {t}" for t in textos]
        vectores = self._st.encode(
            prefijados, batch_size=TAMANO_LOTE, normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vectores, dtype=np.float32)


def cargar_codificador() -> Codificador | None:
    """Carga el modelo de ``SENAL_MODELO_EMBEDDINGS``; ``None`` si no está disponible."""
    modelo = os.environ.get("SENAL_MODELO_EMBEDDINGS", MODELO_POR_DEFECTO)
    try:
        return CodificadorE5(modelo)
    except Exception:  # noqa: BLE001 - cualquier fallo de carga degrada, no tumba la app
        log.exception("No se pudo cargar el modelo de embeddings %s; se usa BM25", modelo)
        return None


def coseno(a: npt.NDArray[np.floating], b: npt.NDArray[np.floating]) -> float:
    """Similitud coseno; 0.0 ante dimensión distinta o norma cero."""
    if a.shape != b.shape:
        return 0.0
    norma = float(np.linalg.norm(a) * np.linalg.norm(b))
    if norma == 0.0:
        return 0.0
    return float(np.dot(a, b) / norma)
