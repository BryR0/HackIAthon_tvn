"""Construye data/processed/ desde data/raw/. Uso: uv run python scripts/build_snapshot.py."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SRC_DIR = RAIZ / "app" / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from senal.snapshot import construir_snapshot


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    base_data = (RAIZ / "app" / "data") if (RAIZ / "app" / "data").exists() else (RAIZ / "data")
    salida = base_data / "processed"
    manifest = construir_snapshot(base_data / "raw", salida)
    reporte = json.loads((salida / "reporte_calidad.json").read_text(encoding="utf-8"))
    logging.info("Corte: %s", manifest["fecha_corte_utc"])
    logging.info("Conteos: %s", manifest["conteos"])
    logging.info("Solicitudes fallidas: %d", len(manifest["solicitudes_fallidas"]))
    logging.info("Calidad: %s", json.dumps(reporte, ensure_ascii=False))


if __name__ == "__main__":
    main()
