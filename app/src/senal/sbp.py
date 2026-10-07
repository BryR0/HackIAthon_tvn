"""Fuente D · SBP: crédito local por sector de los Informes de Actividad Bancaria.

Extensión bancaria (ADR 0003). Reglas:
- Se ancla por el encabezado ``Sector <mes>-23 <mes>-24`` del mes del informe, nunca
  por número de cuadro ni de página: ambos cambian entre meses. Así se descarta la
  tabla por provincias, que no tiene columna base.
- Siempre se emiten los 13 sectores por período; lo que no se encuentra queda
  ``None`` con su exclusión. Una tabla ausente no bloquea la carga (T01).
- Valores sin separador de miles: el validador de citas lee la coma como decimal.
- Solo agregados del sistema; ningún dato por banco ni por cliente (reto §6 D).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from senal.ingest import Exclusion, SerieSBP
from senal.organize import normalizar_texto

VERSION_PARSER = "sbp-credito-local-1.0.0"
UNIDAD = "millones USD"
# Topes al leer un PDF descargado: un informe real pesa ~1,5 MB y tiene ~24 páginas.
MAX_BYTES_PDF = 20 * 1024 * 1024
MAX_PAGINAS_PDF = 120
PREFIJO_SERIE = "SBP:credito_local"
NOMBRE_TABLA = "Crédito local SBN"

# slug → (nombre canónico, patrón sobre la etiqueta normalizada). Orden del cuadro.
SECTORES: Mapping[str, tuple[str, str]] = {
    "total": ("Total", r"total"),
    "sector_publico": ("Sector Público", r"sector publico"),
    "sector_privado": ("Sector Privado", r"sector privado"),
    "act_financieras_seguros": (
        "Act. Financieras y Seguros",
        r"act\.? financieras? y (?:de )?seguros",
    ),
    "agricultura": ("Agricultura", r"agricultura"),
    "ganaderia": ("Ganadería", r"ganaderia"),
    "pesca": ("Pesca", r"pesca"),
    "minas_canteras": ("Minas y Canteras", r"minas y canteras"),
    "comercio": ("Comercio", r"comercio"),
    "industria": ("Industria", r"industria"),
    "hipotecario": ("Hipotecario", r"hipotecario"),
    "construccion": ("Construcción", r"construccion"),
    "consumo_personal": ("Consumo Personal", r"consumo personal"),
}
AGREGADOS = ("total", "sector_publico", "sector_privado")
SECTORES_PRIVADOS = tuple(s for s in SECTORES if s not in AGREGADOS)

MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
}  # fmt: skip

_ARCHIVO = re.compile(r"IAB-(\d{2})(\d{2})\.pdf$", re.IGNORECASE)
_NUM = r"-?\d[\d,]*(?:\.\d+)?"
_ENCABEZADO = re.compile(
    r"^\s*Sector\s+([a-záéíóú]+)[-.](\d{2})\s+([a-záéíóú]+)[-.](\d{2})\b", re.IGNORECASE
)
_FILA = re.compile(
    rf"^\s*(?P<etiqueta>[^\d\n]*?[a-záéíóúñ.)])\s+(?P<base>{_NUM})\s+(?P<valor>{_NUM})"
    rf"\s+(?P<abs>{_NUM})\s+(?P<pct>-?\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_UNIDAD = re.compile(r"en millones (?:de )?usd", re.IGNORECASE)
_DIGITO = re.compile(r"\d")


def periodo_de_archivo(nombre: str) -> str:
    """``IAB-1224.pdf`` → ``2024-12``."""
    coincidencia = _ARCHIVO.search(nombre)
    if coincidencia is None:
        raise ValueError(f"nombre de informe SBP no reconocido: {nombre!r}")
    mes, anio = coincidencia.groups()
    return f"20{anio}-{mes}"


def _numero(texto: str) -> float:
    return float(texto.replace(",", ""))


def _mes(texto: str) -> int | None:
    return MESES.get(normalizar_texto(texto)[:3])


def _sector(etiqueta: str) -> str | None:
    normalizada = " ".join(normalizar_texto(etiqueta).split())
    for slug, (_, patron) in SECTORES.items():
        if re.fullmatch(patron, normalizada):
            return slug
    return None


def _serie(
    slug: str,
    periodo: str,
    fuente_url: str,
    sha256_pdf: str,
    *,
    fila: tuple[float, float, float] | None = None,
    periodo_base: str | None = None,
    cuadro: str | None = None,
    pagina_pdf: int | None = None,
) -> SerieSBP:
    base, valor, variacion = fila if fila is not None else (None, None, None)
    return SerieSBP(
        id_serie=f"{PREFIJO_SERIE}:{slug}",
        periodo=periodo,
        nombre=f"{NOMBRE_TABLA} · {SECTORES[slug][0]}",
        sector=slug,
        valor=valor,
        unidad=UNIDAD,
        valor_base=base,
        periodo_base=periodo_base,
        variacion_pct=variacion,
        cuadro=cuadro,
        pagina_pdf=pagina_pdf,
        fuente_url=fuente_url,
        sha256_pdf=sha256_pdf,
    )


def _filas_de_tabla(lineas: Sequence[str]) -> dict[str, tuple[float, float, float]]:
    """Filas tras el encabezado → (base, valor, variación %). Une etiquetas partidas."""
    encontradas: dict[str, tuple[float, float, float]] = {}
    previa = ""
    for linea in lineas:
        if normalizar_texto(linea).strip().startswith("fuente"):
            break
        fila = _FILA.match(linea)
        if fila is None:
            previa = "" if _DIGITO.search(linea) else linea.strip()
            continue
        etiqueta = fila["etiqueta"]
        slug = _sector(etiqueta) or _sector(f"{previa} {etiqueta}")
        previa = ""
        if slug is not None and slug not in encontradas:
            encontradas[slug] = (_numero(fila["base"]), _numero(fila["valor"]), float(fila["pct"]))
        if len(encontradas) == len(SECTORES):
            break
    return encontradas


def _cuadro(lineas_previas: Sequence[str]) -> str | None:
    for linea in reversed(lineas_previas):
        if "cuadro" in linea.lower():
            return " ".join(linea.split())
    return None


def _exclusion(motivo: str, campo: str, periodo: str, url: str) -> Exclusion:
    return Exclusion(motivo, campo, {"periodo": periodo, "url": url})


def extraer_credito_local(
    paginas: Mapping[int, str],
    *,
    periodo: str,
    fuente_url: str,
    sha256_pdf: str,
) -> tuple[tuple[SerieSBP, ...], tuple[Exclusion, ...]]:
    """Texto por página (1-based) de un informe → 13 series del período."""
    anio, mes = int(periodo[:4]), int(periodo[5:7])
    for numero in sorted(paginas):
        texto = paginas[numero]
        lineas = texto.splitlines()
        for indice, linea in enumerate(lineas):
            encabezado = _ENCABEZADO.match(linea)
            if encabezado is None:
                continue
            mes_base, anio_base, mes_actual, anio_actual = encabezado.groups()
            if _mes(mes_actual) != mes or 2000 + int(anio_actual) != anio:
                continue
            filas = _filas_de_tabla(lineas[indice + 1 :])
            if not filas:
                continue
            mes_de_base = _mes(mes_base)
            periodo_base = (
                f"{2000 + int(anio_base)}-{mes_de_base:02d}" if mes_de_base is not None else None
            )
            cuadro = _cuadro(lineas[:indice])
            series = tuple(
                _serie(
                    slug,
                    periodo,
                    fuente_url,
                    sha256_pdf,
                    fila=filas.get(slug),
                    periodo_base=periodo_base,
                    cuadro=cuadro,
                    pagina_pdf=numero,
                )
                for slug in SECTORES
            )
            excluidos = [
                _exclusion("sector_no_encontrado", slug, periodo, fuente_url)
                for slug in SECTORES
                if slug not in filas
            ]
            if not _UNIDAD.search(texto):
                excluidos.append(_exclusion("unidad_no_declarada", "unidad", periodo, fuente_url))
            if periodo_base is None:
                excluidos.append(
                    _exclusion("periodo_base_no_reconocido", "periodo_base", periodo, fuente_url)
                )
            return series, tuple(excluidos)

    vacias = tuple(_serie(slug, periodo, fuente_url, sha256_pdf) for slug in SECTORES)
    return vacias, (_exclusion("tabla_no_encontrada", "credito_local", periodo, fuente_url),)


def _cerca(suma: float, esperado: float, sumandos: int) -> bool:
    """Tolerancia de redondeo: cada cifra publicada puede diferir ±0,5 de su exacta."""
    return abs(suma - esperado) <= 0.5 * (sumandos + 1)


def validar_sumas(series: Iterable[SerieSBP]) -> list[Exclusion]:
    """Σ sectores privados ≈ Sector Privado; Público + Privado ≈ Total, por período."""
    por_periodo: dict[str, dict[str, float | None]] = {}
    for s in series:
        por_periodo.setdefault(s.periodo, {})[s.sector] = s.valor

    excluidos: list[Exclusion] = []
    for periodo, valores in sorted(por_periodo.items()):
        privados = [valores.get(s) for s in SECTORES_PRIVADOS]
        privado = valores.get("sector_privado")
        if privado is not None and None not in privados:
            suma = sum(v for v in privados if v is not None)
            if not _cerca(suma, privado, len(privados)):
                excluidos.append(
                    Exclusion(
                        "suma_sectores_privados_inconsistente",
                        "sector_privado",
                        {"periodo": periodo, "suma": f"{suma:.1f}", "publicado": f"{privado}"},
                    )
                )
        publico, total = valores.get("sector_publico"), valores.get("total")
        if publico is not None and privado is not None and total is not None:
            if not _cerca(publico + privado, total, 2):
                excluidos.append(
                    Exclusion(
                        "suma_total_inconsistente",
                        "total",
                        {"periodo": periodo, "suma": f"{publico + privado:.1f}"},
                    )
                )
    return excluidos


def leer_paginas_pdf(ruta: Path) -> dict[int, str]:
    """Texto por página (1-based). ``pypdf`` solo se necesita al construir el snapshot.

    Un PDF ilegible, demasiado grande o con demasiadas páginas lanza ``ValueError``:
    quien llama lo registra como exclusión y sigue con los demás meses (T01).
    """
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    if ruta.stat().st_size > MAX_BYTES_PDF:
        raise ValueError(f"PDF demasiado grande: {ruta.name}")
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    try:
        lector = PdfReader(ruta)
        if len(lector.pages) > MAX_PAGINAS_PDF:
            raise ValueError(f"PDF con demasiadas páginas: {ruta.name}")
        return {i + 1: pagina.extract_text() or "" for i, pagina in enumerate(lector.pages)}
    except PyPdfError as error:
        raise ValueError(f"PDF ilegible: {ruta.name}") from error
