# ADR 0003 — Parte 2: extensión bancaria dentro de Señal (fuente D · SBP)

- **Fecha:** 2026-10-07
- **Estado:** Aceptado
- **Contexto:** [Blueprint de la extensión bancaria](../../plans/parte-2-extension-bancaria.md)
- **Decisores:** BryR0

## Contexto

El reto admite la modalidad bancaria "como alternativa o extensión, sin exigir dos
productos completos" (§1). La salida bancaria es un boletín de entorno (§3) y el caso
CU-05 pide señales públicas del entorno logístico, sin score de clientes ni alerta
regulatoria definitiva (§4). La fuente D son 12 informes mensuales 2024 de la
Superintendencia de Bancos de Panamá (SBP), con período, unidad y página de origen (§6).

Hechos verificados (2026-10-07):

- `IAB-0124.pdf` … `IAB-1224.pdf` (Informe de Actividad Bancaria) responden 200.
- Texto extraíble con `pypdf`; la tabla de crédito local por sector aparece en los
  12 meses, con número de cuadro, página y decimales variables.
- Portada: uso informativo, libre acceso, citar a la SBP y ser fiel al contexto.

## Decisiones

### D-B0 — Un solo proyecto, la banca es una modalidad

La extensión vive en `senal/` y en la misma app web: mismo snapshot, misma bandeja,
mismo puntaje y mismo motor de redacción. Se elige la modalidad con
`?modalidad=editorial|banca` (lista permitida, defecto `editorial`).

### D-B1 — Fuente: Informe de Actividad Bancaria mensual 2024

Alternativa descartada: hojas de "Estadísticas financieras" (requieren navegar
formularios y no dan página citable).

### D-B2 — Parser: `pypdf` fijado

Puro Python, sin binarios del sistema. Se ancla por título de la tabla y nombre de
sector, no por número de cuadro ni posición. Fixtures de texto real de tres meses.

### D-B3 — Puntaje intacto

`senal-1.1.0` y `Tema` no cambian. La banca añade un mapa sectorial versionado
(`banca-1.0.0`, siempre rotulado como hipótesis), el contexto SBP y el formato de
salida. No se calculan indicadores de solidez (morosidad, IAC, liquidez): serían
riesgo bancario, que el reto excluye (§2, §9.1).

### D-B4 — PDFs fuera de git

Se versionan `sbp_series.csv` y el SHA-256 de cada PDF en el manifest. Los PDFs se
regeneran con `scripts/extract.py`.

## Consecuencias

- Riesgo de regresión editorial al volver inyectable el formato de `generate.py`;
  se mitiga con `FORMATO_EDITORIAL` por defecto y la suite completa en cada paso.
- Si la SBP cambia el formato de la tabla, el reporte de calidad lo muestra como
  filas faltantes; la carga no se bloquea.
