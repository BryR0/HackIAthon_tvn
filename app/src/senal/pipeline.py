"""Integra las etapas 1–5: snapshot → bandeja priorizada de temas con su ficha.

Sin modelo de embeddings degrada a baseline (palabras clave, título idéntico) y lo
rotula en ``Bandeja.modo_ia``. Los vectores de noticias se cachean en disco con
la huella de los títulos y el nombre del modelo para que la demo arranque rápido.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import zipfile
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from senal.banca import periodo_texto
from senal.catalogo import INDICADORES
from senal.context import EnlaceIndicador, EnlaceSismo, enlazar_indicadores, enlazar_sismos
from senal.contradict import Afirmacion, Contradiccion, detectar_contradicciones
from senal.embed import Codificador, Matriz
from senal.evidence import Pieza, contar_procedencias, es_fuente_oficial, estado_evidencia
from senal.ingest import (
    Indicador,
    Noticia,
    SerieSBP,
    Ventana,
    parsear_fecha,
    validar_indicadores,
    validar_noticias,
    validar_series_sbp,
)
from senal.organize import (
    SIN_TEMA,
    UMBRAL_EVENTO,
    VENTANA_EVENTO_DIAS,
    ClasificadorPrototipos,
    Documento,
    agrupar_eventos,
    clasificar_por_palabras,
    normalizar_texto,
)
from senal.retrieve import Evidencia
from senal.score import RULES_VERSION, Puntaje, SenalesEvento, novedad, ordenar, puntuar
from senal.seguridad import es_sospechoso

log = logging.getLogger(__name__)

MODO_BASELINE = "baseline:palabras_clave"
NOMBRE_PAIS = {
    "PAN": "Panamá",
    "CRI": "Costa Rica",
    "COL": "Colombia",
    "DOM": "República Dominicana",
    "MEX": "México",
    "GTM": "Guatemala",
}


@dataclass(frozen=True)
class Snapshot:
    noticias: tuple[Noticia, ...]
    indicadores: tuple[Indicador, ...]
    eventos: tuple[dict[str, Any], ...]
    manifest: dict[str, Any]
    corte: datetime
    series_sbp: tuple[SerieSBP, ...] = ()  # extensión bancaria; vacío si no hay fuente D


@dataclass(frozen=True)
class Tema:
    id_evento: str
    titulo: str
    tema: str
    tema_baseline: str
    noticias: tuple[Noticia, ...]
    procedencias: int
    fuente_oficial: bool
    estado_evidencia: str
    puntaje: Puntaje
    enlaces_indicadores: tuple[EnlaceIndicador, ...]
    enlaces_sismos: tuple[EnlaceSismo, ...]
    contradicciones: tuple[Contradiccion, ...]
    fecha_referencia: datetime
    sospechoso: bool

    @property
    def ids_noticias(self) -> tuple[str, ...]:
        return tuple(n.id_noticia for n in self.noticias)

    @property
    def medios(self) -> tuple[str, ...]:
        return tuple(sorted({n.medio for n in self.noticias}))

    @property
    def accion_recomendada(self) -> str:
        if self.sospechoso:
            return "Revisar con cautela: la fuente contiene instrucciones sospechosas"
        if self.puntaje.banda == "bajo":
            return "Monitorear; no prioritario"
        if self.estado_evidencia == "suficiente_para_borrador":
            return "Preparar borrador para revisión humana"
        return "Investigar: buscar fuente primaria antes de producir"


@dataclass(frozen=True)
class Bandeja:
    temas: tuple[Tema, ...]
    modo_ia: str
    corte: datetime
    version_reglas: str = RULES_VERSION


def _leer_csv(ruta: Path) -> list[dict[str, str | None]]:
    with ruta.open(encoding="utf-8", newline="") as archivo:
        return [{k: (v or None) for k, v in fila.items()} for fila in csv.DictReader(archivo)]


def cargar_snapshot(directorio: Path) -> Snapshot:
    manifest: dict[str, Any] = json.loads((directorio / "manifest.json").read_text("utf-8"))
    todo = Ventana(datetime.min.replace(tzinfo=UTC), datetime.max.replace(tzinfo=UTC))
    noticias = validar_noticias(_leer_csv(directorio / "noticias.csv"), todo).validas
    indicadores = validar_indicadores(_leer_csv(directorio / "indicadores.csv")).validas
    geo = json.loads((directorio / "eventos.geojson").read_text("utf-8"))
    eventos = tuple(f["properties"] for f in geo.get("features", []))
    corte = parsear_fecha(manifest["fecha_corte_utc"])
    ruta_sbp = directorio / "sbp_series.csv"
    series_sbp = validar_series_sbp(_leer_csv(ruta_sbp)).validas if ruta_sbp.exists() else ()
    return Snapshot(noticias, indicadores, eventos, manifest, corte, series_sbp)


def _huella(textos: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(textos).encode("utf-8")).hexdigest()


def vectores_noticias(
    snapshot: Snapshot, codificador: Codificador, cache: Path | None = None
) -> Matriz:
    """Embeddings de títulos, reutilizando la caché si coinciden modelo y huella."""
    titulos = [n.titulo for n in snapshot.noticias]
    huella = _huella(titulos)
    if cache is not None and cache.exists():
        try:
            with np.load(cache, allow_pickle=False) as guardado:
                if (
                    str(guardado["modelo"]) == codificador.modelo
                    and str(guardado["huella"]) == huella
                ):
                    return np.asarray(guardado["vectores"], dtype=np.float32)
        except (OSError, ValueError, KeyError, zipfile.BadZipFile):
            log.warning("Caché de embeddings ilegible (%s); se recalcula", cache.name)
    vectores = codificador.codificar(titulos, "passage").astype(np.float32)
    if cache is not None:
        # float32 (mismo resultado en la primera corrida y con caché) y escritura atómica.
        temporal = cache.with_name(cache.stem + ".tmp.npz")
        np.savez_compressed(temporal, modelo=codificador.modelo, huella=huella, vectores=vectores)
        os.replace(temporal, cache)
    return vectores


def _clusters_baseline(noticias: Sequence[Noticia]) -> tuple[tuple[str, ...], ...]:
    grupos: dict[str, list[str]] = {}
    for n in noticias:
        grupos.setdefault(" ".join(normalizar_texto(n.titulo).split()), []).append(n.id_noticia)
    return tuple(sorted(tuple(sorted(ids)) for ids in grupos.values()))


def _mayoria(temas: Sequence[str]) -> str:
    utiles = [t for t in temas if t != SIN_TEMA]
    return Counter(utiles).most_common(1)[0][0] if utiles else SIN_TEMA


def _representante(noticias: Sequence[Noticia]) -> Noticia:
    return min(noticias, key=lambda n: (n.medio != "tvn-2.com", n.fecha_referencia, n.id_noticia))


def _enlaces(
    miembros: Sequence[Noticia], snapshot: Snapshot
) -> tuple[tuple[EnlaceIndicador, ...], tuple[EnlaceSismo, ...]]:
    indicadores = {
        e.id_evidencia: e
        for n in miembros
        for e in enlazar_indicadores(n.titulo, snapshot.indicadores)
    }
    sismos = {
        s.id_evidencia: s
        for n in miembros
        for s in enlazar_sismos(n.titulo, n.fecha_referencia, snapshot.eventos)
    }
    return tuple(indicadores.values()), tuple(sismos.values())


def _construir_tema(
    miembros: Sequence[Noticia],
    temas_ia: dict[str, str],
    snapshot: Snapshot,
    valor_novedad: float,
) -> Tema:
    titulos = [n.titulo for n in miembros]
    indicadores, sismos = _enlaces(miembros, snapshot)
    fecha = min(n.fecha_referencia for n in miembros)
    procedencias = contar_procedencias([Pieza(n.url, n.titulo, n.descripcion) for n in miembros])
    oficial = any(es_fuente_oficial(n.url) for n in miembros)
    tema = _mayoria([temas_ia.get(n.id_noticia, SIN_TEMA) for n in miembros])
    puntaje = puntuar(
        SenalesEvento(
            id_evento=f"E-{min(n.id_noticia for n in miembros)}",
            tema=tema,
            texto=" ".join(titulos),
            medios=tuple(n.medio for n in miembros),
            fecha_referencia=fecha,
            dato_oficial_enlazado=bool(indicadores or sismos),
            procedencias_independientes=procedencias,
            fuente_oficial=oficial,
            novedad=valor_novedad,
        ),
        snapshot.corte,
    )
    afirmaciones = [Afirmacion(n.id_noticia, n.titulo) for n in miembros]
    return Tema(
        id_evento=puntaje.id_evento,
        titulo=_representante(miembros).titulo,
        tema=tema,
        tema_baseline=_mayoria([clasificar_por_palabras(t) for t in titulos]),
        noticias=tuple(sorted(miembros, key=lambda n: (n.fecha_referencia, n.id_noticia))),
        procedencias=procedencias,
        fuente_oficial=oficial,
        estado_evidencia=estado_evidencia(procedencias, fuente_oficial=oficial),
        puntaje=puntaje,
        enlaces_indicadores=indicadores,
        enlaces_sismos=sismos,
        contradicciones=tuple(detectar_contradicciones(afirmaciones)),
        fecha_referencia=fecha,
        sospechoso=any(es_sospechoso(t) for t in titulos),
    )


def _novedades(
    clusters: Sequence[Sequence[int]], fechas: Sequence[datetime], vectores: Matriz | None
) -> list[float]:
    """N contra eventos que empezaron antes (no depende del orden de proceso)."""
    if vectores is None:
        return [1.0] * len(clusters)
    centroides = np.vstack([vectores[list(c)].mean(axis=0) for c in clusters])
    centroides /= np.linalg.norm(centroides, axis=1, keepdims=True)
    inicio = np.array([min(fechas[i] for i in c).timestamp() for c in clusters])
    similitud = centroides @ centroides.T
    # j es "previo" a k si empezó antes, o a la misma hora con menor índice (desempate
    # estable): dos eventos simultáneos no pueden ser ambos totalmente novedosos.
    indices = np.arange(len(clusters))
    previos = (inicio[None, :] < inicio[:, None]) | (
        (inicio[None, :] == inicio[:, None]) & (indices[None, :] < indices[:, None])
    )
    similitud[~previos] = 0.0
    return [novedad(float(fila.max(initial=0.0))) for fila in similitud]


def construir_bandeja(
    snapshot: Snapshot, codificador: Codificador | None, vectores: Matriz | None = None
) -> Bandeja:
    noticias = snapshot.noticias
    indice = {n.id_noticia: i for i, n in enumerate(noticias)}
    if codificador is not None:
        if vectores is None:
            vectores = codificador.codificar([n.titulo for n in noticias], "passage")
        clasificador = ClasificadorPrototipos(codificador)
        temas_ia = {
            n.id_noticia: c.tema
            for n, c in zip(noticias, clasificador.clasificar_vectores(vectores), strict=True)
        }
        documentos = [Documento(n.id_noticia, n.titulo, n.fecha_referencia) for n in noticias]
        clusters = agrupar_eventos(
            documentos, vectores, umbral=UMBRAL_EVENTO, ventana_dias=VENTANA_EVENTO_DIAS
        )
        modo = f"hibrido:{codificador.modelo}"
    else:
        vectores = None
        temas_ia = {n.id_noticia: clasificar_por_palabras(n.titulo) for n in noticias}
        clusters = _clusters_baseline(noticias)
        modo = MODO_BASELINE

    posiciones = [[indice[i] for i in c] for c in clusters]
    novedades = _novedades(posiciones, [n.fecha_referencia for n in noticias], vectores)
    temas = [
        _construir_tema([noticias[i] for i in pos], temas_ia, snapshot, nov)
        for pos, nov in zip(posiciones, novedades, strict=True)
    ]
    por_id = {t.id_evento: t for t in temas}
    ordenados = tuple(por_id[p.id_evento] for p in ordenar(t.puntaje for t in temas))
    return Bandeja(ordenados, modo, snapshot.corte)


def _fecha(momento: datetime | None) -> str:
    return momento.isoformat() if momento else ""


def _evidencia_sbp(s: SerieSBP) -> Evidencia:
    return Evidencia(
        s.id_evidencia,
        "serie_sbp",
        {
            "nombre": s.nombre,
            "periodo": periodo_texto(s.periodo),
            "valor": f"{s.valor:.10g}" if s.valor is not None else "",
            "unidad": s.unidad or "",
            "variacion_interanual_pct": "" if s.variacion_pct is None else f"{s.variacion_pct:g}",
            "periodo_base": periodo_texto(s.periodo_base) if s.periodo_base else "",
            "cuadro": s.cuadro or "",
            "pagina_pdf": "" if s.pagina_pdf is None else str(s.pagina_pdf),
            "fuente": "Superintendencia de Bancos de Panamá (SBP), Informe de Actividad Bancaria",
            "periodicidad": "dato mensual",
            "url": s.fuente_url or "",
        },
    )


def evidencias_de(snapshot: Snapshot, *, incluir_sbp: bool = False) -> list[Evidencia]:
    """Corpus recuperable: noticias, indicadores con valor y sismos, con IDs estables.

    Las series SBP solo entran en la modalidad bancaria: la recuperación editorial
    no cambia con la extensión.
    """
    evidencias = [
        Evidencia(
            n.id_noticia,
            "noticia",
            {
                "titulo": n.titulo,
                "medio": n.medio,
                "fecha_publicacion": _fecha(n.fecha_publicacion),
                "fecha_deteccion": _fecha(n.fecha_deteccion),
                "url": n.url,
            },
        )
        for n in snapshot.noticias
    ]
    evidencias += [
        Evidencia(
            f"WB:{i.pais_iso3}:{i.indicador_id}:{i.anio}",
            "indicador",
            {
                "nombre": INDICADORES.get(i.indicador_id, i.indicador_id),
                "pais": NOMBRE_PAIS.get(i.pais_iso3, i.pais_iso3),
                "pais_iso3": i.pais_iso3,
                "anio": str(i.anio),
                "valor": f"{i.valor:.4g}",
                "unidad": i.unidad or "",
                "fuente": "Banco Mundial",
                "periodicidad": "dato anual",
                "url": i.fuente_url or "",
            },
        )
        for i in snapshot.indicadores
        if i.valor is not None
    ]
    evidencias += [
        Evidencia(
            f"USGS:{e['id']}",
            "sismo",
            {
                "nombre": "sismo",
                "fuente": "USGS catálogo sísmico",
                "magnitude": str(e.get("magnitude")),
                "time": str(e.get("time")),
                "place": str(e.get("place")),
                "url": str(e.get("url")),
            },
        )
        for e in snapshot.eventos
    ]
    if incluir_sbp:
        evidencias += [_evidencia_sbp(s) for s in snapshot.series_sbp if s.valor is not None]
    return evidencias
