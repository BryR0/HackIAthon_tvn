"""Recuperación híbrida: BM25 (baseline) + coseno sobre embeddings, fusionados con RRF.

Sin base vectorial: a ~300 evidencias el cálculo exhaustivo tarda milisegundos.
Si no hay modelo, opera en modo ``bm25`` y la interfaz lo rotula.
La fusión RRF (k=60) es la misma idea que ``docversion`` aplica en SQL.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from senal.embed import Codificador
from senal.organize import normalizar_texto

K_RRF = 60
BM25_K1 = 1.5
BM25_B = 0.75
CAMPOS_NO_INDEXADOS = frozenset({"url", "fuente_url"})
STOPWORDS = frozenset(
    "a al algo ante con contra cual cuando de del desde donde el ella en entre es esta este "
    "fue ha hay la las lo los mas me mi muy no o para pero por que quien se segun sin sobre "
    "su sus te un una uno unos y ya cuanto cuantos cuantas cual cuales como "
    "the of in and to".split()
)


@dataclass(frozen=True)
class Evidencia:
    id: str
    tipo: str
    campos: Mapping[str, str]

    @property
    def texto(self) -> str:
        return " ".join(v for k, v in self.campos.items() if k not in CAMPOS_NO_INDEXADOS and v)


@dataclass(frozen=True)
class Resultado:
    id: str
    puntaje: float
    bm25: float
    coseno: float | None
    evidencia: Evidencia


def _raiz(token: str) -> str:
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def tokenizar(texto: str) -> list[str]:
    return [_raiz(t) for t in normalizar_texto(texto).split() if t not in STOPWORDS]


class _BM25:
    def __init__(self, documentos: Sequence[list[str]]) -> None:
        self._docs = [Counter(d) for d in documentos]
        self._largos = [len(d) for d in documentos]
        self._promedio = (sum(self._largos) / len(self._largos)) if self._largos else 0.0
        frecuencia: Counter[str] = Counter()
        for doc in documentos:
            frecuencia.update(set(doc))
        n = len(documentos)
        self._idf = {t: math.log((n - df + 0.5) / (df + 0.5) + 1) for t, df in frecuencia.items()}

    def puntuar(self, consulta: list[str]) -> list[float]:
        puntajes: list[float] = []
        for doc, largo in zip(self._docs, self._largos, strict=True):
            total = 0.0
            for termino in consulta:
                tf = doc.get(termino, 0)
                if tf == 0:
                    continue
                norma = BM25_K1 * (1 - BM25_B + BM25_B * largo / (self._promedio or 1))
                total += self._idf[termino] * tf * (BM25_K1 + 1) / (tf + norma)
            puntajes.append(total)
        return puntajes


class Buscador:
    def __init__(
        self,
        evidencias: Sequence[Evidencia],
        codificador: Codificador | None,
        *,
        vectores: npt.NDArray[np.float32] | None = None,
    ) -> None:
        if vectores is not None and codificador is None:
            raise ValueError("vectores precalculados requieren el codificador que los produjo")
        self._evidencias = tuple(evidencias)
        self._bm25 = _BM25([tokenizar(e.texto) for e in self._evidencias])
        self._codificador = codificador
        self._vectores = (
            vectores
            if vectores is not None
            else codificador.codificar([e.texto for e in self._evidencias], "passage")
            if codificador is not None and self._evidencias
            else None
        )

    def con_evidencias(self, extra: Sequence[Evidencia]) -> Buscador:
        """Nuevo buscador con evidencias adicionales (p. ej. series SBP de la modalidad
        bancaria). Reutiliza los vectores ya calculados y solo codifica lo nuevo; el
        buscador original no cambia."""
        vectores = self._vectores
        if self._codificador is not None and vectores is not None and extra:
            nuevos = self._codificador.codificar([e.texto for e in extra], "passage")
            vectores = np.vstack([vectores, nuevos])
        return Buscador([*self._evidencias, *extra], self._codificador, vectores=vectores)

    @property
    def modo(self) -> str:
        return "bm25" if self._codificador is None else f"hibrido:{self._codificador.modelo}"

    @property
    def evidencias(self) -> tuple[Evidencia, ...]:
        return self._evidencias

    def buscar(self, consulta: str, k: int = 8) -> list[Resultado]:
        if not self._evidencias:
            return []
        bm25 = self._bm25.puntuar(tokenizar(consulta))
        cosenos: list[float] | None = None
        if self._codificador is not None and self._vectores is not None:
            q = self._codificador.codificar([consulta], "query")[0]
            cosenos = [float(x) for x in self._vectores @ q]

        fusion = self._fusionar(bm25, cosenos)
        orden = sorted(
            range(len(self._evidencias)), key=lambda i: (-fusion[i], self._evidencias[i].id)
        )
        return [
            Resultado(
                id=self._evidencias[i].id,
                puntaje=fusion[i],
                bm25=bm25[i],
                coseno=None if cosenos is None else cosenos[i],
                evidencia=self._evidencias[i],
            )
            for i in orden[:k]
        ]

    @staticmethod
    def _fusionar(bm25: list[float], cosenos: list[float] | None) -> list[float]:
        if cosenos is None:
            return bm25
        fusion = [0.0] * len(bm25)
        for puntajes, exige_positivo in ((bm25, True), (cosenos, False)):
            rangos = np.argsort(-np.asarray(puntajes), kind="stable")
            for posicion, i in enumerate(rangos, start=1):
                if exige_positivo and puntajes[i] <= 0:
                    continue
                fusion[i] += 1 / (K_RRF + posicion)
        return fusion
