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

## F5

- 2026-10-07: se implementa §5.8 en el frontend con los contratos existentes de respuestas, avance, resultado, coincidencias y carreras. No se modifica el backend ni se regeneran fixtures. El contenido narrativo permanece en el front; las respuestas, disponibilidad, finalización y resultado proceden del servidor. El modo local conserva el TIP y su comportamiento anterior.
- Las interacciones de Mara se construyen con apertura, ítems ordenados y despedida. El primer saludo procede de instrumento_mara.json; las otras interacciones usan tres variantes DATO DE PRUEBA. Cada opción envía su orden mediante responder-items. Las consultas y acciones descartan respuestas tardías al cambiar de cuenta; las consultas simultáneas del resultado se deduplican por sesión. Un 409 con avance indica resultado pendiente; otros 409 y los errores de conexión se muestran como tales.
- Se retoma el primer ítem pendiente, o la despedida si todos están respondidos. Las completadas abren revisión desde el primer ítem. Con resultado vigente la revisión es de solo lectura; un 409 por respuestas fijadas actualiza esa condición. Se bloquean envíos simultáneos. Ante POST confirmado y fallo de refresco, se reintentan solo GET. El único punto de finalización sigue siendo move en StudentActivityPlayer.tsx al llegar a $fin; revisión, resultado, libro e hidratación no completan actividades.
- **Aviso acordado:** el cierre de act-tip-14 muestra «Elena tiene algo que mostrarte» y enlaza el libro cuando resultados_generados incluye TEST-RIASEC. La cola de avisos y marcado como visto quedan para F6, junto con pasaporte y nivel.
- **Sello acordado:** intereses queda listo solo con resultado vigente y la revelación API se registra por cuenta y calculado_en en el almacenamiento de descubrimiento existente, sin alterar revealedPages local. Otra cuenta o un nuevo resultado exige revelar de nuevo. Antes del resultado, el libro consulta el requisito de Ciudad o el avance de Mara; un fallo no se sustituye por resultados de demostración.
- Resultado y libro muestran las dimensiones de codigo_interes en su orden, con nombres y porcentajes. El libro añade carreras recomendadas y ocupaciones via enlazadas por código. Qué significa abre act-tip-final en revisión. Las afinidades quedan ocultas hasta revelar intereses; después catálogo y detalle usan posición, correlación y ajuste del servidor. Afines antepone por posición; BEST/GREAT/GOOD se presentan como Mejor ajuste/Gran ajuste/Buen ajuste. Un código desconocido conserva su título sin enlace a detalle. Perfil plano ofrece revisión y omite afinidades y recomendaciones. Inteligencias y habilidades conservan ejemplos señalados como disponibles en una próxima iteración.

**Archivos afectados.** En el frontend se amplían tipos, almacén, acciones y adaptadores de servidor; se incorpora MaraInteractionPlayer y se adaptan reproductor, nodos, cierre, Ciudad, detalle de Mara, perfil, libro, descubrimiento, catálogo y rutas. Se agregan servidor-mara.test.mjs y servidor-resultados.test.mjs, su ayuda de fixtures y una comprobación local. Las decisiones de presentación quedan en ov_frontend/docs/student-experience/plan.md. En el backend cambia únicamente este documento, sección F5.

**Recorrido manual · SEMILLA=plataforma, EVALUADOR=falso.** Base SQLite temporal independiente; Camino preparado por API como prerrequisito, sin repetir F4. Backend 8001 y frontend 5176 con proxy temporal; el proxy entregado conserva 8000. Los 60 ítems se responden en el navegador con el patrón de §6 (I=5, R=4, A=3, S/E/C=1).

| Paso | Resultado |
|---|---|
| 8 | Salir tras tres respuestas y volver retoma el cuarto ítem de act-tip-01, conservando las respuestas confirmadas. |
| 9 | Se completan las catorce interacciones. El cierre muestra el aviso de Elena y el libro exige revelar intereses; IRA en orden con 100%, 75% y 50%. |
| 10 | Afines ordenadas por posición, con Geólogo/a primero y correlación 0.826325; detalle con Mejor ajuste. Libro con Ingeniería Civil, Ingeniería Ambiental, Medicina Veterinaria y via; navegación a ocupación y carrera. Las pistas usa el resultado vigente, completa una vez y al recargar abre revisión. Revelación conservada tras recargar. |

**Cierre · 2026-10-07.** F5 completa con las decisiones anteriores.

| Repo | Validación de F5 | Resultado |
|---|---|---|
| Frontend | npm run build y npm run lint | Pasan; aviso previo de bundle mayor de 500 kB. |
| Frontend | Integración con fixtures y modo local | 42 casos pasan: 20 de F4 y 22 nuevos de F5. |
| Frontend | npm test | 334 pruebas: 318 pasan y las mismas 16 fallas previas; nombres y líneas comparados exactamente con F0. No se alteran sus expectativas. |
| Backend | uv run pytest -q, SEMILLA=demo, EVALUADOR=falso, temporales y caché propios | 1006 pasan, cero fallas, dos advertencias previas de deprecación; 1321,45 segundos. |

Las pruebas nuevas cubren construcción y escala, reanudación, despedida, guardado y doble clic, desconexión, 409, revisión de solo lectura, reintento de consultas sin otro POST, concurrencia del resultado, respuestas tardías, bloqueo por URL, aislamiento local, IRA y porcentajes, perfil plano, coincidencias y códigos desconocidos, carreras y via, y sello separado por cuenta y fecha. Sin cambios de contratos, fixtures, dependencias ni áreas protegidas; sin llamadas a Gemini. Un commit en español por repo en iteracion-1, sin push. F6–F7 y las 16 fallas previas quedan pendientes; se detiene antes de F6.

## F7

**Verificación ejecutada · 2026-10-07; aceptación pendiente.** El usuario solicitó expresamente el recorrido completo y el informe F7 sobre el estado actual, con F6 aún sin cerrar. Se mantiene la discrepancia de ocultas registrada en F6; no se resuelve en código ni se consideran aprobadas las HU con defectos. El informe detallado está en `ov_frontend/docs/student-experience/informe-f7.md`.

**Recorrido (§6).** Navegador con SEMILLA=plataforma, EVALUADOR=falso, SQLite desechable, backend 8002 y frontend API 5178 mediante proxy temporal; el proxy versionado sigue en 8000. Reinicio y todas las acciones se hacen desde la interfaz; las consultas directas son GET de contraste. No se prepara el Camino por API. Se ejecutan las nueve actividades del Camino, la repetición completa de enc-mitos, las siete entregas necesarias de la matriz, los 60 ítems en catorce encuentros de Mara, la actividad de resultado, libro, afines/carreras, pasaporte y recargas. Tras tres respuestas de Mara se sale, recarga y retoma la cuarta. Resultado IRA: 100 %, 75 % y 50 %, con I=5, R=4, A=3, S/E/C=1 (DATO DE PRUEBA).

Balance: 24 actividades distintas completadas y 25 eventos COMPLETA_ACTIVIDAD; solo enc-mitos tiene dos. Cuatro fichas, I1–I3 y nivel 3. Consultar libro, revelar y revisar no agrega finalizaciones. Campana final sin pendientes presentables; GET conserva 13 no vistos de ACTIVIDAD posteriores, excluidos de cola y contador por F6. No se fuerza su marcado para producir una respuesta vacía.

| HU | Resultado | Evidencia y límite |
|---|---|---|
| HU-002 · Estados | Pasa | Inicialmente solo bienvenida disponible; mapa evoluciona con estado remoto. Final: nueve actividades del Camino y quince de Ciudad COMPLETADA. Casos/desafíos ajenos al alcance siguen bloqueados. |
| HU-004 · Informativas | Pasa | Bienvenida de cuatro nodos y enc-mitos de 24 nodos completadas desde reproductor; eventos confirmados en servidor. |
| HU-011 · Siguiente actividad | Pasa | Panel recomienda bienvenida, cada actividad posterior y las catorce interacciones de Mara en orden. Al terminar Ciudad no inventa otra actividad. |
| HU-013 · Cierre | Pasa | Desbloqueos confirmados de actividad/ficha/I1; después I2/nivel 2; al terminar Camino, Ciudad/I3/nivel 3. |
| HU-014 · Repetición | Pasa | Segunda ejecución completa de enc-mitos: sin nuevos desbloqueos, conserva COMPLETADA y registra segundo evento, sin aumentar distintas. |
| HU-015 · Fichas | Pasa | Mochila con cuatro de cuatro fichas obtenidas tras informativas y recarga; contenido del frontend. |
| HU-021 · Mara | Pasa | Tres respuestas, salida y recarga, reanudación en cuarto ítem; 60 respuestas y catorce interacciones completas. Revisión posterior de solo lectura con opción guardada. |
| HU-022 · Resultado | Pasa | Libro y actividad de resultado muestran IRA en orden: Investigativa 100 %, Realista 75 %, Artística 50 %, igual al resultado vigente remoto. |
| HU-025 · Requisitos | Pasa | Detalle de enc-mitos pide bienvenida; I4 consulta «Invita a un compañero a tu Crew». Suites cubren Ciudad, fichas, conteos, error/reintento y consulta por solicitud sin eventos. Inteligencias/habilidades indican próxima iteración. |
| HU-026 · Afines y carreras | Pasa | Geólogo/a primero, Mejor ajuste y correlación 0.826325. Libro: Ingeniería Civil, Ingeniería Ambiental, Medicina Veterinaria y via; navegación a ocupación/carrera. Perfil plano y códigos desconocidos cubiertos en pruebas. |
| HU-027 · Sello | Pasa | Cierre 14 muestra Elena y enlace. Sello listo con resultado vigente, revela IRA y persiste tras recarga. Aislamiento por cuenta/fecha cubierto en pruebas. |
| HU-073 · Avisos | Parcial | Ficha, insignias, Ciudad y niveles observados; Elena solo en cierre. Al abrir detalle Mi horizonte con aviso de nivel 2 activo, aviso y temporizador siguen activos bajo el diálogo. Falta coordinar ese overlay con la pausa. Consulta previa, avisos nuevos y reintentos pasan en suites. |
| HU-074 · Pasaporte | Falla | Obtenidas I1–I3, bloqueadas públicas y selección vacía persistente funcionan. Oculta pendiente aparece como botón individual «Logro oculto» y grupo, en lugar del contador aprobado. Tres pruebas F6 fallan. |
| HU-075 · Nivel | Pasa | Niveles 1, 2 y 3 en sus hitos; panel/perfil/pasaporte coinciden en nivel 3, Cartógrafo de posibilidades. Lista de títulos remota; pruebas cubren ausencia de nivel sin cálculo local. |

**Invariantes (§7).** (1) Estados y recompensas remotos en las vistas auditadas; se omiten los cálculos locales en API. (2) Act-07 conserva estado remoto sin completar tras guardar entrega local; la única llamada de finalización desde vista sigue en move de StudentActivityPlayer. (3) Repetición confirmada en eventos; revisión no es nueva realización. (4) La única llamada fetch encontrada en áreas permitidas está en servidor/cliente.ts; no se leen portales protegidos. Adaptadores solo import type. (5) Suites de aislamiento pasan y las 16 fallas anteriores conservan exactamente nombres y líneas; mapa/reproductor local comprobados brevemente en 5179. No se certifica suite local enteramente verde. (6) Los escenarios demo e invariantes pasan dentro de las 1006 pruebas del backend, sin modificar expectativas.

| Repo | Validación F7 | Resultado |
|---|---|---|
| Frontend | npm run build, npm run lint | Pasan; aviso previo de bundle grande. |
| Frontend | npm test | 354: 335 pasan, 19 fallan. Las 16 previas coinciden por nombre y línea con F5/F0; tres de F6 relativas a ocultas, líneas 23, 38 y 63 de servidor-logros.test.mjs. |
| Backend | uv run pytest -q, SEMILLA=demo, EVALUADOR=falso, temporales/caché propios | 1006 pasan, cero fallas, dos advertencias previas, 1234.34 segundos. |

**Pendientes.** Resolver identificación de ocultas sin cambiar el contrato, adaptar la variante de prueba que busca I10 en el fixture anonimizado y verificar ausencia de tarjetas individuales; coordinar pausa del aviso con detalles de actividades. El paso 11 falla y el 12 conserva también ese defecto visual. Repetir esos puntos y cerrar F6 antes de aprobar la iteración. Las 16 fallas previas permanecen fuera de este alcance, sin cambiar expectativas.

**Cierre de trabajo.** README de ambos repos, este registro y el informe por HU actualizados. Evidencias DOM, GET, capturas y logs guardados fuera de Git en visualizaciones de la conversación. Commits F7 de documentación únicamente; cambios pendientes F6 conservados sin incorporarlos a esos commits. Se retiran servidores/base temporales. Sin dependencias, cambios de contratos, regeneración de fixtures, llamadas a Gemini, lectura de áreas protegidas ni push. F7 queda ejecutada como verificación, con aceptación pendiente.
