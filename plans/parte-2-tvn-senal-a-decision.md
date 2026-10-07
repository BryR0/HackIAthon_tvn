# Blueprint de implementación — Parte 2: De la señal a la decisión (TVN Media)

Estado: **v2 — validado por ECC (architect + planner + code-explorer), aprobado con cambios ya integrados.** Gate 0 abierto.  
Rama: `parte-2/tvn-senal-decision` (la Parte 1, Cobertura Clara, sigue intacta en `main`)  
Fuente: `hackIAthon - reto TVN Media.pdf` (autoritativo; contiene las URLs) y su transcripción `hackIAthon_reto_TVN_Media.md`  
Producto propuesto: **Señal TVN** — copiloto de inteligencia informativa

## 0. Validación del plan (2026-10-06)

| Revisor ECC | Veredicto v1 | Hallazgos que cambiaron el plan |
|---|---|---|
| architect | Aprobar con cambios | Embeddings de consultas offline; `ahora` fijo para urgencia; estado de revisión en Vercel; fórmulas del puntaje; detector de contradicciones; validador de citas; anti-inyección; `provider.ts` no reutilizable tal cual |
| planner | Parcial, listo tras revisión | Conflicto de fechas del dataset (D6); mapa por días; rebanada vertical el Día 1; conteos de admisión Notion; trazabilidad CU; privacidad y secretos; criterios de salida medibles; recortes YAGNI |
| code-explorer (`../docversion`) | — | docversion **no** tiene clasificación ni clustering: es RAG (Ollama `nomic-embed-text`, coseno/pgvector, RRF en Postgres). Se reutilizan ideas y algoritmos pequeños, no el servicio. Ver §4.2 |
| Decisión de stack (2026-10-06) | — | El usuario elige **Python FastAPI + Jinja/HTMX** sobre Next.js: el reto no pide web pública y Python resuelve embeddings offline en proceso. Reemplaza D1–D4 de la v2 |

## 1. Decisión

Modalidad **editorial TVN**. La bancaria (CU-05) queda **diferida**: solo si
sobra tiempo tras el congelamiento de funcionalidades.

Flujo exigido (sección 3 del reto): Cargar → Organizar → Contextualizar →
Priorizar → Explicar → Producir → Revisar.

### Principio heredado de la Parte 1

En Cobertura Clara el LLM nunca calcula dinero. Aquí:

**El LLM nunca decide prioridad, ni verdad, ni inventa evidencia.**

| Responsabilidad | Quién la hace |
|---|---|
| Validación, deduplicación por URL, normalización de fechas, reporte de calidad | Código determinista |
| Clasificación temática y agrupación de eventos | **Embeddings multilingües (ML)**; baseline de palabras clave al lado |
| Relevancia Panamá | Gazetteer determinista (no NER) |
| Puntaje `P = 30R + 25I + 20U + 15N + 10E` | Motor puro con constantes versionadas |
| Estado de evidencia | Reglas sobre procedencias independientes |
| Contradicciones | Comparación determinista de cifras/unidades/entidades dentro del cluster |
| Abstención | Compuerta determinista **antes** del LLM + validador después |
| Redacción de brief, guion y copy | LLM sobre evidencia recuperada, salida pydantic |
| Validez de cada cita | Validador determinista |
| Aprobación | Persona revisora con nombre |

Afirmación con `id_evidencia` fuera del contexto recuperado, o con una cifra
que no aparece en el campo citado: **se descarta entera**.

## 2. Objetivo y criterios de éxito

Que un editor pase de fuentes dispersas a un tema investigable con evidencia
trazable y un borrador responsable, **sin internet durante la demo**.

Metas (orientativas, sección 9.1 — se reporta numerador, denominador y fallos):

- Cobertura de citas 100 %; validez de sustento ≥ 90 % sobre ≥ 30 afirmaciones revisadas.
- Abstención correcta ≥ 80 %; abstenciones incorrectas también reportadas.
- Macro-F1 temático IA vs baseline, con n, anotador y guía de etiquetado; documentar dónde gana el baseline.
- Precision@5 vs selección de un editor (o declarada exploratoria).
- Latencia mediana ≤ 15 s y p95; tokens y costo por consulta.
- T01–T10 verdes con evidencia en Notion; demo completa offline.
- Ahorro de tiempo: prueba cronometrada manual vs asistida con n declarado, **o** rotulado como hipótesis de valor en el pitch.

## 3. Alcance

### Incluido
- Snapshot `Panamá · Señales y Evidencias v1` (del organizador si existe; si no, propio — ver D6).
- Bandeja priorizada, ficha de evidencia, consulta en español, paquete editorial, revisión humana.
- Benchmark de 60 consultas (40 desarrollo / 20 reservadas, estratificado).
- Espacio Notion con las 8 páginas obligatorias.

### Fuera de alcance
- Rating, audiencia, conversión; veredicto verdadero/falso; fraude.
- Cuerpos completos, paywalls, imágenes, video.
- Publicación automática; monitoreo continuo.
- Modalidad bancaria (diferida).
- Exportador automático a Notion (la carga manual está permitida; YAGNI).

## 4. Arquitectura

Stack: **Python 3.12 + FastAPI + Jinja2/HTMX + Tailwind (CDN fijado o CSS
compilado)**, proyecto `uv` autocontenido en `senal/`. La app Next.js de la
Parte 1 no se toca. Pruebas con `pytest`.

```
senal/
  pyproject.toml, uv.lock           dependencias fijadas
  .env.example
  scripts/extract_*.py ──> data/raw/        (solo si no hay snapshot del organizador; timebox 2 h)
  scripts/build_snapshot.py ──> data/processed/
     validar + normalizar → noticias.csv, indicadores.csv, eventos.geojson,
     reporte_calidad.json/md, excluidos.csv (con motivo), manifest.json (SHA-256)
  scripts/embed.py ──> data/processed/embeddings.npz (docs + prototipos + consultas demo/benchmark)
  src/senal/
    ingest.py       carga y valida snapshot (pydantic)
    embed.py        sentence-transformers en proceso + cache por hash(texto)+modelo
    organize.py     prototipos por tema (coseno + margen) | baseline palabras clave
                    clustering union-find por umbral de coseno + ventana temporal
    provenance.py   dominio canónico + regex de agencias (EFE/AP/AFP/Reuters) + cluster
    context.py      noticia ↔ indicador (tema+país) | ↔ sismo (tiempo+lugar); nunca forzado
    score.py        puntaje por CLUSTER, ahora = manifest.fecha_corte_UTC
    evidence.py     estado de evidencia
    contradict.py   cifras/unidades/entidades divergentes → "revisión pendiente"
    retrieve.py     BM25 (baseline) + coseno, fusión RRF k=60
    llm.py          cascada Gemini → Ollama → plantilla extractiva; registra tokens
    generate.py     prompt con delimitadores aleatorios; fuentes = datos no confiables
    cite.py         validador de citas + compuerta de abstención
    review.py       estados de revisión → data/reviews.jsonl
    web/            FastAPI app, plantillas Jinja2, parciales HTMX
  tests/            unit/, evals/, e2e/ (Playwright para Python)
  evals/            eval_organize.py, eval_senal.py → eval-results/<fecha>.json
```

### 4.1 Decisiones a cerrar en Gate 0 (ADR 0002)

- **D1 — Stack y ubicación.** Python 3.12 + FastAPI + Jinja2/HTMX, proyecto `uv`
  en `senal/`. El reto no exige web pública ("interfaz web, dashboard o notebook
  interactivo es válido"); exige demo reproducible sin internet. Python aporta
  embeddings en proceso, `pandas`/`pydantic` para el contrato de datos y
  `scikit-learn` para métricas. La Parte 1 (Next.js) queda intacta.
- **D2 — Embeddings.** **Un solo modelo multilingüe en proceso** con
  `sentence-transformers` para documentos, prototipos y consultas:
  `intfloat/multilingual-e5-small` (prefijos `query:`/`passage:`), con
  `-base` como alternativa si el F1 lo justifica. Pesos descargados una vez y
  cacheados localmente → consultas nuevas funcionan offline sin Ollama.
  id + revisión del modelo + dimensión en `manifest.json`.
  Si el modelo no carga: **solo BM25, rotulado en la UI**.
- **D3 — Generación.** `llm.py` con cascada Gemini → Ollama (`llama3.2` local) →
  plantilla extractiva que solo copia campos citados. Registra tokens, latencia
  y costo. Timeout y `max_tokens` dimensionados para brief + guion + copy.
- **D4 — Estado de revisión.** La demo corre **local** (T10 lo exige) y escribe
  `data/reviews.jsonl` con nombre de revisor y marca de tiempo. Sin despliegue
  público obligatorio; si se publica, solo lectura.
- **D5 — Hora.** UTC ISO 8601 en datos; `America/Panama` (UTC−5, sin horario de
  verano) en la UI; regla escrita en `diccionario.md`. `fecha_publicacion` ≠
  `fecha_deteccion` (`seendate` de GDELT).
- **D6 — Conflicto de fechas del dataset (bloqueante).** El reto pide noticias en
  `[2024-01-01, 2025-10-01)` y a la vez "30–90 días previos a la extracción";
  hoy es 2026-10 y ni el RSS ni la API DOC de GDELT (ventana reciente limitada,
  verificar) alcanzan 2024. Acción: preguntar al organizador si entrega el
  snapshot congelado (sección 11). Si no, extraer los últimos 90 días y registrar
  la desviación en `manifest.json` y en Notion (decisión justificada).
- **D7 — Cambios de pesos.** Toda modificación de constantes del puntaje requiere
  entrada de decisión en Notion y subir `RULES_VERSION`.

### 4.2 Reuso de `../docversion`

docversion resuelve **recuperación RAG**, no clasificación. Se toma:

| De docversion | Uso aquí |
|---|---|
| `_cosine` con guardas de dimensión y norma cero (`app/services/rag_service.py:481`) | Equivalente numpy en `senal/src/senal/embed.py` |
| Cache por `content_hash` + modelo + digest (`rag_service.py:353`, `:498`) | Mismo esquema en `embeddings.json` |
| `embed()` que devuelve `None` al fallar (`app/services/ollama_service.py:112`) | Fallo de embedding → fallback BM25 rotulado, nunca excepción en la demo |
| `model_digest()` vía `/api/tags` (`ollama_service.py:138`) | Digest en manifest |
| Fusión RRF `k=60` (`rag_service.py:686`, allí en SQL) | Port a Python en memoria (`retrieve.py`) |

Se construye nuevo (no existe en docversion): prototipos por tema con umbral y
margen, clustering union-find, calibración de umbrales sobre el set de
desarrollo, pruebas y evals. **No** se levanta docversion como sidecar Python:
Vercel no lo aloja y añade un segundo runtime a la demo offline.

## 5. Puntaje de atención

Unidad: **cluster de evento**, no artículo (así tres copias no triplican, T02).
Referencia temporal: `ahora = manifest.fecha_corte_UTC`, parámetro del motor,
nunca `Date.now()`. Constantes bajo `RULES_VERSION = senal-1.0.0`.

| Componente | Peso | Fórmula `[0,1]` |
|---|---:|---|
| R · Relevancia | 30 | gazetteer (Panamá = 1, región = 0,5, ninguno = 0) × peso del tema en tabla editorial |
| I · Impacto | 25 | alcance del tema por tabla (nacional/sectorial/local) + 0,3 si hay dato oficial enlazado; tope 1 |
| U · Urgencia | 20 | `exp(−edad_días / τ)` desde la `fecha_publicacion` más antigua del cluster; τ versionado |
| N · Novedad | 15 | `1 − max coseno` contra clusters con primera fecha anterior (independiente del orden) |
| E · Evidencia | 10 | `min(procedencias_independientes, 3) / 3` + bonus acotado por fuente oficial |

Bandas: bajo `[0,40)`, medio `[40,70)`, alto `[70,100]`. Empates: mayor U, luego ID.
`RULES_VERSION` visible en bandeja y ficha.

**Estado de evidencia** (independiente del puntaje):
0 procedencias independientes = `insuficiente`; 1 = `parcial`;
≥ 2, o 1 oficial pertinente = `suficiente para el borrador`.

**Procedencia independiente:** dominio canónico; misma agencia (regex en título
o `alcance_texto`) o texto casi idéntico (coseno ≥ umbral calibrado) = una sola.

## 6. Contrato de datos

Archivos de la sección 7 del reto (`noticias.csv`, `fuentes.json`,
`indicadores.csv`, `eventos.geojson`, `fichas.jsonl`, `manifest.json`) más
`diccionario.md`, `benchmark.jsonl`, `reporte_calidad.json`, `excluidos.csv`.

- UTF-8, IDs estables (prueba de estabilidad), `.gitattributes` con `data/** eol=lf`, JSON con claves ordenadas para hash estable.
- Nulos del Banco Mundial = `null`, nunca `0`; cuadrícula 6 × 6 × 15 = **540** filas (el reto dice "1.350": error aritmético, confirmado al construir el snapshot; preguntado al organizador).
- `fichas.jsonl` lo genera la aplicación al aprobar/descartar; se versiona.
- Solo titular/metadatos → la salida dice literalmente "basado únicamente en titular/metadatos".
- Fuentes con redistribución restringida (TVN, medios vía GDELT): se entregan metadatos + receta, no contenido.

### 6.1 Fuentes oficiales del reto (§12 del PDF, consultadas por el organizador el 05/10/2026)

Las URLs solo están como hipervínculos en `hackIAthon - reto TVN Media.pdf`; el
`.md` las perdió. Se copian tal cual al Catálogo de datos de Notion.

| Ref | Fuente | URL | Uso / condición |
|---|---|---|---|
| [1] | TVN Panamá · sitio oficial | https://www.tvn-2.com/ | Medio del patrocinador |
| [2] | TVN · feed RSS público | https://www.tvn-2.com/rss/ | Titulares, fechas, descripciones. **No** implica licencia sobre artículos, videos o imágenes. No conserva histórico |
| [3] | GDELT · DOC 2.0 API | https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts | ArtList, filtros dominio/idioma, ventanas, máx. 250 resultados. No confundir con "GDELT Cloud" comercial |
| [4] | Banco Mundial · Indicators API v2 | https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation | Documentación de la API |
| [5] | Banco Mundial · Panamá | https://data.worldbank.org/country/panama | Referencia de indicadores |
| [6] | Banco Mundial · términos | https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets | CC BY 4.0, atribución, excepciones de terceros por indicador; período ≠ año de extracción |
| [7] | USGS · servicio FDSN | https://earthquake.usgs.gov/fdsnws/event/1 | Usar ID y URL del evento para trazabilidad |
| [8] | SBP · estadísticas financieras | https://www.superbancos.gob.pa/estadisticas-financieras | Solo modalidad bancaria (diferida) |
| [9] | SBP · estudios e informes | https://www.superbancos.gob.pa/estadisticas-financieras/estudios | Solo modalidad bancaria (diferida) |

### 6.2 Endpoints derivados (no están en el PDF; verificar en Paso 1)

Construidos a partir de la documentación anterior. Si alguno no responde como
se describe, se corrige aquí y se registra la decisión en Notion.

```text
# [2] TVN RSS
GET https://www.tvn-2.com/rss/

# [3] GDELT DOC 2.0 — una consulta por tema y por ventana de fechas, dedupe por URL
GET https://api.gdeltproject.org/api/v2/doc/doc
    ?query=<tema> sourcecountry:panama
    &mode=ArtList&format=json&maxrecords=250
    &startdatetime=YYYYMMDDHHMMSS&enddatetime=YYYYMMDDHHMMSS
# temas: "Panama", logística/Canal, turismo, economía, eventos naturales
# la API DOC cubre una ventana reciente limitada (verificar): refuerza D6

# [4] Banco Mundial — una consulta por indicador (6), luego completar la cuadrícula
GET https://api.worldbank.org/v2/country/PAN;CRI;COL;DOM;MEX;GTM/indicator/<INDICADOR>
    ?date=2010:2024&format=json&per_page=1000
# indicadores: NY.GDP.MKTP.KD.ZG, FP.CPI.TOTL.ZG, SL.UEM.TOTL.ZS,
#              SP.POP.TOTL, IT.NET.USER.ZS, NE.EXP.GNFS.ZS

# [7] USGS — caja regional 2024, M >= 3
GET https://earthquake.usgs.gov/fdsnws/event/1/query
    ?format=geojson&starttime=2024-01-01&endtime=2024-12-31T23:59:59
    &minlatitude=5&maxlatitude=12&minlongitude=-86&maxlongitude=-76
    &minmagnitude=3
```

## 7. Seguridad, privacidad y ética

- **Citas.** Campos citables por tipo: noticia `titulo`/`alcance_texto`; indicador `valor`+`anio`+`unidad` (año y unidad obligatorios, T04); sismo `magnitude`/`time`/`place`. Toda cifra o año de la afirmación debe aparecer en el campo citado tras normalizar formato es-PA (`1.350` ≡ `1,350`). Inferencias e hipótesis citan sus premisas.
- **Abstención.** Si el mejor puntaje de recuperación está bajo el umbral calibrado en desarrollo, se abstiene **sin llamar al LLM**.
- **Anti-inyección.** Delimitadores aleatorios por petición; quitar caracteres de control, de ancho cero y lookalikes del delimitador; el modelo no tiene herramientas ni acciones; sin secretos en el prompt; salida pydantic; detector heurístico que marca la fuente como "contenido sospechoso" en la ficha. T07 se corre contra LLM **y** fallback local.
- **USGS** solo para hechos sísmicos; la caja geográfica no es el territorio de Panamá; nunca evidencia de inundación o pérdidas.
- **Reputación.** Afirmaciones con acusaciones solo como tipo `declaracion` con atribución. Sin perfiles de personas; minimizar datos personales. Un caso adversarial del benchmark lo prueba.
- **Secretos.** `.env` fuera del repo; `.env.example` sin valores; escaneo de secretos antes de entregar; sin tokens en logs, capturas ni prompts. Notion compartido solo con equipo y jurado.

## 8. Plan por días y pasos

Regla: **rebanada vertical funcional al cierre del Día 1**, luego profundizar.
**Congelamiento de funcionalidades al 75 %**; después solo pruebas, métricas y Notion.

| Día / tramo del reto | Pasos |
|---|---|
| Día 1 · Inicio 15 % + Datos y diseño 20 % | Gate 0, Paso 1, Paso 2 (en paralelo), Paso 3 (rebanada) |
| Día 2 · Construcción 40 % | Pasos 4, 5, 6, 7 → **congelamiento** |
| Día 3 · Pruebas 15 % + Cierre 10 % | Pasos 8, 9 |

### Gate 0 — Decisiones y accesos
- ADR 0002 con D1–D7.
- Notion Business: acceso confirmado; 8 páginas creadas; backlog con ≥ 8 tareas.
- Descargar y cachear `intfloat/multilingual-e5-small`; verificar Ollama `llama3.2` y credencial Gemini (D2, D3).
- Organizador consultado. El §11 del reto le asigna: confirmar cupos de Notion
  Business, preparar **snapshot común y set reservado**, verificar derechos de
  extractos TVN, designar **persona editorial** revisora, conectividad y fallback
  local, y congelar datos ≥ 72 h antes del evento. Preguntar por cada uno:
  - snapshot y rango de fechas → decide D6;
  - set reservado → decide si el Paso 2 escribe las 20 reservadas o solo las 40 de desarrollo;
  - persona editorial → P@5 contra su selección o evaluación declarada exploratoria;
  - derechos TVN → si se pueden usar descripciones del RSS en `alcance_texto` o solo titulares.
- La licencia Notion no cubre servicios externos de IA: costo del proveedor a cargo del equipo.
- **Salida:** ADR fusionado; capturas de acceso Notion; D2 y D6 cerrados; respuestas del organizador registradas.

### Paso 1 — Snapshot
- Si el organizador entrega paquete: validarlo y usarlo; extractores solo como receta.
- Si no (timebox 2 h): `extract-tvn-rss`, `extract-gdelt` (ventanas, ≤ 250/consulta, dedupe por URL), `extract-worldbank` (una consulta por indicador, cuadrícula completa), `extract-usgs` (lat 5–12, lon −86 a −76, M ≥ 3, 2024).
- `build-snapshot`: manifest, reporte de calidad, excluidos.
- **Salida:** ≥ 100 noticias (≥ 20 TVN); 540 filas de indicadores; T01 verde; hash estable en dos corridas.

### Paso 2 — Etiquetado y benchmark (en paralelo a Paso 3)
- Si el organizador entrega el set reservado, el equipo solo escribe las 40 de desarrollo y nunca abre el reservado hasta la evaluación final.
- Si no lo entrega: primero las **20 reservadas** (archivo separado que el agente nunca carga).
- Etiquetar ~100 noticias: tema (economía, logística/Canal, turismo, servicios públicos, eventos naturales, regulación) y cluster de evento; registrar anotador y guía.
- Benchmark estratificado: sustentadas 20/10, contradicción 7/3, sin respuesta 7/3, adversariales 6/4 (sintéticas marcadas).
- **Salida:** conteos exactos por tipo; prueba que falla si el corpus contiene IDs reservados.

### Paso 3 — Organizar + rebanada vertical
- Baseline palabras clave; IA = prototipos por tema (coseno + margen; bajo margen → baseline) y clustering union-find.
- Rebanada: cargar → clasificar → puntuar (versión mínima) → bandeja estática en `/` de la app FastAPI.
- `eval-organize`: macro-F1 IA vs baseline, pureza de clusters, casos donde gana el baseline.
- **Salida:** F1 de ambos reportado con ganador o razón documentada; bandeja visible; T02, T03 verdes.

### Paso 4 — Contextualizar, puntuar, evidencia, contradicciones
- Enlaces a indicadores/sismos con período, unidad y limitaciones visibles; sin relación sustentada no se enlaza.
- Motor de puntaje completo (§5); 10 casos dorados calculados a mano.
- `contradict`: cifras divergentes misma entidad+unidad → "revisión pendiente".
- **Salida:** T04, T08 verdes; 10/10 dorados; prueba "USGS nunca respalda inundación".

### Paso 5 — Recuperación, consulta y abstención
- BM25 (baseline) + coseno con RRF k=60; preprocesado español (acentos, stopwords, stemming ligero) sobre `titulo + alcance_texto`.
- Umbral de abstención calibrado en el set de desarrollo.
- **Salida:** T05, T06 verdes; umbral y su curva registrados en Notion.

### Paso 6 — Generación con citas
- `llm.py` con usage de tokens y timeout acorde.
- Modelo pydantic: `titulo`, `enfoque_interes_publico`, `brief` (≤ 250 palabras), `preguntas[3]`, `verificaciones_pendientes[]`, `guion` (110–150 palabras ≈ 45–60 s a 2,5 palabras/s), `copy` (≤ 80), `afirmaciones[] { texto, tipo: hecho|declaracion|inferencia|hipotesis, citas[] { id_evidencia, campo } }`, `vacios[]`.
- Chequeo de contenido prohibido: entrevistas, citas textuales o imágenes inventadas.
- Página Notion "Diseño de solución": modelo, versión, prompts, parámetros, costo.
- **Salida:** T07 (LLM y fallback), T09 verdes; cobertura de citas 100 % en dev.

### Paso 7 — Interfaz
- Bandeja con componentes desplegables, `RULES_VERSION`, filtros por tema y estado.
- Ficha: qué se reporta, quién, qué está respaldado, qué falta, acción recomendada, "contenido sospechoso".
- Borrador con citas clicables; revisión con 5 estados y nombre del revisor.
- Indicador de proveedor y de modo offline/BM25.
- Accesibilidad básica: teclado y axe en la vista principal (no matriz completa de anchos; YAGNI).
- **Salida:** e2e de CU-01 y CU-02 verdes. → **Congelamiento.**

### Paso 8 — Pruebas, métricas y Notion
- Matriz T01–T10 con resultado observado y evidencia; al menos una prueba fallida con su corrección.
- `eval-senal` sobre dev y reservado; salidas en `eval-results/senal/<fecha>.json` con numerador, denominador y fallos.
- Revisión humana de ≥ 30 afirmaciones; P@5; latencia; costo; ahorro de tiempo o hipótesis.
- Notion: ≥ 5 fichas (una insuficiente), ≥ 3 decisiones justificadas, catálogo con URL/fecha/hash/licencia, riesgos y ética.
- **Salida:** todas las métricas con n; checklist de admisión Notion completa.

### Paso 9 — Entrega y pitch
- README Parte 2, `.env.example`, dependencias fijadas, comando único, escaneo de secretos.
- Pitch desde Notion: 1 problema / 1 solución / 4 demo (consulta, ficha, borrador, abstención) / 2 IA, baseline y métricas / 1 valor / 1 límites; + 5 min preguntas.
- Respuestas preparadas a las 4 preguntas dinámicas del jurado.
- Revalidar acceso del jurado a Notion y GitHub al cierre.
- **Salida:** ensayo ≤ 10 min **con red desconectada**.

## 9. Trazabilidad

### Casos de uso

| CU | Paso | Prueba |
|---|---|---|
| CU-01 ranking top 5 | 4, 7 | `senal/tests/e2e/test_cu01.py` |
| CU-02 tema económico + serie oficial + brief | 4, 6, 7 | `senal/tests/e2e/test_cu02.py` |
| CU-03 repetición vs corroboración | 3, 4 | `senal/tests/unit/test_provenance.py` |
| CU-04 cifra inexistente / contradicción | 4, 5 | `senal/tests/evals/test_query.py` |
| CU-05 banca | — | Diferido |

### Pruebas de aceptación

| ID | Paso | Archivo |
|---|---|---|
| T01 | 1 | `senal/tests/unit/test_ingest.py` |
| T02, T03 | 3 | `senal/tests/unit/test_organize.py` |
| T04 | 4 | `senal/tests/unit/test_context.py` |
| T05, T06 | 5 | `senal/tests/evals/test_query.py` |
| T07 | 6 | `senal/tests/evals/test_injection.py` |
| T08 | 4 | `senal/tests/unit/test_score.py` |
| T09 | 6 | `senal/tests/evals/test_draft.py` |
| T10 | 8 | `senal/tests/e2e/test_offline.py` |

Las pruebas nunca llaman a la red: proveedor y embeddings con dobles.

### Rúbrica → evidencia

| Dimensión (pts) | Dónde se demuestra |
|---|---|
| Utilidad (20) | CU-01/CU-02 en demo; hipótesis o medición de ahorro |
| Prototipo y flujo (20) | Rebanada Día 1 → flujo completo Paso 7 |
| Uso de IA (15) | Embeddings vs baseline (F1, RRF vs BM25), dónde no ayuda |
| Evidencias y explicabilidad (15) | Puntaje desglosado, validador de citas, contradicciones, abstención |
| Notion (15) | 8 páginas, registro durante el evento, prueba fallida + corrección |
| Calidad técnica (10) | `uv run pytest` + `ruff` + `mypy`, evals guardadas, ADR 0002 |
| Seguridad y ética (5) | T07, reglas de reputación, escaneo de secretos |

## 10. Riesgos

| Riesgo | Mitigación |
|---|---|
| Rango de fechas inalcanzable (D6) | Preguntar al organizador; si no, 90 días + desviación documentada |
| Ollama/`bge-m3` no disponible | Gemini para precalcular; consultas nuevas → BM25 rotulado |
| `nomic-embed-text` débil en español | Modelo multilingüe en D2 |
| Notion Business sin acceso a tiempo | Gate 0 bloquea; registro en Markdown local mientras tanto |
| LLM inventa citas o cifras | Validador determinista + compuerta de abstención |
| Puntaje deriva entre corridas | `ahora` = fecha de corte; constantes versionadas |
| GDELT responde 429 (visto 2026-10-06) | Pausa ≥ 5 s entre consultas, reintentos con backoff, cache en `raw/` |
| Pesos del modelo de embeddings sin red en la demo | Descargar y cachear en Gate 0; ruta local en `.env` |
| Derechos de contenido | Solo titulares/metadatos; condiciones en `fuentes.json` |

## 11. Índice de progreso

| Paso | Estado | Evidencia |
|---|---|---|
| Validación del plan | Hecha | §0 |
| Cotejo con PDF original | Hecho | §6.1, §6.2 |
| Gate 0 | Cerrado (Notion pendiente del organizador) | ADR 0002, `docs/parte-2-preguntas-organizador.md` |
| Paso 1 — Snapshot | Verde | 3.049 noticias (68 TVN), 540 indicadores, 82 sismos; T01 |
| Paso 2 — Etiquetado y benchmark | Parcial: benchmark dev 40 casos (borrador); planillas listas; falta etiquetado humano y set reservado | `senal/evals/` |
| Paso 3 — Organizar + rebanada | Verde (macro-F1 pendiente de etiquetas) | `organize.py`; T02 |
| Paso 4 — Contexto, puntaje, contradicciones | Verde | T04, T05, T08, CU-03; reglas `senal-1.1.0` |
| Paso 5 — Consulta y abstención | Verde | T06; abstención 7/7 |
| Paso 6 — Generación con citas | Verde | T07, T09; cobertura de citas 100 % |
| Paso 7 — Interfaz | Verde | `senal/src/senal/web/`; `tests/web/` |
| Paso 8 — Pruebas, métricas y Notion | Verde en código y registro local; pendiente métricas humanas y migración a Notion | `docs/notion/` |
| Paso 9 — Entrega y pitch | Parcial: README, `server_start`, guion de pitch; falta ensayo offline y acceso del jurado | `senal/README.md`, `docs/notion/07-…` |
