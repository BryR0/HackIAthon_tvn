# ADR 0002 — Parte 2 (Señal TVN): stack, embeddings y reglas base

- **Fecha:** 2026-10-06
- **Estado:** Aceptado (D6 provisional hasta respuesta del organizador)
- **Contexto:** Gate 0 del [Blueprint Parte 2](../../plans/parte-2-tvn-senal-a-decision.md)
- **Decisores:** BryR0

## Contexto

El reto "De la señal a la decisión" (TVN Media) exige un flujo de extremo a
extremo sobre un snapshot público, una capacidad sustantiva de ML/NLP comparada
con un baseline, citas verificables, abstención, y una demo **sin internet**.
No exige web pública: "una interfaz web, dashboard o notebook interactivo es
válido".

Hechos verificados del entorno (2026-10-06):

- Python 3.12.10, `uv` 0.9.8, `torch` 2.10 y `sentence-transformers` 5.1 instalados.
- Ollama local responde con `llama3.2`.
- Banco Mundial, USGS y RSS de TVN responden 200. GDELT DOC responde **429**.
- Sin credencial de proveedor hosted en el entorno.
- `../docversion` implementa RAG (Ollama `nomic-embed-text`, coseno, RRF en
  Postgres), no clasificación ni clustering.

## Decisiones

### D1 — Stack: Python + FastAPI + Jinja2/HTMX en `senal/`

Proyecto `uv` autocontenido con dependencias fijadas en `uv.lock`. La app
Next.js de la Parte 1 no se modifica.

Alternativas descartadas:
- **Next.js (stack de la Parte 1):** embeddings de consultas offline dependían
  de Ollama corriendo o de transformers.js; métricas y contrato de datos a mano.
- **Streamlit:** más rápido de construir, menos control sobre estados de revisión
  y la experiencia de la ficha.
- **FastAPI + Next:** dos runtimes y dos procesos en la demo offline.

### D2 — Embeddings multilingües en proceso

`intfloat/multilingual-e5-small` vía `sentence-transformers`, con prefijos
`query:` / `passage:`. Un solo modelo para documentos, prototipos y consultas.
Pesos cacheados localmente: las consultas nuevas funcionan sin red y sin Ollama.
Si el modelo no carga, la recuperación degrada a BM25 y la UI lo rotula.
`nomic-embed-text` descartado: anglocéntrico, y GDELT mezcla español e inglés.

### D3 — Generación: cascada con fallback extractivo

Gemini → Ollama `llama3.2` → plantilla extractiva determinista que solo copia
campos citados. Se registra proveedor, modelo, tokens, latencia y costo. El LLM
nunca decide prioridad, verdad ni evidencia.

### D4 — Estado de revisión local

`data/reviews.jsonl` con revisor y marca de tiempo. La demo autoritativa corre
local. Sin despliegue público obligatorio.

### D5 — Tiempo

UTC ISO 8601 en datos; `America/Panama` (UTC−5, sin horario de verano) en la UI.
`fecha_publicacion` y `fecha_deteccion` (`seendate` de GDELT) nunca se mezclan.
El puntaje usa `ahora = manifest.fecha_corte_UTC`, nunca el reloj del sistema.

### D6 — Ventana de noticias (provisional)

El reto pide `[2024-01-01, 2025-10-01)` y también "30–90 días previos a la
extracción"; ninguna fuente pública de noticias alcanza 2024 desde 2026-10.
Mientras el organizador no entregue el snapshot común, se extraen los últimos
90 días y la desviación queda en `manifest.json` y en Notion. Indicadores
(2010–2024) y sismos (2024) sí cumplen el rango del reto.

### D7 — Versionado de reglas

Toda constante del puntaje vive bajo `RULES_VERSION`. Cambiar un peso exige una
entrada de decisión en Notion y subir la versión.

## Consecuencias

- Dos lenguajes en el repositorio (TS Parte 1, Python Parte 2), aislados por carpeta.
- La primera ejecución descarga los pesos del modelo; debe hacerse antes del evento.
- GDELT necesita pausas y reintentos; el extractor guarda todo en `raw/`.
