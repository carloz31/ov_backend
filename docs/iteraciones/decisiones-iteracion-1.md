# Decisiones de la iteración 1

Registro de decisiones que afectan a ambos repos. Las internas de cada repo van en `ov_backend/docs/decisiones.md` y `ov_frontend/docs/student-experience/plan.md`.

Formato de cada entrada: fecha, fase, decisión, motivo y archivos afectados.

## Actividades por dominio · F4 · 2026-10-08

Recorrido manual de §12 sobre dos SQLite desechables independientes, creadas
con Alembic y `datos.cargar`, evaluador falso y frontend en modo API. No se
modifican archivos de entorno ni la base del usuario. El registro de acceso
del servidor confirma al ingresar únicamente cuentas, ingreso, resumen,
actividades y no vistos; fichas y logros esperan su vista. Perfil y pasaporte
comparten la carga de logros; mochila pide fichas una vez.

Con `piloto`: cinco actividades y Ciudad cerrada al inicio. Bienvenida y
los 24 nodos de enc-mitos se completan desde el navegador: progreso 20 % y
40 %, Ciudad disponible y Mara 1/14. Elena y la actividad sin contenido
están ausentes; esta última emite un aviso por sesión en desarrollo.
Mochila presenta las cuatro fichas obtenidas. Las catorce interacciones de
Mara se aceleran mediante responder-items y completar-actividad sobre la
base temporal: Elena aparece disponible. No se atribuye esa preparación a
un recorrido de catorce reproductores en la interfaz.

Con `plataforma`: nueve actividades, Ciudad cerrada y solo bienvenida
disponible. Tras dos finalizaciones por API sigue cerrada; al completar
las nueve se abre. Mapa y panel reflejan completadas, nivel 3 y siguiente
paso Mara. Mochila muestra cuatro fichas; perfil y pasaporte, I1–I3 y
Cartógrafo de posibilidades. Después de responder y completar las catorce
interacciones por API, Elena pasa de bloqueada a disponible. No hay avisos
de contenido faltante en esta sesión. Menú, panel y presentación conservan
su estructura y textos, salvo las dos excepciones autorizadas en F3.

La revisión detectó una proyección incorrecta: `AL_DESBLOQUEAR` activaba el
indicador local `additional` y mostraba «Misión adicional» en Elena. Se
retira esa proyección en `puntosServidor.ts` y se refuerza el caso existente
de piloto de `servidor-mapa.test.mjs`; no cambian sus expectativas anteriores
ni el número de pruebas. La visibilidad remota no activa la animación local.

`docs/pendientes-interfaz.md` registra los pendientes de §8: texto de la
llave anticipada, ausencia de animación, testimonios, preguntas del diario,
conversaciones y señal de hoy local. Conserva también el contenido ausente
del piloto. No se implementa interfaz para resolverlos. Evidencias y logs
quedan fuera de Git, en visualizaciones de esta conversación.

Front: **413 pruebas, 398 aprobadas y las mismas 15 fallas previas**, con
nombres y detalles idénticos a F3 excluyendo tiempos y ubicaciones de pila.
Build y lint pasan; estructura: **536 archivos, cero infracciones y
excepciones**. Persiste el aviso previo de tamaño del bundle.

Backend: **1103 aprobadas, 4 omitidas y 2 advertencias previas**, evaluador
falso, suite completa en **778,98 segundos**. F4 queda cerrada; se continúa
con X por autorización del usuario. Sin dependencias, Gemini ni push.

## Actividades por dominio · F3 · 2026-10-08

El usuario resuelve expresamente la contradicción entre §7.4 (título del
servidor) y §8 (conservar textos): autoriza únicamente `enc-mitos` →
«La plaza de los rumores» y `act-06` → «Mi mapa de ruta». Se actualizan esos
dos `title` en `ov_frontend/src/data/content/adventure.ts` para igualar
ambos modos. Son los títulos existentes en actividades y avisos. §8
registra esta única excepción; ningún otro texto se modifica.

Los puntos en modo API se construyen en el orden de las actividades del
servidor, usando `contenido` y `visible`. Las secuencias consecutivas se
agrupan y conservan sus códigos individuales para reproducción y revisión.
Los identificadores históricos de los marcadores se conservan como
presentación; no determinan la lista ni el orden. El contenido ausente se
omite con un aviso por actividad y sesión solo en desarrollo. El progreso
usa las actividades visibles SIEMPRE con contenido y posición; conserva el
peso de cada interacción de una secuencia, según D4, y excluye los extras.
Los contenidos sin mapa se omiten sin inventar coordenadas.

Validación F3: front **413 pruebas, 398 aprobadas y las mismas 15 fallas
previas** de F2 (nombres, motivos y detalles iguales, excluyendo tiempos y
ubicaciones de pila). Siete pruebas nuevas del mapa aprobadas. Build, lint
y verificador correctos: 536 archivos, cero infracciones y excepciones.
Backend: **1103 aprobadas, 4 omitidas y 2 avisos previos**, evaluador falso,
734,36 segundos. No cambian contratos ni código del backend. Commit del
front: `40e6f92`. Sin push. Se continúa con F4 por autorización del usuario.

## Actividades por dominio · F2 · 2026-10-08

Se implementan únicamente los servicios, tipos, secciones y adaptadores de
§7.1–7.3 en `ov_frontend`. La consulta global se sustituye por resumen y
actividades al ingresar, fichas al abrir mochila o recursos y logros al
abrir perfil, pasaporte o insignia. La construcción actual del mapa se
conserva; el mapa dinámico corresponde a F3.

**Secuencia autorizada:** el usuario aprueba retirar `obtenerEstado` y
sustituir su caso de prueba en F2. Se corrigen §7.1 y la tabla de fases de
la especificación de actividades por dominio: X retira `EstadoCuenta`,
los fixtures antiguos y el endpoint del backend; el servicio del front
ya se retiró en F2. El backend no cambia contratos, código ni pruebas.

El almacén se divide en módulos concretos de sesión, secciones, avisos,
resultado, consultas de detalle y coordinación de refrescos. Cada sección
guarda datos, estado y error. La confirmación del ingreso habilita las
consultas; resumen, actividades y no vistos se piden en paralelo. La
consulta posterior de RIASEC conserva la condición de Elena disponible.
Los recursos cerrados no mantienen un consumidor activo aunque sigan
montados. Las promesas se comparten por cuenta, sesión y revisión y se
registran antes de publicar la carga, evitando solicitudes duplicadas.

Completar o responder actualiza actividades y no vistos. Los tipos de
desbloqueo invalidan exactamente los dominios de §7.3; las secciones
visibles recargan inmediatamente y las demás esperan su apertura.
Se descartan respuestas de otra cuenta, otro ingreso y de consultas
anteriores a una invalidación. Los errores esperan un reintento explícito;
las acciones confirmadas conservan su recibo para no repetir escrituras.
El reinicio vacía las secciones y conserva la secuencia de nuevo ingreso.

Las pruebas existentes usan los fixtures por dominio de B3 y conservan
sus resultados esperados. No cambian los 18 JSON ni el exportador, porque
no cambia ninguna respuesta del backend. Los archivos de pruebas tocados
y los detalles de adaptación quedan en
`ov_frontend/docs/refactor/decisiones.md`. El cargador de
`adventure-rendering.test.mjs` usa el mismo React simulado para el nuevo
módulo de secciones; sus 1287 aserciones permanecen idénticas por AST.
Se agregan 17 casos de secciones y tres de servicios; el caso del servicio
global se sustituye por resumen conforme a la autorización.

Validación de F2:

- Frontend antes: **386 pruebas, 371 correctas y 15 fallas previas**.
- Frontend después: **406 pruebas, 391 correctas y las mismas 15 fallas**,
  cero omitidas y cero canceladas. Coinciden nombres, orden, mensajes y
  detalles con F1, excluyendo duraciones y ubicaciones de pila. Pasan las
  **111 pruebas `servidor-*`**.
- Build y lint pasan; estructura: **532 archivos, cero infracciones y
  cero excepciones**. Persiste el aviso previo del bundle mayor de 500 kB.
  No queda `/estado` en `src`, ni importación del módulo retirado.
  La auditoría no encuentra ciclos alcanzables desde el almacén remoto;
  todos sus módulos cumplen el máximo de 400 líneas.
- Backend antes: **1103 correctas, 4 omitidas y 2 advertencias**.
  Backend después, suite completa con evaluador falso: **1103 correctas,
  4 omitidas, cero fallas y 2 advertencias**, en **859,04 segundos**.
  Se conservan las cuatro omisiones de PostgreSQL sin `TEST_POSTGRES_URL`
  y las deprecaciones conocidas de Starlette/httpx y Google GenAI.
  Se ejecuta `uv run --no-sync --offline python -m pytest -q`, fuera del
  sandbox por el bloqueo previo de TestClient; bases y caché son temporales
  externas. Pasan los escenarios y límites de consultas existentes.
- No se modifican vistas, textos, estilos, datos narrativos, reglas,
  claves de almacenamiento ni dependencias. Los registros, bases y caché
  de pruebas permanecen fuera de los repos; no se llama a Gemini.

Se actualiza el inventario del frontend. Siguen pendientes los datos sin
vista registrados en `ov_frontend/docs/pendientes-interfaz.md`: testimonios,
preguntas del diario, conversaciones y los casos del piloto. No se
implementa ninguna opción de interfaz. Tipo, orden, contenido, visibilidad
y visible quedan en las secciones para F3.

**Cierre de F2:** un commit por repo tocado en `iteracion-1`, sin push.
El frontend queda confirmado en `9662c16`, con el árbol limpio.
El backend recibe únicamente este registro y la corrección de secuencia
de la spec. El trabajo se detiene antes de F3.

## Actividades por dominio · F0 y F1 · 2026-10-08

Se lee completo `ov_frontend/AGENTS.md` antes de ejecutar la primera fase F.
La solicitud autoriza F0 y F1 en el mismo turno. F0 registra su línea base en
`ov_frontend/docs/refactor/decisiones.md` y queda confirmada en `65cbc0b`:
**379 pruebas, 364 correctas, las mismas 15 fallas previas y cero omitidas**,
con nombres y orden comparados con B3. Build y lint pasan; estructura:
**515 archivos, cero infracciones y cero excepciones**. F0 no modifica el
backend ni repite su suite; conserva como referencia el cierre B3.

F1 mueve seis JSON a `src/data/activities/contenidos/`, crea los siete de
§5.2 y agrega el registro explícito `contenidos.ts`. `catalogo.json` y el
catálogo `compassInstrument` permanecen separados. Los trece contenidos se
comprueban mediante `deepEqual` antes de retirar sus definiciones TypeScript;
solo se añade el campo opcional de presentación `mapa` donde corresponde.
Las claves coinciden con las enviadas por el backend, sin cambiar los datos
de plataforma ni de piloto. El contenido deliberadamente ausente del piloto
sigue sin existir en el registro.

El catálogo local se reconstruye con el mismo orden y los mismos ajustes
del piloto de reflexión, omitiendo los metadatos `mapa`. Una comparación
temporal conserva exactamente `activities`, `parentActivities`,
`finalActivity`, `activityById`, `catalog` y `compassInstrument`. El registro
ofrece los contenidos con metadatos para las fases siguientes, sin cambiar
las fuentes de disponibilidad ni las consultas HTTP actuales. Los íconos
se traducen en un único módulo del dominio de aventura; el selector actual
del Camino conserva sus resultados.

Las tres adaptaciones de pruebas existentes solo cambian rutas de JSON,
conforme a §9.2.2. Se anotan archivos y pruebas por nombre en las decisiones
del front y se comprueba que sus llamadas `assert.*` no cambian.
`contenidos.test.mjs` añade siete pruebas de registro, claves de ambos
conjuntos, presentación y compatibilidad local. No se modifican vistas,
marcado, textos, estilos, claves de almacenamiento, servicios ni hooks.
No aparecen datos sin vista nuevos; los pendientes registrados en B2/B3
siguen pendientes y no se implementa ninguna de sus opciones.

Validación de F1:

- Frontend antes: **379 pruebas, 364 correctas, 15 fallas previas**.
- Frontend después: **386 pruebas, 371 correctas, las mismas 15 fallas**,
  cero omitidas y cero canceladas, en **17,71 segundos**. Los nombres,
  el orden y los errores coinciden con F0, excluyendo duraciones y
  ubicaciones de pila. Las siete pruebas nuevas pasan.
- Build y lint pasan. Estructura: **524 archivos, cero infracciones y cero
  excepciones**. Se conserva el aviso previo de bundle mayor de 500 kB.
- Backend antes: **1103 correctas, 4 omitidas, cero fallas y 2 advertencias**
  (cierre B3). Backend después, suite completa: **1103 correctas, 4 omitidas,
  cero fallas y 2 advertencias**, en **726,48 segundos**. Las cuatro omisiones
  corresponden a PostgreSQL sin `TEST_POSTGRES_URL`; las advertencias son
  las deprecaciones conocidas de Starlette/httpx y Google GenAI. No cambian
  código, pruebas, modelos, migraciones, contratos ni fixtures.
- Evaluador falso, sin llamadas a Gemini ni dependencias nuevas. Se usa
  `uv run python -m pytest` por el problema previo del lanzador, fuera del
  sandbox por el bloqueo de TestClient ya diagnosticado. Los registros,
  la comparación temporal, bases y caché quedan fuera de los repos.

**Cierre de F1:** el frontend queda confirmado en `7725d81`, con el árbol
de trabajo limpio. El backend guarda únicamente este registro en un commit
F1 en `iteracion-1`. Sin push. La integración de consultas por dominio
corresponde a F2 y no se inicia; el trabajo se detiene tras F0 y F1.

## Actividades por dominio · B3 · 2026-10-08

Se implementa únicamente B3: `datos/piloto.py`, su alta en `CONJUNTOS`,
las pruebas del piloto y los diez fixtures nuevos de §5.4. Se reutilizan
los datos y cargadores de plataforma sin modificar sus constantes ni las
de demo. El Camino tiene cinco pasos secuenciales; la Ciudad abre al segundo.
Elena usa `AL_DESBLOQUEAR` y el código `cdd-sin-contenido` conserva una clave
deliberadamente ausente del front. Los logros y niveles del Camino funcionan
con cinco actividades y conservan sus umbrales; no hay reglas adicionales
que deban cambiarse por la reducción del Camino.

El exportador CLI genera 18 archivos mediante bases temporales separadas:
ocho anteriores, siete consultas de plataforma y tres momentos del piloto.
Los momentos del piloto son inicio, `enc-mitos` completa y `act-tip-14`
completa; en los dos últimos solo están completos los dos primeros pasos
del Camino. Los ocho fixtures anteriores exportados se comparan byte por
byte con HEAD del frontend y permanecen idénticos.

La función programática `exportar_fixtures(destino)` conserva su contrato
anterior de ocho archivos; la nueva opción `por_dominio=True`, usada siempre
por el CLI, activa los 18. Así se cumple §5.4 sin adaptar las aserciones
existentes que fijan los ocho nombres o una sola base de plataforma.
El contrato completo, la reproducibilidad, la restauración del evaluador,
el aislamiento de la base del usuario y el fallo previo a escribir se prueban
en `tests/test_fixtures_dominio.py`.

Se completa la equivalencia pendiente de B2 con piloto. En sus tres momentos
se comparan todos los campos anteriores para Ana, Luis y Rosa; en el tercero
se completan el Camino y Mara para incluir a Elena visible. Ninguna aserción
existente cambia, comprobado por AST. B3 añade 16 casos: nueve de piloto,
tres del exportador y cuatro de la parametrización de equivalencia.

El front recibe únicamente los diez JSON nuevos y las entradas de
`docs/pendientes-interfaz.md` sobre el contenido de prueba ausente, el texto
de la llave cuando abre al segundo paso y la falta de animación de revelado.
Son datos y documentación; no se modifican vistas, textos de la interfaz,
estilos, código, tipos, servicios ni hooks. La integración corresponde a
las fases F. También se actualiza el README del backend con la carga del
piloto y las modalidades del exportador.

Validación de B3:

- Backend antes: **1087 pasan, 4 omitidas, cero fallas y 2 advertencias**
  (cierre de B2). Las pruebas dirigidas de piloto, fixtures, equivalencia,
  carga y exportador original aprueban **42 casos**, con una advertencia,
  en 54,52 segundos.
- Backend después, suite completa: **1103 pasan, 4 omitidas, cero fallas
  y 2 advertencias**, en **795,13 segundos**. Pasan los escenarios y los
  límites SQL existentes. Las cuatro omisiones son los casos opcionales de
  PostgreSQL sin `TEST_POSTGRES_URL`; las advertencias son las deprecaciones
  conocidas de Starlette/httpx y Google GenAI.
- Frontend antes: **379 pruebas, 364 pasan, 15 fallas previas y cero omitidas**
  (cierre de B2). La exportación produce los 18 JSON y conserva los ocho
  anteriores exactamente.
- Frontend después: **379 pruebas, 364 pasan, las mismas 15 fallan y cero
  omitidas**. Se comparan exactamente los nombres y el orden con B2.
  Build y lint pasan; estructura: **515 archivos, cero infracciones y cero
  excepciones**. Se conserva el aviso previo de bundle mayor de 500 kB.
  Solo cambian los diez fixtures nuevos y el documento de pendientes.
- Se usa `EVALUADOR=falso`, sin llamadas reales a Gemini ni dependencias
  nuevas. Las pruebas HTTP y el exportador se ejecutan fuera del sandbox
  por el bloqueo de TestClient ya diagnosticado; `uv run python -m pytest`
  evita el problema previo del lanzador. Las bases, caché y registros quedan
  fuera de ambos repos.

**Cierre de B3:** un commit por repo en `iteracion-1`, sin push. El frontend
registra los diez fixtures nuevos y los pendientes en `90d76f6`; el backend
guarda el conjunto piloto, el exportador, las pruebas y estas decisiones.
Quedan pendientes la integración del frontend y las opciones de interfaz
registradas en su documento de pendientes. Se detiene antes de F0.

## Actividades por dominio · B2 · 2026-10-08

Se implementan únicamente las consultas por dominio de §4 y §5.3:
`resumen`, `actividades`, `fichas`, `logros`, `testimonios`,
`diario/preguntas` y `conversaciones`, todas bajo `/cuentas/{cuenta}/`.
La lógica se extrae a los servicios de cada dominio y se comparte con
`/estado`, que conserva sus campos y su orden anterior por código. Las
actividades nuevas incluyen tipo, orden, contenido, visibilidad y `visible`;
sus bloques se ordenan por número y código. No se alteran las reglas,
la semilla `plataforma` ni los escenarios de `demo`.

Se crean `tests/test_consultas_dominio.py` y
`tests/test_estado_equivalente.py`, con 51 casos. La equivalencia compara
todos los campos anteriores para `plataforma` y `demo` al inicio, tras dos
actividades y al completar el Camino (B0 en demo). El usuario aprueba
completar la equivalencia de `piloto` en B3, cuando se cree ese conjunto.
No se modifican pruebas existentes, fixtures ni el exportador.

El único cambio del front es la anotación en `docs/pendientes-interfaz.md`
de los campos de testimonios, preguntas del diario y conversaciones que
todavía no tienen vista en modo API, según el Anexo A. No se implementa
ninguna opción visual, ni se agregan tipos, servicios o hooks para esos
dominios: §4 los reserva para sus futuras iteraciones. La integración del
resto de consultas corresponde a F2 y los fixtures a B3.

Validación de B2:

- Backend antes: **1036 pasan, 4 omitidas, cero fallas y 2 advertencias**
  (cierre de B1). Tras corregir los dos problemas de la ejecución dirigida,
  la revisión de las consultas nuevas y del progreso de insignias aprueba
  **56 pruebas**, con una advertencia de dependencia.
- Backend después, suite completa: **1087 pasan, 4 omitidas, cero fallas
  y 2 advertencias**, en **660,79 segundos**. Se agregan los 51 casos nuevos;
  pasan los escenarios y los límites SQL existentes sin cambiar aserciones.
  Las cuatro omisiones son los casos opcionales de PostgreSQL sin
  `TEST_POSTGRES_URL`; las advertencias son las previas de dependencias.
- Frontend antes y después: **379 pruebas, 364 pasan, las mismas 15 fallan,
  cero omitidas**. Se comparan exactamente sus nombres y orden; coinciden
  con la tabla de B0. Build y lint pasan; estructura: **515 archivos,
  cero infracciones y cero excepciones**. Se conserva el aviso de bundle
  mayor de 500 kB. No se modifican código ni pruebas del frontend.
- Las pruebas usan `EVALUADOR=falso`, sin llamadas a Gemini. Se ejecuta
  `uv run python -m pytest` por el problema previo del lanzador de este
  entorno; las pruebas HTTP se corren fuera del sandbox por el bloqueo
  de `TestClient` diagnosticado en B0/B1. Los registros, las bases y los
  temporales se guardan fuera de los repositorios.
- La auditoría de rutas conserva todas las anteriores y encuentra exactamente
  los siete GET pedidos. La comparación de los 16 esquemas anteriores contra
  HEAD confirma que sus JSON Schema no cambian, incluso al moverlos de archivo.

**Cierre de B2:** un commit por repo en `iteracion-1`, sin push. En el
frontend, `7204a3d` registra únicamente los pendientes de interfaz; el
backend guarda las consultas, las pruebas nuevas y estas decisiones.
B3 y las fases posteriores no se inician. Quedan pendientes el conjunto
`piloto`, su cobertura de equivalencia y los fixtures (B3), y la integración
del frontend desde F0/F1/F2 según el orden de la spec.

## Actividades por dominio · B1 · 2026-10-08

El usuario autoriza explícitamente `codigo.lower().replace("-", "_")`
para `demo` y para las filas existentes de la migración. Se corrigen §5.1
y §5.2 de `spec-iteracion-1-actividades-por-dominio.md`: esta regla resuelve
la contradicción entre los códigos de demo en mayúsculas y el formato de
`contenido`. Los códigos originales permanecen intactos. `plataforma`
recibe las claves explícitas de la tabla de §5.2.

El formato `[a-z0-9_]+` se valida en `datos/cargar.py`, dentro de la
transacción de carga y después de insertar las definiciones. Es la
alternativa del cargador permitida por §5.1, para evitar un CHECK de
expresiones regulares dependiente del dialecto. Una clave inválida
rechaza toda la carga. `contenido` sigue siendo no nula en la BD;
`visibilidad` tiene CHECK de enumerado y valor predeterminado `SIEMPRE`.

La migración `0002_contenido_y_visibilidad.py` se genera con Alembic
`revision --autogenerate --rev-id 0002` y se revisa a mano. Agrega la
clave temporalmente nullable, completa las filas con `lower` y `replace`
portables y luego impone NOT NULL. Para reconstruir tablas referenciadas
en SQLite se usa `conexion_migraciones` de `app/database.py`, que
desactiva las FK solo en esa conexión de migración, comprueba su
integridad y las restaura; las conexiones de la aplicación mantienen
las FK activadas. PostgreSQL conserva su comportamiento habitual.

Validación de B1 antes del cierre:

- Línea base B0: 1023 pasan, 4 omitidas y cero fallas.
- Pruebas dirigidas: 27 pasan y 5 casos excluidos; incluyen las 13 pruebas
  nuevas y la compilación SQL para PostgreSQL. `alembic check` informa
  que no hay diferencias entre modelos y esquema migrado.
- Suite completa: **1032 pasan, 4 fallan, 4 omitidas y 2 advertencias**,
  en 663,82 segundos. Las cuatro fallas son exclusivamente las expectativas
  `0001` de `tests/test_migraciones.py`, líneas 52, 97 y 115 (esta última
  parametrizada para `demo` y `plataforma`). La revisión efectiva es `0002`.
  Las 13 pruebas nuevas pasan; no hay fallas de escenarios.
- Se usa `uv run python -m alembic` y `uv run python -m pytest` porque los
  lanzadores de este entorno fallan al resolver su ruta. La suite HTTP se
  ejecuta fuera del sandbox, con `EVALUADOR=falso`, sin sincronizar ni
  instalar dependencias y con bases, caché y registros externos al repo.
  Las omisiones son PostgreSQL sin `TEST_POSTGRES_URL`; no se llama a Gemini.
- El usuario autoriza adaptar las tres expectativas de revisión después de
  confirmar que explican las cuatro fallas. Se comparan con
  `ScriptDirectory.from_config(configuracion).get_current_head()`, en lugar
  de otra revisión literal, y no cambia ninguna otra aserción. Se corrige
  §5.6 y se registran las tres pruebas por nombre en `docs/decisiones.md`.
  Se repite la suite completa antes del cierre. `ov_frontend` permanece
  sin cambios en B1 y B2 no se inicia.

**Cierre de B1:** la comparación por AST confirma que solo cambiaron las
tres aserciones autorizadas. La suite completa termina con **1036 pasan,
4 omitidas, cero fallas y 2 advertencias**, en 643,11 segundos. Frente a
B0 (1023 pasan y 4 omitidas), se agregan 13 pruebas. Pasan la creación
desde una base vacía, la migración desde `0001` con filas y referencias,
el downgrade y un nuevo upgrade, así como las comprobaciones de esquema
e integridad y la compilación para PostgreSQL. Las cuatro omisiones son
los casos opcionales sin `TEST_POSTGRES_URL`.

Se cierra únicamente B1 con un commit en `iteracion-1`, sin push.
No cambian respuestas HTTP, fixtures, interfaz, dependencias ni archivos
de `ov_frontend`; por eso no se repiten las pruebas del front en B1.
Los registros y las bases temporales quedan fuera de los repositorios.
B2 y las fases posteriores siguen pendientes.

## Actividades por dominio · B0 · 2026-10-08

Se ejecuta únicamente B0 de `spec-iteracion-1-actividades-por-dominio.md`,
sobre `iteracion-1` en ambos repos (backend inicial `bf73ec4`, frontend
inicial `db5c4c7`). Se leen completos los dos documentos de la iteración
y los dos `AGENTS.md`.

La sección «Reglas compartidas» del frontend ya estaba actualizada y se
copia literalmente al backend. Se agrega en ambos la viñeta del Anexo A.2,
y en el frontend la sección literal del Anexo A.1, antes de «Interfaz del
estudiante». La comparación de las secciones compartidas queda vacía.
Se crea `ov_frontend/docs/pendientes-interfaz.md` solo con el encabezado
y la explicación del Anexo A.3, sin entradas ni plantilla de entrada.

| Repo | Comprobación | Antes | Después |
|---|---|---|---|
| Backend | Línea base pytest | Referencia previa R7: 1023 pasan, 4 omitidas, 0 fallas. | B0: 1023 pasan, 4 omitidas, 0 fallas y 2 advertencias; 638,28 segundos. |
| Frontend | `npm test` | 379: 364 pasan, 15 fallan, 0 omitidas. | 379: 364 pasan, las mismas 15 fallan, 0 omitidas. |
| Frontend | `npm run build` y `npm run lint` | — | Pasan; build conserva el aviso de bundle mayor de 500 kB. |
| Frontend | `npm run check:estructura` | — | 515 archivos, 0 infracciones y 0 excepciones. |

Ejecución del backend: el comando solicitado `uv run pytest -q` no llega
a iniciar pytest porque el lanzador informa «uv trampoline failed to
canonicalize script path». Se usa `uv run python -m pytest -q -rs`, con
las dependencias ya instaladas (`UV_NO_SYNC=true`, `UV_OFFLINE=true`) y
`EVALUADOR=falso`. Se indican `cache_dir` y `--basetemp` fuera del repo.
Los intentos dentro del sandbox se interrumpen: uno falla al crear los
temporales y otro queda bloqueado en el `socketpair` interno del bucle
asíncrono de `TestClient`, confirmado con la pila de faulthandler. La
ejecución completa se realiza fuera de ese aislamiento, sin modificar
pruebas ni código y sin llamadas a Gemini.
Las cuatro omisiones corresponden a `tests/test_postgres.py`, por falta
de `TEST_POSTGRES_URL`. Las dos advertencias son de dependencias. Se
ejecuta una sola suite completa del backend para fijar la línea base
de B0; el código y las pruebas permanecen idénticos durante esta fase.

Las 15 fallas del frontend coinciden por nombre y ubicación antes y
después. Todas están en `tests/adventure-rendering.test.mjs`; no se
modifican implementación ni expectativas en esta fase:

| Línea | Nombre de la prueba |
|---|---|
| 1500 | immersive submission preserves validation, drafts, versions and the keep action |
| 1567 | immersive questions preserve attempts, hints, revelation, retry and fresh revision behavior |
| 1696 | immersive finish shows saved sheets, narrative rewards and the prompted journal action |
| 1773 | follow-up service waits 700ms, respects both text thresholds and never asks a third turn |
| 1852 | first text submission saves version one before follow-up; edits and matrices use the normal form |
| 1878 | follow-up accepts two replies, caps the field at available space and saves one condensed version |
| 1912 | omitting all turns preserves version one, while a long reply ends follow-up after one turn |
| 1929 | no question, failure, timeout or fewer than 40 free characters advances silently with the original |
| 1948 | interrupted follow-up recovers only answered turns and loads the condensed form without duplicate versions |
| 1997 | follow-up requires 40 free characters and stops before a second question that cannot fit |
| 2030 | leaving during evaluation never stores a late question and recovery preserves the replied turn |
| 2323 | every supplied mission node renders, including matrices, slides, questions and instrument items |
| 2618 | phase 8 path sequence respects both completion records without changing catalog or real thresholds |
| 2655 | phase 8 direct links open blocked details instead of starting unavailable players |
| 3191 | discovery atlas covers existing IDs, symmetric relations and gated affinity |

Los registros, la caché y los temporales de pytest se mantienen fuera
de los repositorios. No cambian código, contratos, fixtures, datos,
dependencias ni interfaz; no se llama a Gemini ni se hace push.
Queda pendiente B1 y el resto de las fases; B0 no las inicia.

## Refactor de estructura · R5 · 2026-10-08

La documentación de preparación de ambos repositorios pasa a los comandos de
`docs/spec-refactor-estructura.md`: Alembic, carga explícita de `plataforma` y
arranque sobre la base indicada por `DATABASE_URL`. Los siguientes arranques
conservan los datos y solo requieren Uvicorn. El reinicio de desarrollo borra
estado y conserva catálogo, cuentas, vínculos y cartas.

En frontend solo cambian README y aclaraciones históricas de los informes del
estudiante. No cambian código, contratos, fixtures ni modo local. Se conservan
las configuraciones y resultados de ejecuciones anteriores como historial;
el usuario autoriza expresamente esta revisión contextual en R5. El detalle
de coincidencias conservadas y validación está en `docs/decisiones.md`.

Validación: backend **1023 aprobadas, 4 omitidas y 2 avisos**, sin fallos,
en 883.49 segundos; evaluador falso y temporales externos. Las omisiones son
los casos PostgreSQL sin `TEST_POSTGRES_URL`. Frontend: build y lint pasan;
**340 de 356 pruebas aprobadas**, con las mismas **16 fallas previas** de
F0/F7, sin fallas nuevas. Solo se modifican documentos; no hay llamadas a
Gemini ni push. Frontend queda en el commit `3f58c1e`.

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

## F6

**Completa · 2026-10-07.** Se implementan y verifican avisos, pasaporte, nivel y requisitos sobre F5. Tras la verificación inicial F7, el usuario solicita cerrar HU-073 y HU-074 y autoriza corregir la identificación de ocultas según §5.9.

- **Apertura acordada:** la cola automática opera únicamente en Camino y Ciudad, después del reproductor y de los overlays prioritarios. La campana solicita el mismo lote en otros módulos. Los avisos duran siete segundos y admiten cierre manual; no hay una segunda cola.
- **Marcado acordado:** se marca el lote después de mostrar todos sus avisos. Antes del POST global existente se consultan de nuevo los no vistos; los nuevos avisos deben mostrarse primero. El recibo de un POST confirmado permite reintentar solo GET si falla la consulta posterior. Recargar antes del marcado conserva los pendientes; cambiar de cuenta o reiniciar descarta el lote y las respuestas tardías.
- **Elena acordada:** su mensaje permanece exclusivamente en FinishScreen. La cola presenta INSIGNIA, FICHA, BLOQUE CIUDAD y NIVEL; los demás tipos no tienen presentación ni contador, aunque el endpoint global los marca junto al lote.
- Los nuevos desbloqueos de ingreso y finalización se conservan tras el POST aunque falle el refresco. Se deduplican por cuenta, regla, tipo y código. Los registros locales de avisos vistos no intervienen en API.
- Pasaporte y perfil usan insignias del estado remoto, con OBTENIDA como única fuente de adquisición. Las preferencias de hasta tres insignias, incluida una selección vacía, se guardan por cuenta en el almacenamiento de descubrimiento. Los números, títulos y estados de niveles vienen del servidor; las descripciones y siguientes pasos conservan los textos del front. Sin nivel recibido no se calcula ni supone un nivel inicial.
- Los requisitos se consultan al abrir detalles: ACTIVIDAD, BLOQUE CIUDAD, FICHA e INSIGNIA pública. Se añaden carga, error y reintento, con descarte por cuenta y detalle. No se consultan códigos de casos o desafíos ausentes ni se registran eventos por consultar.

**Corrección autorizada.** El plan inicial decía `nombre === '???'`, pero el contrato y fixtures entregan `codigo: '???'`, `nombre: 'Logro oculto'`, sin descripción ni requisito. La solicitud de cierre autoriza usar el código anonimizado y el estado no OBTENIDA: solo se presenta el contador. Cuando el servidor revela una obtenida, su código, nombre, descripción y requisito se muestran normalmente. Se corrige la variante de prueba convirtiendo el registro anonimizado en I10 obtenida; se conservan y refuerzan las aserciones. Sin cambios de contrato ni fixtures.

**Validación previa de F6 (antes del cierre).** Base SQLite desechable independiente, SEMILLA=plataforma y EVALUADOR=falso, backend 8002 y frontend 5177 con proxy temporal. El proxy versionado conserva 8000. La bienvenida se completa en el navegador; los demás hitos del Camino se preparan mediante API para comprobar los avisos, sin repetir la aceptación de F4. Se observa I1 y ficha inicial; I2 y nivel 2; Ciudad, I3 y nivel 3. En catálogo no aparece cola automática y la campana abre siete pendientes. Recargar antes de marcar mantiene los siete; completar el Camino mientras están cargados incorpora el aviso de Ciudad en la consulta previa. Otra recarga mantiene los diez avisos sin marcar; recorrerlos deja la campana vacía y GET de no vistos devuelve `[]`. Perfil y panel de Ciudad muestran Cartógrafo de posibilidades, nivel 3; el diálogo de I4 consulta y muestra «Invita a un compañero a tu Crew». La exclusión visual de ocultas en los pasos 11–12 sigue pendiente.

| Repo | Validación previa | Resultado |
|---|---|---|
| Frontend | npm run build y npm run lint | Pasan; permanece el aviso previo de bundle mayor de 500 kB. |
| Frontend | npm test | 354 pruebas: 335 pasan, las mismas 16 fallas previas por nombre y línea, y 3 fallas nuevas vinculadas a la discrepancia de ocultas. No se cambian expectativas anteriores. |
| Backend | uv run pytest -q, SEMILLA=demo, EVALUADOR=falso, temporales y caché propios | 1006 pasan, cero fallas, dos advertencias previas de deprecación; 1241,26 segundos. |

Los casos nuevos cubren cola, marcado, avisos nuevos, recarga, reintento sin otro POST, ingreso y finalización con refresco fallido, respuestas tardías, pausa y apertura manual, selección por cuenta, niveles remotos, requisitos y aislamiento local. Solo se actualizan estos registros y §5.9 en el backend; no cambian endpoints, contratos, fixtures ni dependencias. Sin acceso a áreas protegidas, llamadas a Gemini ni push. El cierre actual se documenta a continuación.

### Cierre de HU-073 y HU-074

El bloqueo de anuncios API incluye diálogos, drawers y menús montados en portales, actividad y overlays prioritarios. Se comparte announcementBlocked con el criterio de getNextBadge; al ocultar el aviso se desmonta y cancela su temporizador. No se registra como mostrado durante la pausa. La campana solicita el lote sin bloquearse por su propio menú; la cola espera a que se cierre. El efecto de marcado también permanece pausado mientras haya un overlay.

Base desechable nueva, SEMILLA=plataforma y EVALUADOR=falso, backend 8002/frontend 5178. Para repetir exclusivamente los pasos 11–12, el Camino se prepara por API; no se atribuye esa preparación a un nuevo recorrido completo. La verificación completa F7 anterior permanece descrita arriba.

Se abre Mi horizonte mientras hay avisos: quedan siete en la campana, el aviso desaparece y sigue pausado más de siete segundos. No se registra POST de marcado y los 19 no vistos del servidor permanecen. Al cerrar se retoma el aviso con el mismo contador. Actividad y diálogo de salida no presentan la cola; en pasaporte no aparece automáticamente. La campana solicita diez pendientes, y el diálogo de I4 los pausa sin consumirlos. Recargar antes del marcado devuelve los diez.

DATO DE PRUEBA: un evento crudo VENCE_DESAFIO_INTACTO, sin referencia, exclusivamente en esta base desechable obtiene I10 «Luz sin fisuras» mientras el lote está abierto. No se implementa ni se recorre un desafío fuera del alcance. La consulta previa incorpora su aviso después de los diez anteriores: se muestran once en total y solo entonces ocurre un POST global. GET de no vistos queda vacío, incluido tras recargar. I10 se muestra completa, con descripción y requisito del servidor; contador de ocultas desaparece y pasaporte pasa de 3/10 a 4/10. Nivel permanece en 3.

Evidencias nuevas: f6-cierre-dom.json, f6-cierre-inicial.json, f6-cierre-pausa.json, f6-cierre-oculta-obtenida.json, f6-cierre-final.json; capturas f6-cierre-detalle-pausado.png, f6-cierre-pasaporte.png y f6-cierre-obtenida.png; logs f6-cierre-build.log, f6-cierre-lint.log, f6-cierre-tests.log y f6-cierre-pytest.log en visualizaciones de esta conversación.

Validación de cierre frontend: build y lint pasan; npm test tiene 356 pruebas, 340 pasan y únicamente las 16 fallas previas por nombre y línea. Las tres pendientes de F6 pasan sin debilitar aserciones. Se agregan dos casos de pausa del marcado y campana; sin alterar expectativas anteriores.

Validación de cierre backend: uv run pytest -q, con SEMILLA=demo, EVALUADOR=falso y temporales propios, termina con 1006 pruebas que pasan, cero fallas y dos advertencias previas en 1080.83 segundos.

Un commit F6 por repo con el mensaje «Iteración 1 · F6: avisos, pasaporte, nivel y requisitos», en iteracion-1, sin push. Se detiene el trabajo al completar F6.

## F7

**Verificación inicial ejecutada · 2026-10-07.** El usuario solicitó el recorrido completo sobre F6 sin cerrar. Se detectaron los defectos HU-073/HU-074 y posteriormente el usuario autorizó corregirlos al cerrar F6. La tabla siguiente incorpora esa revalidación; el recorrido original se conserva. El informe detallado está en `ov_frontend/docs/student-experience/informe-f7.md`.

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
| HU-073 · Avisos | Pasa | Revalidación de cierre F6: detalle/drawer, actividad, diálogo y menú pausan la cola. Se retoma al cerrar; la consulta previa incorpora I10 nueva y un único POST al terminar deja no vistos vacíos. |
| HU-074 · Pasaporte | Pasa | Revalidación de cierre F6: oculta pendiente solo en contador, sin tarjeta ni nombre en HTML; al obtener I10 aparece completa. Requisitos, nivel y recargas correctos. Tres pruebas corregidas y reforzadas. |
| HU-075 · Nivel | Pasa | Niveles 1, 2 y 3 en sus hitos; panel/perfil/pasaporte coinciden en nivel 3, Cartógrafo de posibilidades. Lista de títulos remota; pruebas cubren ausencia de nivel sin cálculo local. |

**Invariantes (§7).** (1) Estados y recompensas remotos en las vistas auditadas; se omiten los cálculos locales en API. (2) Act-07 conserva estado remoto sin completar tras guardar entrega local; la única llamada de finalización desde vista sigue en move de StudentActivityPlayer. (3) Repetición confirmada en eventos; revisión no es nueva realización. (4) La única llamada fetch encontrada en áreas permitidas está en servidor/cliente.ts; no se leen portales protegidos. Adaptadores solo import type. (5) Suites de aislamiento pasan y las 16 fallas anteriores conservan exactamente nombres y líneas; mapa/reproductor local comprobados brevemente en 5179. No se certifica suite local enteramente verde. (6) Los escenarios demo e invariantes pasan dentro de las 1006 pruebas del backend, sin modificar expectativas.

| Repo | Validación F7 inicial | Resultado |
|---|---|---|
| Frontend | npm run build, npm run lint | Pasan; aviso previo de bundle grande. |
| Frontend | npm test | 354: 335 pasan, 19 fallan. Las 16 previas coinciden por nombre y línea con F5/F0; tres de F6 relativas a ocultas, líneas 23, 38 y 63 de servidor-logros.test.mjs. |
| Backend | uv run pytest -q, SEMILLA=demo, EVALUADOR=falso, temporales/caché propios | 1006 pasan, cero fallas, dos advertencias previas, 1234.34 segundos. |

**Pendientes actuales.** HU-073 y HU-074 corregidas y revalidadas; pasos 11–12 pasan. Solo permanecen las 16 fallas previas del frontend fuera de esta fase, sin modificar sus expectativas. La aprobación formal de la iteración corresponde al usuario.

**Cierre de trabajo.** Los commits F7 iniciales fueron documentales. El cierre posterior F6 incorpora su implementación y registros con validación de HU-073/HU-074. Evidencias DOM, GET, capturas y logs fuera de Git; servidores y base temporales retirados al terminar. Sin dependencias, contratos/fixtures nuevos, Gemini, áreas protegidas ni push. Se detiene el trabajo al cerrar F6.

## Refactor del frontend · R7: rutas del contrato (8 de octubre de 2026)

- El refactor de estructura de `ov_frontend`, autorizado en `refactor-estructura`, termina con la documentación R7. La sección compartida de ambos `AGENTS.md` se actualiza para reflejar las rutas finales: contrato en `src/types/servidor.ts`, peticiones en `src/services/api/`, adaptación en `src/lib/servidor/adaptadores.ts` y estado remoto en `src/store/servidor/`.
- En el `AGENTS.md` del backend solo se modifican las dos reglas del contrato dentro de «Reglas compartidas»; la sección queda idéntica a la del frontend y el resto del archivo permanece intacto. El registro y las reglas se confirman en un commit separado en `iteracion-1`.
- No cambian respuestas HTTP, esquemas, modelos, servicios, migraciones, fixtures, datos, pruebas ni dependencias del backend. Los datos narrativos siguen en el frontend y el servidor conserva la autoridad sobre disponibilidad, progreso y resultados. No se adelantan iteraciones ni se hace push.
- Validación del frontend: build y lint correctos; **365 pruebas, 350 correctas y las mismas 15 fallas previas**; **77/77** pruebas `servidor-*`; estructura **515 archivos, cero infracciones y ninguna excepción**. La auditoría comprueba las rutas documentadas y la igualdad de las reglas compartidas.
- Validación del backend: `uv run --no-sync --offline python -m pytest -q`, con evaluador falso y semilla demo: **1.023 correctas, 4 omitidas, cero fallas**, dos advertencias de dependencias, 772 segundos. Las cuatro omitidas corresponden a los escenarios opcionales de PostgreSQL (`Falta TEST_POSTGRES_URL`), comprobados mediante `-rs`. Caché, bases y temporales de pruebas quedan fuera del repo; los registros están en `ov_frontend/logs/`, ignorados por Git. Sin instalaciones ni llamadas a Gemini. R7 queda cerrada, sin integración ni push.
