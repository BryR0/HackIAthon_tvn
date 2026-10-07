"""Etapa 3 · Contextualizar (T04) y contradicciones dentro de un evento (T05)."""

from datetime import UTC, datetime

from senal.context import enlazar_indicadores, enlazar_sismos
from senal.contradict import Afirmacion, detectar_contradicciones
from senal.ingest import Indicador

CORTE = datetime(2026, 10, 6, tzinfo=UTC)


def _ind(indicador: str, anio: int, valor: float | None, pais: str = "PAN") -> Indicador:
    return Indicador(
        pais, indicador, anio, valor, "annual %", "https://api.worldbank.org/x", CORTE, "CC BY 4.0"
    )


INDICADORES = (
    _ind("FP.CPI.TOTL.ZG", 2023, 1.5),
    _ind("FP.CPI.TOTL.ZG", 2024, 0.7),
    _ind("FP.CPI.TOTL.ZG", 2024, None, pais="CRI"),
    _ind("SL.UEM.TOTL.ZS", 2024, None),
    _ind("SL.UEM.TOTL.ZS", 2023, 7.4),
)


def test_t04_enlace_conserva_pais_anio_unidad_y_advierte_que_no_es_dato_de_hoy() -> None:
    enlaces = enlazar_indicadores("Inflación en Panamá preocupa a comerciantes", INDICADORES)

    assert len(enlaces) == 1
    enlace = enlaces[0]
    assert (enlace.pais_iso3, enlace.indicador_id, enlace.anio) == ("PAN", "FP.CPI.TOTL.ZG", 2024)
    assert enlace.valor == 0.7
    assert enlace.unidad == "annual %"
    assert "2024" in enlace.limitacion
    assert "no describe la situación actual" in enlace.limitacion


def test_usa_el_ultimo_anio_con_valor_y_no_rellena_nulos() -> None:
    enlace = enlazar_indicadores("Sube el desempleo", INDICADORES)[0]

    assert enlace.anio == 2023
    assert enlace.valor == 7.4


def test_sin_relacion_sustentada_no_se_fuerza_enlace() -> None:
    assert enlazar_indicadores("Festival de cine en Boquete", INDICADORES) == []


SISMO = {
    "id": "us6000x",
    "magnitude": 4.6,
    "time": "2024-03-10T05:00:00+00:00",
    "place": "40 km S of Punta de Burica, Panama",
    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us6000x",
}


def test_sismo_solo_se_enlaza_a_noticias_sismicas_cercanas_en_el_tiempo() -> None:
    fecha = datetime(2024, 3, 10, 12, tzinfo=UTC)

    assert [s.id for s in enlazar_sismos("Fuerte sismo sacude Chiriquí", fecha, [SISMO])] == [
        "us6000x"
    ]
    assert enlazar_sismos("Inundaciones en Chiriquí", fecha, [SISMO]) == []
    lejos = datetime(2026, 9, 1, tzinfo=UTC)
    assert enlazar_sismos("Fuerte sismo sacude Chiriquí", lejos, [SISMO]) == []


def test_enlace_sismico_advierte_que_la_caja_no_es_panama() -> None:
    fecha = datetime(2024, 3, 10, tzinfo=UTC)

    enlace = enlazar_sismos("Temblor en el occidente", fecha, [SISMO])[0]

    assert "no equivale al territorio de Panamá" in enlace.limitacion


def test_t05_dos_cifras_incompatibles_se_muestran_ambas_sin_escoger() -> None:
    afirmaciones = [
        Afirmacion("N-1", "Lluvias dejan 3 muertos en Colón"),
        Afirmacion("N-2", "Cifra oficial: 5 muertos por lluvias en Colón"),
        Afirmacion("N-3", "Lluvias afectan a 200 familias en Colón"),
    ]

    contradicciones = detectar_contradicciones(afirmaciones)

    assert len(contradicciones) == 1
    c = contradicciones[0]
    assert c.unidad == "muertos"
    assert sorted(v.valor for v in c.versiones) == [3.0, 5.0]
    assert c.estado == "revision_pendiente"


def test_misma_cifra_en_varias_fuentes_no_es_contradiccion() -> None:
    afirmaciones = [
        Afirmacion("N-1", "Inflación de 2,5% en agosto"),
        Afirmacion("N-2", "La inflación llegó a 2.5 % en agosto"),
    ]

    assert detectar_contradicciones(afirmaciones) == []
