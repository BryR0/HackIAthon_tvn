"""Procedencia independiente y estado de evidencia (CU-03, T02, reto §4)."""

from senal.evidence import (
    Pieza,
    agencia,
    contar_procedencias,
    dominio_canonico,
    es_fuente_oficial,
    estado_evidencia,
)


def test_dominio_canonico_quita_subdominios_de_presentacion() -> None:
    assert dominio_canonico("https://www.prensa.com/a") == "prensa.com"
    assert dominio_canonico("https://m.tvn-2.com/a") == "tvn-2.com"
    assert dominio_canonico("https://amp.cnn.com/x") == "cnn.com"


def test_detecta_agencia_en_titulo_o_descripcion() -> None:
    assert agencia("Canal reduce tránsitos (EFE)") == "EFE"
    assert agencia("Panamá, 5 oct (AFP). La ACP anunció") == "AFP"
    assert agencia("Reuters: Panama Canal cuts transits") == "REUTERS"
    assert agencia("Nota propia de la redacción") is None


def test_cu03_cinco_medios_que_replican_la_misma_agencia_son_una_procedencia() -> None:
    piezas = [
        Pieza(url=f"https://medio{n}.com/a", titulo=f"Titular distinto {n} (EFE)") for n in range(5)
    ]

    assert contar_procedencias(piezas) == 1


def test_titulares_casi_identicos_en_dominios_distintos_son_una_procedencia() -> None:
    piezas = [
        Pieza(url="https://a.com/x", titulo="Canal de Panamá limita tránsitos por sequía"),
        Pieza(url="https://b.com/y", titulo="CANAL DE PANAMÁ LIMITA TRÁNSITOS POR SEQUÍA"),
    ]

    assert contar_procedencias(piezas) == 1


def test_dominios_distintos_con_titulares_propios_son_independientes() -> None:
    piezas = [
        Pieza(url="https://www.prensa.com/x", titulo="ACP confirma restricción de calado"),
        Pieza(url="https://www.tvn-2.com/y", titulo="Navieras ajustan rutas por el Canal"),
        Pieza(url="https://tvn-2.com/z", titulo="Otra nota del mismo medio"),
    ]

    assert contar_procedencias(piezas) == 2


def test_fuente_oficial_por_dominio_gubernamental_u_organismo() -> None:
    assert es_fuente_oficial("https://www.mef.gob.pa/informe")
    assert es_fuente_oficial("https://api.worldbank.org/v2/x")
    assert es_fuente_oficial("https://earthquake.usgs.gov/earthquakes/eventpage/x")
    assert es_fuente_oficial("https://pancanal.com/aviso")
    assert not es_fuente_oficial("https://www.tvn-2.com/a")


def test_estado_de_evidencia_es_independiente_del_puntaje() -> None:
    assert estado_evidencia(0, fuente_oficial=False) == "insuficiente"
    assert estado_evidencia(1, fuente_oficial=False) == "parcial"
    assert estado_evidencia(2, fuente_oficial=False) == "suficiente_para_borrador"
    assert estado_evidencia(1, fuente_oficial=True) == "suficiente_para_borrador"


def test_dominio_oficial_no_se_suplanta_con_sufijo() -> None:
    assert not es_fuente_oficial("https://evilworldbank.org/x")
    assert not es_fuente_oficial("https://notpancanal.com/x")
    assert es_fuente_oficial("https://data.worldbank.org/x")
