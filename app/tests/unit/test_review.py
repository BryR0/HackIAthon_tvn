"""Etapa 7 · Revisar: estados humanos del reto §8 y fichas del contrato §7."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from senal.ingest import Noticia
from senal.pipeline import Snapshot, construir_bandeja
from senal.review import ESTADOS, RegistroRevisiones, Revision, ficha_contrato

AHORA = datetime(2026, 10, 6, 15, 0, tzinfo=UTC)
SNAPSHOT_BANCA = Snapshot(
    noticias=(
        Noticia("N-1", "Canal de Panamá limita tránsitos", "https://prensa.com/n1", "prensa.com",
                "es", AHORA, None, AHORA, "gdelt_doc:logistica", "titular_metadatos"),
    ),
    indicadores=(),
    eventos=(),
    manifest={"fecha_corte_utc": AHORA.isoformat()},
    corte=AHORA,
)  # fmt: skip


def test_estados_son_exactamente_los_del_reto() -> None:
    assert ESTADOS == (
        "nuevo",
        "en_revision",
        "requiere_evidencia",
        "aprobado_como_borrador",
        "descartado",
    )


def test_estado_inicial_es_nuevo_y_el_ultimo_registro_manda(tmp_path: Path) -> None:
    registro = RegistroRevisiones(tmp_path / "reviews.jsonl")

    assert registro.estado_actual("E-1") == "nuevo"
    registro.registrar(Revision("E-1", "en_revision", "Ana Editora", "", AHORA))
    registro.registrar(Revision("E-1", "aprobado_como_borrador", "Ana Editora", "ok", AHORA))

    assert registro.estado_actual("E-1") == "aprobado_como_borrador"
    assert [r.estado for r in registro.historial("E-1")] == [
        "en_revision",
        "aprobado_como_borrador",
    ]


def test_registro_persiste_en_jsonl_y_sobrevive_a_reinicio(tmp_path: Path) -> None:
    ruta = tmp_path / "reviews.jsonl"
    RegistroRevisiones(ruta).registrar(Revision("E-2", "descartado", "Luis", "duplicado", AHORA))

    linea = json.loads(ruta.read_text(encoding="utf-8").splitlines()[0])

    assert linea["revisor"] == "Luis"
    assert RegistroRevisiones(ruta).estado_actual("E-2") == "descartado"


def test_estado_invalido_o_revisor_vacio_se_rechazan(tmp_path: Path) -> None:
    registro = RegistroRevisiones(tmp_path / "reviews.jsonl")

    with pytest.raises(ValueError, match="estado"):
        registro.registrar(Revision("E-1", "publicado", "Ana", "", AHORA))
    with pytest.raises(ValueError, match="revisor"):
        registro.registrar(Revision("E-1", "en_revision", "  ", "", AHORA))


def test_linea_corrupta_se_omite_y_no_rompe_la_bandeja(tmp_path: Path) -> None:
    ruta = tmp_path / "reviews.jsonl"
    registro = RegistroRevisiones(ruta)
    registro.registrar(Revision("E-1", "en_revision", "Ana", "", AHORA))
    with ruta.open("a", encoding="utf-8") as archivo:
        archivo.write('{"id_caso": "E-1", "estado": \n')

    assert registro.estado_actual("E-1") == "en_revision"


def test_revision_guarda_los_ids_de_fuente_del_caso(tmp_path: Path) -> None:
    ruta = tmp_path / "reviews.jsonl"
    RegistroRevisiones(ruta).registrar(
        Revision("E-1", "en_revision", "Ana", "", AHORA, ids_fuente=("N-1", "N-2"))
    )

    assert json.loads(ruta.read_text(encoding="utf-8"))["ids_fuente"] == ["N-1", "N-2"]


# --- TB13 · revisión del boletín bancario (extensión, ADR 0003) ---------------------


def test_tb13_revision_de_boletin_no_pisa_la_editorial(tmp_path: Path) -> None:
    registro = RegistroRevisiones(tmp_path / "reviews.jsonl")
    registro.registrar(Revision("E-1", "aprobado_como_borrador", "Ana Editora", "", AHORA))
    registro.registrar(
        Revision("E-1", "descartado", "Beto Analista", "sin dato", AHORA, modalidad="banca")
    )

    assert registro.estado_actual("E-1") == "aprobado_como_borrador"
    assert registro.estado_actual("E-1", "banca") == "descartado"
    assert [r.revisor for r in registro.historial("E-1", "banca")] == ["Beto Analista"]
    assert set(registro.ultimos()) == {"E-1"}
    assert registro.ultimos("banca")["E-1"].estado == "descartado"


def test_tb13_modalidad_invalida_se_rechaza(tmp_path: Path) -> None:
    registro = RegistroRevisiones(tmp_path / "reviews.jsonl")
    with pytest.raises(ValueError, match="modalidad"):
        registro.registrar(Revision("E-1", "en_revision", "Ana", "", AHORA, modalidad="trading"))


def test_tb13_lineas_previas_sin_modalidad_son_editoriales(tmp_path: Path) -> None:
    ruta = tmp_path / "reviews.jsonl"
    linea = {"id_caso": "E-7", "estado": "en_revision", "revisor": "Ana", "nota": "",
             "fecha_utc": AHORA.isoformat(), "ids_fuente": []}  # fmt: skip
    ruta.write_text(json.dumps(linea) + "\n", encoding="utf-8")

    registro = RegistroRevisiones(ruta)

    assert registro.estado_actual("E-7") == "en_revision"
    assert registro.estado_actual("E-7", "banca") == "nuevo"


def test_tb13_ficha_del_contrato_registra_la_modalidad_bancaria() -> None:
    bandeja = construir_bandeja(SNAPSHOT_BANCA, None, None)
    tema = bandeja.temas[0]
    revision = Revision(tema.id_evento, "en_revision", "Beto", "", AHORA, modalidad="banca")

    ficha = ficha_contrato(tema, None, revision)
    editorial = ficha_contrato(tema, None, None)

    assert ficha["modalidad"] == "banca_boletin"
    assert ficha["estado_revision"] == "en_revision"
    assert ficha["publicado"] is False
    assert editorial["modalidad"] == "tvn_editorial"
