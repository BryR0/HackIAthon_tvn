# Bitácora de ejecución

Registro hecho **durante** el trabajo (reto §5: "registro durante la ejecución,
no solo un resumen final"). Hora de Panamá (UTC−5). Cada entrada con commit de
respaldo en la rama `parte-2/tvn-senal-decision`.

| Fecha y hora | Qué pasó | Evidencia |
|---|---|---|
| 2026-10-06 ~12:30 | Análisis del reto TVN; se crea la rama de la Parte 2 sin tocar la Parte 1 | rama `parte-2/tvn-senal-decision` |
| 2026-10-06 ~13:00 | Validación del plan con 3 agentes revisores (arquitectura, cobertura de requisitos, reuso de `docversion`). Veredicto: aprobar con cambios | plan §0 |
| 2026-10-06 ~13:15 | Cotejo con el PDF original: se recuperan las 9 URLs de fuentes que el `.md` había perdido | plan §6.1 |
| 2026-10-06 13:30 | Plan v2 publicado | `ec3ef9f` |
| 2026-10-06 13:36 | **Decisión:** stack Python + FastAPI en lugar de Next.js (ADR 0002) | `be85aa9` |
| 2026-10-06 13:41 | Validación del snapshot (T01) en verde | `67e4e58` |
| 2026-10-06 13:44 | Parsers de TVN RSS, GDELT, Banco Mundial y USGS | `b7187e0` |
| 2026-10-06 13:49 | Extracción y snapshot determinista. **Hallazgo:** la cuadrícula del reto da 540 filas, no 1.350 | `b297e02` |
| 2026-10-06 13:52 | Clasificación por embeddings con abstención + baseline + agrupación (T02) | `2052bf3` |
| 2026-10-06 13:53 | Motor de puntaje con reglas versionadas (T08) | `d43d6c3` |
| 2026-10-06 13:55 | Procedencia independiente (CU-03) y estado de evidencia | `5e33ecf` |
| 2026-10-06 ~13:45 | **Prueba fallida:** pytest no podía escribir en la carpeta temporal del sistema (`PermissionError`). **Corrección:** carpeta temporal dentro del proyecto | `pyproject.toml` |
| 2026-10-06 ~13:47 | **Prueba fallida:** se esperaban 1.350 indicadores y salieron 540. **Corrección:** la prueba replicaba la errata del reto; el código era correcto | `b297e02` |
| 2026-10-06 ~13:45 | GDELT responde 429 (límite 1 consulta / 5 s). Extracción con espera creciente en segundo plano | `extraccion.py` |
| 2026-10-06 14:04 | Se quitan preguntas al organizador que el reto ya responde | `573596c` |
| 2026-10-06 ~14:10 | Organizador: "avancen con el desarrollo, documenten todo"; Notion se habilita después. Se crea este espacio local | `docs/notion/` |
| 2026-10-06 ~14:40 | Snapshot real: 3.758 noticias únicas → 3.049 en es/en (68 TVN), 540 indicadores, 82 sismos. GDELT: 22/30 consultas OK, 8 con 429 registradas en el manifest | `8506a5c` |
| 2026-10-06 ~14:40 | **Decisión:** descripciones del RSS de TVN fuera del snapshot hasta autorización (reto §6 A: "usar inicialmente los metadatos") | `catalogo.USAR_EXTRACTOS_TVN` |
| 2026-10-06 ~14:50 | **Prueba fallida (calibración):** prototipos con "Panamá" daban margen mediano 0,008 entre temas y `servicios_publicos` casi nunca salía (4/3049). **Corrección:** ejemplares sin topónimo + vecino más cercano | `organize.py` |
| 2026-10-06 ~14:50 | **Prueba fallida (calibración):** enlace simple encadenaba eventos (cluster de 1.327 noticias a umbral 0,90). **Corrección:** enlace promedio, distancia 0,10 → clusters coherentes (p. ej. 39 notas de la visita Mulino–Sheinbaum) | `organize.py` |
| 2026-10-06 ~14:50 | Anti-inyección: saneo, delimitador aleatorio y detector de instrucciones incrustadas (T07) | `seguridad.py` |
| 2026-10-06 ~15:05 | Pipeline real: 3.049 noticias → 1.614 temas en 18 s (0,8 s con caché de embeddings) | `32fa823` |
| 2026-10-06 ~15:10 | **Prueba fallida:** `embeddings.npz` marcado como texto por `.gitattributes` (riesgo de corrupción). **Corrección:** `*.npz binary`; SHA-256 del blob verificado idéntico | `fix: marca embeddings.npz` |
| 2026-10-06 ~15:30 | **Prueba fallida (T06, corpus real):** "precio del bitcoin en Japón" no se abstenía: "precio" coincidía con notas de gasolina. **Corrección:** cobertura léxica por documento (≥50 % de términos en una misma evidencia) | `generate.py` |
| 2026-10-06 ~15:45 | Interfaz web local (bandeja, ficha, borrador, revisión, consulta, calidad) con CSRF, CSP estricta y sin CDN (T10) | `04182e2` |
| 2026-10-06 ~15:55 | **Prueba con Ollama `llama3.2`:** 14,7 s, 1.734+554 tokens. El validador descartó 3/3 afirmaciones (ID mal citado, tipo inválido, sin cita). **Corrección:** normalizar forma (`Hecho`→`hecho`, `[N-1]`→`N-1`) y, si hay evidencia pero el modelo no deja afirmaciones válidas, plantilla extractiva con aviso | `generate.py` |
| 2026-10-06 ~16:45 | **Benchmark dev v1 (40 casos):** BM25 y híbrido 38/40 y 36/40; abstención correcta 5/7 y 4/7 (meta ≥80 %). Fallaban preguntas por años ausentes (PIB 2026, elecciones 2029) | `eval-results/senal/*` |
| 2026-10-06 ~16:55 | **Corrección:** si la consulta nombra un año, una misma evidencia pertinente debe contenerlo. Efecto colateral: S19/S20 (Banco Mundial 2024) pasaron a abstenerse. **Corrección 2:** metadatos de fuente/periodicidad en evidencia de indicadores | `generate.py`, `pipeline.py` |
| 2026-10-06 ~17:00 | **Benchmark dev v2:** 40/40 en BM25 y en híbrido; abstención 7/7; 0/27 abstenciones incorrectas; cobertura de citas 100 %. **Límite declarado:** reglas ajustadas viendo el set de desarrollo (riesgo de sobreajuste); el set reservado es la medida válida. En este benchmark la IA no mejora la recuperación frente a BM25 | `eval-results/senal/*` |
| 2026-10-06 ~17:20 | Lanzador `server_start` (Windows/Linux): crea `.env`, instala `requirements.txt`, libera el puerto (cerró el PID 9924) e inicia el servidor. Probado de punta a punta en Windows | `2be5802` |
| 2026-10-06 ~17:30 | **Revisión de código ECC** (python-reviewer + security-reviewer): 0 CRITICAL; 3 HIGH (números con varios separadores tumbaban el validador; cifras del texto libre sin validar; errores del proveedor sin capturar) y 9 MEDIUM. Todos corregidos con pruebas | `d7e5bbb`, `c9c0a56` |
| 2026-10-06 ~17:30 | Aviso de seguridad al equipo: el `.env` de la raíz (Parte 1) contiene una clave real; no está en git. Recomendado rotarla si se compartió | — |
| 2026-10-06 ~17:40 | **Decisión (D7):** reglas `senal-1.0.0` → `senal-1.1.0`. Relevancia de "medio panameño sin mención a Panamá" 0,8 → 0,5: una nota de drones en el mar Negro era la #2 de la agenda | `score.py` |
| 2026-10-06 ~17:40 | 5 fichas trazables generadas de la bandeja real (incluye un caso con evidencia insuficiente y una abstención) | `docs/notion/04-casos-y-evidencias.md` |
| 2026-10-07 | **Extensión bancaria — plan v2** validado por ECC (architect + planner: aprobar con cambios). Banca como modalidad dentro de la misma app, no segundo producto. Puntaje `senal-1.1.0` intacto; fuera indicadores de solidez (riesgo bancario, §2/§9.1) | `plans/parte-2-extension-bancaria.md`, ADR 0003 |
| 2026-10-07 | **Hallazgo:** los 12 Informes de Actividad Bancaria 2024 de la SBP responden 200 y tienen texto extraíble; número de cuadro, página y decimales cambian por mes; agosto trae además una tabla por provincias | ADR 0003 |
| 2026-10-07 | **Prueba fallida (exploración):** regex ingenuo de "liquidez X%" devolvía 15,3 (que es el IAC) → se descartan ratios; solo la tabla de crédito local por sector. Febrero parte la etiqueta "Act. financiera y de / seguros" en dos líneas → se une con la línea previa | `sbp.py`, fixtures reales |
| 2026-10-07 | Fuente D en el snapshot: 12/12 meses, 156 filas (13 sectores), 0 nulos, sumas consistentes. Paquete editorial byte a byte idéntico (mismos SHA-256) | `sbp_series.csv`, `manifest.json` |
| 2026-10-07 | Contexto bancario: mapa `banca-1.0.0` tema → sectores SBP (siempre hipótesis), carga opcional de `sbp_series.csv` (la app arranca sin él) | `banca.py`, `pipeline.py` |
| 2026-10-07 | Motor único: `Formato` inyectable en `generate.py`; el boletín reutiliza compuerta, anti-inyección, validador y plantilla. Editorial sin regresión | `generate.py`, `boletin.py` |
| 2026-10-07 | **Prueba fallida:** la hipótesis que solo cita el nombre de una serie SBP se descartaba por "sin período". **Corrección:** el período `MM/AAAA` se exige al citar cifras | `cite.py` |
| 2026-10-07 | Web: selector Editorial/Banca, contexto SBP en la ficha, `POST /tema/{id}/boletin`, CU-05 en la consulta, revisión separada por modalidad. Verificado en navegador | `web/`, `review.py` |
| 2026-10-07 | **Prueba con `llama3.2`:** el JSON del boletín omitía `tipo` y `citas` (esquema abreviado en el prompt). **Corrección:** esquema completo; el validador aún descarta sus citas y se usa la plantilla con aviso | `boletin.py` |
| 2026-10-07 | Benchmark bancario: dev 7/7 (BM25 e híbrido); reservado 3/3 en BM25 y **2/3 en híbrido** (RB03: la fuente con instrucciones quedó en el puesto 10 de k = 8; no se usó). Regresión editorial 40/40 | `eval-results/senal/*banca*` |
| 2026-10-07 | **Revisión ECC** (python-reviewer + security-reviewer): 0 CRITICAL; 2 HIGH (PDF corrupto abortaba el snapshot; el boletín podía citar un mes SBP no más reciente) y 9 MEDIUM (léxico prohibido evadible por conjugaciones, comillas o rótulo "declaración"; rutas y tamaño de PDF sin tope; raíces cortas como "ley" o "servicio"; resumen vacío o con cifra SBP sin período). Todos corregidos con prueba; 176 pruebas verdes; métricas sin cambios | `sbp.py`, `snapshot.py`, `boletin.py`, `cite.py` |
