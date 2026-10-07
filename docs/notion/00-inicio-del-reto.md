# Inicio del reto — Señal TVN

| Campo | Contenido |
|---|---|
| Reto | "De la señal a la decisión" — Copiloto de inteligencia informativa (TVN Media) |
| Equipo | BryR0 |
| Modalidad | **Editorial TVN** (recomendada por el reto) + **extensión bancaria** en la misma app (`?modalidad=banca`, ADR 0003) |
| Usuario | Editor/a y periodista de TVN; productor/a digital; en la extensión, analista de estudios económicos o riesgo sectorial |
| Problema | Fuentes dispersas, duplicados y circulación que no equivale a confirmación: cuesta encontrar qué tema revisar, qué evidencia existe y qué falta verificar |
| Solución | Bandeja priorizada por evento con puntaje explicable, ficha de evidencia, consulta en español con abstención y paquete editorial (brief, guion, copy) con citas por afirmación; revisión humana obligatoria |
| Alcance | Snapshot público (TVN RSS + GDELT, Banco Mundial, USGS, SBP 2024), demo local sin internet. Sin rating, sin veredictos de verdad, sin publicación automática |
| Demo | `senal/server_start.bat` (Windows) o `senal/server_start.sh` (Linux) → http://127.0.0.1:8765 |
| Repositorio | `BryR0/HackIAthon`, rama `parte-2/tvn-senal-decision`, carpeta `senal/` |

## Criterios de éxito (reto §9.1) y estado

| Criterio | Meta | Estado (2026-10-06, benchmark de desarrollo) |
|---|---|---|
| Cobertura de citas | 100 % | 245/245 (híbrido) |
| Validez de sustento | ≥ 90 % en ≥ 30 afirmaciones (revisión humana) | Pendiente de revisor humano |
| Abstención correcta | ≥ 80 % | 7/7; 0/27 abstenciones incorrectas |
| Clasificación | macro-F1 vs etiquetas humanas | Planilla lista (`evals/etiquetado/temas.csv`); pendiente de etiquetar |
| Ranking | Precision@5 vs editor | Pool listo; pendiente de editor (si no hay, exploratoria) |
| Eficiencia | Mediana ≤ 15 s | Sin LLM 0,013 s; con Ollama `llama3.2` ≈ 15 s |
| Demo sin internet | T10 | Snapshot y modelo locales; probado |
