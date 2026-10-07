"""Etapa 4 · Priorizar: puntaje P = 30R + 25I + 20U + 15N + 10E (reto §4), T08."""

import math
from datetime import UTC, datetime, timedelta

import pytest

from senal.score import (
    RULES_VERSION,
    SenalesEvento,
    banda,
    nivel_geografico,
    ordenar,
    puntuar,
)

CORTE = datetime(2026, 10, 6, tzinfo=UTC)


def _senales(**over: object) -> SenalesEvento:
    base: dict[str, object] = {
        "id_evento": "E-1",
        "tema": "economia",
        "texto": "Inflación en Panamá sube",
        "medios": ("tvn-2.com",),
        "fecha_referencia": CORTE - timedelta(days=1),
        "dato_oficial_enlazado": False,
        "procedencias_independientes": 1,
        "fuente_oficial": False,
        "novedad": 1.0,
    }
    base.update(over)
    return SenalesEvento(**base)  # type: ignore[arg-type]


def test_componentes_normalizados_y_formula_exacta() -> None:
    p = puntuar(_senales(), CORTE)

    for valor in (p.r, p.i, p.u, p.n, p.e):
        assert 0.0 <= valor <= 1.0
    esperado = 30 * p.r + 25 * p.i + 20 * p.u + 15 * p.n + 10 * p.e
    assert p.total == pytest.approx(round(esperado, 1))
    assert p.version == RULES_VERSION


def test_urgencia_usa_la_fecha_de_corte_y_no_el_reloj() -> None:
    reciente = puntuar(_senales(fecha_referencia=CORTE), CORTE)
    vieja = puntuar(_senales(fecha_referencia=CORTE - timedelta(days=30)), CORTE)

    assert reciente.u == 1.0
    assert vieja.u == pytest.approx(math.exp(-30 / 7), abs=1e-6)


def test_duplicacion_no_incrementa_el_puntaje() -> None:
    una = puntuar(_senales(procedencias_independientes=1), CORTE)
    misma_agencia_cinco_veces = puntuar(
        _senales(
            medios=("a.com", "b.com", "c.com", "d.com", "e.com"), procedencias_independientes=1
        ),
        CORTE,
    )

    assert misma_agencia_cinco_veces.total == una.total


def test_evidencia_satura_en_tres_procedencias_y_bonifica_fuente_oficial() -> None:
    assert puntuar(_senales(procedencias_independientes=3), CORTE).e == 1.0
    assert puntuar(_senales(procedencias_independientes=9), CORTE).e == 1.0
    con_oficial = puntuar(_senales(procedencias_independientes=1, fuente_oficial=True), CORTE)
    sin_oficial = puntuar(_senales(procedencias_independientes=1), CORTE)
    assert con_oficial.e > sin_oficial.e


def test_dato_oficial_enlazado_sube_impacto_con_tope() -> None:
    sin_dato = puntuar(_senales(), CORTE)
    con_dato = puntuar(_senales(dato_oficial_enlazado=True), CORTE)

    assert con_dato.i == pytest.approx(min(sin_dato.i + 0.3, 1.0))


def test_nivel_geografico_por_gazetteer_y_medio() -> None:
    assert nivel_geografico("Sube el agua en Chiriquí", ("cnn.com",)) == 1.0
    assert nivel_geografico("Alcaldía anuncia obras", ("tvn-2.com",)) == 0.5
    assert nivel_geografico("Costa Rica eleva tasas", ("cnn.com",)) == 0.5
    assert nivel_geografico("Bolsa de Tokio cae", ("cnn.com",)) == 0.0


def test_bandas_sin_solapamiento() -> None:
    assert banda(39.9) == "bajo"
    assert banda(40.0) == "medio"
    assert banda(69.9) == "medio"
    assert banda(70.0) == "alto"


def test_empates_por_mayor_urgencia_y_luego_id() -> None:
    a = puntuar(_senales(id_evento="E-2"), CORTE)
    b = puntuar(_senales(id_evento="E-1"), CORTE)

    assert [p.id_evento for p in ordenar([a, b])] == ["E-1", "E-2"]


def test_t08_prioridad_alta_expone_componentes_y_no_habilita_publicacion() -> None:
    p = puntuar(
        _senales(
            texto="Canal de Panamá suspende tránsitos",
            tema="logistica_canal",
            fecha_referencia=CORTE,
            dato_oficial_enlazado=True,
            procedencias_independientes=3,
        ),
        CORTE,
    )

    assert p.banda == "alto"
    assert set(p.desglose()) == {"R", "I", "U", "N", "E"}
    assert p.habilita_publicacion is False
