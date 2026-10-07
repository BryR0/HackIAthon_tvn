# Blueprint — Parte 2 · Extensión bancaria (CU-05, fuente D · SBP)

Estado: **v2 — validado por ECC e implementado (pasos 0–6 verdes; commit pendiente).**
Aprobado por el usuario el 2026-10-07: "agregalo como una extension para no tener 2 proyectos separados".
Rama: `parte-2/tvn-senal-decision` (misma app `senal/`).
Base: reto §1 ("se admite la bancaria como alternativa o extensión, sin exigir
dos productos completos"), §3 "Salida bancaria: boletín de entorno", §4 CU-05,
§6 D, §7, §9 T09, §12 [8][9].

## 0. Validación del plan (2026-10-07)

| Revisor ECC | Veredicto | Cambios integrados |
|---|---|---|
| architect | Aprobar con cambios | Un solo motor de redacción (`Formato` inyectable, no `boletin.py` paralelo); validador SBP en `cite.py`; **no tocar el puntaje** ni `Tema`; CU-05 se abstendría hoy → ruta Banca fuerza evidencias por categoría; IDs con período; carga opcional del CSV; `modalidad` en revisión con clave `(id, modalidad)`; quitar indicadores de solidez (son riesgo bancario) |
| planner | Aprobar con cambios | Campo `alcance` + frase solo-metadatos; léxico prohibido ampliado y solo sobre inferencia/hipótesis; prueba de consistencia del mapa; tolerancia ±0,5·n; ADR al paso 0; timebox y salida por paso; benchmark repartido 40/20 con contradicción; matriz de trazabilidad completa |

## 1. Qué pide el reto → dónde se prueba

| Exigencia | Prueba |
|---|---|
| §3 resumen ≤ 250 palabras, sectores, horizonte, evidencia, 3 preguntas | TB06 |
| §3 separar observación de hipótesis de impacto | TB06b (nada de `hipotesis_impacto` en `observaciones`; tipos correctos) |
| §3 sin compra/venta, pérdidas, impagos, exposición de cartera | TB05 |
| §3 "Basado únicamente en titular/metadatos" | TB10 |
| §4 CU-05 consulta literal "entorno logístico" → contexto sectorial, sin score ni alerta | TB11 (integración) |
| §6 D 12 informes 2024, período, unidad, página | TB01, TB03 |
| §6 D condiciones de reutilización registradas | TB12 (catálogo + manifest) |
| §6 D sin datos de clientes ni por banco | TB12 (esquema de columnas cerrado) |
| §6 D no es opinión oficial de la SBP | TB06 (aviso en boletín) + catálogo |
| §7 ficha con modalidad | TB13 (`test_review.py`) |
| §3 etapa 7 revisión humana sobre el boletín | TB13 |
| §9 T04 análogo: cifra mensual con período, no "hoy" | TB04 |
| §9 T06/T07 | TB07, TB08 |
| §9 T10 demo sin PDFs ni red | TB14 (carga solo con CSV; sin CSV la app sigue) |
| §9.1 cobertura de citas y abstención con numerador/denominador | Benchmark |
| §9.1 validez de sustento revisada a mano | Planilla `evals/etiquetado/boletin_sustento.csv` (≥ 30 afirmaciones si se producen) |

## 2. Hallazgo de factibilidad (2026-10-07)

- `https://www.superbancos.gob.pa/documentos/financiera_y_estadistica/estudios/IAB/IAB-MMAA.pdf`
  responde **200** para los 12 meses de 2024 (0,9–1,5 MB c/u, 16–24 páginas).
- Texto extraíble con `pypdf`. La tabla de crédito local por sector (fila "Comercio
  11,624.4 12,213.3 …") aparece en **los 12 meses**; el número de cuadro, la página y
  los decimales cambian entre meses.
- Portada: "únicamente con fines informativos", libre acceso, citar a la SBP y ser fiel
  a su contenido y contexto.

## 3. Principio

**El LLM nunca decide prioridad, ni verdad, ni sector afectado, ni inventa evidencia.**
Relación tema ↔ sector = tabla versionada, siempre rotulada *hipótesis*.

## 4. Alcance

### Incluido
1. Fuente D: descarga de 12 IAB 2024 → `data/processed/sbp_series.csv` (solo la tabla
   de crédito local por sector: **12 × 13 = 156 filas**; el plan v2 decía 14 sectores, la tabla real tiene 13).
2. Mapa sectorial `banca-1.0.0` y enlace tema → series SBP, calculado **en la vista**.
3. Boletín de entorno con el **mismo motor** de `generate.py` (formato inyectable).
4. UI: `?modalidad=banca` (lista permitida `editorial|banca`, defecto `editorial`),
   botón "Generar boletín" en la ficha, consulta CU-05 precargada.
5. Pruebas, benchmark, ADR 0003, Notion local, bitácora por paso.

### Fuera de alcance
- Indicadores de solidez (morosidad, cartera vencida, IAC, liquidez): son riesgo
  bancario (§2, §9.1) y su regex es frágil.
- Cambiar el puntaje `senal-1.1.0` o `Tema`. Datos por banco o cliente. Gráficos.

## 5. Diseño

### 5.1 `sbp_series.csv` (esquema cerrado)

`id_serie, periodo, nombre, sector, valor, unidad, valor_base, periodo_base,
variacion_pct, cuadro, pagina_pdf, fuente_url, sha256_pdf`

- `id_serie` = `SBP:credito_local:<sector_slug>`; ID de evidencia =
  `SBP:credito_local:<sector_slug>:2024-12`.
- `valor` sin separadores de miles (`13177`, no `13,177`): `cite._valores` lee la coma
  como decimal.
- `periodo` `2024-12`; en texto se exige `12/2024`. `periodo_base` = columna comparada
  (semántica de columnas registrada por mes tras inspección).
- `pagina_pdf` 1-based del PDF (no la impresa). `cuadro` = título anclado
  ("Crédito local – Sistema Bancario Nacional"), no el número.
- Aviso SBP una sola vez en catálogo y boletín, no por fila.
- Nulos = vacío; nunca `0`.

Validaciones (no bloquean; marcan y reportan): Σ sectores privados ≈ Sector Privado y
Público + Privado ≈ Total con tolerancia **±0,5·n**; 12 períodos distintos; 14 sectores
por período; faltantes → `excluidos` con motivo.

Riesgos de parser cubiertos con **fixtures de texto real de 3 meses** (ene, jun, dic):
nombres partidos en dos líneas, negativos con guion o paréntesis, decimales variables.

### 5.2 `banca.py` (`banca-1.0.0`)

Mapa tema → sectores **que el parser realmente emite** (confirmado contra el CSV;
prueba de consistencia):

| Tema | Sectores (hipótesis) |
|---|---|
| logistica_canal | Comercio, Industria |
| turismo | Comercio, Consumo Personal |
| economia | Total, Consumo Personal, Hipotecario |
| eventos_naturales | Agricultura, Ganadería, Pesca, Construcción |
| servicios_publicos | Industria, Sector Público |
| regulacion | Act. Financieras y Seguros |

Horizonte en dos partes: **período de la evidencia** (fechas de noticias + período SBP)
y **horizonte de seguimiento** por tema, rotulado "supuesto".

### 5.3 Motor único de redacción (`generate.py`)

- `Formato` congelado: `sistema`, `modelo` (pydantic), `extractivo(consulta, evidencias)`,
  `limites`, `reglas_extra`. `FORMATO_EDITORIAL` = comportamiento actual (sin cambios).
- `responder(..., formato=FORMATO_EDITORIAL, ids_obligatorios=...)`;
  `ResultadoRespuesta.paquete: Paquete | Boletin`.
- Se reutilizan: compuerta de abstención, aislamiento de sospechosas (T07),
  `FRASE_SOLO_METADATOS`, control de cifras en texto libre, caída a plantilla.
- `boletin.py` = solo datos: `SISTEMA_BANCA`, `Boletin`, extractivo, reglas extra.

`Boletin`: `titulo, resumen (≤250), alcance, horizonte_evidencia, horizonte_seguimiento,
sectores[{sector, razon}] (siempre hipótesis), observaciones[afirmación hecho|declaracion],
hipotesis_impacto[afirmación hipotesis|inferencia], preguntas_analista[3], evidencias[], vacios[]`.

### 5.4 Validador (`cite.py`)

- `CAMPOS_CITABLES["serie_sbp"] = nombre, periodo, valor, unidad, pagina_pdf, cuadro`.
- Regla de período por tipo (generaliza `indicador_sin_anio`): `anio` para Banco Mundial,
  `periodo` (`MM/2024`) para SBP; "hoy/actual/actualmente" junto a cifra SBP → descarte.
- Léxico prohibido **solo en `inferencia`/`hipotesis` y en `resumen`**: comprar, vender,
  invertir, recomendamos, pérdida(s), impago(s), default, exposición de (la) cartera,
  calificación/rating, riesgo de crédito, reducción de riesgo, alerta regulatoria,
  score/puntaje de cliente. Una declaración atribuida ("pérdidas por lluvias", según X) se
  conserva.

### 5.5 Integración

| Módulo | Cambio |
|---|---|
| `catalogo.py` | Fuentes [8][9] con licencia/aviso; quitar "SBP diferida" |
| `extraccion.py` | `_extraer_sbp` + flag `incluir_sbp` (SHA-256 ya lo da `_solicitar`) |
| `sbp.py` (nuevo) | parser de la tabla + validaciones; `TRANSFORMACIONES` con versión pypdf/parser |
| `snapshot.py` | escribe `sbp_series.csv` y reporte |
| `ingest.py` | `SerieSBP` dataclass congelada + `validar_series_sbp` → `ResultadoValidacion` |
| `pipeline.py` | `Snapshot.series_sbp` (opcional si falta CSV); `evidencias_de` agrega SBP; `aviso` en `CAMPOS_NO_INDEXADOS`. **Sin cambios en `Tema` ni puntaje** |
| `retrieve.py` | nada salvo campo no indexado |
| `generate.py` | `Formato` inyectable (refactor sin cambio de comportamiento editorial) |
| `boletin.py` (nuevo) | datos del formato bancario |
| `banca.py` (nuevo) | mapa, horizonte, `enlazar_sbp(tema, series)`, `evidencias_cu05(consulta)` |
| `review.py` | `Revision.modalidad`; clave `(id, modalidad)`; `ficha_contrato` usa modalidad |
| `web/` | `?modalidad=` validado; `POST /tema/{id}/boletin`; `_boletin.html`; consulta banca |

CU-05: la ruta Banca clasifica la consulta (`clasificar_por_palabras`), toma los temas
principales de esa categoría y sus series SBP y los pasa como `ids_obligatorios` (si no,
`_sin_sustento` abstiene).

## 6. Pruebas

| ID | Prueba |
|---|---|
| TB01 | Parser sobre fixtures reales (ene, jun, dic) → 14 filas c/u, valor, unidad, página |
| TB02 | Mes sin tabla → nulos + exclusión con motivo; no bloquea |
| TB03 | Sumas ±0,5·n; 12 períodos; SHA-256 en manifest |
| TB04 | Cifra SBP sin período o con "hoy" → descartada |
| TB05 | Léxico prohibido en hipótesis/resumen → descartado; en declaración atribuida → se conserva |
| TB06 | Boletín: ≤250 palabras, 3 preguntas, sectores como hipótesis, aviso SBP; TB06b separación |
| TB07 | Consulta banca sin sustento → abstención |
| TB08 | Fuente con instrucciones → no entra al boletín |
| TB09 | Web: `?modalidad` lista permitida + defecto; boletín HTMX; CSRF |
| TB10 | Solo metadatos → frase obligatoria |
| TB11 | CU-05 literal → Comercio/Industria citados, sin score ni alerta |
| TB12 | Catálogo con condiciones SBP; columnas de CSV = esquema cerrado |
| TB13 | Revisión de boletín guarda modalidad; no pisa el borrador editorial |
| TB14 | App arranca sin `sbp_series.csv` y sin red |
| Mapa | Cada sector de `banca-1.0.0` existe en el CSV |
| Bench | +10 casos banca repartidos 7 dev / 3 reservados: respondibles, abstención, contradicción, adversarial; léxico prohibido va a unitarias |

Común a cada paso: `pytest` completo verde (sin regresión editorial), `ruff`, `mypy`.

## 7. Orden, timebox y salida

| Paso | Timebox | Salida |
|---|---|---|
| 0 · ADR 0003 (D-B1..D-B4) + bitácora | 20 min | ADR escrito |
| 1 · Fuente D: catálogo, descarga, parser, snapshot | 2 h | TB01–TB03, TB12, 156 filas en CSV |
| 2 · `banca.py` + carga opcional | 1 h | Prueba de mapa, TB14 |
| 3 · `Formato` + boletín + validador | 2,5 h | TB04–TB08, TB10, editorial intacto |
| 4 · UI + revisión | 1,5 h | TB09, TB11, TB13, prueba en navegador |
| 5 · Benchmark, Notion local, README | 1,5 h | Métricas en `eval-results/senal/` |
| 6 · Revisión ECC (python-reviewer + security-reviewer), commit | 45 min | Sin CRITICAL/HIGH |

Bitácora `docs/notion/bitacora.md` al cerrar cada paso.

## 8. Decisiones (ADR 0003)

- **D-B1 Fuente:** IAB mensual 2024 (PDF) — 200 confirmado, texto extraíble, página citable.
- **D-B2 Parser:** `pypdf` (puro Python, fijado en `pyproject`).
- **D-B3 Puntaje:** `senal-1.1.0` intacto; banca = filtro + contexto + formato de salida.
- **D-B4 PDFs fuera de git:** se versionan CSV + SHA-256 (receta reproducible).

## 9. Recortes si falta tiempo (en orden)

1. Ruta LLM del boletín → solo plantilla extractiva.
2. `?modalidad` global → solo botón en ficha + ruta `/banca`.
3. Benchmark banca 10 → 6.
4. Horizonte de seguimiento → valor fijo "mediano (supuesto)".

No se recortan: TB04, TB05, TB10, TB11, aviso SBP.

## 10. Riesgos

| Riesgo | Mitigación |
|---|---|
| Formato de tabla cambia por mes | Ancla por título y nombre de sector; fixtures de 3 meses; reporte de faltantes |
| Lectura como alerta de riesgo | Hipótesis rotuladas, aviso SBP, léxico prohibido, sin indicadores de solidez |
| Regresión editorial al refactorizar `generate.py` | `FORMATO_EDITORIAL` por defecto; suite completa en cada paso |
| Latencia de la ruta LLM | Se mide p95; caída a plantilla |
| Confundir análisis con opinión SBP | Aviso en catálogo y boletín |

## 11. Progreso (2026-10-07)

| Paso | Estado | Evidencia |
|---|---|---|
| 0 · ADR 0003 | Verde | `docs/adr/0003-parte-2-extension-bancaria.md` |
| 1 · Fuente D | Verde | 12/12 meses, 156 filas, 0 nulos, sumas consistentes; paquete editorial con SHA-256 idénticos |
| 2 · `banca.py` + carga opcional | Verde | Prueba de mapa contra el CSV real; TB14 |
| 3 · `Formato` + boletín + validador | Verde | TB04–TB08, TB10, TB11; editorial 40/40 |
| 4 · UI + revisión | Verde | TB09, TB13; verificado en navegador (ficha, boletín, CU-05) |
| 5 · Benchmark, Notion local, README | Verde | Dev 7/7; reservado 2/3 híbrido (RB03 documentado), 3/3 BM25 |
| 6 · Revisión ECC | Verde | 0 CRITICAL; 2 HIGH y 9 MEDIUM corregidos con prueba; 176 pruebas. Commit pendiente de aprobación |
