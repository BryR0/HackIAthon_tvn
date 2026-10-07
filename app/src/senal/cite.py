"""Validador determinista de citas y compuerta de abstención (reto §7, §8, T04, T06, T09).

Una afirmación se **descarta entera** si:
- su tipo no es hecho/declaración/inferencia/hipótesis;
- no tiene cita, cita evidencia no recuperada o un campo no citable;
- contiene una cifra que no aparece en los campos citados;
- cita un indicador anual sin mencionar el año (no confundir con dato de hoy);
- cita una serie mensual SBP sin su período ``MM/AAAA`` o la presenta como dato de hoy;
- presenta una acusación como hecho (debe ser declaración atribuida);
- incumple una regla extra de la modalidad (p. ej. lenguaje prohibido en banca).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from senal.contradict import normalizar_numero
from senal.organize import normalizar_texto
from senal.retrieve import Evidencia, Resultado

TIPOS_AFIRMACION = frozenset({"hecho", "declaracion", "inferencia", "hipotesis"})
CAMPOS_CITABLES: Mapping[str, frozenset[str]] = {
    "noticia": frozenset(
        {"titulo", "descripcion", "medio", "fecha_publicacion", "fecha_deteccion"}
    ),
    "indicador": frozenset({"nombre", "pais", "pais_iso3", "anio", "valor", "unidad"}),
    "sismo": frozenset({"magnitude", "time", "place"}),
    "serie_sbp": frozenset(
        {"nombre", "periodo", "valor", "unidad", "variacion_interanual_pct", "periodo_base",
         "cuadro", "pagina_pdf"}
    ),
}  # fmt: skip
# Marcadores de actualidad: una serie de 2024 no describe la situación de hoy (T04).
PALABRAS_ACTUALIDAD = frozenset({"hoy", "actual", "actualmente", "ahora", "vigente"})
CAMPOS_CIFRA_SBP = frozenset({"valor", "variacion_interanual_pct", "periodo", "periodo_base"})
# Palabras completas y raíces: "robo" no debe coincidir con "robot" ni "lavado" con "lavadora".
PALABRAS_ACUSACION = frozenset(
    {"culpable", "culpables", "delito", "delitos", "fraude", "robo", "soborno", "sobornos",
     "asesino", "asesinos", "estafa", "estafas", "cometio", "lavado"}
)  # fmt: skip
RAICES_ACUSACION = ("enriquecimiento", "corrup", "peculado", "malversacion")
_NUMERO = re.compile(r"\d+(?:[.,]\d+)*")
_MILES_ES = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?")


@dataclass(frozen=True)
class CitaPropuesta:
    id_evidencia: str
    campo: str


@dataclass(frozen=True)
class AfirmacionPropuesta:
    texto: str
    tipo: str
    citas: tuple[CitaPropuesta, ...]


@dataclass(frozen=True)
class Descartada:
    afirmacion: AfirmacionPropuesta
    motivo: str


# Regla de una modalidad: recibe la afirmación y las evidencias recuperadas por ID.
Regla = Callable[[AfirmacionPropuesta, Mapping[str, Evidencia]], str | None]


@dataclass(frozen=True)
class ResultadoCitas:
    aceptadas: tuple[AfirmacionPropuesta, ...]
    descartadas: tuple[Descartada, ...]


def _valores(crudo: str) -> list[tuple[float, int]]:
    """Interpreta una secuencia numérica: miles es-PA (1.234,5), decimal simple (2,5 o 2.5)
    o, si tiene varios separadores ambiguos (06.10.2026, 2.3.4), cada parte por separado."""
    if _MILES_ES.fullmatch(crudo):
        entero, _, fraccion = crudo.partition(",")
        valor = float(entero.replace(".", "") + ("." + fraccion if fraccion else ""))
        return [(valor, len(fraccion))]
    if crudo.count(".") + crudo.count(",") <= 1:
        valor = normalizar_numero(crudo)
        decimales = 0 if valor.is_integer() else len(crudo.replace(",", ".").split(".")[-1])
        return [(valor, decimales)]
    return [(float(parte), 0) for parte in re.split(r"[.,]", crudo) if parte]


def _numeros(texto: str) -> list[tuple[float, int]]:
    """Cifras con su cantidad de decimales, para comparar con la precisión de la afirmación."""
    return [par for crudo in _NUMERO.findall(texto) for par in _valores(crudo)]


def cifras_respaldadas(texto: str, fuentes: Sequence[str]) -> bool:
    """Toda cifra o año de ``texto`` aparece en alguna de ``fuentes``."""
    return _cifras_respaldadas(texto, fuentes)


def _cifras_respaldadas(texto: str, fuentes: Sequence[str]) -> bool:
    disponibles = [v for f in fuentes for v, _ in _numeros(f)]
    return all(
        any(round(f, decimales) == valor for f in disponibles)
        for valor, decimales in _numeros(texto)
    )


def _es_acusacion(texto: str) -> bool:
    tokens = normalizar_texto(texto).split()
    return any(t in PALABRAS_ACUSACION or t.startswith(RAICES_ACUSACION) for t in tokens)


def _motivo_descarte(
    afirmacion: AfirmacionPropuesta, evidencias: Mapping[str, Evidencia]
) -> str | None:
    if afirmacion.tipo not in TIPOS_AFIRMACION:
        return "tipo_invalido"
    if not afirmacion.citas:
        return "sin_cita"
    citadas: list[tuple[Evidencia, str]] = []
    for cita in afirmacion.citas:
        evidencia = evidencias.get(cita.id_evidencia)
        if evidencia is None:
            return "evidencia_no_recuperada"
        if cita.campo not in CAMPOS_CITABLES.get(evidencia.tipo, frozenset()):
            return "campo_no_citable"
        citadas.append((evidencia, cita.campo))

    if not _cifras_respaldadas(afirmacion.texto, [e.campos.get(c, "") for e, c in citadas]):
        return "cifra_sin_respaldo"
    motivo_periodo = _motivo_periodo(afirmacion.texto, citadas)
    if motivo_periodo is not None:
        return motivo_periodo
    if afirmacion.tipo == "hecho" and _es_acusacion(afirmacion.texto):
        return "acusacion_como_hecho"
    return None


def _motivo_periodo(texto: str, citadas: Sequence[tuple[Evidencia, str]]) -> str | None:
    """Indicador anual con su año; cifra de una serie mensual con su ``MM/AAAA``; ninguna
    serie mensual presentada como dato de hoy."""
    cifras_sbp = {e.id for e, campo in citadas if campo in CAMPOS_CIFRA_SBP}
    for evidencia, _ in citadas:
        anio = evidencia.campos.get("anio")
        if evidencia.tipo == "indicador" and anio and anio not in texto:
            return "indicador_sin_anio"
        if evidencia.tipo != "serie_sbp":
            continue
        periodo = evidencia.campos.get("periodo", "")
        if evidencia.id in cifras_sbp and periodo not in texto:
            return "serie_sin_periodo"
        if PALABRAS_ACTUALIDAD & set(normalizar_texto(texto).split()):
            return "serie_como_dato_actual"
    return None


def validar_afirmaciones(
    afirmaciones: Sequence[AfirmacionPropuesta],
    evidencias: Sequence[Evidencia],
    *,
    reglas_extra: Sequence[Regla] = (),
) -> ResultadoCitas:
    """Valida contra las evidencias **recuperadas** para esta consulta, no contra todo el corpus.

    ``reglas_extra`` agrega reglas de la modalidad después de las comunes; la primera que
    devuelve un motivo descarta la afirmación.
    """
    por_id = {e.id: e for e in evidencias}
    aceptadas: list[AfirmacionPropuesta] = []
    descartadas: list[Descartada] = []
    for afirmacion in afirmaciones:
        motivo = _motivo_descarte(afirmacion, por_id) or next(
            (m for regla in reglas_extra if (m := regla(afirmacion, por_id)) is not None), None
        )
        if motivo is None:
            aceptadas.append(afirmacion)
        else:
            descartadas.append(Descartada(afirmacion, motivo))
    return ResultadoCitas(tuple(aceptadas), tuple(descartadas))


def debe_abstenerse(
    resultados: Sequence[Resultado], *, umbral_bm25: float, umbral_coseno: float | None = None
) -> bool:
    """Compuerta previa al LLM: sin evidencia suficientemente cercana, no se genera nada."""
    if not resultados:
        return True
    mejor_bm25 = max(r.bm25 for r in resultados)
    cosenos = [r.coseno for r in resultados if r.coseno is not None]
    if cosenos and umbral_coseno is not None and max(cosenos) >= umbral_coseno:
        return False
    return mejor_bm25 < umbral_bm25
