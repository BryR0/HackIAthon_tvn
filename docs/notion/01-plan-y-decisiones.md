# Plan y decisiones

Plan completo: `plans/parte-2-tvn-senal-a-decision.md`; extensión bancaria: `plans/parte-2-extension-bancaria.md`. Cronología: [bitácora](bitacora.md).

## Backlog

| # | Tarea | Responsable | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Validar el plan con revisores (arquitectura, cobertura, reuso) | BryR0 + agentes ECC | Hecho | plan §0 |
| 2 | ADR 0002: stack, embeddings, reglas | BryR0 | Hecho | `docs/adr/0002-…` |
| 3 | Extracción y snapshot con manifest (T01) | BryR0 | Hecho | `senal/data/processed/` |
| 4 | Clasificación por embeddings + baseline + agrupación (T02) | BryR0 | Hecho | `organize.py` |
| 5 | Puntaje explicable y estado de evidencia (T08, CU-03) | BryR0 | Hecho | `score.py`, `evidence.py` |
| 6 | Contexto oficial y contradicciones (T04, T05) | BryR0 | Hecho | `context.py`, `contradict.py` |
| 7 | Recuperación, abstención y validador de citas (T06) | BryR0 | Hecho | `retrieve.py`, `cite.py` |
| 8 | Generación con citas y anti-inyección (T07, T09) | BryR0 | Hecho | `generate.py`, `seguridad.py` |
| 9 | Interfaz web y revisión humana | BryR0 | Hecho | `web/`, `review.py` |
| 10 | Benchmark de desarrollo y arneses de evaluación | BryR0 | Hecho | `evals/` |
| 11 | Lanzador `server_start` Windows/Linux | BryR0 | Hecho | `server_start.*` |
| 12 | Revisión de código y seguridad | Agentes ECC | Hecho | bitácora 17:30 |
| 13 | Etiquetado humano de temas (macro-F1) | Persona del equipo | Pendiente | `evals/etiquetado/temas.csv` |
| 14 | Selección del editor para Precision@5 | Editor TVN | Pendiente | `evals/etiquetado/ranking_candidatos.csv` |
| 15 | Revisar ≥ 30 afirmaciones (validez de sustento) | Persona del equipo | Pendiente | fichas |
| 16 | Revisar etiquetas del benchmark y correr el set reservado | Organizador + equipo | Pendiente | `evals/benchmark_dev.jsonl` |
| 17 | Migrar este espacio a Notion Business | Equipo | Bloqueado: Notion no habilitado | `docs/notion/` |
| 18 | Ensayo del pitch sin internet (≤ 10 min) | Equipo | Pendiente | página 07 |
| 19 | Extensión bancaria: plan v2 validado por ECC, ADR 0003 | BryR0 + agentes ECC | Hecho | `plans/parte-2-extension-bancaria.md` |
| 20 | Fuente D (SBP): 12 informes 2024 → 156 series | BryR0 | Hecho | `sbp_series.csv`, `sbp.py` |
| 21 | Boletín de entorno con el mismo motor + CU-05 en la web | BryR0 | Hecho | `boletin.py`, `banca.py`, `web/` |
| 22 | Benchmark bancario (7 dev / 3 reservados) | BryR0 | Hecho | `evals/benchmark_banca_*.jsonl` |
| 23 | Persona bancaria revisa boletines y etiquetas del benchmark bancario | Analista bancario | Pendiente | fichas `banca_boletin` |

## Decisiones justificadas

| # | Fecha | Decisión | Alternativas | Justificación |
|---|---|---|---|---|
| D1 | 06/10 | Python + FastAPI + Jinja en `senal/` | Next.js (Parte 1), Streamlit, FastAPI + Next | El reto no pide web pública; exige demo sin internet. Python permite embeddings en proceso, sklearn y un solo runtime |
| D2 | 06/10 | `multilingual-e5-small` en proceso | Ollama `nomic-embed-text`, Gemini embeddings | GDELT mezcla español e inglés; nomic es anglocéntrico; e5 funciona sin red una vez descargado |
| D3 | 06/10 | Redacción en cascada Gemini → Ollama → plantilla extractiva | Solo LLM | Sin LLM la demo sigue funcionando; la plantilla nunca inventa |
| D4 | 06/10 | Revisión en `reviews.jsonl` local | Memoria de servidor | Persistente y auditable; la demo es local |
| D5 | 06/10 | UTC en datos, hora de Panamá en la UI; `ahora` = fecha de corte | Reloj del sistema | El puntaje no deriva entre corridas |
| D6 | 06/10 | Noticias de los últimos 90 días (desviación declarada) | `[2024-01-01, 2025-10-01)` | Ninguna fuente pública de noticias alcanza 2024 desde 2026-10 |
| D7 | 06/10 | Reglas `senal-1.1.0`: medio panameño sin mención a Panamá 0,8 → 0,5 | Mantener 0,8 | Una nota internacional (drones en el mar Negro) era la #2 de la agenda |
| D8 | 06/10 | Sin descripciones del RSS de TVN en el snapshot | Usarlas como `alcance_texto` | Reto §6 A: extractos solo con autorización del patrocinador |
| D9 | 06/10 | Clasificación por vecino más cercano entre ejemplares sin topónimo | Centroides con "Panamá" | Calibración real: el topónimo común borraba el margen entre temas |
| D10 | 06/10 | Agrupación por enlace promedio (distancia 0,10) | Enlace simple (union-find) | El enlace simple encadenaba 1.327 noticias en un solo cluster |
| D11 | 06/10 | Abstención por año pedido ausente en la evidencia | Solo umbrales léxicos | "PIB 2026" se respondía con datos de 2024 |
| D12 | 06/10 | Fuentes sospechosas no alimentan el borrador | Solo marcarlas | Defensa en profundidad contra inyección (T07) |
| D13 | 07/10 | Banca como modalidad de la misma app (`?modalidad=banca`), no segundo producto | Proyecto o servidor aparte | Reto §1: "extensión, sin exigir dos productos completos"; misma bandeja, puntaje y motor |
| D14 | 07/10 | Fuente D = Informe de Actividad Bancaria mensual (PDF) con `pypdf`, anclado por encabezado del mes | Hojas de estadísticas; `pdfplumber` | 12/12 meses con 200 y texto extraíble; página citable; sin binarios |
| D15 | 07/10 | Sin indicadores de solidez (morosidad, IAC, liquidez) | Extraerlos por regex | Son riesgo bancario (reto §2, §9.1) y el regex era frágil ("liquidez" devolvía el IAC) |
| D16 | 07/10 | Mapa tema → sector versionado (`banca-1.0.0`), siempre hipótesis; puntaje `senal-1.1.0` intacto | Que el LLM elija sectores; puntaje bancario | El LLM nunca decide sector; no se crea un "riesgo bancario" |
| D17 | 07/10 | Un solo motor de redacción con `Formato` inyectable | `boletin.py` con motor propio | Reutiliza compuerta, anti-inyección, validador y caída a plantilla |
