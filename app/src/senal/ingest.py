"""Carga y validación del snapshot (etapa 1 · Cargar, prueba T01).

Reglas del contrato (reto §7):
- Una fila inválida se separa con su motivo; nunca bloquea la carga entera.
- Los nulos se conservan como ``None``; nunca se rellenan con cero.
- Fechas en UTC. ``fecha_publicacion`` y ``fecha_deteccion`` no se mezclan.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

Fila = Mapping[str, str | None]

CAMPOS_OBLIGATORIOS_NOTICIA = ("titulo", "url", "medio", "origen")
PARAMETROS_DE_RASTREO = ("utm_", "fbclid", "gclid", "ocid")
FORMATO_GDELT = "%Y%m%dT%H%M%SZ"
_PERIODO_MENSUAL = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
CAMPOS_OBLIGATORIOS_SBP = ("id_serie", "periodo", "sector")


@dataclass(frozen=True)
class Ventana:
    """Intervalo semiabierto ``[desde, hasta)`` de publicación aceptada."""

    desde: datetime
    hasta: datetime

    def contiene(self, momento: datetime) -> bool:
        return self.desde <= momento < self.hasta


@dataclass(frozen=True)
class Exclusion:
    motivo: str
    campo: str
    fila: Mapping[str, str | None]


@dataclass(frozen=True)
class Noticia:
    id_noticia: str
    titulo: str
    url: str
    medio: str
    idioma: str | None
    fecha_publicacion: datetime | None
    fecha_deteccion: datetime | None
    fecha_extraccion: datetime | None
    origen: str
    alcance_texto: str | None
    tema: str | None = None
    descripcion: str | None = None

    @property
    def fecha_referencia(self) -> datetime:
        """Publicación si existe; si no, detección (GDELT). Nunca ambas mezcladas."""
        referencia = self.fecha_publicacion or self.fecha_deteccion
        if referencia is None:  # pragma: no cover - la validación lo impide
            raise ValueError(f"{self.id_noticia} sin fecha")
        return referencia


@dataclass(frozen=True)
class Indicador:
    pais_iso3: str
    indicador_id: str
    anio: int
    valor: float | None
    unidad: str | None
    fuente_url: str | None
    fecha_extraccion: datetime | None
    licencia: str | None


@dataclass(frozen=True)
class SerieSBP:
    """Valor mensual agregado de un informe de la SBP (fuente D, extensión bancaria).

    Sin datos de clientes ni por banco: solo agregados del sistema por sector.
    """

    id_serie: str
    periodo: str  # "2024-12": mes de cierre del informe
    nombre: str
    sector: str
    valor: float | None
    unidad: str | None
    valor_base: float | None
    periodo_base: str | None  # mismo mes del año anterior (variación interanual)
    variacion_pct: float | None
    cuadro: str | None
    pagina_pdf: int | None  # 1-based del PDF, no la numeración impresa
    fuente_url: str | None
    sha256_pdf: str | None

    @property
    def id_evidencia(self) -> str:
        return f"{self.id_serie}:{self.periodo}"

    def con_valor(self, valor: float | None) -> SerieSBP:
        return replace(self, valor=valor)


@dataclass(frozen=True)
class ResultadoValidacion[T]:
    validas: tuple[T, ...]
    excluidos: tuple[Exclusion, ...]


class _FilaInvalida(Exception):
    def __init__(self, motivo: str, campo: str) -> None:
        super().__init__(f"{motivo}:{campo}")
        self.motivo = motivo
        self.campo = campo


def _texto(fila: Fila, campo: str) -> str | None:
    valor = fila.get(campo)
    if valor is None:
        return None
    limpio = valor.strip()
    return limpio or None


def parsear_fecha(texto: str) -> datetime:
    """ISO 8601, RFC 2822 (RSS) o ``seendate`` de GDELT → ``datetime`` en UTC."""
    candidato = texto.strip()
    try:
        momento = datetime.fromisoformat(candidato.replace("Z", "+00:00"))
    except ValueError:
        try:
            momento = datetime.strptime(candidato, FORMATO_GDELT).replace(tzinfo=UTC)
        except ValueError:
            try:
                momento = parsedate_to_datetime(candidato)
            except (TypeError, ValueError) as error:
                raise ValueError(f"fecha no reconocida: {texto!r}") from error
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(UTC)


def _fecha_opcional(fila: Fila, campo: str) -> datetime | None:
    texto = _texto(fila, campo)
    if texto is None:
        return None
    try:
        return parsear_fecha(texto)
    except ValueError as error:
        raise _FilaInvalida("fecha_invalida", campo) from error


def normalizar_url(url: str) -> str:
    """Forma canónica para deduplicar: host en minúsculas, sin rastreo ni barra final."""
    partes = urlsplit(url.strip())
    consulta = [
        (clave, valor)
        for clave, valor in parse_qsl(partes.query, keep_blank_values=True)
        if not clave.lower().startswith(PARAMETROS_DE_RASTREO)
    ]
    ruta = partes.path.rstrip("/")
    return urlunsplit((partes.scheme.lower(), partes.netloc.lower(), ruta, urlencode(consulta), ""))


def id_estable(prefijo: str, url: str) -> str:
    digesto = hashlib.sha256(normalizar_url(url).encode("utf-8")).hexdigest()
    return f"{prefijo}-{digesto[:12]}"


def _construir_noticia(fila: Fila, ventana: Ventana) -> Noticia:
    for campo in CAMPOS_OBLIGATORIOS_NOTICIA:
        if _texto(fila, campo) is None:
            raise _FilaInvalida("campo_obligatorio", campo)

    url = _texto(fila, "url") or ""
    if urlsplit(url).scheme not in ("http", "https"):
        raise _FilaInvalida("url_invalida", "url")

    publicacion = _fecha_opcional(fila, "fecha_publicacion")
    deteccion = _fecha_opcional(fila, "fecha_deteccion")
    referencia = publicacion or deteccion
    if referencia is None:
        raise _FilaInvalida("campo_obligatorio", "fecha_publicacion")
    if not ventana.contiene(referencia):
        raise _FilaInvalida("fuera_de_ventana", "fecha_publicacion")

    return Noticia(
        id_noticia=_texto(fila, "id_noticia") or id_estable("N", url),
        titulo=_texto(fila, "titulo") or "",
        url=url,
        medio=_texto(fila, "medio") or "",
        idioma=_texto(fila, "idioma"),
        fecha_publicacion=publicacion,
        fecha_deteccion=deteccion,
        fecha_extraccion=_fecha_opcional(fila, "fecha_extraccion"),
        origen=_texto(fila, "origen") or "",
        alcance_texto=_texto(fila, "alcance_texto"),
        tema=_texto(fila, "tema"),
        descripcion=_texto(fila, "descripcion"),
    )


def validar_noticias(filas: Iterable[Fila], ventana: Ventana) -> ResultadoValidacion[Noticia]:
    validas: list[Noticia] = []
    excluidos: list[Exclusion] = []
    vistas: set[str] = set()

    for fila in filas:
        try:
            noticia = _construir_noticia(fila, ventana)
        except _FilaInvalida as error:
            excluidos.append(Exclusion(error.motivo, error.campo, dict(fila)))
            continue

        clave = normalizar_url(noticia.url)
        if clave in vistas:
            excluidos.append(Exclusion("url_duplicada", "url", dict(fila)))
            continue
        vistas.add(clave)
        validas.append(noticia)

    return ResultadoValidacion(tuple(validas), tuple(excluidos))


def _construir_indicador(fila: Fila) -> Indicador:
    pais = _texto(fila, "pais_iso3")
    if pais is None:
        raise _FilaInvalida("campo_obligatorio", "pais_iso3")
    indicador_id = _texto(fila, "indicador_id")
    if indicador_id is None:
        raise _FilaInvalida("campo_obligatorio", "indicador_id")

    try:
        anio = int(_texto(fila, "anio") or "")
    except ValueError as error:
        raise _FilaInvalida("anio_invalido", "anio") from error

    texto_valor = _texto(fila, "valor")
    try:
        valor = None if texto_valor is None else float(texto_valor)
    except ValueError as error:
        raise _FilaInvalida("valor_invalido", "valor") from error

    return Indicador(
        pais_iso3=pais.upper(),
        indicador_id=indicador_id,
        anio=anio,
        valor=valor,
        unidad=_texto(fila, "unidad"),
        fuente_url=_texto(fila, "fuente_url"),
        fecha_extraccion=_fecha_opcional(fila, "fecha_extraccion"),
        licencia=_texto(fila, "licencia"),
    )


def validar_indicadores(filas: Iterable[Fila]) -> ResultadoValidacion[Indicador]:
    validas: list[Indicador] = []
    excluidos: list[Exclusion] = []
    for fila in filas:
        try:
            validas.append(_construir_indicador(fila))
        except _FilaInvalida as error:
            excluidos.append(Exclusion(error.motivo, error.campo, dict(fila)))
    return ResultadoValidacion(tuple(validas), tuple(excluidos))


def completar_cuadricula(
    observados: Iterable[Indicador],
    *,
    paises: Iterable[str],
    indicadores: Iterable[str],
    anios: Iterable[int],
    unidades: Mapping[str, str],
    fecha_extraccion: datetime,
    licencia: str = "CC BY 4.0",
) -> tuple[Indicador, ...]:
    """País × indicador × año completo; las combinaciones ausentes quedan con ``valor=None``."""
    por_clave = {(i.pais_iso3, i.indicador_id, i.anio): i for i in observados}
    anios_ordenados = tuple(anios)
    cuadricula: list[Indicador] = []

    for pais in paises:
        for indicador_id in indicadores:
            for anio in anios_ordenados:
                existente = por_clave.get((pais, indicador_id, anio))
                cuadricula.append(
                    existente
                    or Indicador(
                        pais_iso3=pais,
                        indicador_id=indicador_id,
                        anio=anio,
                        valor=None,
                        unidad=unidades.get(indicador_id),
                        fuente_url=None,
                        fecha_extraccion=fecha_extraccion,
                        licencia=licencia,
                    )
                )
    return tuple(cuadricula)


def _numero_opcional(fila: Fila, campo: str) -> float | None:
    texto = _texto(fila, campo)
    try:
        return None if texto is None else float(texto)
    except ValueError as error:
        raise _FilaInvalida(f"{campo}_invalido", campo) from error


def _entero_opcional(fila: Fila, campo: str) -> int | None:
    valor = _numero_opcional(fila, campo)
    return None if valor is None else int(valor)


def _periodo_opcional(fila: Fila, campo: str) -> str | None:
    texto = _texto(fila, campo)
    if texto is not None and not _PERIODO_MENSUAL.fullmatch(texto):
        raise _FilaInvalida("periodo_invalido", campo)
    return texto


def _construir_serie_sbp(fila: Fila) -> SerieSBP:
    for campo in CAMPOS_OBLIGATORIOS_SBP:
        if _texto(fila, campo) is None:
            raise _FilaInvalida("campo_obligatorio", campo)
    periodo = _periodo_opcional(fila, "periodo")
    valor = _numero_opcional(fila, "valor")
    assert periodo is not None
    return SerieSBP(
        id_serie=_texto(fila, "id_serie") or "",
        periodo=periodo,
        nombre=_texto(fila, "nombre") or "",
        sector=_texto(fila, "sector") or "",
        valor=valor,
        unidad=_texto(fila, "unidad"),
        valor_base=_numero_opcional(fila, "valor_base"),
        periodo_base=_periodo_opcional(fila, "periodo_base"),
        variacion_pct=_numero_opcional(fila, "variacion_pct"),
        cuadro=_texto(fila, "cuadro"),
        pagina_pdf=_entero_opcional(fila, "pagina_pdf"),
        fuente_url=_texto(fila, "fuente_url"),
        sha256_pdf=_texto(fila, "sha256_pdf"),
    )


def validar_series_sbp(filas: Iterable[Fila]) -> ResultadoValidacion[SerieSBP]:
    """Carga de ``sbp_series.csv``: nulos se conservan; filas inválidas se separan (T01)."""
    validas: list[SerieSBP] = []
    excluidos: list[Exclusion] = []
    for fila in filas:
        try:
            validas.append(_construir_serie_sbp(fila))
        except _FilaInvalida as error:
            excluidos.append(Exclusion(error.motivo, error.campo, dict(fila)))
    return ResultadoValidacion(tuple(validas), tuple(excluidos))
