"""Clasificación temática y utilidad del ranking contra criterio humano (reto §9.1).

    uv run python evals/eval_organize.py preparar   # genera planillas para personas
    uv run python evals/eval_organize.py medir      # macro-F1 IA vs baseline y Precision@5

1. ``evals/etiquetado/temas.csv``: 120 titulares estratificados por tema predicho.
   Una persona llena ``tema_humano`` (economia, logistica_canal, turismo,
   servicios_publicos, eventos_naturales, regulacion o sin_tema), idealmente con
   las columnas ``tema_ia`` y ``tema_baseline`` ocultas.
2. ``evals/etiquetado/ranking_candidatos.csv``: pool barajado y sin puntajes (top 15
   del sistema ∪ top 15 por fecha, el baseline). Un editor marca con ``x`` en
   ``elegido_por_editor`` los 5 temas que llevaría a la agenda.
Sin especialista, la evaluación del ranking se declara exploratoria (reto §9.1).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sklearn.metrics import f1_score, precision_recall_fscore_support

from senal.embed import cargar_codificador
from senal.organize import SIN_TEMA, TEMAS, ClasificadorPrototipos, clasificar_por_palabras
from senal.pipeline import cargar_snapshot, construir_bandeja, vectores_noticias

RAIZ = Path(__file__).resolve().parents[1]
PROCESADO = RAIZ / "data" / "processed"
ETIQUETADO = RAIZ / "evals" / "etiquetado"
PLANILLA_TEMAS = ETIQUETADO / "temas.csv"
PLANILLA_RANKING = ETIQUETADO / "ranking_candidatos.csv"
ORDEN_RANKING = ETIQUETADO / "ranking_orden.json"
ETIQUETAS = (*TEMAS, SIN_TEMA)
SEMILLA = 7
MUESTRA_TEMAS = 120
TOP_POOL = 15
K = 5


def _escribir_csv(ruta: Path, filas: list[dict[str, Any]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]), lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)


def _leer_csv(ruta: Path) -> list[dict[str, str]]:
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def _planilla_temas(snapshot: Any, temas_ia: list[str], azar: random.Random) -> None:
    if PLANILLA_TEMAS.exists():
        print(f"Ya existe {PLANILLA_TEMAS.name}; no se sobrescribe (puede tener etiquetas).")
        return
    por_tema: dict[str, list[int]] = {}
    for i, tema in enumerate(temas_ia):
        por_tema.setdefault(tema, []).append(i)
    cuota = MUESTRA_TEMAS // len(por_tema)
    elegidos = sorted(
        i for indices in por_tema.values() for i in azar.sample(indices, min(cuota, len(indices)))
    )
    filas = [
        {
            "id_noticia": snapshot.noticias[i].id_noticia,
            "titulo": snapshot.noticias[i].titulo,
            "medio": snapshot.noticias[i].medio,
            "tema_ia": temas_ia[i],
            "tema_baseline": clasificar_por_palabras(snapshot.noticias[i].titulo),
            "tema_humano": "",
            "notas": "",
        }
        for i in elegidos
    ]
    azar.shuffle(filas)
    _escribir_csv(PLANILLA_TEMAS, filas)
    print(f"Planilla de temas: {len(filas)} filas -> {PLANILLA_TEMAS.relative_to(RAIZ)}")


def preparar() -> None:
    snapshot = cargar_snapshot(PROCESADO)
    codificador = cargar_codificador()
    if codificador is None:
        raise SystemExit("Se necesita el modelo de embeddings para preparar las planillas.")
    vectores = vectores_noticias(snapshot, codificador, PROCESADO / "embeddings.npz")
    temas_ia = [c.tema for c in ClasificadorPrototipos(codificador).clasificar_vectores(vectores)]
    azar = random.Random(SEMILLA)  # noqa: S311 - muestreo reproducible, no criptografía
    _planilla_temas(snapshot, temas_ia, azar)

    bandeja = construir_bandeja(snapshot, codificador, vectores)
    por_fecha = sorted(bandeja.temas, key=lambda t: t.fecha_referencia, reverse=True)
    candidatos = list(
        {t.id_evento: t for t in [*bandeja.temas[:TOP_POOL], *por_fecha[:TOP_POOL]]}.values()
    )
    azar.shuffle(candidatos)
    _escribir_csv(
        PLANILLA_RANKING,
        [
            {
                "id_evento": t.id_evento,
                "titulo": t.titulo,
                "n_noticias": len(t.noticias),
                "medios": " ".join(t.medios[:5]),
                "elegido_por_editor": "",
            }
            for t in candidatos
        ],
    )
    orden = {
        "sistema": [t.id_evento for t in bandeja.temas[:K]],
        "baseline_fecha": [t.id_evento for t in por_fecha[:K]],
        "corte_utc": snapshot.manifest["fecha_corte_utc"],
    }
    ORDEN_RANKING.write_text(json.dumps(orden, indent=2), "utf-8")
    print(f"Pool de ranking: {len(candidatos)} temas -> {PLANILLA_RANKING.relative_to(RAIZ)}")


def _metricas(verdad: list[str], prediccion: list[str]) -> dict[str, Any]:
    etiquetas = list(ETIQUETAS)
    p, r, _, n = precision_recall_fscore_support(
        verdad, prediccion, labels=etiquetas, zero_division=0
    )
    macro = f1_score(verdad, prediccion, labels=etiquetas, average="macro", zero_division=0)
    return {
        "macro_f1": round(float(macro), 3),
        "por_clase": {
            e: {"precision": round(float(p[i]), 3), "recall": round(float(r[i]), 3), "n": int(n[i])}
            for i, e in enumerate(etiquetas)
        },
    }


def _medir_clasificacion() -> dict[str, Any] | None:
    filas = [f for f in _leer_csv(PLANILLA_TEMAS) if f["tema_humano"].strip()]
    if not filas:
        print("Sin etiquetas humanas en temas.csv: clasificación no medida.")
        return None
    invalidas = [f["id_noticia"] for f in filas if f["tema_humano"].strip() not in ETIQUETAS]
    if invalidas:
        raise SystemExit(f"Etiquetas humanas inválidas en: {', '.join(invalidas[:10])}")
    verdad = [f["tema_humano"].strip() for f in filas]
    resultado = {
        "n_etiquetadas": len(filas),
        "distribucion_humana": dict(Counter(verdad)),
        "ia": _metricas(verdad, [f["tema_ia"] for f in filas]),
        "baseline": _metricas(verdad, [f["tema_baseline"] for f in filas]),
        "gana_baseline": [
            f["id_noticia"]
            for f in filas
            if f["tema_baseline"] == f["tema_humano"].strip() != f["tema_ia"]
        ],
    }
    print(
        f"Clasificación (n={len(filas)}): macro-F1 IA {resultado['ia']['macro_f1']} "
        f"| baseline {resultado['baseline']['macro_f1']}"
    )
    return resultado


def _medir_ranking() -> dict[str, Any] | None:
    elegidos = {
        f["id_evento"] for f in _leer_csv(PLANILLA_RANKING) if f["elegido_por_editor"].strip()
    }
    if not elegidos or not ORDEN_RANKING.exists():
        print("Sin selección del editor: Precision@5 no medida (evaluación exploratoria).")
        return None
    orden = json.loads(ORDEN_RANKING.read_text("utf-8"))
    resultado = {
        "elegidos_por_editor": sorted(elegidos),
        "precision_at_5_sistema": len(elegidos & set(orden["sistema"])) / K,
        "precision_at_5_baseline_fecha": len(elegidos & set(orden["baseline_fecha"])) / K,
    }
    print(
        f"Precision@5: sistema {resultado['precision_at_5_sistema']:.2f} "
        f"| baseline por fecha {resultado['precision_at_5_baseline_fecha']:.2f}"
    )
    return resultado


def medir() -> None:
    resultado = {
        "fecha_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "clasificacion": _medir_clasificacion(),
        "ranking": _medir_ranking(),
    }
    destino = RAIZ / "eval-results" / "senal"
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / f"organize_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), "utf-8")
    print(f"Resultados -> {ruta.relative_to(RAIZ)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accion", choices=("preparar", "medir"))
    args = parser.parse_args()
    if args.accion == "preparar":
        preparar()
    else:
        medir()


if __name__ == "__main__":
    main()
