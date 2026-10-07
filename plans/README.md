# Índice de planes

| Plan | Estado | Próxima acción |
|---|---|---|
| [Reto 3 — Estimador de copago y cobertura](./reto-3-estimador-copago-cobertura.md) | Pasos 1-8 verdes | Desplegar en Vercel y enviar los dos enlaces a hackiathon@viamatica.com |
| [Parte 2 — De la señal a la decisión (TVN Media)](./parte-2-tvn-senal-a-decision.md) | Pasos 1, 3–7 verdes; 2, 8, 9 parciales | Etiquetado humano, set reservado, migrar a Notion y ensayo offline |
| [Parte 2 — Extensión bancaria (CU-05, SBP)](./parte-2-extension-bancaria.md) | Pasos 0–5 verdes | Revisión ECC (paso 6), commit y revisión por una persona analista |

## Decisiones

- [ADR 0001 — Stack del MVP y reglas base](../docs/adr/0001-mvp-stack-and-rules.md)
- [ADR 0002 — Parte 2: stack Python, embeddings y reglas](../docs/adr/0002-parte-2-senal-stack-y-reglas.md)

## Progreso

| Paso | Estado | Evidencia |
|---|---|---|
| Gate 0 | Cerrado | `docs/adr/0001-mvp-stack-and-rules.md` |
| Paso 1 — Contratos, datos y casos dorados | Verde | 18 casos de estimacion + 6 de triage |
| Paso 2 — Scaffold, calidad y tokens | Verde | `npm run build` verde; 0 vulnerabilidades |
| Paso 3 — Motor determinista | Verde | 33 pruebas; motor TS coincide con oraculo Python en 18/18 |
| Paso 4 — Agente y guardrails | Verde | 12 evals; corpus 30/30, emergencia e inyeccion 5/5 |
| Paso 5 — Experiencia accesible | Verde | 10 estados; axe sin violaciones |
| Paso 6 — Integracion y explicabilidad | Verde | 35 pruebas de contrato de API |
| Paso 7 — Pruebas y endurecimiento | Verde | 80 unidad/integracion/evals + 20 E2E |
| Paso 8 — Entrega | Parcial | README listo; falta desplegar y enviar el correo |
