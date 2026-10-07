"""Genera las fichas trazables para la página "Casos y evidencias" de Notion (reto §5).

    uv run python evals/fichas_demo.py

Elige, de la bandeja real: los 3 temas de mayor prioridad, el de mayor prioridad con
evidencia apenas parcial (caso sin evidencia suficiente para borrador) y una consulta
sin sustento (abstención). Redacta con la plantilla extractiva para que el resultado
sea reproducible. El estado de revisión queda "nuevo": la decisión es humana.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from senal.embed import cargar_codificador
from senal.generate import ResultadoRespuesta, responder
from senal.pipeline import (
    Tema,
    cargar_snapshot,
    construir_bandeja,
    evidencias_de,
    vectores_noticias,
)
from senal.retrieve import Buscador
from senal.review import ficha_contrato

RAIZ = Path(__file__).resolve().parents[1]
PROCESADO = RAIZ / "data" / "processed"
PAGINA = RAIZ.parent / "docs" / "notion" / "04-casos-y-evidencias.md"
SALIDA_JSONL = RAIZ / "evals" / "fichas_demo.jsonl"
CONSULTA_SIN_SUSTENTO = "crecimiento del PIB de Panamá en 2026 según el Banco Mundial"
MAX_IDS = 8


def _ids(tema: Tema) -> list[str]:
    return [
        *tema.ids_noticias,
        *(e.id_evidencia for e in tema.enlaces_indicadores),
        *(e.id_evidencia for e in tema.enlaces_sismos),
    ]


def _markdown_tema(n: int, tema: Tema, r: ResultadoRespuesta, motivo: str) -> list[str]:
    p = tema.puntaje
    resto = " …" if len(tema.ids_noticias) > MAX_IDS else ""
    lineas = [
        f"## Ficha {n} · {tema.id_evento} — {motivo}",
        "",
        f"**Tema:** {tema.titulo}",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Fuentes (IDs) | {', '.join(tema.ids_noticias[:MAX_IDS])}{resto} |",
        f"| Medios | {', '.join(tema.medios[:6])} |",
        f"| Puntaje | {p.total} ({p.banda}) · R {p.r:.2f} · I {p.i:.2f} · U {p.u:.2f}"
        f" · N {p.n:.2f} · E {p.e:.2f} · reglas {p.version} |",
        f"| Procedencias independientes | {tema.procedencias} de {len(tema.noticias)} notas |",
        f"| Estado de evidencia | {tema.estado_evidencia} |",
        f"| Acción recomendada | {tema.accion_recomendada} |",
        "| Estado de revisión | nuevo — pendiente de persona revisora |",
        "",
        "**Afirmaciones del borrador (plantilla extractiva) con citas:**",
        "",
    ]
    for a in r.aceptadas[:5]:
        citas = ", ".join(f"{c.id_evidencia}·{c.campo}" for c in a.citas)
        lineas.append(f"- *{a.tipo}* — {a.texto} `[{citas}]`")
    lineas += ["", f"**Brief:** {r.paquete.brief if r.paquete else '—'}", ""]
    return lineas


def _ficha_abstencion(buscador: Buscador) -> tuple[list[str], dict[str, Any]]:
    r = responder(CONSULTA_SIN_SUSTENTO, buscador, None)
    lineas = [
        "## Ficha 5 · consulta sin evidencia — abstención",
        "",
        f"**Consulta:** {CONSULTA_SIN_SUSTENTO}",
        "",
        f"**Resultado:** {'abstención' if r.abstencion else 'respondida'}. {r.motivo}",
        "",
        "El corpus solo tiene datos anuales del Banco Mundial hasta 2024; el sistema no"
        " presenta el dato de 2024 como si fuera de 2026 (T04, T06).",
        "",
    ]
    fila = {
        "id_caso": "Q-PIB-2026",
        "consulta": CONSULTA_SIN_SUSTENTO,
        "abstencion": r.abstencion,
        "motivo": r.motivo,
        "estado_revision": "nuevo",
        "publicado": False,
    }
    return lineas, fila


def main() -> None:
    snapshot = cargar_snapshot(PROCESADO)
    codificador = cargar_codificador()
    vectores = (
        vectores_noticias(snapshot, codificador, PROCESADO / "embeddings.npz")
        if codificador
        else None
    )
    bandeja = construir_bandeja(snapshot, codificador, vectores)
    buscador = Buscador(evidencias_de(snapshot), codificador)

    elegidos: list[tuple[Tema, str]] = [(t, "prioridad alta") for t in bandeja.temas[:3]]
    parcial = next(t for t in bandeja.temas[3:] if t.estado_evidencia != "suficiente_para_borrador")
    elegidos.append((parcial, "evidencia insuficiente para borrador: requiere investigación"))

    lineas = [
        "# Casos y evidencias",
        "",
        f"Fichas trazables generadas de la bandeja real (corte "
        f"{snapshot.manifest['fecha_corte_utc']}, {bandeja.modo_ia}). Redacción con plantilla"
        " extractiva para que sea reproducible: `uv run python evals/fichas_demo.py`."
        " La decisión de revisión es humana.",
        "",
    ]
    filas: list[dict[str, Any]] = []
    for n, (tema, motivo) in enumerate(elegidos, 1):
        r = responder(tema.titulo, buscador, None, ids_obligatorios=_ids(tema))
        lineas += _markdown_tema(n, tema, r, motivo)
        filas.append(ficha_contrato(tema, r, None))

    lineas_abst, fila_abst = _ficha_abstencion(buscador)
    lineas += lineas_abst
    filas.append(fila_abst)

    PAGINA.write_text("\n".join(lineas), encoding="utf-8")
    SALIDA_JSONL.write_text(
        "\n".join(json.dumps(f, ensure_ascii=False) for f in filas) + "\n", encoding="utf-8"
    )
    print(f"{len(filas)} fichas -> {PAGINA.name} y {SALIDA_JSONL.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
