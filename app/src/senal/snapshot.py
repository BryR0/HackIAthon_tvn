"""raw/ → processed/ (Paso 1): validar, deduplicar, completar y sellar con SHA-256.

Determinista: mismo raw produce los mismos bytes. La fecha de corte sale de
``extraccion.json``, nunca del reloj. Los nulos se escriben como celda vacía en
CSV y ``null`` en JSON (``diccionario.md``).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from senal import catalogo, sbp
from senal.fuentes import parsear_gdelt, parsear_rss_tvn, parsear_usgs, parsear_worldbank
from senal.ingest import (
    Exclusion,
    Indicador,
    Noticia,
    SerieSBP,
    Ventana,
    completar_cuadricula,
    parsear_fecha,
    validar_indicadores,
    validar_noticias,
)

COLUMNAS_NOTICIAS = (
    "id_noticia",
    "titulo",
    "url",
    "medio",
    "idioma",
    "fecha_publicacion",
    "fecha_deteccion",
    "fecha_extraccion",
    "tema",
    "origen",
    "alcance_texto",
    "descripcion",
)
COLUMNAS_INDICADORES = (
    "pais_iso3",
    "indicador_id",
    "anio",
    "valor",
    "unidad",
    "fuente_url",
    "fecha_extraccion",
    "licencia",
)
COLUMNAS_SBP = (
    "id_serie",
    "periodo",
    "nombre",
    "sector",
    "valor",
    "unidad",
    "valor_base",
    "periodo_base",
    "variacion_pct",
    "cuadro",
    "pagina_pdf",
    "fuente_url",
    "sha256_pdf",
)
COLUMNAS_EXCLUIDOS = ("tipo", "motivo", "campo", "referencia", "fila")
# La revisión editorial es en español/inglés; otros idiomas se excluyen y se registran.
IDIOMAS_SOPORTADOS = frozenset({"es", "en"})
TRANSFORMACIONES = (
    "Fechas a UTC ISO 8601; seendate de GDELT solo como fecha_deteccion",
    "URL normalizada (host en minúsculas, sin parámetros utm/fbclid, sin barra final)",
    "Deduplicación por URL normalizada; prioridad TVN RSS sobre GDELT",
    "Exclusión de noticias fuera de la ventana de extracción",
    "Exclusión de noticias en idiomas distintos de español e inglés",
    "Descripción del RSS de TVN omitida hasta autorización del patrocinador (solo metadatos)",
    "Cuadrícula país × indicador × año completada con valor nulo",
    "Unidad del Banco Mundial derivada del nombre del indicador cuando 'unit' viene vacío",
)
TRANSFORMACIONES_SBP = (
    f"SBP: tabla de crédito local por sector extraída con pypdf ({sbp.VERSION_PARSER}); "
    "anclada por encabezado del mes, valores sin separador de miles, página 1-based del PDF",
    "SBP: sumas de sectores validadas con tolerancia de redondeo ±0,5 por sumando",
)
LectorPdf = Callable[[Path], dict[int, str]]


def _iso(momento: datetime | None) -> str:
    return "" if momento is None else momento.isoformat()


def _celda(valor: object) -> str:
    return "" if valor is None else str(valor)


def _csv(columnas: Sequence[str], filas: Iterable[Sequence[object]]) -> bytes:
    buffer = io.StringIO()
    escritor = csv.writer(buffer, lineterminator="\n")
    escritor.writerow(columnas)
    escritor.writerows([_celda(v) for v in fila] for fila in filas)
    return buffer.getvalue().encode("utf-8")


def _json(dato: object) -> bytes:
    return (json.dumps(dato, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _cargar_registro(raw: Path) -> dict[str, Any]:
    registro: dict[str, Any] = json.loads((raw / "extraccion.json").read_text(encoding="utf-8"))
    return registro


def _exitosas(registro: dict[str, Any], prefijo: str) -> list[dict[str, Any]]:
    return sorted(
        (
            s
            for s in registro["solicitudes"]
            if s["fuente"].startswith(prefijo) and s["estado"] == 200 and s["archivo"]
        ),
        key=lambda s: str(s["archivo"]),
    )


def _filas_noticias(raw: Path, registro: dict[str, Any], corte: datetime) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for solicitud in _exitosas(registro, "tvn_rss"):
        filas.extend(parsear_rss_tvn((raw / solicitud["archivo"]).read_text("utf-8"), corte))
    for solicitud in _exitosas(registro, "gdelt"):
        consulta = solicitud["fuente"].split(":", 1)[1]
        texto = (raw / solicitud["archivo"]).read_text("utf-8")
        filas.extend(parsear_gdelt(texto, corte, consulta))
    return filas


def _filas_indicadores(raw: Path, registro: dict[str, Any], corte: datetime) -> list[Any]:
    filas: list[Any] = []
    for solicitud in _exitosas(registro, "worldbank"):
        texto = (raw / solicitud["archivo"]).read_text("utf-8")
        filas.extend(parsear_worldbank(texto, corte, solicitud["url"]))
    return filas


def _eventos(raw: Path, registro: dict[str, Any]) -> list[dict[str, Any]]:
    eventos: list[dict[str, Any]] = []
    for solicitud in _exitosas(registro, "usgs"):
        eventos.extend(parsear_usgs((raw / solicitud["archivo"]).read_text("utf-8")))
    return sorted(eventos, key=lambda e: str(e["id"]))


def _series_sbp(
    raw: Path, registro: dict[str, Any], leer_pdf: LectorPdf
) -> tuple[list[SerieSBP], list[Exclusion]]:
    series: list[SerieSBP] = []
    excluidos: list[Exclusion] = []
    base = raw.resolve()
    for solicitud in _exitosas(registro, "sbp:"):
        ruta = raw / solicitud["archivo"]
        fila = {"archivo": str(solicitud["archivo"]), "url": solicitud["url"]}
        # extraccion.json es local, pero no se lee nada fuera de raw/.
        if not ruta.resolve().is_relative_to(base):
            excluidos.append(Exclusion("ruta_fuera_de_raw", "archivo", fila))
            continue
        if not ruta.exists():
            excluidos.append(Exclusion("pdf_no_disponible", "archivo", fila))
            continue
        try:
            periodo = sbp.periodo_de_archivo(ruta.name)
            paginas = leer_pdf(ruta)
        except (ValueError, OSError):
            excluidos.append(Exclusion("pdf_ilegible", "archivo", fila))
            continue
        nuevas, exclusiones = sbp.extraer_credito_local(
            paginas,
            periodo=periodo,
            fuente_url=solicitud["url"],
            sha256_pdf=solicitud.get("sha256") or "",
        )
        series.extend(nuevas)
        excluidos.extend(exclusiones)
    excluidos.extend(sbp.validar_sumas(series))
    return sorted(series, key=lambda s: (s.periodo, s.id_serie)), excluidos


def _fila_sbp(s: SerieSBP) -> tuple[object, ...]:
    return (
        s.id_serie,
        s.periodo,
        s.nombre,
        s.sector,
        s.valor,
        s.unidad,
        s.valor_base,
        s.periodo_base,
        s.variacion_pct,
        s.cuadro,
        s.pagina_pdf,
        s.fuente_url,
        s.sha256_pdf,
    )


def _reporte_sbp(series: Sequence[SerieSBP], excluidos: Sequence[Exclusion]) -> dict[str, Any]:
    periodos = sorted({s.periodo for s in series if s.valor is not None})
    return {
        "filas": len(series),
        "nulos": sum(s.valor is None for s in series),
        "periodos": periodos,
        "periodos_faltantes": len(catalogo.SBP_MESES) - len(periodos),
        "inconsistencias": sum(e.motivo.startswith("suma_") for e in excluidos),
        "excluidas_por_motivo": dict(sorted(Counter(e.motivo for e in excluidos).items())),
    }


def _geojson(eventos: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": e["id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [e["longitude"], e["latitude"], e["depth"]],
                },
                "properties": e,
            }
            for e in eventos
        ],
    }


def _fila_noticia(n: Noticia) -> tuple[object, ...]:
    con_extracto = catalogo.USAR_EXTRACTOS_TVN or n.origen != "tvn_rss"
    return (
        n.id_noticia,
        n.titulo,
        n.url,
        n.medio,
        n.idioma,
        _iso(n.fecha_publicacion),
        _iso(n.fecha_deteccion),
        _iso(n.fecha_extraccion),
        n.tema,
        n.origen,
        n.alcance_texto if con_extracto else "titular_metadatos",
        n.descripcion if con_extracto else None,
    )


def _fila_indicador(i: Indicador) -> tuple[object, ...]:
    return (
        i.pais_iso3,
        i.indicador_id,
        i.anio,
        i.valor,
        i.unidad,
        i.fuente_url,
        _iso(i.fecha_extraccion),
        i.licencia,
    )


def _fila_exclusion(tipo: str, e: Exclusion) -> tuple[object, ...]:
    referencia = e.fila.get("url") or e.fila.get("indicador_id") or ""
    return (tipo, e.motivo, e.campo, referencia, json.dumps(dict(e.fila), ensure_ascii=False))


def _filtrar_idioma(
    noticias: Iterable[Noticia],
) -> tuple[list[Noticia], list[Exclusion]]:
    soportadas: list[Noticia] = []
    excluidas: list[Exclusion] = []
    for n in noticias:
        if (n.idioma or "") in IDIOMAS_SOPORTADOS:
            soportadas.append(n)
        else:
            fila = {"url": n.url, "titulo": n.titulo, "idioma": n.idioma, "origen": n.origen}
            excluidas.append(Exclusion("idioma_no_soportado", "idioma", fila))
    return soportadas, excluidas


def _reporte(
    noticias: Sequence[Noticia],
    excluidas: Sequence[Exclusion],
    indicadores: Sequence[Indicador],
    eventos: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "noticias": {
            "validas": len(noticias),
            "excluidas_por_motivo": dict(sorted(Counter(e.motivo for e in excluidas).items())),
            "por_origen": dict(sorted(Counter(n.origen for n in noticias).items())),
            "por_medio": dict(sorted(Counter(n.medio for n in noticias).items())),
            "sin_fecha_publicacion": sum(n.fecha_publicacion is None for n in noticias),
            "de_tvn": sum(n.medio == "tvn-2.com" for n in noticias),
        },
        "indicadores": {
            "filas": len(indicadores),
            "nulos": sum(i.valor is None for i in indicadores),
        },
        "eventos": {"total": len(eventos)},
    }


def construir_snapshot(
    raw: Path, salida: Path, *, leer_pdf: LectorPdf = sbp.leer_paginas_pdf
) -> dict[str, Any]:
    """Construye ``processed/`` desde ``raw/`` y devuelve el manifest escrito.

    La fuente D (SBP) es opcional: sin solicitudes ``sbp:`` no se escribe
    ``sbp_series.csv`` y el paquete editorial queda idéntico.
    """
    registro = _cargar_registro(raw)
    corte = parsear_fecha(registro["fecha_corte_utc"])
    ventana = Ventana(
        corte - timedelta(days=catalogo.VENTANA_NOTICIAS_DIAS), corte + timedelta(seconds=1)
    )

    noticias_res = validar_noticias(_filas_noticias(raw, registro, corte), ventana)
    soportadas, por_idioma = _filtrar_idioma(noticias_res.validas)
    noticias = sorted(soportadas, key=lambda n: n.id_noticia)
    excluidas_noticias = [*noticias_res.excluidos, *por_idioma]
    indicadores_res = validar_indicadores(_filas_indicadores(raw, registro, corte))
    indicadores = completar_cuadricula(
        indicadores_res.validas,
        paises=catalogo.PAISES,
        indicadores=tuple(catalogo.INDICADORES),
        anios=catalogo.ANIOS,
        unidades={i.indicador_id: i.unidad for i in indicadores_res.validas if i.unidad},
        fecha_extraccion=corte,
    )
    eventos = _eventos(raw, registro)
    con_sbp = any(s["fuente"].startswith("sbp:") for s in registro["solicitudes"])
    series_sbp, excluidas_sbp = _series_sbp(raw, registro, leer_pdf) if con_sbp else ([], [])
    excluidos = (
        [_fila_exclusion("noticia", e) for e in excluidas_noticias]
        + [_fila_exclusion("indicador", e) for e in indicadores_res.excluidos]
        + [_fila_exclusion("sbp", e) for e in excluidas_sbp]
    )

    reporte = _reporte(noticias, excluidas_noticias, indicadores, eventos)
    contenidos = {
        "noticias.csv": _csv(COLUMNAS_NOTICIAS, map(_fila_noticia, noticias)),
        "indicadores.csv": _csv(COLUMNAS_INDICADORES, map(_fila_indicador, indicadores)),
        "eventos.geojson": _json(_geojson(eventos)),
        "excluidos.csv": _csv(COLUMNAS_EXCLUIDOS, excluidos),
    }
    conteos_sbp: dict[str, int] = {}
    if con_sbp:
        contenidos["sbp_series.csv"] = _csv(COLUMNAS_SBP, map(_fila_sbp, series_sbp))
        reporte["sbp"] = _reporte_sbp(series_sbp, excluidas_sbp)
        conteos_sbp["sbp_series.csv"] = len(series_sbp)
    contenidos["reporte_calidad.json"] = _json(reporte)
    salida.mkdir(parents=True, exist_ok=True)
    for nombre, contenido in contenidos.items():
        (salida / nombre).write_bytes(contenido)

    manifest: dict[str, Any] = {
        "version": registro["version"],
        "fecha_corte_utc": corte.isoformat(),
        "ventana_noticias": [ventana.desde.isoformat(), corte.isoformat()],
        "consultas": [
            {k: s.get(k) for k in ("fuente", "url", "params", "estado", "sha256")}
            for s in registro["solicitudes"]
        ],
        "solicitudes_fallidas": [
            {"fuente": s["fuente"], "estado": s["estado"]}
            for s in registro["solicitudes"]
            if s["estado"] != 200
        ],
        "conteos": {
            "noticias.csv": len(noticias),
            "indicadores.csv": len(indicadores),
            "eventos.geojson": len(eventos),
            "excluidos.csv": len(excluidos),
            **conteos_sbp,
        },
        "archivos": {n: hashlib.sha256(c).hexdigest() for n, c in sorted(contenidos.items())},
        "licencias": [
            {"ref": f.ref, "fuente": f.nombre, "url": f.url, "condiciones": f.condiciones}
            for f in catalogo.FUENTES
        ],
        "transformaciones": [*TRANSFORMACIONES, *(TRANSFORMACIONES_SBP if con_sbp else ())],
        "desviaciones": [
            "D6 (ADR 0002): noticias de los últimos "
            f"{catalogo.VENTANA_NOTICIAS_DIAS} días antes del corte, no [2024-01-01, 2025-10-01); "
            "ninguna fuente pública de noticias alcanza 2024 desde 2026-10."
        ],
    }
    (salida / "manifest.json").write_bytes(_json(manifest))
    return manifest
