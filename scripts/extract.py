"""Descarga las fuentes públicas a data/raw/.

Uso: scripts/extract.py [--sin-gdelt] [--sin-sbp | --solo-sbp]
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SRC_DIR = RAIZ / "app" / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from senal.extraccion import agregar_sbp, extraer_todo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-gdelt", action="store_true", help="omite GDELT (límite de tasa)")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--sin-sbp", action="store_true", help="omite la fuente D (SBP)")
    grupo.add_argument(
        "--solo-sbp",
        action="store_true",
        help="agrega solo la fuente D a un extraccion.json existente; no toca las noticias",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    base_data = (RAIZ / "app" / "data") if (RAIZ / "app" / "data").exists() else (RAIZ / "data")
    raw = base_data / "raw"
    registro = (
        agregar_sbp(raw)
        if args.solo_sbp
        else extraer_todo(raw, incluir_gdelt=not args.sin_gdelt, incluir_sbp=not args.sin_sbp)
    )
    solicitudes = registro["solicitudes"]
    assert isinstance(solicitudes, list)
    estados = Counter((s["fuente"].split(":")[0], s["estado"]) for s in solicitudes)
    for (fuente, estado), total in sorted(estados.items(), key=str):
        logging.info("%-10s estado=%s solicitudes=%d", fuente, estado, total)


if __name__ == "__main__":
    main()
