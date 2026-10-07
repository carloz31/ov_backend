# Validación de la demo

La fuente de verdad es `spec-demo-motor-desbloqueos.md`. Los 17 tests de
`tests/test_escenarios.py` reproducen E1–E17 de la sección 9, reiniciando la
demo y ejecutando sus prerrequisitos por las acciones de dominio.

Las ampliaciones se rigen además por `spec-demo-instrumentos.md` y
`spec-demo-registro-gemini.md`. Las secciones por fase conservan los resultados
históricos. El [cierre de Registro v2](#registro-v2-fase-8-cierre-consolidado)
reúne la cobertura vigente, presupuestos SQL y validación visual y real.
El cierre de v1 se conserva como historial.

## Invariantes de la sección 8

Las pruebas de integración adicionales están en `tests/test_invariantes.py`.
Todas usan SQLite temporal, independiente de `demo.db`.

| Nº | Invariante | Prueba adicional |
|---|---|---|
| 1 | Desbloqueo único por cuenta y regla | `test_desbloqueos_unicos_permanentes_y_nivel_monotono_en_recorrido`: contrasta filas persistidas y nuevos desbloqueos anunciados después de cada acción, incluyendo coautoría. |
| 2 | Desbloqueos permanentes | La misma prueba conserva id, fecha e indicador visto de los desbloqueos anteriores durante el recorrido, las repeticiones y eventos con fechas anteriores. |
| 3 | Actividad bloqueada devuelve 409 sin eventos | `test_actividad_bloqueada_no_altera_estado_ni_historial`: seis casos de bloque contenedor, cadena y condición compuesta; compara estado, eventos, desbloqueos, progresos e intentos antes y después. |
| 4 | Estado filtrado por audiencia | `test_audiencias_se_conservan_tras_eventos_compartidos`: comprueba bloques, actividades, fichas, testimonios, preguntas, insignias y niveles de las tres cuentas después de conversaciones y coautoría. |
| 5 | Eventos de primera vez por referencia y cuenta | `test_eventos_de_primera_vez_y_repeticiones_por_cuenta_y_referencia`: recorre todos los bloques, ambos casos, ambas cartas y ambas conversaciones; compara el historial exacto después de repetir acciones. |
| 6 | Cada finalización registra COMPLETA_ACTIVIDAD | La misma prueba verifica los conteos por actividad y cuenta, incluyendo intentos de caso aprobados y fallidos. |
| 7 | Rehacer conserva COMPLETADA | La misma prueba compara las filas de progreso antes y después de rehacer, y comprueba COMPLETADA en el estado público. |
| 8 | Check-in diario y respuesta GUIADA únicos | `test_check_in_unico_por_dia_con_aislamiento_entre_estudiantes` y `test_diario_guiado_unico_por_cuenta_y_pregunta_y_libre_repetible`: verifican rechazo sin efectos, independencia entre estudiantes y entradas libres repetibles. |
| 9 | Nivel actual nunca baja | `test_desbloqueos_unicos_permanentes_y_nivel_monotono_en_recorrido`: observa los niveles 1–5 tras cada paso y conserva el 5 después de un caso fallido y acciones con fechas anteriores. |

La idempotencia de los eventos de primera vez corresponde a las acciones de
dominio. `/eventos` permite eventos crudos sin esas validaciones, como define
la sección 5. `/demo/reiniciar` elimina intencionadamente el estado y se
comprueba por separado en `tests/test_fase1.py`.

Las pruebas existentes también cubren los tres tipos de conteo, condiciones
conjuntas, reglas alternativas, evaluador especial, códigos públicos,
restricciones SQL y reversión completa de acciones que fallan, incluidas las
que escriben en dos cuentas.

## Ejecución

Desde la raíz del proyecto:

```powershell
uv run pytest -q
```

La fase 5 agrega pruebas y este mapa de cobertura. No modifica la semilla,
la semántica del motor ni las expectativas de E1–E17.

## Página visual opcional

`tests/test_demo.py` comprueba que `/demo`, sus recursos y su catálogo no
modifican estado; verifica códigos públicos, tipos de casos y ausencia de
cartas o logros ocultos en el catálogo. Al cerrar esa etapa, la suite contenía
188 pruebas; las ampliaciones posteriores se registran más abajo.

La revisión manual en navegador usó una base SQLite temporal y cubrió:

- Ruta desde ACT-01 hasta ACT-13, apertura de la ciudad, Helena y nivel 5.
- Requisitos de una actividad bloqueada y rechazo 409 sin aumentar eventos.
- Intentos de caso con 50, 85 y 95; superación inicial y repetición sin duplicados.
- Entrevista con Ana y Luis, cambio de cuenta y marcado de novedades aislado.
- Check-in duplicado y tres días distintos, con revelación de Constancia.
- Diario guiado, respuesta duplicada rechazada y entrada libre.
- Cartas, ruta de Rosa y conversación que registra eventos para ambos roles.
- Evaluador de carreras: conteo cumplido con dos familias y desbloqueo al visitar la tercera.
- Registro reflexivo, ingreso, cancelación del reinicio y reinicio de las cuentas de prueba.
- Diseño de escritorio y móvil; en móvil se completó una actividad y no hubo desbordamiento horizontal del documento.

## Instrumentos: fase 1

Se conservan los 188 tests anteriores, con las adaptaciones de conteos y
catálogos autorizadas y registradas en `decisiones.md`. E1 conserva el estado
de las 18 actividades originales y verifica LAB por separado; E2–E17
conservan sus resultados esperados.

`tests/test_semilla_instrumentos.py` agrega cobertura de:

- Totales exactos de tablas, catálogo, instrumentos, dimensiones, escalas,
  opciones, aplicaciones e ítems. LAB disponible para estudiantes y ausente
  del estado de Rosa; la semilla no crea eventos ni respuestas.
- Rejillas exactas, orden RIASEC, textos de autopercepción, reutilización de
  sus ítems, ítems inversos, rangos de actividades y aplicaciones.
- Distribución que rechaza ítems faltantes, repetidos o de otro instrumento.
- Archivo válido, ausente, ilegible, vacío, con columnas diferentes, valores
  inválidos, códigos duplicados o códigos requeridos faltantes.
- Catálogo real de 923 ocupaciones y 5538 puntajes, y las diez relaciones de
  las ocho carreras. Sustitución de Medicina por el primer `29-12` del archivo
  cuando falta 29-1216.00.
- Restricciones SQL: versión única, respuesta única por progreso e ítem,
  opción e ítem únicos, claves compuestas, resultado vigente único y ajustes
  y posiciones válidos de coincidencias.
- Rechazo al arrancar de bases sin versión, con versión 1 o 3, sin fila de
  versión o con tablas faltantes, sin modificar el archivo anterior.
- Versión 2 y catálogo completo tras reinicios sucesivos; carga de semilla
  revertida íntegramente ante errores de ocupaciones; reinicio fallido que
  devuelve el error y conserva estado, eventos y desbloqueos anteriores.

Todas las pruebas usan SQLite temporal, independiente de `demo.db`. Si falta
el Excel, solo se omiten las pruebas del catálogo real; una fixture de tests
carga las definiciones sin inventar ocupaciones. Esta excepción no existe en
producción.

Los escenarios I1–I14 por endpoints y las pruebas puras de cálculo se
incorporarán en las fases siguientes; esta fase prepara sus datos y modelos.

Resultado al cerrar la fase 1: `uv run pytest -q` devuelve **236 passed**
(los 188 anteriores y 48 nuevos). La ejecución adicional con una ruta de
Excel ausente simulada devuelve **235 passed, 1 skipped**; solo se omite la
verificación del catálogo real. E1–E17 pasan en ambas ejecuciones.

## Instrumentos: fase 2

`tests/test_calculo_instrumentos.py` agrega 64 pruebas puras. No solicita las
fixtures de aplicación, cliente o sesión ni lee el Excel. Cubre:

- Los cuatro pares de Pearson y ajuste de la sección 9.1, con tolerancia
  absoluta de 1e-6, y la correlación negativa del notebook que debe descartarse.
- Límites inclusivos de ajuste, correlación cero y valores negativos.
- Puntuación directa e inversión Sí/No, Likert y escalas con mínimo distinto
  de cero; suma de máximos individuales y porcentajes a dos decimales.
- Las cadenas completas A y B con sus seis puntajes, máximos, porcentajes
  y códigos de interés, y los cálculos de inteligencias y habilidades sociales
  con los resultados numéricos de I8 e I9, todavía sin persistencia ni endpoints.
- Código de interés, desempates en orden RIASEC y empate entre tercera y cuarta
  dimensiones; un empate entre primeras posiciones no implica empate en el corte.
- Orden y límite del top 10, posiciones consecutivas, desempate por código,
  conservación de títulos y correlaciones sin redondear y entradas sin modificar.
- Perfil plano que no evalúa ocupaciones y conserva RIA con empate; entradas
  inválidas y ocupación constante que falla identificando su código.

Comando de las pruebas puras:

```powershell
uv run pytest -q tests/test_calculo_instrumentos.py
```

Estas funciones se integrarán en la fase 3. No cambian los endpoints,
la semilla, el motor ni las expectativas de los tests anteriores.

Resultado al cerrar la fase 2: **64 passed** en las pruebas puras y
**300 passed** con `uv run pytest -q` (las 236 anteriores y 64 nuevas).
E1–E17 siguen pasando. No se agregan dependencias.

## Instrumentos: fase 3

`tests/test_instrumentos.py` agrega 32 pruebas de integración. Las acciones
se ejercitan por HTTP, con SQLite temporal y sin modificar `demo.db`.
Los resultados se verifican en las tablas; sus consultas públicas se
incorporarán en la fase 4.

| Escenario | Cobertura de esta fase | Pendiente para fase 4 |
|---|---|---|
| I1 | LAB, estados exactos y audiencia; sin respuestas ni resultados iniciales | Catálogo y avance por aplicación |
| I2 | Guardado parcial, EN_CURSO y rechazo de finalización con códigos faltantes | Consulta de respuestas y avance |
| I3 | Pertenencia, escala, disponibilidad y reemplazo sin duplicados | Ninguno para las validaciones de escritura |
| I4 | Cadena A, desbloqueos sucesivos, resultado al cuarto bloque y puntajes exactos | Resultado y código ERS por GET |
| I5 | Cadena B, top 10 exacto del Excel, títulos, ajustes y correlaciones guardadas sin redondear | Resultado y carreras recomendadas por GET |
| I6 | Perfil plano, dimensiones y ausencia de coincidencias | Resultado, RIA y empate por GET |
| I7 | Respuestas fijas, reintento con evento nuevo y resultado inalterado | Historial y resultado vigente por GET |
| I8 | Dos actividades de inteligencias, resultado solo al finalizar ambas, siete dimensiones exactas | Resultado por GET |
| I9 | Habilidades sociales e ítems inversos, seis dimensiones exactas | Resultado por GET |
| I10 | Entrada/salida independientes, respuestas fijas y comparación numérica esperada sin resultados | Comparación por GET |
| I11–I14 | No implementados en esta fase | Reinicio e invariantes en fase 5 |

También se comprueba:

- Lotes vacíos o repetidos y opciones con tipos inválidos rechazados con 422.
- Validación completa del lote antes de crear progreso o reemplazar respuestas.
- Cuentas o actividades inexistentes, apoderados y actividades sin ítems.
- Respuestas aisladas por cuenta y progreso; una cuenta no completa con las
  respuestas de otra. Autopercepción conserva veinte respuestas para sus dos
  progresos, con diez ítems compartidos y sin resultado calculado.
- Edición de una actividad completada mientras la aplicación sigue incompleta,
  sin cambiar su estado COMPLETADA; bloqueo de edición con resultado vigente.
- BLOQUEADA conserva prioridad sobre EN_CURSO si el bloque no está disponible.
- Una actividad genera un resultado por cada aplicación completa que la incluye.
- Fallo forzado después de guardar dimensiones y conceder un desbloqueo:
  toda la finalización se revierte, incluidos resultado, progreso, eventos y
  desbloqueos, conservando las respuestas guardadas en peticiones anteriores.
- Actividades originales sin ítems mantienen eventos y desbloqueos y devuelven
  `resultados_generados: []`. Las respuestas del resto de las acciones no cambian.

El único test anterior de comportamiento adaptado en esta fase es
`test_estado_expone_en_curso_con_progreso_parcial`, según la excepción autorizada
de 5.9. Las pruebas de acciones, consultas y E1–E17 pasan: **91 passed**.

Comando de las pruebas de integración:

```powershell
uv run pytest -q tests/test_instrumentos.py
```

Resultado de estas pruebas: **32 passed**. Con una ruta de Excel ausente
simulada: **29 passed, 3 skipped**. Solo se omiten I4, I5 e I7, que usan
resultados RIASEC no planos; las demás cargan definiciones mediante la fixture
exclusiva de tests, sin ocupaciones ficticias. Producción sigue exigiendo el Excel.

Resultado al cerrar la fase 3: **332 passed** con `uv run pytest -q`
(las 300 anteriores y 32 nuevas). E1–E17 conservan sus resultados originales.
Permanece el aviso de deprecación de Starlette/httpx ya existente; no hay fallos.
No se agregan dependencias ni se cambia la versión del esquema.

## Instrumentos: fase 4

Las siete consultas de la sección 6.2 están implementadas y se verifican
mediante HTTP. `tests/test_instrumentos.py` conserva las comprobaciones de
persistencia de fase 3, amplía I1–I10 con consultas públicas y agrega 23 casos:
el módulo contiene **55 pruebas**. No se modifica ningún test del motor ni
las expectativas de E1–E17 en esta fase.

| Escenario | Verificación pública completada |
|---|---|
| I1 | Cuatro instrumentos y cinco aplicaciones, todos NO_INICIADO; totales exactos y audiencia de LAB |
| I2 | EN_PROGRESO, 10/60 ítems, 0/4 actividades, respuestas actuales y resultado 409 con el mismo avance |
| I3 | Validaciones de escritura y consulta de la respuesta reemplazada, con opción y fechas exactas |
| I4 | Resultado 409 con actividades faltantes tras cada bloque; resultado final, seis dimensiones, ERS y diez coincidencias |
| I5 | Resultado de Luis: RIE, top 10 exacto del notebook, ajustes y carreras CAR-FOR, CAR-AMB, CAR-AGR con vías ordenadas |
| I6 | Resultado plano, seis puntajes de 20, RIA con empate y ninguna coincidencia ni carrera |
| I7 | Rehacer conserva el resultado público íntegro y un único resultado en historial |
| I8 | Siete dimensiones de inteligencias y omisión de código de interés, coincidencias y carreras |
| I9 | Seis dimensiones de habilidades, con inversión y omisión de campos exclusivos del RIASEC |
| I10 | Comparación 409 hasta completar salida; diez opciones y diferencias exactas, sin resultados calculados |

Las pruebas adicionales comprueban:

- Catálogo con dimensiones, escalas, opciones y aplicaciones en orden, y
  cobertura exacta de ítems en todas las actividades de cada aplicación.
- Ítems compartidos de autopercepción y los cuatro ítems inversos de habilidades.
- Los cinco GET con cuenta rechazan tanto a apoderados como a cuentas inexistentes
  con 404; las referencias inexistentes, actividades de apoderado y aplicaciones
  ajenas al instrumento también devuelven 404.
- Selección obligatoria de aplicación cuando hay varias, incluido un instrumento
  con dimensiones preparado exclusivamente en la base de prueba; historial de
  ambas aplicaciones y desempate por id interno, sin exponerlo.
- Resultado inexistente devuelve 409 con avance; actividad de estudiante sin
  ítems devuelve colecciones vacías. Las respuestas y avances se aíslan por cuenta
  y aplicación, incluso con el mismo ítem de autopercepción.
- Historial de tres resultados anulados con sus dimensiones y diez coincidencias,
  fechas descendentes y desempate de fechas iguales. Las copias y anulaciones se
  preparan en SQL exclusivamente en los tests; no anticipan el endpoint de reinicio.
- Un resultado anulado no se devuelve como vigente ni hace que el avance marque
  COMPLETADO para instrumentos con dimensiones.
- Las siete consultas no escriben en ninguna de las 39 tablas, no exponen ids
  internos y conservan las correlaciones almacenadas sin redondear.

Resultado del módulo: **55 passed**. Con una ruta de Excel ausente simulada:
**51 passed, 4 skipped** (I4, I5, I7 y el historial con coincidencias reales).
La fixture sigue siendo exclusiva de tests y no introduce ocupaciones ficticias.

Pendiente: fase 5 para el reinicio público, I11–I14 y la verificación conjunta
de los siete invariantes; fase 6 para la interfaz y fase 7 para la validación final.
Las restricciones de resultado vigente único, distribución de ítems y ajuste ya
tienen pruebas de semilla; el aislamiento y la reversión transaccional tienen
cobertura parcial desde fase 3 y se completarán con el reinicio.

Resultado al cerrar la fase 4: **355 passed** con `uv run pytest -q`
(las 332 anteriores y 23 nuevas). I1–I10 se comprueban por los endpoints públicos;
E1–E17 conservan sus resultados esperados. Permanece únicamente el aviso de
deprecación de Starlette/httpx ya existente. No se agregan dependencias ni se
modifica la versión 2 del esquema.

## Instrumentos: fase 5

`POST /acciones/reiniciar-instrumento` está implementado. Se agregan 24 casos
a `tests/test_instrumentos.py`, que contiene **79 pruebas**. Los escenarios
I1–I10 conservan sus valores y se completan los cuatro restantes:

| Escenario | Verificación |
|---|---|
| I11 | Cadena A, reinicio, cuatro actividades EN_CURSO sin respuestas y con disponibilidad conservada; 409 de resultado; cadena B con nuevo vigente e historial de dos resultados |
| I12 | Aplicación obligatoria para TEST-AUTO, reinicio solo de salida sin tocar entrada; comparación 409 hasta completar salida otra vez; reinicio vacío 409 |
| I13 | Respuestas y finalizaciones de Ana y Luis intercaladas; puntajes y códigos independientes; respuestas fijas en las cuatro actividades; reinicio de Ana no afecta ninguna consulta de Luis |
| I14 | Fallo después de persistir el cálculo de LAB-RIA4: se revierten resultado, dimensiones, finalización, eventos y desbloqueos, conservando respuestas anteriores |

I14 usa un perfil plano para poder probar la transacción sin Excel. El fallo
después de crear un desbloqueo también sigue cubierto por la prueba de HAB
de fase 3. El auxiliar de cadenas ahora permite una fecha explícita, para
verificar la nueva aplicación de I11 después de la anulación.

Mapa de los siete invariantes de instrumentos:

| Invariante | Cobertura |
|---|---|
| 1. Único resultado vigente por cuenta y aplicación | Restricción SQL en semilla; I7, I11 y ciclos planos de uno y tres reinicios, con verificación en cada transición |
| 2. Aplicación completa para resultados vigentes | I4, I8, I11, I13, I14 y `verificar_invariantes_persistidos`; los anulados permanecen en historial durante EN_CURSO |
| 3. Respuestas fijas con resultado vigente | I7 e I13 rechazan modificaciones y comparan respuestas; ciclos planos rechazan incluso enviar la misma opción |
| 4. Reinicio conserva desbloqueos, eventos y resultados | I11 compara desbloqueos y eventos completos; dimensiones y correlaciones históricas conservadas; ciclos mantienen todos los resultados |
| 5. Aislamiento entre cuentas | I13 compara todas las consultas de Luis antes y después de reiniciar Ana; respuestas y resultados independientes; pruebas parciales de fases 3–4 |
| 6. Cada ítem exactamente una vez por aplicación | Semilla y sus casos inválidos, catálogo por HTTP y `verificar_invariantes_persistidos` durante ciclos e intercalación |
| 7. Correlación no negativa y ajuste correcto | I4–I5 y verificación de todas las coincidencias, incluidas anuladas; restricciones SQL para valores, ajustes y posiciones inválidos |

El invariante 2 se comprueba exclusivamente sobre resultados **vigentes**,
según el plan aprobado. El reinicio anula el resultado y permite que sus
actividades actuales estén EN_CURSO, manteniendo intacto el historial.

Además se verifica:

- 404 para cuenta o instrumento inexistentes, apoderados y aplicación ajena;
  422 para falta de selección o entradas inválidas. Ningún rechazo modifica estado.
- 409 en las cinco aplicaciones iniciales, sin respuestas ni resultado vigente.
- Reinicio parcial sin resultado: solo cambia el progreso existente, sin crear
  los restantes ni abrir actividades bloqueadas. Otro reinicio vacío no emite eventos.
- Borrado limitado a ítems del instrumento y progresos de la aplicación; otras
  respuestas y aplicaciones se conservan, incluso con un ítem ajeno insertado
  exclusivamente en la base de prueba.
- Fallo después de registrar REINICIA_INSTRUMENTO, con y sin resultado previo:
  una fotografía de las 39 tablas confirma la reversión íntegra de anulación,
  respuestas, progresos y evento.
- Fechas locales, referencia pública del evento y metadatos de anulación sin ids.

Resultado del módulo: **79 passed**. Con una ruta de Excel ausente simulada:
**73 passed, 6 skipped**; además de las cuatro omisiones de fase 4, se omiten
I11 e I13, que comparan los perfiles no planos contra las ocupaciones reales.
Las pruebas de reinicio, comparación, ciclos e I14 siguen ejecutándose.

Pendiente: fase 6 para la interfaz mínima y fase 7 para la documentación y
validación manual final. No se modifican E1–E17, el motor, la semilla ni el
esquema versión 2; no se agregan dependencias.

Resultado al cerrar la fase 5: **379 passed** con `uv run pytest -q`
(las 355 anteriores y 24 nuevas). I1–I14 y los siete invariantes de
instrumentos están cubiertos; E1–E17 conservan sus resultados esperados.
Permanece únicamente el aviso de deprecación de Starlette/httpx ya existente.

## Instrumentos: fase 6

Se incorpora `/demo/instrumentos`, enlazada desde `/demo`, con recursos locales.
No se modifican tests ni expectativas de E1–E17. La suite completa conserva
**379 passed** con `uv run pytest -q`; permanece el aviso de Starlette/httpx.
No se agregan dependencias ni se cambia el esquema versión 2.

Verificación manual mediante controles de la interfaz y endpoints reales,
con una base independiente en `.uv-cache/verificacion-instrumentos-ui-20260930.db`:

| Recorrido | Comprobación |
|---|---|
| Navegación | Enlace desde `/demo`, cuatro instrumentos, selector de cuenta y aplicaciones de TEST-AUTO |
| RIASEC inicial | LAB-RIA2 bloqueada con requisitos de LAB-RIA1; completar sin respuestas devuelve 409 con ítems faltantes |
| Relleno rápido | Elegir A marca 15 radios sin guardar; Guardar disponibles escribe solo LAB-RIA1 (15/60, 0/4); completar abre la siguiente y conserva la cadena |
| Cadena A | Cuatro finalizaciones; puntajes 21, 9, 17, 20, 28, 15; ERS, coincidencias y respuestas fijas; rehacer no añade otro resultado |
| Reinicio e historial | Cancelar conserva el estado; confirmar anula A, vacía respuestas y mantiene las cuatro actividades abiertas; historial conserva dimensiones y coincidencias |
| Cadena B | Tras reiniciar, Guardar disponibles guarda 60 ítems sin completar actividades; cuatro finalizaciones dan RIE y el top 10 de I5; CAR-FOR, CAR-AMB y CAR-AGR con vías ordenadas |
| Reemplazo de cadena | Con las cuatro actividades abiertas y borradores A, guardar B reemplaza las 60 opciones; tras recargar, LAB-RIA2 presenta `333233333443333`, sin reutilizar borradores A |
| Perfil plano | Relleno de 60 opciones 3, cuatro finalizaciones; seis puntajes 20/40, 50%, RIA con empate, sin coincidencias ni carreras |
| Inteligencias | Impares Sí, dos actividades; puntajes 7, 4, 2, 1, 3, 1, 4 y máximos 10, 7, 4, 5, 4, 8, 5 |
| Habilidades | Primeros 12 Casi siempre y restantes Casi nunca; puntajes 2, 2, 1, 1, 0, 4, con porcentajes de I9 y sin campos exclusivos de RIASEC |
| Autopercepción | Entrada BCCDBCACDB y salida AABCAACBBA; comparación pendiente antes de salida; diferencias 1, 2, 1, 1, 1, 2, −2, 1, 2, 1, sin resultados calculados |
| Reiniciar salida | Entrada permanece completada con 10 respuestas; salida queda EN_PROGRESO, 0/10; comparación 409 hasta completar salida otra vez |
| Errores y bloqueo | Lote vacío 422, finalización parcial 409 y cadena de longitud inválida sin POST; respuestas y errores visibles en registro; todos los controles deshabilitados durante el reinicio en curso |
| Aislamiento | Ana y Luis muestran avances propios; seleccionar Rosa devuelve 404, vacía paneles y bloquea acciones; volver a estudiante recupera su estado |
| Persistencia | Recargar recupera resultados, avances y opciones del servidor; no depende de borradores locales |

Revisión visual en escritorio **1440 × 900**, tableta **768 × 1024** y móvil
**390 × 844**. No hay desbordamiento horizontal de la página; las tablas anchas
se desplazan dentro de su contenedor. Se verifican radios, selección, guardado,
finalización y resultados en móvil, y navegación por los enlaces a paneles.
La consola del navegador no registra errores JavaScript. Las capturas de
escritorio y móvil quedan en `.uv-cache/instrumentos-escritorio.jpg` y
`.uv-cache/instrumentos-movil.jpg`, fuera de los archivos versionados.
No se modifica `demo.db` durante estos recorridos; el servidor de verificación
se detiene al terminar.

README incluye la guía de la interfaz y decisiones registra sus elecciones.
Pendiente: fase 7 para consolidar la documentación, revisar la cobertura final
y realizar la validación final solicitada.

## Ampliación 5.6.1: dimensiones destacadas

Actualización de las secciones 5.6.1, 6.2 y 9.1, las expectativas I8 e I9 y el
nuevo escenario I8b. Se conserva el mapa anterior de I1–I14 y E1–E17.

| Caso | Cobertura |
|---|---|
| I8 | Resultado público incluye únicamente INT-INTRA, con su objeto de dimensión completo; puntuaciones anteriores intactas |
| I8b | Sí en 7, 18, 26, 29, 5, 10, 31 y 39; destaca INT-ESP e INT-MUS al 100%, en orden; restantes en cero; reinicio conserva destacadas históricas |
| I9 | Resultado público destaca únicamente HAB-VAL al 80%; se mantienen máximos, inversión y puntuaciones anteriores |
| Todas en cero | TEST-INT con No en todos los ítems destaca las siete dimensiones, en orden |
| Función pura | 3/4, 3/4, 2/4; 4/7 frente a 1/2; todos cero; 4/7 frente a 5714/10000 (ambos muestran 57.14%); 4/7 y 8/14 como empate exacto; orden recibido conservado |

Se adaptan las listas exactas del JSON de I8 e I9 para añadir el nuevo campo,
sin relajar sus afirmaciones previas. La lógica se deriva de puntajes y máximos
almacenados al consultar vigente e historial; no se requieren migraciones ni
resultados nuevos. RIASEC omite el campo y conserva su código de interés;
autopercepción conserva la comparación. No cambia la versión 2 ni la semilla.

Pruebas focalizadas: **9 passed**, incluidas las cinco pruebas puras, I8, I8b,
I9 y el caso en cero. Los mismos **9 passed** con ruta de Excel ausente simulada,
sin omisiones ni ocupaciones ficticias. Siete casos nuevos respecto de los 379
anteriores. La ejecución programática de esa comprobación añade un aviso de
reescritura de asserts de anyio; no afecta los resultados.
Verificación manual con base separada
`.uv-cache/verificacion-destacadas-20260930.db`: la interfaz muestra Intrapersonal
al 80%, Espacial y Musical al 100% tras reiniciar, el resultado anterior anulado
con Intrapersonal, y Valores y participación al 80% en habilidades. Sin errores
JavaScript; captura en `.uv-cache/dimensiones-destacadas.jpg`. No se modifican
las respuestas de la demo del usuario durante esta verificación.

Suite completa tras la ampliación: **386 passed** con `uv run pytest -q`
(379 anteriores y siete nuevos), con el aviso de Starlette/httpx ya existente.
E1–E17 conservan sus resultados esperados.

Esta ampliación no cierra la fase 7 pendiente de documentación y validación final.

## Registro: fase 1

Se incorpora el esquema 4: `posicion` nullable, los tres enumerados y las cinco
tablas de registro. La semilla agrega REG y REG-ACT08 con sus tres ítems y seis
criterios exactos, sin agregar reglas ni eventos. Se extiende la caché de
definiciones y se valida el JSON durante el arranque y el reinicio.

`tests/test_registro.py` contiene **40 pruebas** de esta fase:

| Área | Verificación |
|---|---|
| Esquema | Columnas exactas, enumerados, posición nullable y clave compuesta |
| Semilla | Consignas, mínimos, obligatoriedad, repreguntas y criterios contrastados con §5.2; tres asociaciones ordenadas y ausencia de respuestas o evaluaciones iniciales |
| Audiencia | REG-ACT08 disponible para Ana y Luis; REG ausente del estado de Rosa; sin reglas nuevas |
| Persistencia | Borrador, clasificación inicial nullable, ampliación por defecto falsa, posición y dos evaluaciones con JSON y metadatos opcionales; NO_EVALUADA persistida |
| Restricciones | Códigos y respuestas duplicados rechazados; claves foráneas, enumerados, intentos distintos de 1–2 y criterios JSON inválidos rechazados por SQL |
| Aislamiento del modelo | Un mismo ítem admite respuestas distintas en los progresos de Ana y Luis |
| JSON público | Plantilla, momentos, líneas e ítems disponibles como recurso estático, sin escrituras |
| R17 | Actividad o ítem inexistente, lista incompleta, orden incorrecto, ítem repetido, ids de momento repetidos o vacíos, estructura inválida y archivo ausente o mal formado impiden arrancar |
| Transacciones | JSON inválido revierte la semilla inicial; un arranque rechazado conserva el archivo existente; un reinicio rechazado conserva las 44 tablas y la caché |
| Caché | Ítems y criterios ordenados, códigos C1/C2 aislados por ítem, cero SQL al consultar definiciones; reconstrucción tras commit y reinicio, conservación tras rollback |
| Compatibilidad | `/acciones/responder-registro` sigue rechazando NO_EVALUADA sin modificar estado |

La prueba previa de rechazo de esquema incorpora versión 3 y usa versión 5
como futura inválida; conserva el rechazo de versión 1 y ambas verificaciones
de versión 2. Solo se adaptan los conteos y listas autorizados de tablas,
bloques y actividades. Las condiciones y resultados de E1–E17 e I1–I14 no se
modifican. Las fixtures imponen `EVALUADOR=falso`.

R1 está cubierto parcialmente por semilla y audiencia: las consultas nuevas
del registro y su 404 para Rosa pertenecen a fase 3. R2–R16 y sus endpoints,
evaluadores, finalización y presupuestos SQL quedan pendientes de sus fases.
No se agregan dependencias ni se ejecuta Gemini. La base local `demo.db`
permanece en versión 3 y no se modifica: antes de usar el nuevo código con ella,
se requiere conservar un respaldo y recrearla según la política documentada.

Resultado al cerrar la fase 1: **454 passed, 1 warning** con
`uv run pytest -q` (413 pruebas anteriores con las adaptaciones autorizadas,
40 pruebas nuevas de registro y un caso adicional de rechazo de esquema 3).
E1–E17 e I1–I14 pasan, junto con los límites SQL y pruebas de crecimiento
existentes. Permanece únicamente el aviso previo de Starlette/httpx.
La primera ejecución completa detectó una lista de audiencia sin REG; se
amplió esa lista y la de actividades con REG-ACT08, dentro de las adaptaciones
de catálogo autorizadas. La ejecución completa posterior pasa íntegramente.

La fase 1 termina aquí. Sigue la fase 2: interfaz de evaluación, evaluador falso
y lógica pura de mínimo de caracteres y consistencia, sin llamadas a Gemini.

## Registro: fase 2

Se incorpora `app/evaluador_respuestas.py` con tipos de contexto y resultado,
el protocolo de evaluación, `EvaluadorFalso`, validación común y procesamiento
de texto vacío, mínimo, resultado y fallos. Los enumerados de registro se
comparten desde `app/tipos_registro.py`; sus nombres en `app/models.py` y el
esquema 4 permanecen iguales.

`tests/test_evaluador_respuestas.py` agrega **73 pruebas puras**, sin sesiones,
clientes HTTP, archivos de datos ni llamadas de red:

| Área | Verificación |
|---|---|
| Independencia | Un intérprete nuevo importa el módulo sin cargar SQLAlchemy, FastAPI ni `app.models` |
| Contexto | Solo título, consigna, criterios, respuestas anteriores y texto; sin campos de cuenta o nombre |
| Falso | ADECUADA por defecto; VAGA con criterios y fórmula exacta; atención sin repregunta; fallo y precedencia de marcadores; conserva todos los contextos |
| Entrada | Vacío y espacios Unicode rechazados sin evaluar; mínimo aplicado antes de los marcadores del falso |
| Caracteres | Fronteras 39/40/41 y 29/30/31, acentos y espacios exteriores; conserva el texto original |
| Esquema | Cuatro campos requeridos, tipos estrictos, sin campos adicionales ni NO_EVALUADA del evaluador |
| Consistencia | Criterios ajenos rechazados; ADECUADA sin faltantes; VAGA con repregunta, salvo atención; orden de criterios conservado |
| Validación defensiva | Revalida resultados previamente mutados o construidos sin validar, sin mostrar sus valores en avisos |
| Análisis | Origen, clasificación, criterios, repregunta, atención, texto, modelo y versión; latencia exacta de 125 ms con reloj simulado |
| Fallos | Esquemas incorrectos y excepciones se convierten en FALLO/NO_EVALUADA; categorías de error seguras y una sola llamada |
| Tiempo máximo | Timeout informado por el evaluador y fronteras 7.999/8/8.001 segundos, sin esperar ni llamar a servicios reales |
| Parámetros | Mínimo inválido, timeout no positivo o no finito y repregunta mínima vacía rechazan la configuración sin evaluar |

Resultado focalizado: **73 passed, 1 warning**. Permanece el aviso previo de
Starlette/httpx, originado por las importaciones de las fixtures del proyecto.
La función detecta resultados tardíos y timeouts del adaptador; el límite real
de espera de red se configurará en el SDK durante fase 6.

Pendiente: fase 3 para construir el contexto desde respuestas FINAL, guardar
evaluaciones y aplicar estados, intentos, eventos y contratos HTTP de R1–R10 y
R13–R16. Todavía no se implementan esas acciones ni se usa Gemini. No se agregan
dependencias, se modifican tests anteriores ni se cambia la base local.

Resultado al cerrar la fase 2: **527 passed, 1 warning** con
`uv run pytest -q`: las 454 pruebas de fase 1 y las 73 nuevas pruebas puras.
E1–E17, I1–I14, las restricciones de esquema 4, R17, los límites SQL y las
pruebas de crecimiento existentes siguen pasando. Permanece únicamente el
aviso previo de Starlette/httpx. Se detiene el trabajo al cerrar esta fase.

## Registro: fase 3

Se implementan los siete endpoints de §7 y la persistencia de evaluaciones,
con contratos públicos separados de la auditoría técnica. Los escenarios nuevos
de `tests/test_registro.py` parten de `/demo/reiniciar` y usan SQLite temporal y
evaluadores falsos; las pruebas estructurales de fase 1 se conservan.

| Área | Verificación |
|---|---|
| R1 | Tres ítems en orden, sin criterios; registro inicial vacío; Rosa recibe 404; consultas sin escrituras |
| R2 | Posición recuperable y progreso EN_CURSO en el mapa; posición desconocida 422 sin cambios |
| R3 | Un borrador reemplazable, sin evaluaciones ni eventos y sin llamar al evaluador |
| R4–R5 | Mínimo de caracteres y repregunta persistida; segundo intento FINAL con ampliación y evento, primer texto y clasificación inmutables |
| R6–R7 | VAGA del falso y continuar sin ampliar sin eventos; ADECUADA al primer intento con evaluación y evento de referencia nula |
| R8 | Contexto con consignas, criterios ordenados y solo respuestas FINAL de otros ítems de la misma cuenta; sin nombres ni códigos de cuenta |
| R9–R10 | Fallo finaliza NO_EVALUADA sin evento; atención finaliza sin repregunta y se conserva solo en auditoría |
| R13 | Editar FINAL actualiza texto sin evaluaciones/eventos y conserva primer envío, clasificación, ampliación y creación; borrador FINAL 409 |
| R14 | Borrador o envío paralelo, con respuesta inicialmente ausente, BORRADOR o PENDIENTE; original 409 y su evaluación descartada incluso con misma fecha |
| R15 | El propio falso comprueba que ambas sesiones son independientes, no hay transacciones y el pool tiene cero conexiones tomadas al evaluar |
| R16 | Posiciones, respuestas y evaluaciones de Ana y Luis se aíslan |
| Fronteras | 39/40/41 y 29/30/31 caracteres con acentos y espacios exteriores; texto original preservado; envío vacío o espacios Unicode 422 sin cambios; borrador vacío permitido |
| Ampliación | Borrador pendiente conserva repregunta e historial; segundo intento VAGA, corto, fallido o con atención siempre FINAL y con un solo evento |
| Rechazos | Cuenta/actividad ausente y apoderado 404, actividad bloqueada o ítem ajeno 409, continuar fuera de PENDIENTE 409; sin escrituras |
| Errores del evaluador | Timeout, resultado inconsistente, criterio desconocido y excepción se guardan como FALLO con mensajes seguros, sin reintento ni exposición de detalles |
| Concurrencia | Marca monotónica con reloj fijo; comparación SQL protege también un cambio entre relectura y escritura |
| Atomicidad | Errores SQL después de insertar evaluación, evento o desbloqueo revierten progreso/respuesta/evaluación/eventos/desbloqueos, con respuestas previamente ausentes, borradores y pendientes |
| Relectura | Contextos distintos entre transacciones; eventos intercalados se tienen en cuenta al calcular desbloqueos |
| Recuperación | Reabrir la aplicación conserva posición, borrador de ampliación, repregunta e historial; respuestas ordenadas por ítem e historial por inserción |
| Contenido | Reinicio inválido conserva las posiciones en caché; reinicio válido adopta los nuevos ids del JSON |
| Progreso | Guardar posición y editar no degradan un progreso COMPLETADA |

Resultado focalizado antes de añadir la última prueba de conservación de progreso:
**122 passed, 1 warning** con `uv run pytest -q tests/test_registro.py`.

Pendiente de las próximas fases: validación para completar (R11/R12), presupuestos
SQL de los endpoints nuevos y crecimiento, adaptador Gemini y script sin ejecución
real, interfaz web y cierre consolidado. No se modifican tests ni expectativas
anteriores, dependencias o base local. No se ejecutan llamadas reales a Gemini.

Resultado al cerrar fase 3: **610 passed, 1 warning** en 432.78 segundos con
`uv run pytest -q`. Son las 527 pruebas anteriores y 83 nuevas; el archivo
`tests/test_registro.py` contiene ahora 123 casos, incluidos los 40 de fase 1.
Pasan E1–E17, I1–I14, R1–R10, R13–R17 y las comprobaciones SQL existentes.
Se conserva únicamente el aviso previo de Starlette/httpx. No se ajustan
expectativas de tests anteriores. Se detiene el trabajo al terminar esta fase;
la siguiente es fase 4 (validación de completar y R11/R12).

## Registro: fase 4

La acción existente de completar exige que los ítems de registro obligatorios
estén FINAL, antes de escribir progreso, eventos o desbloqueos. Reutiliza el
motor y el contrato de respuesta existentes.

`tests/test_registro.py` incorpora 19 casos, sin modificar pruebas anteriores.
El comando focalizado `uv run pytest -q tests/test_registro.py -k "r11 or r12 or
completar or faltantes or rehacer"` devuelve **21 passed, 121 deselected,
1 warning**, incluyendo dos casos anteriores seleccionados.

| Área | Verificación |
|---|---|
| R11 | Dos FINAL y un BORRADOR: 409 con REG-HAB-3 faltante, solo lecturas SQL y fotografía íntegra sin cambios; con los tres FINAL: COMPLETADA y eventos COMPLETA_ACTIVIDAD(REG-ACT08) y COMPLETA_BLOQUE(REG) |
| R12 | Tres envíos adecuados: un evento reflexivo de referencia nula cada uno; el tercero obtiene LOG-PENSADOR; reglas/condiciones intactas, una sola obtención y tres evaluaciones iniciales |
| Faltantes | Ausencia de progreso/respuestas, todos BORRADOR o todos PENDIENTE rechazan en orden, sin escrituras ni evaluación |
| FINAL | Se permite completar después de fallo, atención, continuar sin ampliar o segundo intento fallido; no se exige clasificación ADECUADA ni se modifica auditoría |
| Opcionales | Ítem opcional ausente, BORRADOR o PENDIENTE no impide completar; todos opcionales permiten completar sin respuestas |
| Orden | Los faltantes siguen el orden de presentación, distinto del código/id, y excluyen opcionales |
| Cuenta | Apoderada y cuenta inexistente reciben 404 sin cambios; los FINAL de Luis no completan el registro de Ana |
| Actividad | Las respuestas FINAL de los mismos ítems en otra actividad no cumplen los requisitos de REG-ACT08 |
| Rehacer y editar | Misma fecha simulada: cada finalización suma COMPLETA_ACTIVIDAD, solo una COMPLETA_BLOQUE y un logro; posición, respuestas y evaluaciones se conservan; edición FINAL sin nueva evaluación/evento reflexivo y primer envío/clasificación inmutables |

Las variantes de definición solo afectan la base temporal de cada prueba.
No se cambia semilla, motor, instrumentos, dependencias ni base local, y no se
ejecuta Gemini. La siguiente fase amplía presupuestos SQL y crecimiento.

Resultado al cerrar fase 4: **629 passed, 1 warning** en 427.94 segundos con
`uv run pytest -q`: 610 pruebas anteriores y 19 nuevas. El archivo de registro
contiene ahora 142 casos. Pasan R1–R17, E1–E17, I1–I14 y las comprobaciones SQL
anteriores, sin adaptar expectativas previas. Permanece únicamente el aviso
de Starlette/httpx ya existente. La fase termina aquí; siguen los presupuestos
SQL nuevos y las pruebas de crecimiento de fase 5.

## Registro: fase 5

Se amplía `LIMITES_SQL` y las mediciones de `tests/test_consultas.py` sin cambiar
los límites existentes. El contador observa la petición HTTP completa, incluidas
las dos transacciones del envío; la preparación y la carga de la caché quedan
fuera de la medición. Todos los casos usan SQLite temporal y evaluadores falsos.

| Petición | SQL observado | Límite |
|---|---:|---:|
| Guardar posición nueva / existente o completada | 4 / 3 | 4 |
| Guardar borrador nuevo / reemplazo o ampliación pendiente | 4 / 3 | 6 |
| Enviar mínimo o FALLO, primer intento | 6–7 | 12 |
| Enviar VAGA del falso, primer intento | 6–7 | 12 |
| Enviar ADECUADA o atención, primer intento | 9–10 | 12 |
| Enviar segundo intento, de cualquier origen | 9 | 12 |
| Enviar que obtiene LOG-PENSADOR y reglas adicionales | 10–11 | 12 |
| Editar FINAL | 5 | 12 |
| Continuar sin ampliar, tras mínimo o LLM | 3 | 8 |
| Ítems de registro desde caché | 0 | 1 |
| Estado sin progreso, con posición/borrador/FINAL o completado | 2 | 4 |
| Estado con repregunta pendiente | 3 | 4 |
| Evaluaciones: 0, 3 o 6 filas | 2 | 4 (adoptado para la demo) |
| Completar rechazado / primera vez / rehacer | 2 / 8 / 7 | 15 |

Se cubren los cuatro estados previos de envío: respuesta ausente con y sin
progreso, BORRADOR y PENDIENTE_AMPLIACION. Se combinan con mínimo, ADECUADA,
VAGA, atención, fallo del falso, timeout simulado y resultado inconsistente;
se comprueba el origen persistido y el evento que corresponde. La edición FINAL
se mide aparte y no vuelve a llamar al evaluador.

El caso específico del contador comprueba desde el falso que el pool tiene cero
conexiones tomadas y la evaluación no suma SQL, y verifica lecturas de ambas
transacciones junto con la escritura de la evaluación.

La prueba de crecimiento compara una base normal y otra con **100 reglas
reflexivas y 500 eventos adicionales**. Ambas tienen dos reflexiones de
preparación; la ampliada carga todas las definiciones antes de la primera
consulta medida. Las reglas nuevas tienen referencia nula y EVENTOS ≥3.

| Envío | SQL normal | SQL ampliado |
|---|---:|---:|
| Primera respuesta sin progreso | 11 | 11 |
| Reemplazar borrador | 10 | 10 |
| Ampliar | 10 | 10 |
| Texto mínimo | 7 | 7 |
| VAGA del falso | 7 | 7 |
| Fallo del falso | 7 | 7 |
| Atención | 11 | 11 |
| Edición FINAL | 5 | 5 |

En cada caso, el estado del registro antes y después cuesta lo mismo en ambas
bases: 2 consultas, o 3 cuando hay repregunta pendiente. Las cuatro ramas que
registran evento reflexivo evalúan cada regla nueva una vez y guardan los 100
desbloqueos adicionales en una sola inserción en lote. Se verifica también la
persistencia; las ramas sin evento no evalúan ni otorgan esos desbloqueos.

Resultado focalizado: **58 passed, 55 deselected, 1 warning** con
`uv run pytest -q tests/test_consultas.py -k registro -s`. Las 59 pruebas nuevas
incluyen además el caso específico del contador, cuyo nombre no contiene
`registro` y se ejecuta por separado y en la suite completa.

No se modifica código de aplicación, semilla, motor, instrumentos, contratos,
dependencias ni base local. No hay llamadas reales a Gemini. Sigue fase 6 para
el adaptador y el script; su ejecución real permanece pendiente de petición
explícita.

La prueba específica del contador devuelve **1 passed, 1 warning** con
`uv run pytest -q tests/test_consultas.py::test_contador_del_envio_incluye_ambas_transacciones_y_excluye_sql_al_evaluar`.

Resultado al cerrar fase 5: **688 passed, 1 warning** en 482.93 segundos con
`uv run pytest -q`: 629 pruebas anteriores y 59 nuevas. Pasan E1–E17, I1–I14,
R1–R17, todos los presupuestos SQL y las pruebas de crecimiento anteriores y
nuevas. Permanece únicamente el aviso previo de Starlette/httpx. No se modifican
expectativas anteriores ni se ejecuta Gemini. El trabajo se detiene aquí; sigue
fase 6 con pruebas simuladas y ejecución real pendiente de petición explícita.

## Registro: fase 6

`tests/test_evaluador_gemini.py` comprueba el adaptador exclusivamente con
clientes simulados y una petición del SDK sobre `httpx.MockTransport`. La fixture
general sigue imponiendo `EVALUADOR=falso`; estas pruebas no acceden a Gemini.
La protección de sockets permite solo el loopback interno que Windows necesita
para iniciar asyncio, y rechaza conexiones externas.

| Área | Comprobación |
|---|---|
| Configuración | Defaults, lectura de `.env`, prioridad del proceso sin modificarlo, ausencia de interpolación, clave excluida de `repr`, proveedor/modelo/timeout inválidos y rechazo de Gemini sin clave antes de crear la base |
| Petición | Prompt v1, solo los cinco campos de contexto, criterios ordenados, anteriores sin identidad, temperatura 0.2, JSON estructurado estricto, candidato único y funciones automáticas desactivadas |
| Razonamiento | Mínimo compatible para modelos reconocidos; ajuste omitido para desconocidos sin descubrimiento remoto |
| Resultado | ADECUADA, VAGA y atención; rechazo de tipos erróneos, campos adicionales, clasificación inválida, criterios desconocidos, inconsistencia y repregunta ausente/vacía |
| Transporte | Timeout simulado, conexión fallida, 429 y 504; FALLO con mensajes saneados y una única llamada. El SDK con transporte simulado recibe timeout 1250 ms y attempts=1 y realiza exactamente una petición ante 429 |
| Secretos | Mensajes directos y persistidos sin clave, sin causa externa visible; log con clave y traceback saneado; CLI con excepción externa no expone su mensaje |
| Recursos | Latencia no negativa del adaptador y procesador; cliente propio cerrado, cliente inyectado conservado; pool libre durante llamada desde un envío HTTP y metadatos guardados en la auditoría separada |
| Script | Los 14 casos llegan al adaptador, incluidos los cortos; caso 12 corregido y caso 14 de atención; contextos previos de casos 2/6, 13 pausas, reporte temporal escapado, continuidad ante errores, ayuda sin cliente y pausas inválidas rechazadas |

El script prepara definiciones oficiales en memoria y cierra su motor antes de
llamar al evaluador. No modifica `demo.db`. No se ha ejecutado contra la API real
ni generado el reporte real `docs/evaluacion_gemini.md`; clasificación semántica,
calidad de repreguntas, detección real del caso 14, cuotas y latencias reales
siguen sin verificarse hasta una petición explícita.

Resultado focalizado final: **59 passed, 2 warnings** con
`uv run pytest -q tests/test_evaluador_gemini.py`. El aviso previo de Starlette/httpx
permanece; se añade un aviso interno de `google.genai.types` por
`_UnionGenericAlias`, deprecado en Python 3.14 y previsto para retirada en 3.17.
No se suprime ningún aviso ni se añade una dependencia para resolverlo.

Resultado al cerrar fase 6: **747 passed, 2 warnings** en 506.40 segundos con
`uv run pytest -q`: 688 pruebas anteriores y 59 nuevas. Se conservan los
resultados de E1–E17, I1–I14 y R1–R17, todos los presupuestos SQL y las mediciones
de crecimiento. `uv lock --check` pasa. Se comprobó que `.env` y `demo.db` siguen
ignorados, `.env.example` puede versionarse, la base local no fue modificada y
no existe `docs/evaluacion_gemini.md`. Finaliza esta fase; sigue la interfaz
`/demo/registro` de fase 7, con ejecución y reporte real todavía pendientes.

## Registro: fase 7

La página `/demo/registro` se sirve con HTML, CSS y JavaScript planos, reutiliza
`demo.css` y se enlaza desde `/demo`. `tests/test_demo_registro.py` comprueba que
la página, sus tres recursos y el JSON estático se sirven sin SQL, no modifican
posición, respuestas, evaluaciones ni eventos y no llaman al evaluador. No se
añade un endpoint de datos ni se expone la página en OpenAPI.

La comprobación en navegador se ejecutó con Edge/Chromium, sobre una aplicación
con `EVALUADOR=falso` y una SQLite temporal independiente de `demo.db`.
`tests/validar_registro_ui.cjs` usa Playwright del entorno de verificación; sus
herramientas no se incorporan a `pyproject.toml`. Se revisaron las capturas.

| Caso | Resultado comprobado |
|---|---|
| Explicación | Tres líneas del JSON, Lumi, posición inicial nula y Continuar guardando `plan`; la recarga recupera la posición y la fecha simulada |
| Teclado | El enlace de salto activado con Enter lleva el foco a la actividad; formularios y botones son nativos y conservan el foco visible del estilo existente |
| Carga inicial fallida | Un 503 simulado deja Actualizar disponible; reintenta las definiciones y carga el plan sin recargar la página |
| Borrador y mínimo | Se recupera Borrador al recargar; “Asertividad” produce la repregunta mínima y se conserva tras recarga |
| Ampliación | Borrador de ampliación conserva texto, estado y pregunta; el segundo envío VAGA del falso queda FINAL sin otra repregunta |
| Edición FINAL | Guardar cambios reemplaza texto sin una evaluación nueva; Guardar borrador permanece deshabilitado |
| Aislamiento | Texto local se conserva entre ítems, se borra al cambiar cuenta; Luis recupera solo su borrador y su auditoría, Rosa no tiene formulario ni detalle técnico |
| Continuar y completar | Continuar sin ampliar deja FINAL; el botón exige los tres FINAL y completar se recupera como COMPLETADA al recargar |
| Espera | Petición pausada en el navegador: mensaje exacto de Lumi, indicador visible, cuenta y botones deshabilitados; al terminar recuperan su estado |
| Novedades | Tres primeras respuestas adecuadas de Luis obtienen LOG-PENSADOR; Marcar como visto oculta novedades mediante el endpoint autorizado |
| Conflicto | Un 409 simulado después de guardar un borrador paralelo relee el servidor, conserva el texto local y no reenvía ni agrega evaluaciones |
| Lectura posterior fallida | El POST se confirma, un GET simulado falla: se informa “Respuesta guardada” y Actualizar recupera el texto sin nueva evaluación |
| Auditoría tardía | La respuesta retrasada de Ana no sustituye las tres evaluaciones de Luis tras cambiar cuenta |
| Móvil | Emulación táctil 390/360×844: explicación, borrador de ampliación recuperado, pregunta única, edición y completar; sin desbordamiento horizontal |
| Fallo y atención | `[falla]` y `[atencion]` del falso dejan FINAL sin repregunta ni clasificación o marcas técnicas en la actividad pública |
| Rutas y JavaScript | Todas las solicitudes de escritorio y móvil se ajustan a las rutas autorizadas; no hay errores JavaScript |

La espera y el 409 de esta comprobación se simulan en la capa del navegador.
R14/R15 siguen verificando la concurrencia y liberación de sesiones del backend.
La emulación móvil no constituye una prueba con un dispositivo físico ni con
Safari. No hay llamadas reales a Gemini ni resultados del script de §10.

Evidencias guardadas, con el falso:

- [Resumen de comprobaciones](evidencias/registro/comprobaciones.json).
- [Explicación de escritorio](evidencias/registro/explicacion-desktop.png),
  [repregunta de escritorio](evidencias/registro/repregunta-desktop.png),
  [espera](evidencias/registro/espera-desktop.png) y
  [detalle técnico](evidencias/registro/tecnico-desktop.png).
- [Explicación móvil](evidencias/registro/explicacion-movil.png),
  [repregunta móvil](evidencias/registro/repregunta-movil.png) y
  [finalización móvil](evidencias/registro/completado-movil.png).

Para repetir en una base descartable, iniciar en una terminal:

```powershell
uv run python tests/servidor_registro_ui.py
```

En otra, con Node y Playwright disponibles en el entorno de verificación:

```powershell
node tests/validar_registro_ui.cjs http://127.0.0.1:8787 docs/evidencias/registro
```

El servidor fuerza `falso`, usa una SQLite temporal y se termina con Ctrl+C.
El script de navegador reinicia esa demo de pruebas; no ejecutarlo contra la
base de trabajo. El canal por defecto es Edge (`msedge`); `CANAL_NAVEGADOR`
permite seleccionar otro canal ya disponible. No descarga navegadores.

Resultado focalizado: **3 passed, 1 warning** con
`uv run pytest -q tests/test_demo_registro.py tests/test_demo.py`.
La sintaxis de `registro.js` pasa la comprobación de Node y el recorrido del
navegador termina con código 0. La base local conserva su fecha y tamaño.
Sigue fase 8 para consolidación; la evaluación real permanece pendiente.

Resultado completo al cerrar fase 7: **748 passed, 2 warnings** en 649.36 segundos
con `uv run pytest -q`. Las 747 pruebas anteriores y la nueva comprobación de
la página pasan; se conservan E1–E17, I1–I14, R1–R17 y los presupuestos SQL.
Los avisos siguen siendo las deprecaciones conocidas de Starlette/httpx y
`google.genai.types` en Python 3.14. No se ejecutó Gemini real ni se generó su reporte.

## Registro: fase 8, cierre consolidado

Esta fase actualiza las instrucciones y reúne las comprobaciones de las siete
fases anteriores, sin cambiar aplicación, modelos, semilla, reglas, contratos,
expectativas de escenarios ni dependencias. La base inicial comprobada era de
413 tests; al cerrar fase 7 son 748, incluyendo las ampliaciones autorizadas.
La ejecución completa de cierre se registra al final de esta sección.

### Cobertura de aceptación

| Requisito | Evidencia automatizada |
|---|---|
| E1–E17 e invariantes anteriores | `tests/test_escenarios.py`, `tests/test_invariantes.py` y `tests/test_motor.py`; se conservan resultados, eventos de primera vez y desbloqueos permanentes |
| I1–I14 | `tests/test_instrumentos.py`, junto con semilla y cálculos; se conservan instrumentos, resultados y recomendaciones |
| R1–R3 | `tests/test_registro.py`: estado inicial, audiencia, posición recuperable y borrador reemplazable sin evaluación ni eventos |
| R4–R7 | Mínimo sin LLM, una ampliación, VAGA del falso, continuar sin ampliar y ADECUADA; primer texto y clasificación inicial inmutables |
| R8 | Contexto puro limitado a título, consignas, criterios ordenados, respuestas FINAL de otros ítems de la misma cuenta y texto actual; sin identidad |
| R9–R10 | Fallo y atención terminan en FINAL; solo la auditoría contiene clasificación, criterios y marcas técnicas |
| R11–R12 | Faltantes ordenados con 409 sin escrituras; FINAL obligatorio para completar; tres reflexiones de referencia nula obtienen LOG-PENSADOR sin modificar su regla |
| R13 | Edición FINAL y repetición de completar conservan clasificación inicial, primer envío, posición e historial; editar no evalúa ni registra eventos |
| R14 | Concurrencia con respuesta ausente o existente, incluso con fecha simulada fija; marca monotónica y comparación SQL; 409 descarta íntegramente la evaluación |
| R15 | Pool libre y ninguna sesión/transacción durante evaluación; dos transacciones de persistencia separadas; contexto de consulta reconstruido |
| R16 | Aislamiento entre Ana y Luis de posición, respuestas y evaluaciones; apoderados sin acceso al registro |
| R17 | JSON inválido impide arrancar; reinicio fallido conserva base/caché y reinicio válido reconstruye definiciones y posiciones |
| Fronteras y fallos | `tests/test_evaluador_respuestas.py` y `tests/test_registro.py`: vacío, espacios Unicode, 39/40/41 y 29/30/31 caracteres, resultados inconsistentes, timeout, borrador pendiente y segundo intento fallido |
| Restricciones y atomicidad | Claves, enumerados, JSON e intentos 1–2; errores SQL después de evaluación, evento o desbloqueo revierten todo; versiones 1–3 y futura 5 rechazadas |
| Contrato anterior | `/acciones/responder-registro` sigue aceptando exclusivamente ADECUADA y VAGA |
| Adaptador y script | `tests/test_evaluador_gemini.py`: 59 casos con clientes/transporte simulados; prompt v1, temperatura 0.2, salida estricta, timeout, latencia, un intento y secretos saneados; 14 casos preparados, incluido el caso 12 corregido |
| Página y recursos | `tests/test_demo_registro.py`: 0 SQL, sin escritura ni evaluación al servir HTML, CSS, JavaScript y JSON; sin API auxiliar |

El [detalle de acciones](#registro-fase-3), la [finalización](#registro-fase-4)
y el [adaptador simulado](#registro-fase-6) conservan los casos y resultados
focalizados. Todos los tests de persistencia usan SQLite temporal; la fixture
general impone `EVALUADOR=falso`. Las pruebas específicas del SDK sustituyen
cliente/transporte y bloquean conexiones externas: ninguna prueba usa Gemini real.

### Presupuestos SQL consolidados

`tests/test_consultas.py` exige estos máximos sobre la petición completa. En el
envío cuenta conjuntamente las dos transacciones; durante la evaluación no hay SQL.
Los valores observados proceden de las [mediciones de fase 5](#registro-fase-5),
que se conservan en la suite completa.

| Petición | Máximo observado | Presupuesto exigido |
|---|---:|---:|
| Guardar posición | 4 | 4 |
| Guardar borrador | 4 | 6 |
| Enviar, incluyendo ampliación, fallo y edición | 11 | 12 |
| Continuar sin ampliar | 3 | 8 |
| Ítems | 0 | 1 |
| Estado del registro | 3 | 4 |
| Completar REG-ACT08 | 8 | 15 |
| Evaluaciones, consulta técnica de la demo | 2 | 4 (decisión adicional) |

El crecimiento exige igualdad de consultas al añadir **100 reglas activadas por
RESPUESTA_REFLEXIVA y 500 eventos**. Cubre ocho ramas de envío y el estado antes
y después; las ramas reflexivas comprueban también 100 desbloqueos persistidos
en una sola inserción en lote. No se alteran los presupuestos anteriores.

### Interfaz y visualización

La [validación visual de fase 7](#registro-fase-7) incluye Edge/Chromium en
1440×1000 y emulación táctil de 390/360×844, siete capturas revisadas,
222 solicitudes de interfaz solo a rutas autorizadas y cero errores JavaScript.
Cubre recarga, aislamiento, borradores, repregunta única, ampliación, edición,
finalización, novedades, espera, recuperación tras error y auditoría tardía.
Los fallos de lectura, espera y 409 del navegador se simulan por interceptación;
la concurrencia real del backend se comprueba en R14/R15. No se atribuye esa
emulación a un teléfono físico ni a Safari.

Para abrir el resultado sin reemplazar la base anterior, usar
`uv run python tests/servidor_registro_ui.py` y
`http://127.0.0.1:8787/demo/registro`. El servidor fuerza `falso`, siembra una
SQLite temporal con esquema 4 y mantiene los cambios hasta detenerlo. El arranque
de visualización se comprobó con GET 200, registro inicial vacío y posición nula;
no se ejecuta el script que reinicia datos mientras el usuario explora esta sesión.
La base local anterior conserva tamaño y fecha; no se migra ni elimina al arrancar.

### Evaluación real pendiente

La integración está implementada y comprobada con dobles de prueba. Quedan
pendientes, exclusivamente ante petición explícita, la ejecución de
`scripts/evaluar_gemini.py` y la revisión de `docs/evaluacion_gemini.md`.
Todavía no existe ese reporte. No están verificadas la calidad semántica de
clasificaciones/repreguntas, detección real del caso 14, latencias ni cuotas del
proveedor. El falso clasifica de forma determinista y no permite inferir esa calidad.

### Resultado final

`uv run pytest -q`: **748 passed, 2 warnings** en 532.26 segundos (8 min 52 s).
Pasan E1–E17, I1–I14, R1–R17, restricciones, reversión, caché, presupuestos SQL
y crecimiento; no se añaden tests ni se ajustan expectativas en esta fase.
Los avisos son las deprecaciones conocidas de Starlette/httpx y del SDK de Google
en Python 3.14. `uv lock --check` pasa. Se verificó que `demo.db` conserva
602112 bytes y su fecha de modificación anterior, y que el reporte real no existe.

Las ocho fases de implementación de registro quedan cerradas. La demo temporal
se deja activa y abierta para visualización; sus cambios duran hasta detener el
servidor. Solo queda la evaluación real y su reporte bajo petición explícita.

## Diagnóstico real posterior al cierre

El usuario autorizó una única llamada diagnóstica a Gemini con texto de prueba
inventado (caso 6), después de comunicar otro FALLO en la interfaz. Se realizó
fuera del entorno restringido, con el mismo adaptador, configuración y un intento
total, sin modificar `demo.db` ni ejecutar la batería de 14 casos.

Resultado: **1 llamada, HTTP 503, ServerError, 2049 ms, sin evaluación válida**.
Se mostraron solo metadatos saneados, sin clave ni mensajes externos. La
[documentación oficial](https://ai.google.dev/gemini-api/docs/troubleshooting)
clasifica 503 UNAVAILABLE entre los errores transitorios. No se hizo otro intento.

Este diagnóstico comprueba acceso al servicio y observa indisponibilidad en esa
petición; no constituye validación semántica del modelo. Tampoco prueba el código
HTTP de evaluaciones anteriores, que conservan el error genérico original. El
reporte completo `docs/evaluacion_gemini.md` sigue pendiente de autorización.

## Registro: reinicio desde la interfaz

El botón **Reiniciar demo** de `/demo/registro` reutiliza el POST existente y
pide confirmar el borrado de todas las cuentas. La ampliación no añade APIs,
dependencias ni cambios en los contratos de acciones o en el motor.

`tests/test_demo_registro.py` añade una prueba de integración que prepara
respuestas FINAL, pendientes y un borrador de Ana y Luis, y verifica que el
reinicio elimina respuestas, posición, progreso, evaluaciones y eventos.
Las definiciones y configuración se conservan; no se llama al evaluador durante
el reinicio. Un envío posterior registra solamente el intento 1 con contexto
previo vacío. Prueba focalizada: **2 passed, 1 warning** en 2.76 segundos.

La comprobación visual usa el evaluador falso y una SQLite temporal distinta de
las demos persistentes. Verifica Conservar progreso y Escape con una ampliación
local sin guardar, confirmación con controles bloqueados y mensaje de espera,
retorno a Lumi, texto y detalle técnico vacíos, recarga, tres ítems Vacío y
cambio a Luis sin respuestas anteriores. Las lecturas de ambas cuentas después
del reinicio confirman cero respuestas y evaluaciones y posición nula.

Se revisan el diálogo en escritorio y a 360×844, sin desbordamiento horizontal,
con ambos botones visibles y foco inicial en cancelar. El navegador no registra
errores JavaScript. Evidencias:
[escritorio](evidencias/registro/reinicio-escritorio.jpg) y
[móvil](evidencias/registro/reinicio-movil.jpg). `node --check` valida el JavaScript.
No se llama a Gemini ni se reinician las bases persistentes del usuario.

Suite completa después de esta ampliación: `uv run pytest -q`, **749 passed,
2 warnings** en 604.23 segundos. Conserva E1–E17, I1–I14, R1–R17 y los
presupuestos SQL; los dos avisos de deprecación siguen siendo los conocidos de
Starlette/httpx y Google en Python 3.14.

## Registro v2: fase 1

La estructura de v2 conserva esquema versión 4 y aumenta a 45 tablas.
`tests/test_registro.py` exige los campos y enumerados nuevos, la eliminación
de los campos duplicados de v1, los turnos con orden 1–2 y número de evaluación
positivo (admite 3). Mantiene las comprobaciones de semilla, JSON inválido,
caché sin SQL, reconstrucción por commit/reinicio y conservación por rollback.

Las pruebas nuevas cubren turnos sin respuesta, con borrador y respondidos,
persistencia de criterios JSON y fechas, conservación del texto inicial al
editar un turno directamente, unicidad, FK, orden inválido y JSON no-lista.
Verifican que reiniciar borra los turnos y las respuestas y reconstruye la
caché de definiciones. Los turnos no se almacenan en esa caché.

Cuatro variantes temporales de estructura v1 con `esquema_version = 4`
se rechazan sin modificar el archivo: tabla de turnos ausente o columnas de
ítem, respuesta y evaluación anteriores. Las pruebas existentes conservan
rechazos de versiones 1, 2, 3 y futura 5. Ninguna comprobación renueva una base
persistente del usuario.

Los escenarios de acciones, evaluación, Gemini simulado e interfaz aún
caracterizan el flujo previo, adaptando solo nombres de campos y enumerados.
La aceptación del seguimiento v2 y de «evaluador primero, longitud de respaldo»
queda para fases 2–3; no se considera comprobada en esta fase. E1–E17 e I1–I14
mantienen expectativas, igual que el contrato `/acciones/responder-registro`.
El [detalle de decisiones](decisiones.md#registro-v2) indica las adaptaciones
transitorias y el alcance de las fases pendientes. Los tests usan SQLite temporal
y el falso o clientes simulados, sin llamadas reales.

Resultado de fase 1 v2: `uv run pytest -q`, **764 passed, 2 warnings** en
593.76 segundos. Las 15 pruebas adicionales respecto de las 749 anteriores
cubren la nueva estructura y sus restricciones; no se omiten pruebas.
La escritura de concurrencia se adapta de `texto` a `texto_inicial` conservando
su expectativa de 409; pasa también de forma focalizada. Los avisos siguen
siendo los conocidos de Starlette/httpx y Google en Python 3.14.
`node --check` pasa para `app/static/registro.js` y el script visual; no se
realiza validación visual de una conversación v2 todavía no implementada.

## Registro v2: fase 2

La evaluación pura usa conversaciones completas y criterios faltantes previos.
Las pruebas de `tests/test_evaluador_respuestas.py` comprueban que el módulo no
importa SQLAlchemy, FastAPI ni modelos; que el contexto solo tiene los campos
de §6.5 y que el falso decide por el texto más reciente, conservando los contextos.
Cubren marcas `[falta:...]`, subconjuntos de criterios, rechazo de criterios ya
cumplidos, resultados inconsistentes y conservación de conversación/Unicode/orden.

Se verifica la regla «evaluador primero» con texto corto y largo y los límites
39/40/41 y 29/30/31 caracteres, con espacios exteriores. Ante fallo se comprueban
las decisiones puras de R5/R5b y R11: inicial corto VAGA con pregunta genérica y
todos los criterios; inicial suficiente o seguimiento NO_EVALUADA, sin pregunta.
Se prueban fallos y timeouts tanto en el primer seguimiento como en el segundo,
incluidas respuestas cortas. Vacíos se rechazan antes de evaluar, aunque haya
texto inicial y turnos anteriores. Se exigen una sola llamada, errores saneados,
metadatos conservados y límites de timeout exactos sin esperas reales.

Los clientes Gemini simulados comprueban el contexto v2, salida `pregunta` y
prompt v2, conservando los controles de timeout, reintentos desactivados y secretos.
Una conversación con seguimiento y otro ítem FINAL se envía íntegra, y su parte
actual coincide con `texto_evaluado`. El script sigue con 14 casos simulados;
las dos conversaciones adicionales se incorporarán en fase 6. No se llama a
la API real ni se produce un reporte real de Gemini.

Las pruebas HTTP mantienen temporalmente el flujo anterior mediante una
adaptación aislada de las acciones; la aceptación de escenarios v2 con turnos,
el turno genérico sin reevaluación y la interfaz quedan para fases posteriores.
No se omiten escenarios del motor/instrumentos ni se relajan límites SQL.
Las bases persistentes del usuario no se recrean ni modifican.

Comprobación focalizada previa: **459 passed, 2 warnings** en 431.09 segundos
para evaluador puro, Gemini simulado, registro y consultas. Luego se incorporan
15 comprobaciones adicionales del resultado v1 rechazado, respaldo de salida
inválida con texto corto y llamada Gemini simulada para texto corto, incluidas
en la suite completa de cierre.

Resultado de cierre de fase 2: `uv run pytest -q`, **836 passed, 2 warnings**
en 552.67 segundos. La suite pasa de 764 a 836 pruebas y conserva E1–E17,
I1–I14, el contrato `/acciones/responder-registro` y los presupuestos SQL vigentes.
Los dos avisos son las deprecaciones conocidas de Starlette/httpx y Google en
Python 3.14. Se detiene la implementación tras fase 2; la siguiente fase elimina
la adaptación anterior y conecta acciones, consultas y escenarios a los turnos v2.

## Registro v2: fase 3

Las acciones usan directamente la evaluación v2. Enviar el inicial y responder
seguimiento tienen dos transacciones independientes, con evaluación sin sesión
ni conexión entre ellas. Las consultas recuperan la conversación completa y los
borradores de los turnos; el historial técnico usa `numero` y `pregunta_generada`.
El endpoint previo del motor `/acciones/responder-registro` mantiene su contrato.

`tests/test_registro.py` reemplaza los escenarios v1 autorizados por R1–R13,
R13d y R14–R16 de v2. Comprueba respaldo corto que llama primero al falso,
respuesta genérica sin reevaluación, texto corto ADECUADO por el falso, objetivos
de criterios faltantes, dos seguimientos y tres evaluaciones como máximo,
continuar con pregunta conservada, contexto completo de otros ítems FINAL,
fallos iniciales y de seguimiento, atención oculta y borradores recuperables.
Texto inicial, clasificación inicial y primeras evaluaciones no se sobrescriben
al responder turnos; editar FINAL conserva auditoría y métricas, sin eventos nuevos.

La concurrencia cubre respuesta ausente, BORRADOR y seguimiento pendiente,
con borradores y envíos paralelos y fecha simulada idéntica. Exige 409,
conservación del cambio paralelo y descarte de evaluación/turnos/eventos del
envío rechazado. Las comprobaciones de pool y sesiones se ejecutan desde el
evaluador tanto para el inicial como para seguimiento. Se conserva la comparación
condicional entre relectura y escritura y la reconstrucción del contexto de
consultas para incluir eventos guardados durante la evaluación.

`tests/test_registro_v2.py` añade rechazo de reescritura mientras hay seguimiento,
orden de edición obligatorio y estricto, turnos inexistentes/no respondidos,
vacíos sin escrituras ni evaluación, borrador vacío, continuar descartando solo
el borrador no enviado, evento único después de un turno enviado, criterios ya
cumplidos, segundo borrador reemplazado en el contexto, edición del turno 2,
preguntas sin respuesta de otros FINAL y concurrencia con reloj fijo. Los fallos
al insertar una nueva pregunta revierten toda la transacción; también se mantiene
la reversión ante errores en evaluación, eventos y desbloqueos.

Los tests existentes de consultas SQL adaptan sus preparaciones y endpoints a
v2, manteniendo todos los límites y casos de crecimiento. La medición de
seguimiento usa de momento el presupuesto de envío (12); la entrada específica
en `LIMITES_SQL` y la ampliación de crecimiento corresponden a fase 5. Se
conservan las comprobaciones existentes de completar sin cambiar su implementación;
la revisión completa de finalización corresponde a fase 4. La interfaz se adapta
en fase 7: servir sus recursos no constituye validación visual de conversaciones.

Antes de la suite completa: **345 passed, 2 warnings** en 398.42 segundos
para registro, consultas, recursos y Gemini simulado; y **170 passed, 1 warning**
en 61.20 segundos para casos adicionales v2 y evaluación pura. No se llaman
servicios reales ni se recrean las bases persistentes del usuario.

Resultado de cierre de fase 3: `uv run pytest -q`, **875 passed, 2 warnings**
en 1155.83 segundos. Son 39 pruebas más que las 836 de fase 2. Se conservan
E1–E17, I1–I14, el contrato previo del motor y los presupuestos SQL vigentes.
No hubo fallos. Los avisos siguen siendo las deprecaciones conocidas de
Starlette/httpx y Google en Python 3.14. Las bases locales conservan tamaño y
fecha de modificación, y no se ejecuta Gemini real. Se detiene tras fase 3;
la siguiente es la revisión de finalización e integración con el motor.

## Registro v2: fase 4

Se revisa la sección 6.8 y se conserva la implementación anterior de completar,
porque ya exige todos los ítems obligatorios en FINAL antes de escribir. Las
pruebas existentes siguen comprobando faltantes ordenados, ítems opcionales,
aislamiento entre cuentas y actividades, y finalización sin exigir ADECUADA.
El motor, las reglas, la semilla y los contratos de instrumentos no cambian.

`tests/test_registro_finalizacion_v2.py` añade 11 comprobaciones de integración:

- R13b con REG-HAB-3 en borrador inicial, seguimiento genérico, turno 1 o turno 2
  pendiente, incluidos borradores de seguimiento. El 409 devuelve únicamente
  ese ítem, ejecuta solo SELECT, no evalúa y deja intacta toda la base temporal.
  Después de finalizarlo se registran COMPLETA_ACTIVIDAD y COMPLETA_BLOQUE(REG),
  sin modificar respuestas, turnos ni evaluaciones.
- Completar después del segundo turno VAGO, de fallo o atención en ese turno,
  o de omitirlo tras responder el primero. Se acepta FINAL conservando la
  clasificación inicial VAGA y la conversación completa.
- R13c con seguimientos genéricos y del falso: los pasos pendientes no generan
  eventos; cada FINAL registra una reflexión de referencia nula y el tercero
  obtiene LOG-PENSADOR mediante R-LOG-PENSADOR. Las reglas y condiciones siguen
  intactas y rehacer no agrega reflexiones ni desbloqueos.
- Rehacer conserva posición, respuestas iniciales, los dos turnos, preguntas
  omitidas y auditoría. Editar posteriormente el inicial y ambos turnos conserva
  criterios, fechas y métricas originales, sin llamar al evaluador ni duplicar
  eventos. COMPLETA_BLOQUE se emite una vez, incluso después de repetir completar.
- Un error SQL después de insertar los eventos de completar revierte progreso
  y eventos, conserva respuestas/turnos/auditoría y permite completar al reintentar.

Comprobación focalizada: `uv run pytest -q tests/test_registro_finalizacion_v2.py
tests/test_registro.py -k 'completar or rehacer or r13c or r12_tres'`, **29 passed,
150 deselected, 1 warning** en 62.02 segundos. La simulación de fallo SQL se
inyecta después de ejecutar el lote completo de eventos del motor.

Se usan SQLite temporal y el evaluador falso. No se ejecuta la API real ni se
recrean bases persistentes. La validación visual de la interfaz v2 sigue pendiente.
La siguiente fase amplía los presupuestos SQL y las pruebas de crecimiento.

Resultado de cierre de fase 4: `uv run pytest -q`, **886 passed, 2 warnings**
en 1135.36 segundos (18:55). Son 11 pruebas más que las 875 de fase 3. Se
conservan E1–E17, I1–I14 y los presupuestos SQL anteriores, incluido completar
registro con un máximo de 15 consultas en primera finalización, rehacer y
rechazo por faltantes. Los avisos son las deprecaciones conocidas de
Starlette/httpx y Google en Python 3.14. Se detiene la implementación tras fase 4.

## Registro v2: fase 5

Se incorpora el presupuesto independiente `responder_seguimiento_registro: 12`
en `tests/test_consultas.py`. Los seguimientos antes medidos provisionalmente
como envío pasan a usar esa entrada. Se conservan todos los límites anteriores.
El contador suma ambas transacciones de cada petición y se comprueba que no
crece durante la evaluación ni hay conexión tomada, para inicial y turnos 1 y 2.

Las mediciones amplían la cobertura a ambos turnos y sus borradores, nueve
evaluaciones, tres conversaciones completas, finalización y rehacer con dos
turnos por ítem, y rechazo al completar con el segundo turno pendiente. Cubren
resultados ADECUADA/VAGA, atención, fallo, timeout, salida inválida, turno genérico
sin nueva evaluación y edición de los turnos finales sin nuevas evaluaciones.

| Petición | Máximo observado en las pruebas focalizadas | Límite |
|---|---:|---:|
| Guardar posición | 4 | 4 |
| Guardar borrador | 4 | 6 |
| Enviar | 11 | 12 |
| Responder seguimiento | 11 | 12 |
| Continuar sin responder | 7 | 8 |
| Ítems de registro | 0 | 1 |
| Estado del registro | 2 | 4 |
| Evaluaciones (hasta nueve) | 2 | 4 |
| Completar REG-ACT08 | 8 | 15 |

La prueba de crecimiento pasa de 8 a 19 recorridos, conservando los anteriores.
En las dos bases temporales la cantidad y distribución por tipo de SQL coinciden
exactamente, con y sin 100 reglas reflexivas adicionales y 500 eventos extra.
Se comprueba el estado antes y después de la acción, ambos turnos, máximo
alcanzado todavía VAGA, fallo/timeout/salida inválida, atención, seguimiento
genérico y edición de los dos turnos. Los recorridos nuevos incluyen otras dos
conversaciones FINAL con dos turnos cada una y, cuando corresponde, un borrador.

El estado mantiene **2 = 2** consultas. Enviar/responder mantiene entre **5 = 5**
y **11 = 11**, según el recorrido. Si la acción registra reflexión, las 100
reglas se evalúan una vez cada una y los desbloqueos se insertan en un solo lote;
en los otros recorridos no se evalúan ni generan desbloqueos sintéticos. Las
peticiones medidas no consultan de nuevo las definiciones de reglas/condiciones.
El turno genérico y las ediciones mantienen el contador de llamadas al evaluador.

Comprobaciones focalizadas:

- `uv run pytest -q -s tests/test_consultas.py -k 'registro'`: **80 passed,
  73 deselected, 1 warning** en 203.06 segundos. Incluye los 19 recorridos de
  crecimiento. Esta ejecución precede a cuatro casos adicionales de auditoría
  y completar que se verifican en la tercera ejecución.
- Los cuatro tests de seguimiento con otras conversaciones, pregunta genérica,
  edición de turno y contador de ambas transacciones: **19 passed, 1 warning**
  en 39.75 segundos. El filtro anterior no selecciona sus nombres; se ejecutan
  expresamente por sus identificadores completos.
- `uv run pytest -q -s tests/test_consultas.py -k 'limite_sql_completar_registro
  or limite_sql_evaluaciones_registro'`: **10 passed, 147 deselected, 1 warning**
  en 23.82 segundos. Incluye nueve evaluaciones y completar/rehacer con turnos.

No se modifica código de producción ni se relajan presupuestos. Se usa el
evaluador falso y SQLite temporal; las bases persistentes se conservan y no se
llama a Gemini real. La interfaz de conversaciones sigue pendiente. La fase 6
preparará el adaptador/script de 16 casos con cliente simulado; la ejecución
real requerirá una petición explícita.

Resultado de cierre de fase 5: `uv run pytest -q`, **930 passed, 2 warnings**
en 1303.33 segundos (21:43). Se pasa de 886 a 930 pruebas, conservando E1–E17,
I1–I14, los contratos anteriores y todos los límites SQL. Los dos avisos son
las deprecaciones conocidas de Starlette/httpx y Google en Python 3.14.
Se detiene tras fase 5; quedan el adaptador/script v2, la interfaz y el cierre.

## Registro v2: fase 6

El adaptador existente usa prompt v2 y evalúa la conversación completa con salida
estructurada, temperatura 0.2, timeout, latencia y un solo intento. La configuración
del proveedor y sus errores seguros se conservan. Se amplía el script a los 16
casos oficiales: caso 7 con solo C2 faltante, caso 12 corregido y caso 16 con
«Voy a esforzarme más.» como inicial. Los primeros 14 textos siguen intactos.

Los casos 15 y 16 responden a la pregunta recibida del modelo con el texto de su
turno 1. Se evalúa toda la conversación y se mantienen los criterios faltantes de
la evaluación anterior. El caso 16 permite observar la segunda pregunta; no se
inventa una respuesta al turno 2. Hay hasta 18 llamadas y la pausa se aplica entre
todas ellas. Si el inicial finaliza, el turno no se ejecuta; si se genera una
pregunta genérica por respaldo, su respuesta no necesita otra evaluación.

El script usa las definiciones oficiales en SQLite en memoria, incluido el mínimo
para el respaldo por longitud; libera las conexiones y destruye ese motor antes
de evaluar. No persiste respuestas, turnos, evaluaciones o eventos ni consulta
las bases locales. El reporte distingue pasos con y sin evaluación, incluye
preguntas respondidas y generadas y sanea errores, HTML y claves literales o
codificadas. Los reportes simulados se guardan en directorios temporales.

Comprobación focalizada: `uv run pytest -q tests/test_evaluador_gemini.py
tests/test_evaluador_respuestas.py`, **221 passed, 2 warnings** en 8.90 segundos.
Se agregan 17 casos al conjunto de pruebas, además de adaptar los existentes:

- Correspondencia literal del prompt y de los textos/expectativas con §10.
- Preguntas recibidas, conversación completa, criterios restantes y segunda
  pregunta distinta con resultados simulados de los casos 15 y 16.
- Inicial FINAL por adecuación o atención, y respaldo genérico sin nueva llamada.
- Fallo, timeout y salida inconsistente de ambos casos de seguimiento, sin
  reintentos ni interrupción del lote; criterio satisfecho que reaparece.
- Transporte HTTP simulado del SDK para inicial y ambos turnos, con configuración
  y JSON reales del cliente instalado, sin acceder a servicios externos.
- Pausas entre llamadas, saneamiento literal/codificado de secretos, formato del
  reporte, CLI simulada, cierre del cliente y entorno del servidor intacto.
- Ninguna conexión tomada ni SQL durante la evaluación, y ninguna escritura de
  respuestas, turnos, evaluaciones o eventos en la preparación del script.

La prueba semántica de Gemini real continúa pendiente: los resultados simulados
no certifican la calidad de sus preguntas ni las clasificaciones de los textos.
No se ejecuta una llamada real ni se genera `docs/evaluacion_gemini.md` en esta fase.
La interfaz sigue siendo v1 y su adaptación corresponde a la fase 7.

Resultado de cierre de fase 6: `uv run pytest -q`, **947 passed, 2 warnings**
en 1301.42 segundos (21:41). Son 17 casos más que los 930 de fase 5. Se conservan
E1–E17, I1–I14, los escenarios de registro, los contratos y todos los presupuestos
SQL. Los avisos siguen siendo las deprecaciones de Starlette/httpx y Google en
Python 3.14. Las bases persistentes conservan sus tamaños y fechas de modificación.
Se detiene tras fase 6; siguen pendientes la interfaz, el cierre documental y
la ejecución/revisión real de Gemini bajo petición explícita.

## Registro v2: fase 7

Se adapta `/demo/registro` a la conversación v2: inicial inmutable durante los
seguimientos, hasta dos preguntas en un hilo, campo nuevo para responder,
borradores recuperables y **Prefiero seguir**. En FINAL se puede elegir editar
el inicial o un turno respondido sin nueva evaluación. El detalle técnico muestra
los números v2 y permite revisar preguntas y conversación evaluada.

`uv run pytest -q tests/test_demo_registro.py`: **2 passed, 1 warning** en 4.33
segundos. La página y recursos no consultan SQL, escriben datos ni evalúan textos;
el reinicio mantiene el proveedor/configuración y permite comenzar desde cero.

Se ejecuta `tests/validar_registro_ui.cjs` con el Node/Playwright del entorno de
comprobación, contra `tests/servidor_registro_ui.py --puerto 8790`: evaluador falso
impuesto y base SQLite temporal. Este puerto evita actuar sobre el servidor del
usuario. Las peticiones del navegador se restringen al origen local.

Resultado del recorrido: **257 peticiones de interfaz, 0 errores JavaScript** y
ningún endpoint auxiliar nuevo. Se comprueban:

- Reintento de carga fallida, explicación, navegación de teclado, fecha simulada,
  tres íconos y posición recuperada al recargar.
- Borrador inicial y de ambos turnos; campos nuevos vacíos tras enviar; inicial
  intacto durante preguntas; máximo de dos turnos aun con resultado VAGO.
- Edición individual del inicial y de ambos turnos FINAL sin cambiar la auditoría;
  buffers locales distintos por mensaje y cuenta.
- Respaldo corto con pregunta genérica y respuesta sin reevaluar; inicial corto
  adecuado por el falso; LOG-PENSADOR, marcar novedades y completar/recargar.
- **Prefiero seguir** en el primer y segundo turno, preservando respuestas previas
  y pregunta omitida, sin conservar su borrador ni ofrecer editarla.
- Aislamiento entre Ana, Luis y Rosa; auditoría plegada sin consulta anticipada
  y respuesta técnica tardía descartada al cambiar de cuenta.
- Conflicto 409 simulado durante un seguimiento, recuperación del servidor y texto
  local preservado sin reenvío. El control de concurrencia real se mantiene en R14.
- Petición pausada para observar espera y controles bloqueados; lectura fallida
  después de una edición confirmada, recuperable con Actualizar sin otra evaluación.
- Texto HTML literal sin ejecución; espacios no enviables; fallo/atención del
  falso sin clasificación ni marcas técnicas en la vista del estudiante.
- Interacción móvil táctil a 390 y 360 px, recarga del segundo borrador y ausencia
  de desbordamiento horizontal; completar, cancelar reinicio y confirmarlo.

Evidencias actuales en [registro-v2](evidencias/registro-v2/comprobaciones.json):
explicación de escritorio/móvil, segundo turno de escritorio/móvil, espera,
detalle técnico y finalización móvil. Se inspeccionan visualmente las capturas
del segundo turno en ambos tamaños, detalle técnico y finalización móvil; el hilo
y los controles se leen sin recortes.
Las evidencias v1 anteriores se conservan como historial.

Estas comprobaciones corresponden al evaluador falso. No se llama a Gemini real
ni se modifica `.env` o una base persistente. El reporte real y la calidad semántica
siguen pendientes de una petición explícita. La fase siguiente es el cierre.

Resultado de cierre de fase 7: `uv run pytest -q`, **947 passed, 2 warnings**
en 1283.01 segundos (21:23). Se mantienen los 947 tests de fase 6: esta fase adapta
la comprobación real del navegador, sin cambiar escenarios ni añadir tests de
implementación estática. Pasan E1–E17, I1–I14, los escenarios de registro, contratos
anteriores y límites SQL. Los avisos son los conocidos de Starlette/httpx y Google
en Python 3.14. Las bases persistentes conservan sus tamaños y fechas. Se deja
disponible la demo temporal con falso en el puerto 8790 para visualizarla.
Se detiene tras fase 7; quedan el cierre de fase 8 y la evaluación real autorizada
por separado.

## Registro v2: fase 8, cierre consolidado

La referencia vigente es la versión 2 de `spec-demo-registro-gemini.md`.
Las ocho fases conservan REG-ACT08, su semilla, JSON y caché, y reemplazan la
reescritura de v1 por un inicial y hasta dos turnos. Siempre se evalúa primero
el envío no vacío; la longitud es el respaldo ante fallo. La clasificación
inicial y evaluaciones anteriores permanecen inmutables. El motor, instrumentos,
contratos previos y resultados E1–E17/I1–I14 se conservan.

### Mapa de cobertura vigente

| Cobertura | Evidencia |
|---|---|
| E1–E17, invariantes y contratos anteriores | `tests/test_escenarios.py`, `tests/test_invariantes.py` y pruebas de acciones/consultas originales. |
| I1–I14, cálculo e integración de instrumentos | `tests/test_instrumentos.py` y pruebas de resultados, catálogos y consultas de instrumentos. |
| R1–R3: disponibilidad, posición y borrador | `tests/test_registro.py`: estado inicial, posición recuperable, reemplazo de borrador sin evaluar/eventos. |
| R4, R5, R5b, R5c: evaluar primero y respaldo | `tests/test_registro.py` y `tests/test_evaluador_respuestas.py`: texto corto evaluado, fallo corto, turno genérico sin reevaluar, conversación completa de seguimiento. |
| R6–R10: criterios restantes y conversaciones | `tests/test_registro.py`: C2 objetivo, máximo dos turnos, pregunta omitida, adecuada al inicial y contexto de otros FINAL de la misma cuenta. |
| R11–R13: fallos, atención y borradores de turno | Pruebas de registro y evaluación pura: límites exactos, timeout, resultados inconsistentes, error seguro, atención solo en auditoría y borradores retomables. |
| R13b, R13c, R13d: completar, reflexivas y edición | `tests/test_registro_finalizacion_v2.py`, `tests/test_registro.py` y `tests/test_registro_v2.py`: 409 sin escrituras, LOG-PENSADOR por regla original, rehacer/editar conservando auditoría y clasificación inicial. |
| R14–R16: concurrencia, evaluación sin conexión y aislamiento | Pruebas de registro/v2: respuesta existente o inexistente, borrador durante evaluación, fecha/reloj iguales, actualización monotónica, conflicto completo y relectura de contexto entre transacciones. |
| R17, estructura y caché | `tests/test_registro.py`: JSON inválido, reconstrucción tras reinicio, rollback conservando caché, restricciones SQL y rechazo de v1 con versión 4, versiones 1–3 y futura 5. |
| Adaptador y script v2 sin red | `tests/test_evaluador_gemini.py`: clientes y transporte SDK simulados, esquema, configuración, latencia, timeout, ausencia de reintentos, saneamiento, casos 15/16, CLI y conexiones liberadas antes de evaluar. |
| Página y recorrido visual | `tests/test_demo_registro.py` y `tests/validar_registro_ui.cjs`: recursos sin SQL/escrituras, conversaciones, borradores, recarga, edición, aislamiento, errores y móvil. |

Las pruebas de registro y SQL usan el falso impuesto por fixtures y SQLite
temporal; las pruebas del adaptador sustituyen el cliente o transporte y bloquean
la red. Ninguna prueba de pytest usa la API real. Los fallos SQL revierten respuesta,
turnos, evaluaciones, eventos y desbloqueos. Los envíos suman ambas transacciones
y no hay sesiones, transacciones ni conexiones tomadas durante la evaluación.

### Presupuestos SQL e igualdad con crecimiento

| Petición | Máximo observado | Presupuesto |
|---|---:|---:|
| Posición | 4 | 4 |
| Borrador inicial o de turno | 4 | 6 |
| Enviar inicial | 11 | 12 |
| Responder seguimiento | 11 | 12 |
| Continuar sin responder | 7 | 8 |
| Ítems | 0 | 1 |
| Estado del registro | 2 | 4 |
| Auditoría de evaluaciones | 2 | 4 |
| Completar y rehacer REG-ACT08 | 8 | 15 |

Se conservan los 19 recorridos de crecimiento de fase 5. La cantidad y distribución
por tipo de consulta son idénticas con y sin 100 reglas de RESPUESTA_REFLEXIVA y
500 eventos extra. Se incluyen ambos turnos, otros FINAL completos, resultados
adecuados/vagos, atención, fallo, timeout, salida inválida, turno genérico y edición.
Estado mantiene 2 = 2; enviar/responder, entre 5 = 5 y 11 = 11, según recorrido.
Las reglas sintéticas solo existen en SQLite temporal; se evalúan una vez y sus
desbloqueos se insertan en lote. Las definiciones no se releen en las peticiones.

### Interfaz con evaluador falso

Se conservan las evidencias de fase 7, con escritorio 1440×1000 y móvil táctil
390/360×844: [comprobaciones](evidencias/registro-v2/comprobaciones.json), 257
peticiones y cero errores JavaScript. La petición de espera se pausa expresamente
para poder observarla; los errores de lectura y 409 del navegador se simulan, y
la reversión/concurrencia reales se comprueban en pytest. Se revisan las capturas
de conversación de segundo turno, detalle técnico y finalización móvil.

La instancia temporal 8790 fuerza el falso; el servidor habitual 8000 respeta
`.env` y las variables de su proceso. `LLM` es un origen compartido: por sí solo
no identifica Gemini. En las evaluaciones del falso el modelo es nulo y la latencia
puede ser cero. Las marcas de prueba entre corchetes son texto ficticio escrito
para activar el falso; la interfaz no añade clasificación ni marcas de auditoría
a las respuestas del estudiante.

### Evaluación real autorizada y revisión semántica

El 2026-10-01 el usuario autoriza expresamente las llamadas reales. Se ejecuta una
vez `uv run python -m scripts.evaluar_gemini --pausa 5`, separado de pytest. El
[reporte completo](evaluacion_gemini.md) contiene salidas y revisión manual. Se usa
el modelo configurado `gemini-3.1-flash-lite`, prompt v2, temperatura 0.2 y timeout
de 10 segundos, sin modificar `.env` ni repetir los fallos. El script prepara
definiciones en memoria y libera las conexiones antes de llamar; no lee ni escribe
respuestas de la demo del usuario.

Resultado: 16 iniciales y un seguimiento real, **17 llamadas**, 18 filas de reporte,
**12 resultados LLM válidos y 5 respaldos** (3 timeout y 2 otros fallos).
El inicial del caso 15 finaliza NO_EVALUADA por respaldo; su seguimiento no se
evalúa ni se atribuye al LLM. Latencia 1643–10122 ms, mediana 2967 ms; las ocho
preguntas válidas tienen 21–28 palabras.

Las 12 clasificaciones válidas coinciden con lo esperado, incluida atención en
14. Se confirman el texto corregido de 12 y las dos preguntas distintas de 16,
ambas con C1/C2. La aceptación semántica es **parcial**: 7 y 11 devuelven C1/C2
cuando debe faltar solo C2; 1 elogia la elección; 2, 5, 6, 8 y 15 no obtienen
salida válida del modelo. El respaldo de esos casos es correcto según §6.3.

Se completa la ejecución y revisión real solicitada, sin presentarla como 16/16
casos aprobados. Estas observaciones de calidad se conservan como resultados de
la prueba, sin cambiar criterios, escenarios o el prompt especificado. Mejorar
esa calidad requiere una iteración acordada de instrucciones y otra medición;
no forma parte de un reintento automático ni se declara resuelta.

### Resultado de cierre

- `uv run pytest -q`: **947 passed, 2 warnings** en 1038.05 segundos (17:18).
  Los avisos son las deprecaciones conocidas de Starlette/httpx y Google en
  Python 3.14. La suite automática se mantiene sin llamadas reales.
- `uv lock --check`: correcto, 43 paquetes resueltos sin modificar dependencias.
- Navegador con falso: 257 peticiones, cero errores JavaScript, escritorio y
  móvil verificados en fase 7; no se cambió la interfaz después de esas pruebas.
- Ejecución real separada: 17 llamadas, 12 resultados válidos y 5 respaldos;
  revisión de los 16 casos y de los pasos de seguimiento efectivamente realizados.
- Reporte saneado: se verifica que no contiene la clave literal, escapada en HTML
  ni codificada en URL. Los textos enviados son los casos ficticios del script.

Se conservan E1–E17, I1–I14 y R1–R17 con sus ampliaciones, restricciones, JSON,
caché, concurrencia, reversión, aislamiento y presupuestos SQL. No se cambian
criterios, escenarios, datos semilla, contratos, configuración ni código para
dar por aprobadas discrepancias del modelo. No se escriben respuestas de prueba
en la demo persistente del usuario.

Las ocho fases de implementación, documentación y ejecución/revisión real están
terminadas. La calidad semántica del modelo tiene observaciones abiertas en el
reporte; esa aceptación parcial se mantiene visible y requiere una iteración
acordada si se quiere corregir y volver a medir. Autenticación, alertas a la
orientadora, otras tareas LLM y reintentos automáticos siguen fuera de alcance.
