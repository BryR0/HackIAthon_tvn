"""Proveedores de LLM para redactar borradores (ADR 0002 D3).

Cascada: ``SENAL_LLM`` explícito → Gemini si hay ``GEMINI_API_KEY`` → Ollama
local si responde → ``None`` (quien llama usa la plantilla extractiva).
El LLM solo redacta sobre evidencia recuperada; nunca decide prioridad ni verdad.
La credencial vive en el entorno del servidor; nunca entra al prompt ni a logs.
Costo medido = tokens × tarifa configurada (``SENAL_TARIFA_*_USD_1M``); 0 en local.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

log = logging.getLogger(__name__)

TIEMPO_ESPERA_SEGUNDOS = 35.0
TEMPERATURA = 0.2
MAX_TOKENS_SALIDA = 1500
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
GEMINI_MODELO_POR_DEFECTO = "gemini-flash-latest"
OLLAMA_URL_POR_DEFECTO = "http://127.0.0.1:11434"
OLLAMA_MODELO_POR_DEFECTO = "llama3.2"


@dataclass(frozen=True)
class RespuestaLLM:
    texto: str
    proveedor: str
    modelo: str
    tokens_entrada: int
    tokens_salida: int
    latencia_s: float
    costo_usd: float


class ProveedorLLM(Protocol):
    nombre: str
    modelo: str

    def generar(self, sistema: str, usuario: str) -> RespuestaLLM: ...


def _env(nombre: str, defecto: str = "") -> str:
    return os.environ.get(nombre, defecto).strip()


def _costo(entrada: int, salida: int) -> float:
    tarifa_in = float(_env("SENAL_TARIFA_ENTRADA_USD_1M", "0") or 0)
    tarifa_out = float(_env("SENAL_TARIFA_SALIDA_USD_1M", "0") or 0)
    return (entrada * tarifa_in + salida * tarifa_out) / 1_000_000


class ProveedorGemini:
    nombre = "gemini"

    def __init__(self, clave: str, modelo: str = GEMINI_MODELO_POR_DEFECTO) -> None:
        self._clave = clave
        self.modelo = modelo

    def generar(self, sistema: str, usuario: str) -> RespuestaLLM:
        inicio = time.perf_counter()
        cuerpo: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": sistema}]},
            "contents": [{"role": "user", "parts": [{"text": usuario}]}],
            "generationConfig": {
                "temperature": TEMPERATURA,
                "maxOutputTokens": MAX_TOKENS_SALIDA,
                "responseMimeType": "application/json",
            },
        }
        reintentos_max = 3
        respuesta = None
        for intento in range(reintentos_max):
            try:
                respuesta = httpx.post(
                    GEMINI_URL.format(modelo=self.modelo),
                    headers={"x-goog-api-key": self._clave},
                    json=cuerpo,
                    timeout=TIEMPO_ESPERA_SEGUNDOS,
                )
                if (
                    respuesta.status_code in (503, 502, 504, 429)
                    and intento < reintentos_max - 1
                ):
                    espera = 1.5 * (intento + 1)
                    log.warning(
                        "Gemini respondió con HTTP %d en intento %d/%d; reintentando en %.1fs...",
                        respuesta.status_code,
                        intento + 1,
                        reintentos_max,
                        espera,
                    )
                    time.sleep(espera)
                    continue
                respuesta.raise_for_status()
                break
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                if intento < reintentos_max - 1:
                    espera = 1.5 * (intento + 1)
                    log.warning(
                        "Fallo de conexión con Gemini (%s) en intento %d/%d; reintentando en %.1fs...",
                        type(exc).__name__,
                        intento + 1,
                        reintentos_max,
                        espera,
                    )
                    time.sleep(espera)
                    continue
                raise

        assert respuesta is not None
        datos = respuesta.json()
        candidatos = datos.get("candidates") or []
        if not candidatos:  # p. ej. bloqueo de seguridad: se trata como fallo del proveedor
            raise ValueError("Gemini no devolvió candidatos")
        partes = candidatos[0].get("content", {}).get("parts", [])
        texto = "".join(p.get("text", "") for p in partes)
        uso = datos.get("usageMetadata", {})
        entrada = int(uso.get("promptTokenCount", 0))
        # Los tokens de razonamiento se facturan como salida.
        salida = int(uso.get("candidatesTokenCount", 0)) + int(uso.get("thoughtsTokenCount", 0))
        latencia = time.perf_counter() - inicio
        costo = _costo(entrada, salida)
        return RespuestaLLM(texto, self.nombre, self.modelo, entrada, salida, latencia, costo)


class ProveedorOllama:
    nombre = "ollama"

    def __init__(
        self, url: str = OLLAMA_URL_POR_DEFECTO, modelo: str = OLLAMA_MODELO_POR_DEFECTO
    ) -> None:
        self._url = url.rstrip("/")
        self.modelo = modelo

    def disponible(self) -> bool:
        try:
            return httpx.get(f"{self._url}/api/tags", timeout=1.5).status_code == 200
        except httpx.HTTPError:
            return False

    def generar(self, sistema: str, usuario: str) -> RespuestaLLM:
        inicio = time.perf_counter()
        respuesta = httpx.post(
            f"{self._url}/api/chat",
            json={
                "model": self.modelo,
                "stream": False,
                "format": "json",
                "options": {"temperature": TEMPERATURA, "num_predict": MAX_TOKENS_SALIDA},
                "messages": [
                    {"role": "system", "content": sistema},
                    {"role": "user", "content": usuario},
                ],
            },
            timeout=TIEMPO_ESPERA_SEGUNDOS * 3,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
        texto = datos.get("message", {}).get("content", "")
        entrada = int(datos.get("prompt_eval_count", 0))
        salida = int(datos.get("eval_count", 0))
        latencia = time.perf_counter() - inicio
        return RespuestaLLM(texto, self.nombre, self.modelo, entrada, salida, latencia, 0.0)


def cargar_proveedor() -> ProveedorLLM | None:
    """Resuelve la cascada. ``None`` → plantilla extractiva (rotulada en la interfaz)."""
    pedido = (_env("SENAL_LLM") or _env("AI_PROVIDER")).lower()
    if pedido == "ninguno":
        return None
    clave = _env("GEMINI_API_KEY") or _env("AI_API_KEY")
    if pedido in ("", "gemini") and clave:
        return ProveedorGemini(clave, _env("SENAL_GEMINI_MODELO", GEMINI_MODELO_POR_DEFECTO))
    if pedido in ("", "ollama"):
        ollama = ProveedorOllama(
            _env("OLLAMA_BASE_URL", OLLAMA_URL_POR_DEFECTO),
            _env("SENAL_OLLAMA_MODELO", OLLAMA_MODELO_POR_DEFECTO),
        )
        if ollama.disponible():
            return ollama
        log.warning("Ollama no responde; se usará la plantilla extractiva")
    return None
