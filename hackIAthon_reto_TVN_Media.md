# De la señal a la decisión

## Copiloto de inteligencia informativa y análisis de entorno con IA

## 1. Resumen ejecutivo

Construir un prototipo que convierta noticias públicas e indicadores
oficiales en una bandeja de temas priorizados, fichas de evidencia y
borradores útiles para una decisión humana. Para TVN Media, la solución
apoya la planificación editorial, la investigación y la preparación de
contenidos. Para un banco, el mismo núcleo genera boletines de entorno
económico y alertas sectoriales para análisis, sin evaluar clientes ni
ejecutar decisiones financieras.

La innovación no consiste en producir más texto: consiste en reducir el
tiempo para encontrar un tema relevante, comprobar qué evidencia existe,
identificar qué falta verificar y entregar un resultado trazable. Toda
afirmación factual debe poder vincularse con su fuente, fecha y alcance.

### Condiciones esenciales del reto

-   La modalidad recomendada es la editorial; se admite la bancaria como
    alternativa o extensión, sin exigir dos productos completos.
-   Notion es obligatorio para ejecutar, documentar y presentar el
    proyecto. La organización dispondrá de una licencia Business para el
    caso; el acceso de participantes y jurado se debe configurar antes
    del evento.
-   El prototipo utiliza datos públicos reproducibles y casos
    controlados de prueba. No requiere archivos privados de TVN ni datos
    reales de clientes bancarios.
-   Los resultados son borradores y señales para revisión. No se
    publican noticias, alertas al público ni decisiones bancarias de
    manera automática.

## 2. Problema, beneficiarios y alcance

### Problema que se busca resolver

Un equipo editorial debe revisar fuentes dispersas, eliminar duplicados,
ubicar los hechos en contexto y preparar piezas con rapidez. La
circulación de una noticia no equivale a su confirmación: varios medios
pueden repetir una misma fuente. Un analista bancario enfrenta un
problema similar al monitorear economía, logística, turismo, regulación
y continuidad operativa.

  -----------------------------------------------------------------------
  Modalidad                           Usuario y resultado útil
  ----------------------------------- -----------------------------------
  TVN · principal                     Editor/a y periodista: agenda
                                      priorizada, ficha de investigación,
                                      preguntas pendientes y borradores
                                      por formato.

  TVN · digital                       Productor/a digital: propuestas de
                                      titulares, resumen web y copy
                                      social, siempre sujetos a revisión.

  Banca                               Analista de estudios económicos o
                                      riesgo sectorial: boletín de
                                      entorno, señales y preguntas para
                                      seguimiento.
  -----------------------------------------------------------------------

### Objetivo general

Demostrar que la IA puede transformar un corpus público en información
accionable, con evidencia verificable, una priorización explicada y un
flujo de revisión documentado en Notion.

### Incluye: producto mínimo viable

-   Ingesta de al menos dos familias de fuentes públicas:
    noticias/metadatos y datos estructurados oficiales.
-   Normalización, búsqueda, clasificación temática, agrupación de
    duplicados y detección de información faltante o contradictoria.
-   Bandeja priorizada, ficha de evidencia, consultas en español y un
    entregable específico de la modalidad elegida.
-   Registro en Notion de decisiones, pruebas, riesgos y aprobación
    humana; presentación final desde Notion.

### No incluye

-   Medición de rating, audiencia o conversión publicitaria real: el
    dataset público no contiene esos datos.
-   Detección definitiva de noticias falsas, culpabilidad, fraude
    bancario, solvencia o riesgo individual de crédito.
-   Datos personales de clientes, expedientes confidenciales, perfiles
    de personas o recuperación de contenido detrás de paywalls.
-   Producción audiovisual automática, clonación de voz, integración con
    emisión televisiva o sistemas transaccionales. Son extensiones
    futuras, no requisitos.

## 3. En qué consiste el prototipo

El equipo elegirá una modalidad, explicará quién usa el producto y
ejecutará el siguiente flujo de extremo a extremo. Una interfaz web,
dashboard o notebook interactivo es válido si permite demostrar todo el
recorrido.

  -----------------------------------------------------------------------
  Etapa                               Comportamiento mínimo esperado
  ----------------------------------- -----------------------------------
  1 · Cargar                          Leer el paquete público congelado.
                                      Validar IDs, URLs, fechas, campos
                                      obligatorios y filas nulas. Emitir
                                      un reporte de calidad.

  2 · Organizar                       Clasificar temas: economía,
                                      logística/Canal, turismo, servicios
                                      públicos, eventos naturales y
                                      regulación. Agrupar noticias sobre
                                      el mismo evento.

  3 · Contextualizar                  Relacionar noticias con indicadores
                                      o eventos oficiales pertinentes.
                                      Mostrar período, unidad y
                                      limitaciones. Si no existe relación
                                      sustentada, no forzarla.

  4 · Priorizar                       Calcular un puntaje de atención,
                                      mostrar componentes y generar una
                                      lista ordenada. Distinguir
                                      relevancia de suficiencia de
                                      evidencia.

  5 · Explicar                        Abrir una ficha: qué se reporta,
                                      quién lo reporta, qué está
                                      respaldado, qué falta comprobar y
                                      qué acción se recomienda al
                                      usuario.

  6 · Producir                        Redactar un borrador propio de la
                                      modalidad, con citas por
                                      afirmación. Diferenciar hechos,
                                      declaraciones, inferencias e
                                      hipótesis.

  7 · Revisar                         Registrar aceptación, corrección o
                                      descarte por una persona
                                      responsable. Crear o actualizar
                                      manualmente la ficha en Notion;
                                      automatizar este paso es opcional.
  -----------------------------------------------------------------------

### Salida TVN: paquete editorial

-   Brief de hasta 250 palabras; título propuesto; enfoque de interés
    público; 3 preguntas de investigación; fuentes y verificaciones
    pendientes.
-   Borrador de guion de 45--60 segundos y copy digital de hasta 80
    palabras. No inventar entrevistas, citas, imágenes disponibles ni
    afirmaciones no respaldadas.

### Salida bancaria: boletín de entorno

-   Resumen de hasta 250 palabras, sectores potencialmente relacionados,
    horizonte temporal, evidencia y 3 preguntas para el analista.
-   Separar observación de hipótesis de impacto. No recomendar
    compra/venta ni inferir pérdidas, impagos o exposición de una
    cartera inexistente.

**Restricción común:** si solo se dispone del titular y metadatos, la
salida debe decir "basado únicamente en titular/metadatos". No simular
la lectura del artículo completo ni atribuirle detalles adicionales.

## 4. Casos de uso y priorización explicable

### Casos de uso que debe demostrar el equipo

-   **CU-01 · TVN:** "¿Qué cinco temas merecen revisión para la agenda
    de Panamá y por qué?". Mostrar ranking, evidencia disponible y
    vacíos de verificación.
-   **CU-02 · TVN:** abrir un tema económico, incorporar una serie
    oficial y redactar un brief sin confundir un dato anual histórico
    con una medición de hoy.
-   **CU-03 · Común:** agrupar titulares repetidos y distinguir
    repetición de corroboración independiente; una agencia replicada
    cuenta como una sola procedencia.
-   **CU-04 · Común:** preguntar por una cifra inexistente o por una
    contradicción. Abstenerse o mostrar las versiones y la verificación
    pendiente.
-   **CU-05 · Banca:** "¿Qué señales públicas del entorno logístico debo
    revisar?". Entregar contexto sectorial, no un score de clientes ni
    una alerta regulatoria definitiva.

### Puntaje de atención sugerido: 0--100

Es una herramienta de ordenamiento, no una probabilidad de verdad ni de
pérdida. Cada componente se normaliza a 0--1 con criterios documentados.
Pesos iniciales propuestos:

  ------------------------------------------------------------------------
  Componente                                    Peso Qué mide
  --------------------- ---------------------------- ---------------------
  R · Relevancia                                  30 Relación con Panamá y
                                                     con los temas de la
                                                     modalidad.

  I · Impacto potencial                           25 Interés público o
                                                     alcance sectorial,
                                                     justificado con
                                                     datos; no con
                                                     sensacionalismo.

  U · Urgencia                                    20 Tiempo disponible
                                                     para revisar una
                                                     información o un
                                                     evento.

  N · Novedad                                     15 Diferencia frente a
                                                     eventos ya agrupados;
                                                     duplicación no
                                                     incrementa el
                                                     puntaje.

  E · Evidencia                                   10 Fuentes pertinentes,
  disponible                                         primarias y con
                                                     procedencia
                                                     identificable.
  ------------------------------------------------------------------------

`P = 30R + 25I + 20U + 15N + 10E`

Rangos sin solapamiento: bajo `[0,40)`, medio `[40,70)`, alto
`[70,100]`. Empates: mayor urgencia y luego ID. Mostrar la versión de
reglas y permitir justificar cambios de pesos.

### Estado de evidencia: independiente del puntaje

"Insuficiente", "parcial" o "suficiente para el borrador". Una prioridad
alta con evidencia insuficiente requiere investigación; no habilita
publicación. El prototipo no debe etiquetar automáticamente una noticia
como verdadera o falsa. La persona revisora conserva la decisión
editorial o analítica final.

## 5. Notion Business: requisito indispensable

Notion será el espacio central de trabajo y la superficie oficial de
presentación. La organización dispondrá de una licencia Business para el
caso. Antes de iniciar debe validar puestos o invitados disponibles,
permisos, acceso del jurado y políticas de uso; esta licencia no
presupone cuentas ilimitadas ni cubre servicios externos de IA.

### Estructura obligatoria por equipo

  -----------------------------------------------------------------------
  Página o base                       Contenido exigido
  ----------------------------------- -----------------------------------
  Inicio del reto                     Equipo, modalidad, problema,
                                      usuario, alcance, criterios de
                                      éxito y accesos a demo y
                                      repositorio.

  Plan y decisiones                   Backlog, responsables, estados,
                                      cronología y decisiones técnicas o
                                      de producto.

  Catálogo de datos                   Fuente, URL, fecha de extracción,
                                      cobertura, campos,
                                      licencia/condiciones,
                                      transformaciones y hash del
                                      snapshot.

  Diseño de solución                  Arquitectura, modelo de datos,
                                      reglas, modelos, prompts, versiones
                                      y límites del sistema.

  Casos y evidencias                  Fichas con IDs, fuentes, puntaje
                                      desglosado, estado de evidencia,
                                      borrador y persona revisora.

  Pruebas y métricas                  Caso, entrada, resultado esperado,
                                      resultado observado, evidencia de
                                      ejecución y corrección.

  Riesgos y ética                     Privacidad, derechos, sesgos,
                                      ataques al agente, controles y
                                      escenarios fuera de alcance.

  Presentación al jurado              Problema → solución → demo → IA y
                                      evidencias → resultados → límites →
                                      próximos pasos.
  -----------------------------------------------------------------------

### Evidencias mínimas para ser admitido a evaluación

-   URL de Notion accesible al jurado al cierre; plan con al menos 8
    tareas y 3 decisiones justificadas. Registro durante la ejecución,
    no solo un resumen final.
-   Catálogo completo de las fuentes utilizadas y al menos 5 fichas de
    casos trazables, incluyendo un caso sin evidencia suficiente.
-   Matriz con los 10 casos de prueba de la sección 9 y métricas de la
    ejecución final.
-   Pitch de 10 minutos presentado desde Notion: se permiten enlaces o
    embeds al prototipo y GitHub. Un PDF o PowerPoint no reemplaza este
    requisito.

Condición de habilitación: si falta el espacio, el acceso o la
documentación/presentación obligatoria, no se admite la entrega a
evaluación final hasta subsanar dentro del plazo establecido. La calidad
de Notion también recibe puntaje. No es obligatorio usar Notion AI ni
automatizar la carga; sí es obligatorio usar Notion como registro y
presentación.

## 6. Set de datos públicos de prueba

Paquete propuesto: **"Panamá · Señales y Evidencias v1"**. Los volúmenes
son metas de preparación, no datos ya descargados. La organización debe
congelar una versión común antes del evento y usarla para todos los
equipos. El núcleo obligatorio combina A y B; C añade eventos
verificables; D es una extensión bancaria.

### A · Noticias públicas: TVN RSS + GDELT DOC 2.0

Meta: 200 registros únicos; mínimo operativo: 100, con al menos 20 de
TVN. Recopilar titulares, URLs, medio, idioma y marcas temporales de los
30 días previos a la extracción. Si faltan registros, ampliar hasta 90
días y registrar la cobertura efectiva. GDELT se consulta por "Panama",
logística, turismo, economía y eventos naturales; la API devuelve como
máximo 250 artículos por consulta. Dividir por fechas y deduplicar por
URL.

Archivos: `noticias.csv` y `fuentes.json`. No exigir cuerpos completos
ni videos. En TVN usar inicialmente los metadatos; reutilizar extractos
o contenido completo solo bajo condiciones aplicables o autorización
explícita del patrocinador. El patrocinio no concede por sí solo
derechos de republicación. La API de GDELT tampoco transfiere derechos
de los medios enlazados.

### B · Banco Mundial: contexto económico comparable

Seis países: PAN, CRI, COL, DOM, MEX y GTM. Años: 2010--2024. Seis
indicadores:

-   `NY.GDP.MKTP.KD.ZG` --- crecimiento del PIB
-   `FP.CPI.TOTL.ZG` --- inflación
-   `SL.UEM.TOTL.ZS` --- desempleo
-   `SP.POP.TOTL` --- población
-   `IT.NET.USER.ZS` --- uso de internet
-   `NE.EXP.GNFS.ZS` --- exportaciones/PIB

Archivo: `indicadores.csv`. Cuadrícula de 1.350 combinaciones país ×
indicador × año; conservar explícitamente valores faltantes. No prometer
1.350 observaciones válidas. Uso: respaldar cifras, comparar períodos y
evitar inventar datos actuales. Licencia general CC BY 4.0, salvo
excepciones indicadas en metadatos.

### C · USGS: eventos sísmicos oficiales

Archivo `eventos.geojson`. Extraer sismos del 01/01/2024 al 31/12/2024
en la caja regional latitud 5--12, longitud −86 a −76; magnitud mínima
3. Volumen: todos los eventos devueltos; no fijar un número ficticio. La
caja no equivale al territorio de Panamá. Mantener ubicación y usar la
fuente solo para hechos sísmicos, nunca como evidencia de inundación o
de pérdidas económicas.

### D · SBP: extensión bancaria opcional

Seleccionar 12 informes mensuales disponibles del año 2024 o un período
de 12 meses documentado de la Superintendencia de Bancos de Panamá.
Extraer series agregadas con período, unidad y página de origen. Son
datos informativos, revisables; validar condiciones de reutilización. No
incluir información de clientes ni confundir análisis del equipo con una
opinión oficial de la SBP.

## 7. Contrato de datos y reproducibilidad

  -----------------------------------------------------------------------
  Archivo                             Campos mínimos
  ----------------------------------- -----------------------------------
  `noticias.csv`                      `id_noticia`, `titulo`, `url`,
                                      `medio`, `idioma`,
                                      `fecha_publicacion`,
                                      `fecha_deteccion`,
                                      `fecha_extraccion`, `tema`,
                                      `origen`, `alcance_texto`.

  `indicadores.csv`                   `pais_iso3`, `indicador_id`,
                                      `anio`, `valor` (nullable),
                                      `unidad`, `fuente_url`,
                                      `fecha_extraccion`, `licencia`.

  `eventos.geojson`                   `id`, `magnitude`, `time`,
                                      `updated`, `longitude`, `latitude`,
                                      `depth`, `place`, `status` y URL
                                      del evento.

  `fichas.jsonl`                      `id_caso`, `modalidad`,
                                      `ids_fuente`, `afirmaciones`,
                                      `citas`, `puntaje`, `componentes`,
                                      `estado_evidencia`, `borrador`,
                                      `estado_revision`.

  `manifest.json`                     `versión`, `fecha_corte_UTC`,
                                      `consultas`, cantidad por archivo,
                                      licencia/condiciones, SHA-256 y
                                      transformaciones.
  -----------------------------------------------------------------------

### Reglas de integridad

-   Usar UTF-8, IDs estables y fechas ISO 8601 en UTC; mostrar hora de
    Panamá en la interfaz. Mantener la fecha de publicación distinta de
    `seendate` de GDELT, que indica detección.
-   Conservar nulos y unidades originales. No rellenar ausencia de
    información con cero. Documentar revisiones, cambios de fuente y
    registros excluidos.
-   Cada afirmación generada debe referenciar el ID de evidencia y el
    campo, pasaje o página que la respalda. Una URL sin relación con la
    afirmación no constituye una cita válida.

### Normas de extracción propuestas

-   No asumir que el RSS conserva todo el histórico.
-   Ejecutar una consulta por indicador y completar la cuadrícula de
    combinaciones faltantes.
-   Excluir registros fuera del intervalo `[2024-01-01, 2025-10-01)`.

### Paquete común y conjunto reservado

Guardar `raw/`, `processed/`, manifest y diccionario. Preparar
`benchmark.jsonl` con 60 consultas: 30 de respuesta sustentada, 10 de
contradicción o ambigüedad, 10 sin respuesta y 10 adversariales. Usar 40
para desarrollo y reservar 20 al jurado, conservando los tipos. Las
etiquetas se crean por revisión humana: no vienen de GDELT. Identificar
los casos alterados como sintéticos. No mezclar respuestas reservadas
con el corpus del agente.

## 8. Arquitectura, IA y controles

### Arquitectura mínima sugerida

Fuentes públicas / snapshot → validación y normalización →
almacenamiento → búsqueda y agrupación → motor de priorización →
generación con evidencias → interfaz → revisión humana → registro en
Notion.

Para el MVP basta una carga por lote; no se exige monitoreo continuo ni
acceso a internet durante el pitch.

### Uso sustantivo de inteligencia artificial

-   Implementar al menos una capacidad de ML/NLP: clasificación
    semántica, similitud para agrupar eventos, extracción de entidades o
    recuperación semántica. Un conjunto de IF/ELSE no basta como uso de
    IA.
-   Generar respuestas y borradores sobre evidencia recuperada. Si se
    usa un LLM, separar instrucciones del contenido de fuentes y exigir
    estructura de salida con citas y vacíos de información.
-   Comparar al menos una tarea con un baseline simple: búsqueda por
    palabras clave, reglas temáticas o ranking por fecha. Explicar qué
    mejora aporta la IA y cuándo no ayuda.
-   Documentar modelo/proveedor, versión, prompts, parámetros, costo
    medido y limitaciones. El stack es libre; no se obliga a contratar
    APIs ni bases de datos comerciales.

### Seguridad y ética obligatorias

-   Control humano: los estados son "nuevo", "en revisión", "requiere
    evidencia", "aprobado como borrador" y "descartado". Aprobar un
    borrador no significa publicar.
-   Anti-alucinación: no inventar hechos, declaraciones, entrevistados,
    cifras, causalidades ni fuentes. Si falta evidencia, abstenerse y
    explicar qué información se necesita.
-   Anti-inyección: el texto de una fuente es dato, no instrucción. Un
    artículo que pide revelar secretos o cambiar reglas nunca debe
    modificar el comportamiento del agente.
-   Privacidad y reputación: evitar almacenar datos personales
    innecesarios; no crear perfiles sensibles ni listas de supuestos
    delincuentes o clientes riesgosos. Las acusaciones se atribuyen como
    declaraciones, no como hechos probados.
-   Derechos y acceso: registrar condiciones por fuente; no redistribuir
    artículos, imágenes o videos sin permiso. Notion debe compartirse
    solo con participantes y jurado autorizados; no es obligatorio
    publicar el espacio en la web.
-   Credenciales fuera del código y de Notion público. No registrar
    tokens ni secretos en capturas, prompts o logs. Mantener
    dependencias y costos bajo control.

Una alerta es una invitación a investigar. Ni tono negativo, ni volumen
de noticias, ni repetición equivalen a fraude, pérdida financiera o
verdad comprobada.

## 9. Pruebas de aceptación y métricas

  -----------------------------------------------------------------------
  ID                      Prueba                  Resultado esperado
  ----------------------- ----------------------- -----------------------
  T01                     Archivo con fechas      Validar, separar
                          inválidas y nulos       errores y conservar
                                                  nulos; no bloquear toda
                                                  la carga.

  T02                     Tres registros del      Agrupar sin perder
                          mismo evento            fuentes; no triplicar
                                                  importancia ni
                                                  corroboración.

  T03                     Noticia antigua         Mostrar fecha original;
                          recirculada             no presentarla como un
                                                  evento nuevo.

  T04                     Cifra anual del Banco   Mantener país, año y
                          Mundial                 unidad; citar dato y no
                                                  describirlo como cifra
                                                  de hoy.

  T05                     Dos afirmaciones        Mostrar ambas, su
                          incompatibles           alcance y la revisión
                                                  pendiente; no escoger
                                                  arbitrariamente.

  T06                     Consulta sin respuesta  Abstención explícita;
                          en el corpus            ninguna cifra o cita
                                                  inventada.

  T07                     Fuente que exige        Tratarla como contenido
                          ignorar instrucciones   no confiable; no
                                                  revelar secretos ni
                                                  ejecutar acciones.

  T08                     Caso de prioridad alta  Exponer componentes y
                                                  regla; la prioridad no
                                                  habilita publicación.

  T09                     Brief editorial o       Formato útil, citas
                          boletín bancario        pertinentes y
                                                  distinción de hechos e
                                                  inferencias.

  T10                     Sin internet durante la Funcionar con snapshot
                          demo                    y fallback documentado;
                                                  dejar evidencia en
                                                  Notion.
  -----------------------------------------------------------------------

### 9.1. Evaluación reproducible y métricas

Ejecutar benchmark de desarrollo y evaluación reservada, con salidas
guardadas. Las metas siguientes son orientativas del reto, no resultados
ya obtenidos. Reportar numerador, denominador y fallos; no esconder
errores tras un promedio.

-   **Cobertura de citas:** 100% de afirmaciones factuales emitidas
    deben enlazar una evidencia identificable. Validez de sustento: meta
    ≥90% según revisión humana de al menos 30 afirmaciones, si se
    producen tantas.
-   **Abstención:** meta ≥80% de consultas sin respuesta correctamente
    rechazadas. Registrar también abstenciones incorrectas en preguntas
    respondibles.
-   **Clasificación/agrupación:** reportar macro-F1 o precisión/recall
    sobre etiquetas humanas, incluyendo tamaño y método de etiquetado.
    No usar exactitud de un modelo de fraude: este reto no tiene
    etiquetas de fraude.
-   **Utilidad del ranking:** Precision@5 frente a selección
    independiente de un editor o analista. Si no hay especialista,
    declarar la evaluación como exploratoria.
-   **Eficiencia:** tiempo mediano y p95, tokens y costo por consulta si
    aplica. Meta sugerida: mediana ≤15 s en el entorno declarado, sin
    sacrificar sustento.

Medir ahorro de tiempo solo con una tarea equivalente manual
vs. asistida, indicando número de pruebas. No inferir aumento de
audiencia, rentabilidad o reducción de riesgo bancario con este dataset.

## 10. Entregables y rúbrica única

### Entregables obligatorios

-   Prototipo ejecutable con el flujo completo de la modalidad elegida y
    una demo reproducible sin depender de una fuente en vivo.
-   Repositorio GitHub con acceso al jurado: README, instalación,
    comando de ejecución, dependencias fijadas, `.env.example` sin
    secretos y pruebas.
-   Paquete de datos públicos permitido: snapshot, diccionario,
    manifest, licencias/condiciones y benchmark de desarrollo. Si una
    fuente restringe redistribución, entregar metadatos y receta, no su
    contenido protegido.
-   Espacio Notion con los artefactos de la sección 5 y presentación
    final. PDF de respaldo opcional; nunca sustituto del espacio
    obligatorio.

### Rúbrica propuesta: 100 puntos

  ------------------------------------------------------------------------
  Dimensión                                     Peso Qué permite obtener
                                                     máxima puntuación
  --------------------- ---------------------------- ---------------------
  Utilidad para TVN o                             20 Usuario claro, flujo
  banca                                              realista, salidas
                                                     accionables e impacto
                                                     demostrado sin
                                                     exagerar.

  Prototipo y flujo                               20 Carga, consulta,
  completo                                           priorización, ficha,
                                                     borrador y revisión
                                                     funcionan con datos
                                                     comunes.

  Uso efectivo de IA                              15 Capacidad NLP/ML
                                                     sustantiva, baseline
                                                     y mejora o limitación
                                                     medida.

  Evidencias y                                    15 Citas pertinentes,
  explicabilidad                                     puntaje reproducible,
                                                     contradicciones y
                                                     abstención correctas.

  Notion: ejecución y                             15 Trabajo trazable
  pitch                                              durante el evento,
                                                     catálogo y pruebas
                                                     completos; pitch
                                                     navegable.

  Calidad técnica y                               10 Código reproducible,
  evaluación                                         arquitectura
                                                     proporcional, pruebas
                                                     y métricas
                                                     verificables.

  Seguridad, privacidad                            5 Controles operativos,
  y ética                                            derechos documentados
                                                     y resistencia a abuso
                                                     del agente.
  ------------------------------------------------------------------------

Escala: 0 ausente; 1 parcial; 2 básico; 3 funcional; 4 sólido; 5
excepcional y verificado.

`Puntaje = Σ(peso × nota/5)`

Esta rúbrica reemplaza las matrices de pesos distintos del documento
original.

### Condiciones previas, separadas del puntaje

Aplican las condiciones de admisión de la sección 5: acceso a Notion,
documentación y pitch obligatorios. También se exige demo ejecutable,
fuentes declaradas y ausencia de secretos. Citas falsas o acciones
prohibidas deben corregirse antes del cierre.

## 11. Ejecución del evento y presentación

### Ruta de trabajo sugerida

Para un evento de 24--48 horas, ajustar las franjas al calendario
definitivo. Limitarse a una modalidad y un recorrido convincente antes
de añadir funcionalidades.

  -----------------------------------------------------------------------
  Tramo                               Actividad y evidencia en Notion
  ----------------------------------- -----------------------------------
  Inicio · 15%                        Elegir usuario y modalidad; definir
                                      alcance; comprobar acceso Business,
                                      datos y permisos del jurado.

  Datos y diseño · 20%                Validar snapshot; crear catálogo;
                                      acordar etiquetas, baseline,
                                      arquitectura y reglas.

  Construcción · 40%                  Implementar búsqueda/agrupación,
                                      ranking, generación con citas e
                                      interfaz; guardar decisiones.

  Pruebas · 15%                       Ejecutar T01--T10 y benchmark;
                                      corregir citas, abstención y manejo
                                      de derechos.

  Cierre · 10%                        Completar fichas, métricas y pitch;
                                      ensayar demo offline y verificar
                                      acceso al repositorio.
  -----------------------------------------------------------------------

### Pitch obligatorio desde Notion: 10 minutos

-   **1 min:** problema, usuario y por qué importa a TVN Media o al
    banco elegido.
-   **1 min:** solución, alcance y datos públicos utilizados.
-   **4 min:** demo en vivo; una consulta útil, una ficha con citas, un
    borrador y un caso de abstención.
-   **2 min:** arquitectura, uso sustantivo de IA, baseline y métricas
    observadas.
-   **1 min:** valor operativo medido o hipótesis de valor claramente
    identificada.
-   **1 min:** riesgos, limitaciones y próximos pasos.

Añadir 5 minutos de preguntas del jurado.

### Pruebas dinámicas del jurado

-   "Muéstrame de dónde proviene esta cifra y de qué año es".
-   "Si cinco medios replican la misma agencia, ¿cuántas fuentes
    independientes cuentas?".
-   "¿Qué ocurre si el sistema no tiene evidencia o una fuente intenta
    cambiar sus instrucciones?".
-   "Muéstrame en Notion una decisión, una prueba fallida y su
    corrección".

### Preparación requerida a la organización

Confirmar accesos y cupos de la licencia Business; publicar reglas y
rúbrica; preparar el snapshot común y el set reservado; verificar
derechos de extractos TVN; designar una persona editorial y, si aplica,
bancaria para revisar casos. Tener conectividad y fallback local.
Congelar datos al menos 72 horas antes; la fecha del evento está por
confirmar.

## 12. Fuentes y notas para la implementación

Fuentes públicas identificadas para diseñar el paquete de pruebas. Fecha
de consulta: **05/10/2026**. Se verificaron páginas y documentación, no
se descargó ni auditó el dataset completo.

1.  TVN Panamá · sitio oficial.
2.  TVN · feed RSS público. Base para titulares y enlaces del
    patrocinador. El RSS observado contiene noticias, fechas y
    descripciones; eso no implica licencia abierta sobre artículos,
    videos o imágenes.
3.  GDELT · documentación DOC 2.0 API. Documenta ArtList, filtros por
    dominio/idioma, ventanas temporales y límite de 250 resultados.
    Verificar funcionamiento al congelar el paquete. La API DOC pública
    no debe confundirse con servicios comerciales llamados GDELT Cloud.
4.  Banco Mundial · documentación Indicators API v2.
5.  Banco Mundial · indicadores de Panamá.
6.  Banco Mundial · términos para datasets. Aplicar atribución y revisar
    excepciones de terceros por indicador. Los datos pueden revisarse y
    su período de referencia no coincide necesariamente con el año de
    extracción.
7.  USGS · catálogo sísmico y parámetros del servicio. Usar IDs y URL de
    evento para trazabilidad. Confirmar condiciones aplicables a datos o
    elementos de terceros.
8.  SBP · estadísticas financieras.
9.  SBP · estudios e informes publicados. Extensión local para la
    modalidad bancaria. Seleccionar los informes y columnas antes del
    evento, conservando las advertencias de uso informativo y las
    condiciones correspondientes.

### Criterio de éxito

El proyecto será convincente si una persona de editorial puede pasar de
un conjunto disperso de fuentes a un tema investigable, con evidencia y
un borrador responsable; o si un analista bancario puede construir un
boletín de entorno sustentado.

La calidad de la decisión asistida, la trazabilidad en Notion y la
capacidad de reconocer lo que no se sabe importan más que el volumen de
texto generado.

### Plan por días

-   **Día 1 --- Datos y diseño:** preparar las fuentes, definir
    arquitectura, crear el espacio Notion e implementar la carga. Núcleo
    de IA: búsqueda, agrupación de noticias, priorización y respuestas
    con evidencias.
-   **Día 2 --- Producto funcional:** interfaz, fichas, generación de
    briefs/guiones y revisión humana.
-   **Día 3 --- Pruebas:** validar citas, contradicciones, consultas sin
    respuesta y resistencia a instrucciones maliciosas. Cierre: corregir
    fallos, completar métricas y Notion, preparar y ensayar la
    presentación.
