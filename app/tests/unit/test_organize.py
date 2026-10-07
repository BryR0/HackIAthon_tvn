"""Etapa 2 · Organizar: baseline, clasificación por prototipos y agrupación de eventos (T02)."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import numpy as np
import numpy.typing as npt

from senal.embed import coseno
from senal.organize import (
    SIN_TEMA,
    ClasificadorPrototipos,
    Documento,
    agrupar_eventos,
    clasificar_por_palabras,
)

# Ejes del espacio falso: 0=economía 1=canal 2=turismo 3=ruido
VECTORES = {
    "economia": [1.0, 0.0, 0.0, 0.0],
    "canal": [0.0, 1.0, 0.0, 0.0],
    "turismo": [0.0, 0.0, 1.0, 0.0],
    "ambiguo": [0.6, 0.6, 0.0, 0.0],
    "ruido": [0.0, 0.0, 0.0, 1.0],
}


class CodificadorFalso:
    modelo = "falso-v1"

    def codificar(self, textos: Sequence[str], tipo: str) -> npt.NDArray[np.float32]:
        filas = []
        for texto in textos:
            clave = next((k for k in VECTORES if k in texto), "ruido")
            vector = np.array(VECTORES[clave], dtype=np.float32)
            filas.append(vector / np.linalg.norm(vector))
        return np.vstack(filas)


PROTOTIPOS = {
    "economia": ["economia inflación"],
    "logistica_canal": ["canal tránsitos"],
    "turismo": ["turismo visitantes"],
}


def test_coseno_con_guardas_de_dimension_y_norma_cero() -> None:
    assert coseno(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == 1.0
    assert coseno(np.array([0.0, 0.0]), np.array([1.0, 0.0])) == 0.0
    assert coseno(np.array([1.0, 0.0]), np.array([1.0, 0.0, 0.0])) == 0.0


def test_baseline_por_palabras_clave_reconoce_temas_y_no_fuerza() -> None:
    assert clasificar_por_palabras("Canal de Panamá reduce tránsitos por sequía") == (
        "logistica_canal"
    )
    assert clasificar_por_palabras("Inflación en Panamá sube 2%") == "economia"
    assert clasificar_por_palabras("Selección gana partido amistoso") == SIN_TEMA


def test_prototipos_asignan_el_tema_mas_cercano_con_puntaje() -> None:
    clasificador = ClasificadorPrototipos(CodificadorFalso(), PROTOTIPOS)

    resultado = clasificador.clasificar(["noticia de economia", "noticia del canal"])

    assert [r.tema for r in resultado] == ["economia", "logistica_canal"]
    assert all(r.puntaje > 0.99 for r in resultado)
    assert all(r.metodo == "prototipos:falso-v1" for r in resultado)


def test_prototipos_se_abstienen_con_baja_similitud_o_margen_estrecho() -> None:
    clasificador = ClasificadorPrototipos(CodificadorFalso(), PROTOTIPOS, umbral=0.5, margen=0.1)

    resultado = clasificador.clasificar(["texto ruido", "caso ambiguo"])

    assert [r.tema for r in resultado] == [SIN_TEMA, SIN_TEMA]


T0 = datetime(2026, 9, 1, tzinfo=UTC)


def _doc(id_: str, texto: str, dias: int = 0) -> Documento:
    return Documento(id=id_, texto=texto, fecha=T0 + timedelta(days=dias))


def test_t02_tres_registros_del_mismo_evento_forman_un_solo_cluster() -> None:
    docs = [
        _doc("N-3", "canal reduce calado"),
        _doc("N-1", "canal anuncia restricción"),
        _doc("N-2", "canal limita buques", dias=1),
        _doc("N-9", "turismo crece"),
    ]
    vectores = CodificadorFalso().codificar([d.texto for d in docs], "passage")

    clusters = agrupar_eventos(docs, vectores, umbral=0.9, ventana_dias=3)

    assert clusters == (("N-1", "N-2", "N-3"), ("N-9",))


def test_mismo_tema_fuera_de_la_ventana_temporal_no_se_agrupa() -> None:
    docs = [_doc("N-1", "canal restricción"), _doc("N-2", "canal restricción", dias=30)]
    vectores = CodificadorFalso().codificar([d.texto for d in docs], "passage")

    clusters = agrupar_eventos(docs, vectores, umbral=0.9, ventana_dias=3)

    assert clusters == (("N-1",), ("N-2",))
