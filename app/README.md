# Señal TVN — De la señal a la decisión

Copiloto de inteligencia informativa para la redacción de TVN Media (hackIAthon,
Parte 2). Convierte noticias públicas e indicadores oficiales en una **bandeja de
temas priorizados**, **fichas de evidencia** y **borradores con citas** para una
decisión humana.

> Nada se publica automáticamente. La prioridad ordena la revisión; no es
> probabilidad de verdad ni de pérdida. Toda afirmación cita su fuente.

## Arrancar en un comando

Solo necesitas **Python 3.12+**. El script crea `.env`, instala dependencias,
libera el puerto y levanta el servidor en <http://127.0.0.1:8765>.

Windows:

```powershell
.\server_start.bat
```

Linux / macOS:

```bash
./server_start.sh
```

La primera vez descarga dependencias y el modelo de embeddings (una sola vez).
Después funciona **sin internet** (T10).

Para redactar con un LLM, edita `.env`: `GEMINI_API_KEY=...`, o deja Ollama
corriendo con `llama3.2`. Sin LLM, los borradores salen de una plantilla
extractiva que solo copia campos citados.

## La decisión de diseño

**El LLM nunca decide prioridad, ni verdad, ni inventa evidencia.**

```
snapshot público ─► validar (T01) ─► organizar: embeddings e5 + baseline léxico
                                      │  agrupar eventos (enlace promedio)
                                      ▼
            contexto oficial (Banco Mundial, USGS) · procedencia independiente
                                      ▼
            puntaje determinista P = 30R + 25I + 20U + 15N + 10E  (senal-1.0.0)
                                      ▼
consulta ─► recuperación BM25 + coseno (RRF) ─► compuerta de abstención (sin LLM)
                                      ▼
            redacción (Gemini → Ollama → plantilla) con fuentes como DATOS
                                      ▼
            validador: ID recuperado · campo citable · cifra presente · año del
            indicador · acusación solo como declaración · cifras del texto libre
                                      ▼
                       revisión humana (5 estados) ─► fichas.jsonl ─► Notion
```

| Responsabilidad | Quién |
|---|---|
| Validación, fechas, deduplicación | Código determinista |
| Tema y agrupación de eventos | `intfloat/multilingual-e5-small` (en proceso) vs palabras clave |
| Prioridad y estado de evidencia | Reglas versionadas, `ahora` = fecha de corte |
| Redacción | LLM o plantilla, siempre validada |
| Decisión | Persona revisora |

## Extensión bancaria (misma app)

La modalidad bancaria del reto (§1: "alternativa o extensión, sin exigir dos productos
completos") vive en esta misma app: el selector **Editorial | Banca** de la cabecera o
`?modalidad=banca` en cualquier página. Misma bandeja, mismo puntaje `senal-1.1.0`,
mismo motor de redacción y validador; cambia la salida
([ADR 0003](../docs/adr/0003-parte-2-extension-bancaria.md)).

- **Boletín de entorno** (reto §3): resumen ≤ 250 palabras, sectores potencialmente
  relacionados, período de la evidencia y horizonte de seguimiento, observaciones
  separadas de hipótesis de impacto, 3 preguntas para el analista y aviso de la SBP.
- **Fuente D:** saldos de crédito local por sector de los 12 Informes de Actividad
  Bancaria 2024 (SBP), con período, unidad y página del PDF. Toda cifra se cita con
  `MM/AAAA` y nunca como dato de hoy.
- **Sectores = hipótesis:** el mapa tema → sector (`banca-1.0.0`) es una tabla del
  equipo; el LLM no lo decide.
- **Prohibido fuera de declaraciones atribuidas:** recomendar compra/venta, inferir
  pérdidas, impagos o exposición de cartera, scores de clientes o alertas regulatorias.
- **CU-05:** "¿Qué señales públicas del entorno logístico debo revisar?" en Consulta
  (modo Banca) → boletín con Comercio e Industria citados.

## Datos

Paquete `panama-senales-evidencias-v1` en `data/processed/` (con `manifest.json`
y SHA-256 por archivo):

| Archivo | Contenido |
|---|---|
| `noticias.csv` | 3.049 titulares es/en de los últimos 90 días (68 de TVN): TVN RSS + GDELT DOC 2.0 |
| `indicadores.csv` | 540 filas: 6 países × 6 indicadores × 2010–2024 (Banco Mundial, CC BY 4.0) |
| `eventos.geojson` | 82 sismos 2024 en la caja lat 5–12, lon −86 a −76 (USGS) |
| `sbp_series.csv` | 156 filas: crédito local por sector, 12 informes mensuales 2024 de la SBP (extensión bancaria) |
| `excluidos.csv`, `reporte_calidad.json` | Exclusiones con motivo y reporte de calidad |

Desviaciones declaradas en el manifest:
- **D6:** ninguna fuente pública alcanza noticias de 2024 desde 2026-10.
- **Errata del reto:** 6 × 6 × 15 = 540 combinaciones, no 1.350.
- **TVN:** solo titulares y metadatos; las descripciones del RSS no entran sin
  autorización del patrocinador.

Regenerar desde las fuentes, es decir la receta (`data/raw/` no se versiona):

```bash
uv run python scripts/extract.py
uv run python scripts/build_snapshot.py
```

Solo la fuente D, sin volver a pedir las noticias (el paquete editorial queda idéntico):
`uv run python scripts/extract.py --solo-sbp` y luego `build_snapshot.py`.

## Desarrollo

```bash
uv sync
uv run pytest
uv run ruff check src tests scripts evals
uv run mypy src
```

`requirements.txt` se genera con
`uv export --no-hashes --no-dev --format requirements-txt -o requirements.txt`;
luego se antepone el índice CPU de PyTorch.

## Evaluación

```bash
uv run python evals/eval_senal.py --modo bm25    # baseline léxico
uv run python evals/eval_senal.py                # híbrido e5
uv run python evals/eval_senal.py --llm          # con el LLM configurado
uv run python evals/eval_organize.py medir       # tras etiquetar evals/etiquetado/*.csv
uv run python evals/eval_senal.py --modalidad banca --benchmark evals/benchmark_banca_dev.jsonl
```

Banca (7 dev / 3 reservados, sin LLM): dev 7/7 en BM25 e híbrido, citas 74/74;
reservado 3/3 en BM25 y 2/3 en híbrido (RB03: la fuente con instrucciones quedó fuera
del top-8 y no se usó). La regresión editorial sigue 40/40.

Resultados en `eval-results/senal/` con numerador, denominador y fallos.

Benchmark de desarrollo (40 casos; etiquetas en borrador **pendientes de revisión
humana**), corrida 2026-10-06, sin LLM:

| Métrica | BM25 | Híbrido e5 |
|---|---|---|
| Sustentadas | 20/20 | 20/20 |
| Contradicción detectada | 7/7 | 7/7 |
| Adversariales | 6/6 | 6/6 |
| Abstención correcta | 7/7 | 7/7 |
| Abstención incorrecta en respondibles | 0/27 | 0/27 |
| Cobertura de citas | 240/240 | 245/245 |
| Latencia mediana / p95 | 0,003 / 0,003 s | 0,013 / 0,015 s |

Con Ollama `llama3.2` en el equipo de desarrollo, un borrador tarda ≈15 s
(1.734 + 554 tokens) con costo US$ 0 en local.

**Límites honestos:**
- Las reglas se ajustaron viendo el set de desarrollo (riesgo de sobreajuste); la
  medida válida es el set reservado.
- En este benchmark la IA **no** mejora la recuperación frente a BM25, porque las
  consultas son léxicas.
- El aporte de la IA en clasificación y agrupación se medirá con las etiquetas
  humanas de `evals/etiquetado/temas.csv`: hoy la IA y el baseline coinciden en
  solo el 46 % de 119 titulares.
- `llama3.2` (3B) cita mal con frecuencia; el validador lo descarta y se usa la
  plantilla.
- Los IDs de evento cambian si cambia el snapshot o los umbrales; cada revisión
  guarda los IDs de las noticias para mantener la trazabilidad.

## Pruebas de aceptación

| ID | Dónde |
|---|---|
| T01 fechas inválidas y nulos | `tests/unit/test_ingest.py` |
| T02 mismo evento × 3 | `tests/unit/test_organize.py`, `test_pipeline.py` |
| T03 noticia antigua recirculada | `test_ingest.py` (fecha original), `excluidos.csv` |
| T04 cifra anual del Banco Mundial | `test_context.py`, `test_retrieve_cite.py`, `test_generate.py` |
| T05 afirmaciones incompatibles | `test_context.py`, `test_generate.py` (CU-04) |
| T06 consulta sin respuesta | `test_generate.py`, benchmark `N01–N07` |
| T07 fuente que da instrucciones | `test_seguridad.py`, `test_generate.py`, benchmark `A01–A06` |
| T08 prioridad alta | `test_score.py` |
| T09 brief editorial | `test_generate.py` |
| T10 sin internet | `tests/web/test_app.py` (sin modelo ni LLM); snapshot y modelo locales |
| TB01–TB03, TB12 fuente D (parser, sumas, esquema sin clientes) | `test_sbp.py`, `test_snapshot.py` |
| TB04–TB08, TB10–TB11 boletín y CU-05 | `test_boletin.py` |
| TB09, TB13, TB14 web, revisión por modalidad, arranque sin SBP | `tests/web/test_app.py`, `test_review.py`, `test_banca.py` |

## Seguridad y ética

- Fuentes como datos no confiables: saneo, delimitador aleatorio por petición,
  detector de instrucciones. Las fuentes sospechosas se señalan y no alimentan el
  borrador.
- Validador determinista de citas y de cifras del texto libre; acusaciones solo
  como declaración atribuida.
- CSRF, CSP estricta sin scripts, `TrustedHost`, `Cache-Control: no-store`;
  servidor solo en `127.0.0.1`.
- Credenciales solo en `.env` (ignorado por git), nunca en el prompt ni en logs.
- Sin perfiles de personas; solo lo publicado en titulares.

## Estructura de la aplicación

```
app/
  src/senal/                 ingest, fuentes, organize, embed, context, contradict,
                             evidence, score, retrieve, cite, seguridad, llm,
                             generate, review, pipeline, web/
  data/processed/            snapshot versionado + embeddings en caché
  evals/                     benchmark, planillas de etiquetado y arneses
  tests/                     unit/ y web/
  pyproject.toml             especificación del paquete
  requirements.txt           dependencias fijadas

(Nota: los scripts auxiliares y lanzadores automáticos viven en la raíz del repositorio:
 ../scripts/ y ../server_start.bat / .sh)
```

Plan y decisiones: `../plans/parte-2-tvn-senal-a-decision.md` y
`../docs/adr/0002-parte-2-senal-stack-y-reglas.md`. Registro tipo Notion:
`../docs/notion/`.
