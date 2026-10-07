# Decisiones de la iteración 1

Registro de decisiones que afectan a ambos repos. Las internas de cada repo van en `ov_backend/docs/decisiones.md` y `ov_frontend/docs/student-experience/plan.md`.

Formato de cada entrada: fecha, fase, decisión, motivo y archivos afectados.

## Decisiones tomadas antes de implementar

Ver la sección 8 de `spec-iteracion-1.md`.

## F0. Línea base

### 2026-10-07 · Verificación inicial, sin cambios de código

**Decisión y motivo.** Ejecutar únicamente F0 y registrar las fallas previas, sin
corregir la implementación ni adaptar pruebas. La sección 9 de la especificación
permite cerrar esta fase con fallas previas documentadas. Se leyeron completos,
en este orden, los `AGENTS.md` de ambos repos, el plan de iteraciones y la
especificación de la iteración 1.

**Archivos afectados.** Solo este documento. Se conservan los cambios previos en
los dos `AGENTS.md` y los demás documentos de iteraciones que ya estaban sin
versionar. No se modifican código, pruebas, manifiestos ni archivos de bloqueo.
No se agregan dependencias, no se ejecuta Gemini y no se hace push.

**Preparación.** `uv sync` terminó correctamente: 43 paquetes resueltos y 42
verificados. `npm install` terminó correctamente, con las dependencias al día.
Herramientas: Python 3.14.7, uv 0.11.16, Node.js 24.19.0 y npm 12.0.2.

**Reglas compartidas.** Las secciones que comienzan con
`## Reglas compartidas entre ov_backend y ov_frontend` son idénticas mediante
comparación exacta, incluidos espacios y saltos de línea: 3191 caracteres cada
una. No fue necesario editarlas.

**Ramas y commits.** El backend ya estaba en `iteracion-1`. En el frontend se
creó `iteracion-1` desde la rama existente `iteration-1`, conservando el estado
de trabajo. El commit del backend incluye únicamente este registro; el del
frontend es vacío para dejar constancia de F0 sin agregar archivos ni incluir
los cambios previos del usuario.

| Repo | Comando | Resultado |
|---|---|---|
| Backend | `uv run pytest -q`, con `EVALUADOR=falso` y `SEMILLA=demo` | 947 pruebas pasan, 0 fallas, 2 advertencias; 889,05 segundos (14 min 49 s), con temporales propios. |
| Frontend | `npm run build` | Correcto; 2820 módulos transformados. |
| Frontend | `npm run lint` | Correcto, salida 0; sin diagnósticos emitidos. |
| Frontend | `npm test` | 292 pruebas: 276 pasan, 16 fallan; 0 canceladas, omitidas o pendientes. 12 archivos de pruebas; 0 suites declaradas. |

**Incidencias del entorno del backend.** El primer intento dentro del sandbox
falló antes de ejecutar pytest con `uv trampoline failed to canonicalize script
path`. Fuera del sandbox, pytest encontró `PermissionError: [WinError 5]` al
acceder a `C:\Users\mauri\AppData\Local\Temp\pytest-of-mauri`, además de avisos
de permisos de la caché existente. Se diagnosticó el primer error con
`uv run pytest -q -x --tb=short` y se interrumpió la ejecución completa afectada.
La repetición usa un directorio temporal propio y otra caché, solo mediante
variables de entorno del proceso; no cambia la configuración del proyecto:

```powershell
$env:EVALUADOR = 'falso'
$env:SEMILLA = 'demo'
$env:TEMP = Join-Path $env:LOCALAPPDATA 'Temp\ov-f0-20261007'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$env:PYTEST_ADDOPTS = '-o cache_dir=' + ($env:TEMP -replace '\\','/') + '/cache'
uv run pytest -q
```

La suite completa terminó con salida 0. Sus dos advertencias son de
deprecación: `httpx` en `starlette.testclient` y `_UnionGenericAlias` en
`google.genai.types`. No se cambian dependencias para resolverlas en F0.

**Advertencia previa del build.** Vite avisa que el JavaScript principal supera
500 kB: 1628,19 kB, o 477,00 kB con gzip. El aviso no impide compilar y no se
aplican cambios para resolverlo en F0.

**Fallas previas del frontend.** Dos ejecuciones de `npm test` terminaron con
las mismas 16 fallas. Todas pertenecen a `tests/adventure-rendering.test.mjs`:

| Línea del test | Nombre reportado |
|---|---|
| 731 | real access conditions lock successive missions and expose the city gate without changing review mode |
| 1504 | immersive submission preserves validation, drafts, versions and the keep action |
| 1571 | immersive questions preserve attempts, hints, revelation, retry and fresh revision behavior |
| 1699 | immersive finish shows saved sheets, narrative rewards and the prompted journal action |
| 1776 | follow-up service waits 700ms, respects both text thresholds and never asks a third turn |
| 1855 | first text submission saves version one before follow-up; edits and matrices use the normal form |
| 1881 | follow-up accepts two replies, caps the field at available space and saves one condensed version |
| 1915 | omitting all turns preserves version one, while a long reply ends follow-up after one turn |
| 1932 | no question, failure, timeout or fewer than 40 free characters advances silently with the original |
| 1951 | interrupted follow-up recovers only answered turns and loads the condensed form without duplicate versions |
| 2000 | follow-up requires 40 free characters and stops before a second question that cannot fit |
| 2033 | leaving during evaluation never stores a late question and recovery preserves the replied turn |
| 2326 | every supplied mission node renders, including matrices, slides, questions and instrument items |
| 2621 | phase 8 path sequence respects both completion records without changing catalog or real thresholds |
| 2658 | phase 8 direct links open blocked details instead of starting unavailable players |
| 3229 | discovery atlas covers existing IDs, symmetric relations and gated affinity |

Entre los diagnósticos observados están diferencias entre `locked` y
`completed`, el texto esperado «Salir de la actividad» frente a «Salir de la
misión», expectativas de preguntas de seguimiento y la relación
`psychology:psychologist`. Son síntomas reportados por las pruebas, no un
diagnóstico de causa raíz. No se abrieron ni modificaron las carpetas de los
portales ni `tests/counselor-portal.test.mjs`; sus suites se ejecutaron como
permite el `AGENTS.md` del frontend.

**Cierre y pendientes.** F0 completa, con las fallas previas documentadas según
el criterio de la especificación. F1–F7 quedan sin ejecutar. Las 16 fallas
previas del frontend requieren una tarea posterior de diagnóstico; no se
corrigen ni se cambian sus resultados esperados en F0.

## F1

- 2026-10-07: se autoriza adaptar los mensajes de esquema incompatible al nombre real del archivo, conservando rechazo y base intacta; ver [Iteración 1 · F1](../decisiones.md#iteración-1--f1).
- 2026-10-07: `plataforma` se selecciona pero su carga se rechaza antes de crear o reiniciar tablas en F1; F2 sustituye el rechazo por la carga real y elimina su prueba; ver [Iteración 1 · F1](../decisiones.md#iteración-1--f1).

**Cierre · 2026-10-07.** F1 completa en el backend: selección de semilla y base,
esquema 5, contrato `CoincidenciaPublica.codigo`, adaptaciones autorizadas y
README. Las nueve pruebas existentes adaptadas y su autorización en §4.2
se detallan en [Decisiones](../decisiones.md#iteración-1--f1).

| Repo | Validación de F1 | Resultado |
|---|---|---|
| Backend | `uv run pytest -q`, con `SEMILLA=demo`, `EVALUADOR=falso` y temporales propios | 969 pruebas pasan, 0 fallas, 2 advertencias de deprecación; 901,12 segundos (15 min 1 s). |
| Frontend | Sin cambios en esta fase; no se reejecutan sus pruebas | Se conserva la línea base de F0: 276 pasan y 16 fallan; build y lint pasan. |

No se agregan dependencias ni se ejecutan llamadas reales a Gemini. Las 45
tablas y la semántica de la demo se conservan. F2–F7 quedan pendientes,
incluida la sustitución del rechazo temporal por la semilla `plataforma` real.
Las 16 fallas previas del frontend siguen pendientes de diagnóstico.

## F2

- 2026-10-07: bases F1 de esquema 5 con CHECK antiguo se rechazan antes de cargar datos o caché, con el archivo real, sin modificación ni migración; ver [Iteración 1 · F2](../decisiones.md#iteración-1--f2).
- 2026-10-07: las relaciones de carreras incorporan sus ocupaciones propias y excluyen `drone-operator`, según §4.3.8, sin cambiar el catálogo local; ver [Iteración 1 · F2](../decisiones.md#iteración-1--f2).
- 2026-10-07: `11-3012.00` existe en el Excel y se usa para `public-administrator`; ver [Iteración 1 · F2](../decisiones.md#iteración-1--f2).

**Cierre · 2026-10-07.** F2 completa en el backend: semilla plataforma,
evaluador, tres eventos nuevos y validación de los CHECK sin migración.
Se verifican exactamente P1–P16, con una prueba principal por escenario,
y 21 casos complementarios, incluida la guardia que prohíbe llamar a
`cargar_definiciones_instrumentos` al arrancar o reiniciar plataforma.

| Repo | Validación de F2 | Resultado |
|---|---|---|
| Backend | `uv run pytest -q`, con `SEMILLA=demo`, `EVALUADOR=falso` y temporales propios | 1003 pruebas pasan, 0 fallas, 2 advertencias de deprecación; 654,01 segundos (10 min 54 s). |
| Frontend | Sin cambios en esta fase; no se reejecutan sus pruebas | Se conserva la línea base de F0: 276 pasan y 16 fallan; build y lint pasan. |

Se elimina únicamente la prueba temporal de F1, con sus tres casos, según
la autorización previa; no se adaptan otras expectativas existentes. Las
decisiones, pruebas y resultados están en [Decisiones](../decisiones.md#iteración-1--f2).
No se agregan dependencias ni endpoints ni se llama a Gemini. F3–F7 y el
diagnóstico de las 16 fallas previas del frontend quedan pendientes.

## F3

- 2026-10-07: se exportan los ocho fixtures de §4.5 a `ov_frontend/tests/fixtures/servidor`, desde una base temporal plataforma, con evaluador falso y fecha fija; ver [Iteración 1 · F3](../decisiones.md#iteración-1--f3).
- 2026-10-07: el fixture de no vistos se toma tras P7 y antes de Mara, según el prerrequisito de P12; se verifica el marcado y luego se captura P10. Los JSON son respuestas de la API sin metadatos añadidos; ver [Iteración 1 · F3](../decisiones.md#iteración-1--f3).

**Cierre · 2026-10-07.** F3 completa: se creó el script de §4.5 y se ejecutó
con `--destino C:/Users/mauri/Documents/GitHub/ov_frontend/tests/fixtures/servidor`.
Los ocho archivos se generan desde respuestas de la API, y las tres pruebas
del exportador verifican el contrato, aislamiento, errores y regeneración.

| Repo | Validación de F3 | Resultado |
|---|---|---|
| Backend | `uv run pytest -q`, con `SEMILLA=demo`, `EVALUADOR=falso` y temporales propios | 1006 pruebas pasan, 0 fallas, 2 advertencias de deprecación; 774,55 segundos (12 min 54 s). |
| Frontend | `npm run build` y `npm run lint` | Ambos pasan; build conserva el aviso previo de chunks mayores de 500 kB. |
| Frontend | `npm test` | 292 pruebas: 276 pasan, las mismas 16 fallas previas de F0; 18,86 segundos. |

Los nombres y líneas de las fallas coinciden con la tabla de F0; no se
inspeccionan ni modifican las áreas protegidas del front. No cambian contratos,
código del frontend ni pruebas existentes. Se mantienen `iteracion-1` y un
commit de F3 por repo, sin push. Sin nuevas dependencias ni llamadas a Gemini.
F4–F7 y el diagnóstico de las 16 fallas previas del front quedan pendientes.

## F4

- 2026-10-07: por solicitud directa del usuario, se implementan §§5.1–5.7 y 5.11 en el frontend. Los pasos de aceptación 3 y 6 se validan mediante el cierre con actividad, fichas, insignias y nivel de `nuevos_desbloqueos`. La cola de avisos, pasaporte, vista de nivel y marcado como vistos se incorporan en F6; Mara y sus resultados, en F5. Se consultan los requisitos de actividades y fichas exigidos por §§5.5–5.7 al abrir sus detalles; el resto de §5.10 queda para F6.
- La disponibilidad, finalización, fichas, insignias y nivel proceden exclusivamente de la BD en API. Los textos, borradores, respuestas de brújula, comprobaciones, versiones y seguimiento conservan su almacenamiento local. Los límites del prototipo, demostración y contenido pendiente no controlan la disponibilidad API. Ciudad depende de CIUDAD; adicionales, casos y desafíos permanecen bloqueados o excluidos, incluidos accesos por URL.
- Se crean los siete archivos de `src/features/servidor/`: configuración proporcionada por `main.tsx`, contratos Pydantic copiados sin traducciones, cliente fetch, selección de cuenta, almacén externo, acciones y adaptadores puros con solo imports de tipos. No se cambian contratos del backend ni se regeneran los ocho fixtures.
- El usuario escrito se compara con cuentas ESTUDIANTE y el respaldo es Ana. La sesión `ov.cuenta-servidor.v1` queda en `sessionStorage`; las dos copias API usan sus claves `.api` y entradas por cuenta, para conservar borradores sin mezclarlos al cambiar de estudiante. Los ingresos concurrentes se deduplican y los resultados tardíos de una sesión anterior se descartan.
- El único punto que informa finalización es `StudentActivityPlayer.tsx`, función `move`, cuando el siguiente destino es `$fin`. Repetir una informativa vuelve a enviar la acción. Las entregas y el seguimiento guardan sus datos sin aplicar finalización o recompensas locales. No hay finalizaciones desde shell, hidratación ni cierre recuperado.
- El POST precede al cierre y al refresco de la proyección. Ante 409 se muestra el requisito o los ítems faltantes; ante desconexión se ofrece reintento. Si el POST tuvo éxito y falla el refresco, se conserva su respuesta y solo se reintentan las consultas. No se marcan desbloqueos vistos en F4. El reinicio requiere confirmación y está disponible únicamente en API y desarrollo; tras éxito limpia las dos claves API y recarga.

**Recorrido manual · SEMILLA=plataforma, EVALUADOR=falso.** Se usa una base temporal independiente. El puerto 8000 estaba ocupado: backend de prueba en 8001, frontend en 5175 y configuración temporal del proxy. El proxy entregado apunta a 8000. Las respuestas escritas llevan DATO DE PRUEBA F4.

| Paso | Resultado |
|---|---|
| 1 | Reinicio desde el menú e ingreso como est-ana; primera actividad recomendada y resto bloqueado. |
| 2 | La segunda informativa bloqueada muestra «Requisito: completa “El inicio del viaje”». |
| 3 | La bienvenida confirma y muestra actividad siguiente, first-steps e I1 en FinishScreen, según la delimitación aprobada. |
| 4 | La segunda informativa habilita tres fichas más; la mochila conserva cuatro obtenidas tras recargar. |
| 5 | Repetición completa de sus 24 nodos: sin nuevos desbloqueos y conserva COMPLETADA. |
| 6 | act-07 y mission-story confirmadas al llegar a su último diálogo; cierre con I2 y nivel 2 (Recolector de pistas). |
| 7 | Resto del camino, incluida la matriz con sus siete entregas necesarias, confirmado. Cierre final con CIUDAD, I3 y nivel 3 (Cartógrafo de posibilidades). Ciudad abre y Mara muestra su primera interacción pendiente con cinco ítems consultados, sin ejecutar el TIP local. |

**Cierre · 2026-10-07.** F4 completa con la delimitación aprobada; las decisiones de presentación y comprobaciones del navegador se registran en `ov_frontend/docs/student-experience/plan.md`.

| Repo | Validación de F4 | Resultado |
|---|---|---|
| Frontend | `npm run build`, `npm run lint` | Pasan; permanece el aviso previo de chunks mayores de 500 kB. |
| Frontend | Pruebas nuevas de servidor y modo local | 20 casos pasan; fixtures sin modificaciones. |
| Frontend | `npm test` | 312 pruebas: 296 pasan y las mismas 16 fallas de F3; nombres y líneas coinciden con F0. No se cambian expectativas anteriores. |
| Backend | `uv run pytest -q`, con `SEMILLA=demo`, `EVALUADOR=falso`, basetemp y caché propias | 1006 pruebas pasan, 0 fallas, dos advertencias previas de deprecación; 656,83 segundos. |

Las pruebas nuevas cubren cuenta y respaldo, montaje concurrente y respuesta tardía, claves por modo y cuenta, borradores y nodos conservados, hidratación sin espacio, fuente de estado y fichas, cierre y repetición, doble clic, 409, desconexión, reintento de consulta sin otro POST, cierre recuperado, lectura sin adquisición, URL y reinicio exclusivo de desarrollo. El modo local no usa adaptadores ni red. Todos los accesos fetch quedan en el módulo de servidor.

En el backend solo cambia esta sección; no se agregan dependencias, no se llama a Gemini ni se accede a las áreas protegidas del frontend. Un commit F4 por repo en `iteracion-1`, sin push. F5–F7 y el diagnóstico de las 16 fallas previas del frontend quedan pendientes; se detiene el trabajo antes de F5.
