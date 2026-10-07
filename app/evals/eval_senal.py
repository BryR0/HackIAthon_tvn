"""Evaluación reproducible del agente (reto §9.1): abstención, citas, contradicciones,
adversariales, recuperación y eficiencia, con numerador, denominador y fallos.

Uso:
    uv run python evals/eval_senal.py                 # híbrido e5 + plantilla extractiva
    uv run python evals/eval_senal.py --modo bm25     # baseline léxico (comparación §8)
    uv run python evals/eval_senal.py --llm           # usa el LLM configurado (Ollama/Gemini)
    uv run python evals/eval_senal.py --benchmark evals/benchmark_reservado.jsonl
    uv run python evals/eval_senal.py --modalidad banca --benchmark evals/benchmark_banca_dev.jsonl

Los casos sintéticos (SINT-*) se agregan solo al buscador de esta corrida, nunca al
snapshot ni a la app. Las etiquetas del benchmark de desarrollo son un borrador que
debe confirmar una persona (reto §7: "Las etiquetas se crean por revisión humana").
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from senal.boletin import Boletin, formato_banca, ids_consulta_banca, tema_de_consulta
from senal.embed import cargar_codificador
from senal.generate import (
    COBERTURA_MINIMA,
    UMBRAL_BM25,
    UMBRAL_COSENO,
    UMBRAL_COSENO_FUERTE,
    Paquete,
    ResultadoRespuesta,
    responder,
)
from senal.llm import cargar_proveedor
from senal.organize import normalizar_texto
from senal.pipeline import (
    Snapshot,
    Tema,
    cargar_snapshot,
    construir_bandeja,
    evidencias_de,
    vectores_noticias,
)
from senal.retrieve import Buscador, Evidencia
from senal.score import RULES_VERSION

RAIZ = Path(__file__).resolve().parents[1]


def _cargar_benchmark(ruta: Path) -> list[dict[str, Any]]:
    return [json.loads(linea) for linea in ruta.read_text("utf-8").splitlines() if linea.strip()]


def _texto_emitido(r: ResultadoRespuesta) -> str:
    partes = [a.texto for a in r.aceptadas]
    p = r.paquete
    if isinstance(p, Paquete):
        partes += [p.titulo, p.brief, p.guion, p.copy_digital, *p.preguntas]
    elif isinstance(p, Boletin):
        partes += [p.titulo, p.resumen, *p.preguntas_analista, *(s.razon for s in p.sectores)]
    return " ".join(partes)


def _texto_propio(r: ResultadoRespuesta) -> str:
    """Lo que redacta el sistema, sin titulares atribuidos: allí se busca el léxico
    prohibido en banca (citar "pérdidas" de un medio es válido; inferirlas, no)."""
    partes = [a.texto for a in r.aceptadas if a.tipo != "declaracion"]
    p = r.paquete
    if isinstance(p, Boletin):
        partes += [*p.preguntas_analista, *(s.razon for s in p.sectores), p.horizonte_seguimiento]
    return " ".join(partes)


def _recupero(r: ResultadoRespuesta, esperado: dict[str, Any]) -> bool | None:
    ids, terminos = esperado.get("ids"), esperado.get("terminos")
    if not ids and not terminos:
        return None
    presentes = {e.id for e in r.evidencias} | set(r.sospechosas)
    if ids:
        return all(i in presentes for i in ids)
    textos = [normalizar_texto(e.texto) for e in r.evidencias]
    return any(normalizar_texto(t).strip() in tx for t in terminos for tx in textos)


def _evaluar_caso(caso: dict[str, Any], r: ResultadoRespuesta) -> dict[str, Any]:
    esperado = caso.get("esperado", {})
    emitido = _texto_emitido(r)
    chequeos: dict[str, bool] = {}
    if "abstener" in esperado:
        chequeos["abstencion_correcta"] = r.abstencion == esperado["abstener"]
    recupero = _recupero(r, esperado)
    if recupero is not None and not esperado.get("abstener", False):
        chequeos["recuperacion"] = recupero
    if esperado.get("contradiccion"):
        ids_en_conflicto = {v.id_fuente for c in r.contradicciones for v in c.versiones}
        chequeos["contradiccion_detectada"] = set(esperado.get("ids", [])) <= ids_en_conflicto
    for prohibido in esperado.get("prohibido", []):
        chequeos[f"sin:{prohibido}"] = prohibido.lower() not in emitido.lower()
    propio = normalizar_texto(_texto_propio(r))
    for prohibido in esperado.get("prohibido_propio", []):
        chequeos[f"sin_propio:{prohibido}"] = normalizar_texto(prohibido) not in propio
    if esperado.get("ids_citados"):
        citados = {c.id_evidencia for a in r.aceptadas for c in a.citas}
        chequeos["ids_citados"] = set(esperado["ids_citados"]) <= citados
    for sospechoso in esperado.get("sospechoso", []):
        chequeos[f"sospechoso:{sospechoso}"] = sospechoso in r.sospechosas
    if esperado.get("acusacion_no_como_hecho"):
        chequeos["acusacion_no_como_hecho"] = not any(
            a.tipo == "hecho" and "corrup" in normalizar_texto(a.texto) for a in r.aceptadas
        )
    return {
        "id": caso["id"],
        "tipo": caso["tipo"],
        "consulta": caso["consulta"],
        "abstencion": r.abstencion,
        "aceptadas": len(r.aceptadas),
        "descartadas": [d.motivo for d in r.descartadas],
        "cobertura_citas": r.cobertura_citas,
        "chequeos": chequeos,
        "aprobado": all(chequeos.values()),
        "proveedor": r.proveedor,
        "avisos": list(r.avisos),
    }


def _percentil(valores: list[float], p: float) -> float:
    ordenados = sorted(valores)
    if not ordenados:
        return 0.0
    k = (len(ordenados) - 1) * p
    bajo, alto = int(k), min(int(k) + 1, len(ordenados) - 1)
    return ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (k - bajo)


def _resumen(filas: list[dict[str, Any]], latencias: list[float]) -> dict[str, Any]:
    por_tipo: dict[str, dict[str, int]] = defaultdict(lambda: {"num": 0, "den": 0})
    for f in filas:
        por_tipo[f["tipo"]]["den"] += 1
        por_tipo[f["tipo"]]["num"] += int(f["aprobado"])
    sin_respuesta = [f for f in filas if f["tipo"] == "sin_respuesta"]
    respondibles = [f for f in filas if f["tipo"] in ("sustentada", "contradiccion")]
    aceptadas = sum(f["aceptadas"] for f in filas)
    return {
        "por_tipo": dict(por_tipo),
        "abstencion_correcta": {
            "num": sum(f["abstencion"] for f in sin_respuesta),
            "den": len(sin_respuesta),
        },
        "abstencion_incorrecta_en_respondibles": {
            "num": sum(f["abstencion"] for f in respondibles),
            "den": len(respondibles),
        },
        "cobertura_citas": {
            "num": round(sum(f["cobertura_citas"] * f["aceptadas"] for f in filas)),
            "den": aceptadas,
        },
        "latencia_s": {
            "mediana": round(statistics.median(latencias), 3) if latencias else 0.0,
            "p95": round(_percentil(latencias, 0.95), 3),
        },
    }


def _imprimir(salida: dict[str, Any], ruta: Path) -> None:
    r = salida["resumen"]
    print(f"Resultados -> {ruta.relative_to(RAIZ)}")
    print(f"Busqueda: {salida['config']['busqueda']} | Redaccion: {salida['config']['redaccion']}")
    for tipo, c in sorted(r["por_tipo"].items()):
        print(f"  {tipo:14} {c['num']:2}/{c['den']:2} aprobados")
    claves = ("abstencion_correcta", "abstencion_incorrecta_en_respondibles", "cobertura_citas")
    for clave in claves:
        print(f"  {clave:38} {r[clave]['num']}/{r[clave]['den']}")
    print(f"  latencia mediana {r['latencia_s']['mediana']} s | p95 {r['latencia_s']['p95']} s")
    print(f"  tokens {salida['tokens_totales']} | costo US$ {salida['costo_usd']}")
    for f in salida["fallos"]:
        fallidos = [k for k, v in f["chequeos"].items() if not v]
        print(f"  FALLO {f['id']} ({f['tipo']}): {', '.join(fallidos)} | {f['consulta']}")


def _temas(snapshot: Snapshot, modo: str) -> tuple[Tema, ...]:
    """Bandeja de la corrida: CU-05 toma las noticias de los temas mejor priorizados."""
    if modo != "hibrido":
        return construir_bandeja(snapshot, None, None).temas
    codificador = cargar_codificador()
    cache = RAIZ / "data" / "processed" / "embeddings.npz"
    vectores = vectores_noticias(snapshot, codificador, cache)
    return construir_bandeja(snapshot, codificador, vectores).temas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=RAIZ / "evals" / "benchmark_dev.jsonl")
    parser.add_argument("--modo", choices=("hibrido", "bm25"), default="hibrido")
    parser.add_argument("--llm", action="store_true", help="usar el LLM configurado")
    parser.add_argument(
        "--modalidad",
        choices=("editorial", "banca"),
        default="editorial",
        help="banca: boletín de entorno con series SBP (extensión, ADR 0003)",
    )
    args = parser.parse_args()
    banca = args.modalidad == "banca"

    casos = _cargar_benchmark(args.benchmark)
    snapshot = cargar_snapshot(RAIZ / "data" / "processed")
    sinteticas = [Evidencia(**e) for c in casos for e in c.get("evidencia_sintetica", [])]
    codificador = cargar_codificador() if args.modo == "hibrido" else None
    corpus = evidencias_de(snapshot, incluir_sbp=banca)
    buscador = Buscador([*corpus, *sinteticas], codificador)
    proveedor = cargar_proveedor() if args.llm else None
    temas = _temas(snapshot, args.modo) if banca else ()

    filas, latencias, tokens, costo = [], [], 0, 0.0
    for caso in casos:
        inicio = time.perf_counter()
        if banca:
            consulta = caso["consulta"]
            resultado = responder(
                consulta,
                buscador,
                proveedor,
                ids_obligatorios=ids_consulta_banca(consulta, temas, snapshot.series_sbp),
                formato=formato_banca(tema_de_consulta(consulta)),
            )
        else:
            resultado = responder(caso["consulta"], buscador, proveedor)
        latencias.append(time.perf_counter() - inicio)
        tokens += resultado.tokens_entrada + resultado.tokens_salida
        costo += resultado.costo_usd
        filas.append(_evaluar_caso(caso, resultado))

    salida: dict[str, Any] = {
        "fecha_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "config": {
            "benchmark": args.benchmark.name,
            "modalidad": args.modalidad,
            "casos": len(casos),
            "busqueda": buscador.modo,
            "redaccion": f"{proveedor.nombre}:{proveedor.modelo}" if proveedor else "extractivo",
            "umbrales": {
                "bm25": UMBRAL_BM25,
                "coseno": UMBRAL_COSENO,
                "coseno_fuerte": UMBRAL_COSENO_FUERTE,
                "cobertura_minima": COBERTURA_MINIMA,
            },
            "version_reglas": RULES_VERSION,
            "snapshot_corte_utc": snapshot.manifest["fecha_corte_utc"],
        },
        "resumen": _resumen(filas, latencias),
        "tokens_totales": tokens,
        "costo_usd": round(costo, 6),
        "fallos": [f for f in filas if not f["aprobado"]],
        "casos": filas,
    }
    destino = RAIZ / "eval-results" / "senal"
    destino.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    sufijo = f"{'_banca' if banca else ''}{'_llm' if args.llm else ''}"
    ruta = destino / f"{marca}_{args.modo}{sufijo}.json"
    ruta.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    _imprimir(salida, ruta)


if __name__ == "__main__":
    main()
