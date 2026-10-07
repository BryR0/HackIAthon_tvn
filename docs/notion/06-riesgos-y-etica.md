# Riesgos y ética

| Riesgo | Control implementado | Evidencia |
|---|---|---|
| Alucinación (hechos, cifras, fuentes) | Compuerta de abstención antes del LLM; validador de citas (ID recuperado, campo citable, cifra presente, año del indicador); cifras del texto libre verificadas | `cite.py`, `generate.py`, T04/T06/T09 |
| Inyección desde fuentes | Fuentes como datos no confiables, saneo, delimitador aleatorio, detector; las sospechosas no alimentan el borrador; el modelo no tiene herramientas | `seguridad.py`, T07, A01–A06 |
| Confundir circulación con confirmación | Procedencias independientes (agencia/titular replicado = 1); estado de evidencia separado del puntaje | `evidence.py`, CU-03 |
| Dato histórico presentado como actual | Año y unidad obligatorios; advertencia "dato anual, no actual" | `context.py`, T04 |
| Reputación y acusaciones | Acusaciones solo como declaración atribuida; sin perfiles de personas | `cite.py`, A04 |
| Privacidad | Solo titulares públicos; sin datos personales adicionales; sin listas de personas | snapshot |
| Derechos de autor | Solo titulares y metadatos; descripciones del RSS de TVN excluidas; `data/raw/` no se redistribuye | D8, manifest |
| Publicación automática | No existe ninguna acción de publicar; "aprobado como borrador" ≠ publicar | `review.py`, T08 |
| Sesgo de fuentes | GDELT sobrerrepresenta medios grandes e internacionales; relevancia Panamá con gazetteer explícito; idiomas fuera de es/en excluidos y registrados | `reporte_calidad.json` |
| Sesgo del ranking | Pesos documentados y versionados; cambios exigen decisión (D7) | `score.py` |
| Credenciales | Solo en `.env` (ignorado por git); nunca en el prompt ni en logs; la clave va en cabecera, no en la URL | `llm.py`, revisión ECC |
| Abuso de la app | CSRF, CSP sin scripts, TrustedHost, solo 127.0.0.1, límites de formulario, generación serializada y cacheada | `web/app.py` |
| Disponibilidad sin red | Snapshot y modelo locales, plantilla sin LLM | T10 |
| Boletín leído como recomendación o alerta (banca) | Léxico prohibido (compra/venta, pérdidas, impagos, exposición de cartera, scores, alertas) en hipótesis y resumen; sectores siempre "hipótesis"; aviso SBP fijo | `boletin.py`, TB05, TB06 |
| Serie mensual SBP presentada como dato de hoy | Período `MM/AAAA` obligatorio al citar cifras; "hoy/actual" descartado | `cite.py`, TB04 |
| Confundir el análisis con opinión de la SBP | Aviso en catálogo, manifest, ficha y boletín | ADR 0003 |
| Riesgo crediticio o de clientes inferido | Sin datos por banco ni cliente (esquema cerrado); sin morosidad ni solvencia | TB12, D15 |

## Fuera de alcance (declarado)

Rating y audiencia, detección de noticias falsas o culpabilidad, scoring de clientes
bancarios, lectura de artículos completos o tras paywall, producción audiovisual,
publicación.

## Riesgos residuales

- El detector de instrucciones es heurístico; la defensa real es la validación
  posterior.
- La redacción del texto libre no se verifica (solo sus cifras); la interfaz lo dice.
- Un LLM pequeño produce borradores pobres; se cae a la plantilla con aviso.
- Banca: el mapa tema → sector es un supuesto del equipo, no una relación medida.
- Banca: con recuperación híbrida, una fuente con instrucciones puede quedar fuera del
  top-k (RB03); no se usa ni se marca.
