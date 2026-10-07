# Presentación al jurado (10 min + 5 de preguntas)

Presentar desde Notion con la app abierta en http://127.0.0.1:8765 y **wifi apagado**.

| Min | Bloque | Contenido |
|---|---|---|
| 1 | Problema | La redacción revisa fuentes dispersas; repetir no es confirmar; el tiempo se va en buscar qué revisar y qué falta verificar |
| 1 | Solución y datos | Bandeja por evento con puntaje explicable, ficha, consulta y paquete editorial con citas. Snapshot público: 3.049 titulares (68 TVN), Banco Mundial 540 filas, USGS 82 sismos. Desviaciones declaradas |
| 4 | Demo | (1) Bandeja: top 5 y por qué (CU-01). (2) Ficha: quién, qué está respaldado, qué falta, desglose del puntaje. (3) Borrador con citas `[ID · campo]`. (4) Consulta "precio del bitcoin en Japón" → abstención. (5) Registrar una revisión. (6) Selector **Banca**: CU-05 "¿Qué señales públicas del entorno logístico debo revisar?" → boletín con series SBP 12/2024 citadas, sectores como hipótesis y aviso SBP |
| 2 | IA, baseline y métricas | e5 multilingüe en proceso vs palabras clave y BM25; benchmark 40/40 en ambos (la IA no mejora la recuperación en consultas léxicas); validador de citas 100 %; abstención 7/7 |
| 1 | Valor | Hipótesis de valor (sin medición manual vs asistida todavía): menos tiempo para pasar de 3.000 titulares a 5 temas investigables con evidencia |
| 1 | Riesgos y próximos pasos | Límites (solo titulares, agrupación imperfecta, LLM pequeño); próximos: etiquetas humanas, set reservado, extractos autorizados de TVN, revisión del boletín por una persona analista |

## Preguntas dinámicas del jurado

| Pregunta | Dónde se responde |
|---|---|
| "¿De dónde proviene esta cifra y de qué año es?" | Ficha → "Qué está respaldado": `WB:PAN:…:2024`, unidad y advertencia "dato anual, no actual"; enlace a la fuente |
| "Si cinco medios replican la misma agencia, ¿cuántas fuentes independientes cuentas?" | Una. Ficha → "procedencias independientes"; prueba `test_cu03…` |
| "¿Qué pasa sin evidencia o si una fuente intenta cambiar instrucciones?" | Consulta sin sustento → abstención. Fuente con instrucciones → "contenido sospechoso", excluida del borrador (A01–A06) |
| "Muéstrame una decisión, una prueba fallida y su corrección" | Página 01 (D1–D12) y página 05 (pruebas fallidas), con commits |

## Antes de presentar

- [ ] `server_start` ejecutado una vez con internet (dependencias y modelo en caché).
- [ ] Ensayo completo con wifi apagado, ≤ 10 min.
- [ ] Acceso del jurado a Notion y a GitHub verificado.
- [ ] `.env` sin claves en pantalla.
