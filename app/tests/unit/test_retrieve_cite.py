"""Recuperación híbrida, compuerta de abstención (T06) y validador de citas (T04, T09)."""

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from senal.cite import AfirmacionPropuesta, CitaPropuesta, debe_abstenerse, validar_afirmaciones
from senal.retrieve import Buscador, Evidencia

EVIDENCIAS = (
    Evidencia(
        "N-1",
        "noticia",
        {
            "titulo": "Canal de Panamá limita tránsitos a 24 diarios por sequía",
            "medio": "tvn-2.com",
        },
    ),
    Evidencia("N-2", "noticia", {"titulo": "Hoteles reportan alta ocupación en Boquete"}),
    Evidencia(
        "WB:PAN:FP.CPI.TOTL.ZG:2024",
        "indicador",
        {
            "nombre": "inflación",
            "pais_iso3": "PAN",
            "anio": "2024",
            "valor": "0.7036",
            "unidad": "annual %",
        },
    ),
    Evidencia(
        "N-3",
        "noticia",
        {
            "titulo": (
                "Exdirector de la CSS es aprehendido por supuesto enriquecimiento injustificado"
            )
        },
    ),
)


class CodificadorFalso:
    modelo = "falso"
    ejes = ("canal", "hotel", "inflaci", "css")

    def codificar(self, textos: Sequence[str], tipo: str) -> npt.NDArray[np.float32]:
        filas = []
        for t in textos:
            v = np.array([1.0 if e in t.lower() else 0.0 for e in self.ejes] + [0.1], np.float32)
            filas.append(v / np.linalg.norm(v))
        return np.vstack(filas)


def test_bm25_recupera_por_terminos_sin_modelo() -> None:
    buscador = Buscador(EVIDENCIAS, codificador=None)

    resultados = buscador.buscar("tránsitos del canal", k=2)

    assert resultados[0].id == "N-1"
    assert buscador.modo == "bm25"


def test_hibrido_fusiona_bm25_y_coseno_con_rrf() -> None:
    buscador = Buscador(EVIDENCIAS, codificador=CodificadorFalso())

    resultados = buscador.buscar("inflación de Panamá", k=3)

    assert resultados[0].id == "WB:PAN:FP.CPI.TOTL.ZG:2024"
    assert buscador.modo == "hibrido:falso"
    assert resultados[0].puntaje > resultados[-1].puntaje


def test_t06_consulta_sin_respuesta_activa_la_compuerta_de_abstencion() -> None:
    buscador = Buscador(EVIDENCIAS, codificador=None)

    assert debe_abstenerse(buscador.buscar("precio del bitcoin en Japón", k=3), umbral_bm25=0.5)
    assert not debe_abstenerse(buscador.buscar("ocupación hotelera Boquete", k=3), umbral_bm25=0.5)


def _afirmacion(texto: str, *citas: tuple[str, str], tipo: str = "hecho") -> AfirmacionPropuesta:
    return AfirmacionPropuesta(texto, tipo, tuple(CitaPropuesta(i, c) for i, c in citas))


def test_afirmacion_con_cita_valida_y_cifra_presente_se_acepta() -> None:
    resultado = validar_afirmaciones(
        [_afirmacion("El Canal limitó los tránsitos a 24 diarios.", ("N-1", "titulo"))], EVIDENCIAS
    )

    assert len(resultado.aceptadas) == 1
    assert resultado.descartadas == ()


def test_cita_a_evidencia_no_recuperada_se_descarta_entera() -> None:
    resultado = validar_afirmaciones(
        [_afirmacion("El Canal cerró.", ("N-99", "titulo"))], EVIDENCIAS
    )

    assert resultado.aceptadas == ()
    assert resultado.descartadas[0].motivo == "evidencia_no_recuperada"


def test_cifra_que_no_esta_en_el_campo_citado_se_descarta() -> None:
    resultado = validar_afirmaciones(
        [_afirmacion("El Canal limitó los tránsitos a 30 diarios.", ("N-1", "titulo"))], EVIDENCIAS
    )

    assert resultado.descartadas[0].motivo == "cifra_sin_respaldo"


def test_sin_citas_se_descarta() -> None:
    resultado = validar_afirmaciones([_afirmacion("Panamá crece mucho.")], EVIDENCIAS)

    assert resultado.descartadas[0].motivo == "sin_cita"


def test_t04_cifra_de_indicador_exige_mencionar_el_anio() -> None:
    sin_anio = _afirmacion(
        "La inflación de Panamá es 0,7%.", ("WB:PAN:FP.CPI.TOTL.ZG:2024", "valor")
    )
    con_anio = _afirmacion(
        "La inflación anual de Panamá fue 0,7% en 2024.",
        ("WB:PAN:FP.CPI.TOTL.ZG:2024", "valor"),
        ("WB:PAN:FP.CPI.TOTL.ZG:2024", "anio"),
    )

    resultado = validar_afirmaciones([sin_anio, con_anio], EVIDENCIAS)

    assert [d.motivo for d in resultado.descartadas] == ["indicador_sin_anio"]
    assert len(resultado.aceptadas) == 1


def test_acusacion_solo_se_acepta_como_declaracion_atribuida() -> None:
    como_hecho = _afirmacion(
        "El exdirector cometió enriquecimiento injustificado.", ("N-3", "titulo")
    )
    como_declaracion = _afirmacion(
        "Según el titular, el exdirector fue aprehendido por supuesto enriquecimiento.",
        ("N-3", "titulo"),
        tipo="declaracion",
    )

    resultado = validar_afirmaciones([como_hecho, como_declaracion], EVIDENCIAS)

    assert [d.motivo for d in resultado.descartadas] == ["acusacion_como_hecho"]
    assert resultado.aceptadas[0].tipo == "declaracion"


def test_campo_no_citable_se_descarta() -> None:
    resultado = validar_afirmaciones([_afirmacion("Lo publicó TVN.", ("N-1", "url"))], EVIDENCIAS)

    assert resultado.descartadas[0].motivo == "campo_no_citable"


def test_numeros_con_varios_separadores_no_rompen_el_validador() -> None:
    evidencias = (
        Evidencia(
            "N-d", "noticia", {"titulo": "Decreto 2.3.4 del 06.10.2026 fija 1.234,5 tarifas"}
        ),
    )
    textos = ["Decreto 2.3.4 publicado", "El 06.10.2026 se fijó", "Hubo 1.234,5 tarifas", "v1,2,3"]

    resultado = validar_afirmaciones(
        [_afirmacion(t, ("N-d", "titulo")) for t in textos], evidencias
    )

    assert len(resultado.aceptadas) + len(resultado.descartadas) == 4


def test_palabras_parecidas_no_cuentan_como_acusacion() -> None:
    evidencias = (
        Evidencia("N-r", "noticia", {"titulo": "Fábrica de robots y lavadoras abre en Colón"}),
    )

    resultado = validar_afirmaciones(
        [_afirmacion("Abre una fábrica de robots y lavadoras.", ("N-r", "titulo"))], evidencias
    )

    assert len(resultado.aceptadas) == 1


def test_buscador_extendido_reutiliza_vectores_y_solo_codifica_lo_nuevo() -> None:
    codificador = CodificadorFalso()
    llamadas: list[int] = []
    original = codificador.codificar

    def contar(textos: Sequence[str], tipo: str) -> npt.NDArray[np.float32]:
        llamadas.append(len(textos))
        return original(textos, tipo)

    codificador.codificar = contar  # type: ignore[method-assign]
    base = Buscador(EVIDENCIAS, codificador=codificador)
    extra = Evidencia(
        "SBP:credito_local:pesca:2024-12", "serie_sbp", {"nombre": "Crédito local SBN · Pesca"}
    )

    extendido = base.con_evidencias([extra])

    assert llamadas == [len(EVIDENCIAS), 1]
    assert len(extendido.evidencias) == len(EVIDENCIAS) + 1
    assert extendido.buscar("crédito local pesca", k=1)[0].id == extra.id
    assert extra.id not in {r.id for r in base.buscar("crédito local pesca", k=len(EVIDENCIAS))}
