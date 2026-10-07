"""Extensión bancaria: mapa sectorial, enlace a series SBP y carga opcional (TB14)."""

import csv
import shutil
from dataclasses import replace
from pathlib import Path

from senal import sbp
from senal.banca import (
    HORIZONTE_SEGUIMIENTO,
    SECTORES_POR_TEMA,
    VERSION_BANCA,
    enlazar_sbp,
    es_tema_bancario,
)
from senal.ingest import SerieSBP, validar_series_sbp
from senal.organize import TEMAS
from senal.pipeline import cargar_snapshot, evidencias_de

PROCESADO = Path(__file__).resolve().parents[2] / "data" / "processed"


def _serie(sector: str, periodo: str, valor: float | None) -> SerieSBP:
    return SerieSBP(
        id_serie=f"SBP:credito_local:{sector}",
        periodo=periodo,
        nombre=f"Crédito local SBN · {sector}",
        sector=sector,
        valor=valor,
        unidad="millones USD",
        valor_base=100.0,
        periodo_base=f"2023-{periodo[5:]}",
        variacion_pct=7.9,
        cuadro="Cuadro 5",
        pagina_pdf=14,
        fuente_url="https://www.superbancos.gob.pa/x.pdf",
        sha256_pdf="h",
    )


def test_mapa_cubre_todos_los_temas_con_sectores_que_existen_en_los_datos() -> None:
    with (PROCESADO / "sbp_series.csv").open(encoding="utf-8", newline="") as archivo:
        en_csv = {fila["sector"] for fila in csv.DictReader(archivo)}

    assert set(SECTORES_POR_TEMA) == set(TEMAS)
    assert set(HORIZONTE_SEGUIMIENTO) == set(TEMAS)
    for tema, sectores in SECTORES_POR_TEMA.items():
        assert sectores, tema
        assert set(sectores) <= set(sbp.SECTORES), tema
        assert set(sectores) <= en_csv, tema
    assert VERSION_BANCA.startswith("banca-")


def test_logistica_enlaza_comercio_e_industria_del_ultimo_mes_con_dato() -> None:
    series = (
        _serie("comercio", "2024-11", 1.0),
        _serie("comercio", "2024-12", 13177.0),
        _serie("industria", "2024-12", None),
        _serie("industria", "2024-10", 4081.7),
        _serie("pesca", "2024-12", 87.0),
    )

    enlaces = enlazar_sbp("logistica_canal", series)

    assert [(e.sector, e.periodo) for e in enlaces] == [
        ("comercio", "2024-12"),
        ("industria", "2024-10"),
    ]
    comercio = enlaces[0]
    assert comercio.id_evidencia == "SBP:credito_local:comercio:2024-12"
    assert comercio.relacion == "hipotesis"
    assert "12/2024" in comercio.limitacion
    assert "no describe la situación actual" in comercio.limitacion
    assert "SBP" in comercio.limitacion


def test_tema_sin_mapa_no_fuerza_enlaces() -> None:
    assert enlazar_sbp("sin_tema", (_serie("comercio", "2024-12", 1.0),)) == ()
    assert not es_tema_bancario("sin_tema")
    assert es_tema_bancario("logistica_canal")


def test_validar_series_sbp_conserva_nulos_y_separa_filas_invalidas() -> None:
    filas = [
        {"id_serie": "SBP:credito_local:pesca", "periodo": "2024-12", "sector": "pesca",
         "nombre": "Pesca", "valor": "", "unidad": "millones USD", "pagina_pdf": "14"},
        {"id_serie": "SBP:credito_local:pesca", "periodo": "diciembre", "sector": "pesca",
         "nombre": "Pesca", "valor": "87", "unidad": "millones USD"},
        {"id_serie": None, "periodo": "2024-12", "sector": "pesca", "valor": "87"},
        {"id_serie": "SBP:credito_local:pesca", "periodo": "2024-11", "sector": "pesca",
         "nombre": "Pesca", "valor": "ochenta", "unidad": "millones USD"},
    ]  # fmt: skip

    resultado = validar_series_sbp(filas)

    assert len(resultado.validas) == 1
    assert resultado.validas[0].valor is None
    assert resultado.validas[0].pagina_pdf == 14
    assert sorted(e.motivo for e in resultado.excluidos) == [
        "campo_obligatorio",
        "periodo_invalido",
        "valor_invalido",
    ]


def test_tb14_snapshot_sin_series_sbp_carga_y_sigue_editorial(tmp_path: Path) -> None:
    for nombre in ("manifest.json", "noticias.csv", "indicadores.csv", "eventos.geojson"):
        shutil.copy(PROCESADO / nombre, tmp_path / nombre)

    snapshot = cargar_snapshot(tmp_path)

    assert snapshot.series_sbp == ()
    assert len(snapshot.noticias) > 0


def test_snapshot_real_trae_156_series_y_evidencias_sbp_solo_si_se_piden() -> None:
    snapshot = cargar_snapshot(PROCESADO)
    assert len(snapshot.series_sbp) == 156

    editorial = evidencias_de(snapshot)
    banca = evidencias_de(snapshot, incluir_sbp=True)

    assert not any(e.id.startswith("SBP:") for e in editorial)
    sbp_ev = {e.id: e for e in banca if e.id.startswith("SBP:")}
    assert len(sbp_ev) == 156
    comercio = sbp_ev["SBP:credito_local:comercio:2024-12"]
    assert comercio.tipo == "serie_sbp"
    assert comercio.campos["periodo"] == "12/2024"
    assert comercio.campos["valor"] == "13177"
    assert comercio.campos["unidad"] == "millones USD"
    assert comercio.campos["pagina_pdf"] == "14"
    assert comercio.campos["fuente"].startswith("Superintendencia de Bancos")
    assert comercio.campos["periodicidad"] == "dato mensual"


def test_series_nulas_no_entran_como_evidencia() -> None:
    snapshot = replace(
        cargar_snapshot(PROCESADO),
        series_sbp=(_serie("pesca", "2024-12", None), _serie("comercio", "2024-12", 1.5)),
    )
    ids = [e.id for e in evidencias_de(snapshot, incluir_sbp=True)]
    assert "SBP:credito_local:pesca:2024-12" not in ids
    assert "SBP:credito_local:comercio:2024-12" in ids
