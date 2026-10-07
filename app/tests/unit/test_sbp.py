"""Fuente D · SBP: tabla de crédito local por sector (TB01–TB03, reto §6 D).

Los fixtures son texto real extraído con pypdf de los Informes de Actividad
Bancaria 2024 (enero: etiquetas con espacios largos; febrero: etiqueta partida en
dos líneas; agosto: tabla por provincias que no debe confundirse; diciembre:
título "Crédito local" con sangrías).
"""

import json
from pathlib import Path

import pytest

from senal.ingest import SerieSBP
from senal.sbp import (
    SECTORES,
    extraer_credito_local,
    periodo_de_archivo,
    validar_sumas,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sbp"
URL = "https://www.superbancos.gob.pa/documentos/financiera_y_estadistica/estudios/IAB/IAB-{}.pdf"


def _paginas(mes: str) -> dict[int, str]:
    crudo = json.loads((FIXTURES / f"IAB-{mes}.json").read_text("utf-8"))
    return {int(k): v for k, v in crudo.items()}


def _extraer(mes: str) -> tuple[list[SerieSBP], list[object]]:
    series, excluidos = extraer_credito_local(
        _paginas(mes),
        periodo=periodo_de_archivo(f"IAB-{mes}.pdf"),
        fuente_url=URL.format(mes),
        sha256_pdf="abc123",
    )
    return list(series), list(excluidos)


def test_periodo_sale_del_nombre_del_archivo() -> None:
    assert periodo_de_archivo("IAB-0124.pdf") == "2024-01"
    assert periodo_de_archivo("data/raw/sbp/IAB-1224.pdf") == "2024-12"
    with pytest.raises(ValueError):
        periodo_de_archivo("informe.pdf")


@pytest.mark.parametrize("mes", ["0124", "0224", "0824", "1224"])
def test_tb01_trece_sectores_con_valor_unidad_y_pagina(mes: str) -> None:
    series, excluidos = _extraer(mes)

    assert [s.sector for s in series] == list(SECTORES)
    assert all(s.valor is not None for s in series)
    assert all(s.unidad == "millones USD" for s in series)
    assert all(s.pagina_pdf is not None for s in series)
    assert all(s.periodo == f"2024-{mes[:2]}" for s in series)
    assert all(s.periodo_base == f"2023-{mes[:2]}" for s in series)
    assert all(s.sha256_pdf == "abc123" for s in series)
    assert excluidos == []


def test_tb01_valores_de_diciembre_sin_separador_de_miles() -> None:
    series, _ = _extraer("1224")
    por_sector = {s.sector: s for s in series}

    comercio = por_sector["comercio"]
    assert comercio.valor == 13177.0
    assert comercio.valor_base == 12210.0
    assert comercio.variacion_pct == 7.9
    assert comercio.pagina_pdf == 14
    assert comercio.id_serie == "SBP:credito_local:comercio"
    assert comercio.id_evidencia == "SBP:credito_local:comercio:2024-12"
    assert comercio.cuadro is not None and "Cuadro 5" in comercio.cuadro
    assert por_sector["pesca"].variacion_pct == -34.1


def test_tb01_etiqueta_partida_en_dos_lineas() -> None:
    series, _ = _extraer("0224")
    financieras = next(s for s in series if s.sector == "act_financieras_seguros")
    assert financieras.valor == 2006.1


def test_tb01_no_confunde_la_tabla_por_provincias() -> None:
    series, _ = _extraer("0824")
    comercio = next(s for s in series if s.sector == "comercio")
    # La tabla nacional es la página 15; la de provincias (p. 17) no tiene año base.
    assert comercio.pagina_pdf == 15
    assert comercio.valor_base == 11949.0


def test_tb02_mes_sin_tabla_deja_nulos_y_exclusion_sin_bloquear() -> None:
    series, excluidos = extraer_credito_local(
        {1: "Portada sin cuadros"},
        periodo="2024-03",
        fuente_url=URL.format("0324"),
        sha256_pdf="x",
    )
    assert len(series) == len(SECTORES)
    assert all(s.valor is None for s in series)
    assert [e.motivo for e in excluidos] == ["tabla_no_encontrada"]


def test_tb02_encabezado_de_otro_mes_no_se_acepta() -> None:
    series, excluidos = extraer_credito_local(
        _paginas("1224"), periodo="2024-11", fuente_url=URL.format("1124"), sha256_pdf="x"
    )
    assert all(s.valor is None for s in series)
    assert [e.motivo for e in excluidos] == ["tabla_no_encontrada"]


@pytest.mark.parametrize("mes", ["0124", "0224", "0824", "1224"])
def test_tb03_sumas_consistentes_en_datos_reales(mes: str) -> None:
    series, _ = _extraer(mes)
    assert validar_sumas(series) == []


def test_tb03_suma_inconsistente_se_marca() -> None:
    series, _ = _extraer("1224")
    alteradas = [
        s if s.sector != "comercio" else s.con_valor((s.valor or 0) + 500) for s in series
    ]
    motivos = [e.motivo for e in validar_sumas(alteradas)]
    assert motivos == ["suma_sectores_privados_inconsistente"]


def _diciembre_con(antes: str, despues: str) -> dict[int, str]:
    paginas = _paginas("1224")
    return {n: t.replace(antes, despues) for n, t in paginas.items()}


def test_coma_suelta_en_una_fila_no_aborta_el_parser() -> None:
    paginas = _diciembre_con("Pesca 132 87", "Pesca , 87")

    series, excluidos = extraer_credito_local(
        paginas, periodo="2024-12", fuente_url=URL.format("1224"), sha256_pdf="x"
    )

    por_sector = {s.sector: s for s in series}
    assert por_sector["pesca"].valor is None
    assert por_sector["comercio"].valor == 13177.0
    assert [(e.motivo, e.campo) for e in excluidos] == [("sector_no_encontrado", "pesca")]


def test_mes_base_irreconocible_no_inventa_periodo_base() -> None:
    paginas = _diciembre_con("Sector dic-23 dic-24", "Sector xyz-23 dic-24")

    series, excluidos = extraer_credito_local(
        paginas, periodo="2024-12", fuente_url=URL.format("1224"), sha256_pdf="x"
    )

    assert all(s.periodo_base is None for s in series)
    assert all(s.valor is not None for s in series)
    assert [e.motivo for e in excluidos] == ["periodo_base_no_reconocido"]


def test_pdf_ilegible_lanza_value_error(tmp_path: Path) -> None:
    from senal.sbp import leer_paginas_pdf

    ruta = tmp_path / "IAB-0124.pdf"
    ruta.write_bytes(b"esto no es un pdf")

    with pytest.raises(ValueError, match="ilegible"):
        leer_paginas_pdf(ruta)
