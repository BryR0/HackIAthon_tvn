"""Anti-inyección (reto §8, T07).

El texto de una fuente es **dato, nunca instrucción**. Defensas en capas:
1. ``sanear``: quita caracteres de control/formato (ancho cero, bidi) y
   neutraliza secuencias que imitan delimitadores.
2. ``delimitador_aleatorio``: el bloque de fuentes del prompt se cierra con un
   token impredecible por petición, que una fuente no puede adivinar.
3. ``es_sospechoso``: heurística que marca la ficha como "contenido sospechoso"
   para la persona revisora; no bloquea el dato, lo señala.
El modelo no tiene herramientas ni acciones, y el prompt nunca contiene secretos.
"""

from __future__ import annotations

import re
import secrets
import unicodedata

from senal.organize import normalizar_texto

_SECUENCIAS_DELIMITADOR = re.compile(r"<{3,}|>{3,}|`{3,}|={4,}|#{3,}")
_PATRONES_INYECCION = tuple(
    re.compile(p)
    for p in (
        r"\bignor\w* (?:todas |all )?(?:las |tus |the |your )?(?:anteriores |previas |previous |"
        r"prior |above )?(?:instrucciones|reglas|indicaciones|instructions|rules)",
        r"\bignore (?:all )?(?:previous|prior|above) instructions",
        r"\bolvid\w* (?:tus|las|todas) (?:reglas|instrucciones)",
        r"\b(?:revela|muestra|imprime|reveal|show|print)\w* (?:tu |su |la |el |your |the )?"
        r"(?:system prompt|prompt del sistema|prompt|api key|clave|contrasena|password|secreto|"
        r"secret|token|credencial)",
        r"\bahora eres\b",
        r"\byou are now\b",
        r"\bmodo desarrollador\b|\bdeveloper mode\b|\bjailbreak\b",
    )
)


def sanear(texto: str) -> str:
    """Texto de fuente apto para ir dentro del bloque de datos del prompt."""
    sin_control = "".join(
        " " if unicodedata.category(c) in ("Cc", "Zl", "Zp") else c
        for c in texto
        if unicodedata.category(c) != "Cf"
    )
    sin_delimitadores = _SECUENCIAS_DELIMITADOR.sub(" ", sin_control)
    return " ".join(sin_delimitadores.split())


def es_sospechoso(texto: str) -> bool:
    normalizado = " ".join(normalizar_texto(texto).split())
    return any(p.search(normalizado) for p in _PATRONES_INYECCION)


def delimitador_aleatorio() -> str:
    return f"FUENTES_{secrets.token_hex(12).upper()}"
