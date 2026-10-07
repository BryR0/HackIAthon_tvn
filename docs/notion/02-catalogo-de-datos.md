# Catálogo de datos

Paquete `panama-senales-evidencias-v1` · corte `2026-10-06T18:46:40+00:00` · SHA-256
por archivo en `senal/data/processed/manifest.json` (también visible en la app, en la
página "Datos y calidad").

| Ref | Fuente | URL | Extracción | Cobertura | Campos | Licencia / condiciones | Transformaciones |
|---|---|---|---|---|---|---|---|
| [2] | TVN · RSS | https://www.tvn-2.com/rss/ | 2026-10-06 | 152 ítems; 68 válidos en la ventana | titulo, url, medio, fecha_publicacion | Titulares y metadatos; no implica licencia sobre artículos, videos o imágenes. Descripciones **excluidas** hasta autorización | Fecha a UTC; dedupe por URL; prioridad sobre GDELT |
| [3] | GDELT DOC 2.0 | https://api.gdeltproject.org/api/v2/doc/doc | 2026-10-06 | 22/30 consultas OK (8 con HTTP 429, registradas); 5 temas × 6 tramos de 15 días | titulo, url, dominio, idioma, seendate | Metadatos; no transfiere derechos de los medios | `seendate` solo como `fecha_deteccion`; idiomas ≠ es/en excluidos |
| [4][5][6] | Banco Mundial · Indicators API v2 | https://api.worldbank.org/v2/country/PAN;CRI;COL;DOM;MEX;GTM/indicator/… | 2026-10-06 | 6 países × 6 indicadores × 2010–2024 = **540** filas | pais_iso3, indicador_id, anio, valor (nullable), unidad, fuente_url, licencia | CC BY 4.0 salvo excepciones; atribución; período de referencia ≠ año de extracción | Cuadrícula completa con nulos; unidad desde el nombre del indicador |
| [8][9] | SBP · Informe de Actividad Bancaria (extensión bancaria) | https://www.superbancos.gob.pa/documentos/financiera_y_estadistica/estudios/IAB/IAB-MM24.pdf | 2026-10-07 | 12 informes 2024 × 13 sectores = **156** filas, 0 nulos | id_serie, periodo, nombre, sector, valor, unidad, valor_base, periodo_base, variacion_pct, cuadro, pagina_pdf, fuente_url, sha256_pdf | Uso informativo; citar a la SBP; ser fiel al contenido y contexto; el análisis del equipo no es opinión de la SBP. Solo agregados, sin clientes ni bancos | Tabla de crédito local por sector anclada por encabezado del mes; sin separador de miles; página 1-based del PDF; sumas validadas ±0,5 por sumando |
| [7] | USGS · FDSN | https://earthquake.usgs.gov/fdsnws/event/1/query | 2026-10-06 | 82 sismos 2024, M ≥ 3, lat 5–12, lon −86 a −76 | id, magnitude, time, updated, lon, lat, depth, place, status, url | ID y URL por evento; solo hechos sísmicos; la caja no es Panamá | Epoch ms → ISO UTC |

## Resultado de calidad

| Concepto | Valor |
|---|---|
| Noticias válidas | 3.049 (68 TVN) |
| Excluidas | 740 URL duplicada · 79 fuera de ventana · 709 idioma no soportado · 3 campo obligatorio |
| Sin fecha de publicación (solo detección GDELT) | Mayoría de GDELT; se rotula "(detección)" en la UI |
| Indicadores nulos | Conservados como `null`, nunca 0 |
| Series SBP | 156 filas, 12/12 meses, 0 nulos, 0 inconsistencias de suma |

## Desviaciones

- **D6:** ventana de 90 días en lugar de `[2024-01-01, 2025-10-01)`.
- **Errata del reto:** "1.350 combinaciones" → la cuadrícula real es 540.
- **SBP:** solo la tabla de crédito local por sector; los indicadores de solidez quedan fuera (D15). Los PDFs no se versionan; el manifest guarda su SHA-256.
- **Receta, no redistribución:** `data/raw/` no se versiona; se regenera con
  `scripts/extract.py` y `scripts/build_snapshot.py`.
