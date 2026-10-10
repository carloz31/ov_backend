# Integración entre ov_backend y ov_frontend

Contrato vigente entre los dos repos. Lo usan los agentes de ambos. Las reglas generales están en «Reglas compartidas» de los `AGENTS.md`; aquí está el detalle.

## Quién es dueño de cada dato

| Dato | Dueño |
|---|---|
| Cuentas, bloques, actividades (código, título, tipo, orden, `contenido`, `visibilidad`), reglas | Base de datos |
| Fichas, insignias y niveles (código, nombre, requisito, oculta) | Base de datos. La presentación (íconos, imágenes, cuerpo de la ficha) está en el front, buscada por código. |
| Instrumento RIASEC (ítems, enunciados, escala, dimensiones con descripción, aplicación) | Base de datos |
| Ocupaciones y carreras del universo de recomendación, con sus puntajes O*NET | Base de datos |
| Estado del estudiante: progreso, eventos, desbloqueos, respuestas a ítems, resultados | Base de datos. El front solo guarda una copia de presentación. |
| Estado del apoderado: disponibilidad, completitud de actividades y eventos | Base de datos. Nodo actual, intentos de práctica y elecciones quedan en el front por cuenta. |
| Contenido narrativo de cada actividad (nodos JSON) | Front (`src/data/activities/contenidos/`) |
| Textos de registros, borradores, respuestas de la brújula, intentos de comprobaciones, favoritos, planes | Front (local). Pasan al servidor en iteraciones siguientes. |
| Detalle del catálogo (descripciones, ingresos, instituciones, duración de carreras) | Front (`src/data/catalog/`) |

`ov_frontend/docs/origen-de-datos.md` tiene el inventario completo del lado del front.

## Códigos

- Los códigos del backend son exactamente los ids del front (`mission-welcome`, `enc-mitos`, `act-tip-01`, `ficha-mitos`, `I1`, `nursing`). No hay tabla de traducción.
- Los códigos nuevos usan el mismo estilo (minúsculas y guiones), salvo los que ya existen en el backend: `TEST-RIASEC`, `APL-RIASEC`, `ESC-LIKERT5`, dimensiones `R`…`C`, reglas `R-…`.
- `actividad.contenido` es la clave del JSON del front (`[a-z0-9_]`). Varias actividades pueden compartirla: las 14 interacciones de Mara usan `instrumento_mara`. Si el front renombra un JSON, se cambia también en `datos/`.

## Modos del front

- `VITE_DATOS=local` (por defecto): el front funciona solo, con sus datos y cálculos de demostración.
- `VITE_DATOS=api`: usa el servidor. `prototypeAllUnlocked`, `studentDemoEnabled` y `pendingContent` no afectan la disponibilidad. En desarrollo, el proxy de Vite envía `/api` a `http://127.0.0.1:8000`, sin CORS.

## Consultas por dominio

Todas son GET, reciben el código de la cuenta y responden 404 «Cuenta no encontrada» si no existe. Para un apoderado, las listas propias del estudiante salen vacías.

| Ruta | Respuesta | El front la pide |
|---|---|---|
| `/cuentas/{c}/resumen` | `ResumenCuenta`: `cuenta` y `nivel_actual` | Al ingresar (menú y panel) |
| `/cuentas/{c}/actividades` | `list[BloqueActividades]` | Al ingresar (mapa y panel del estudiante; inicio y actividades del apoderado) |
| `/cuentas/{c}/fichas` | `list[ContenidoEstado]` | Al abrir la mochila o un recurso |
| `/cuentas/{c}/logros` | `LogrosCuenta`: `insignias` y `niveles` | Al abrir el perfil, el pasaporte o una insignia |
| `/cuentas/{c}/testimonios` | `list[ContenidoEstado]` | Todavía no (sin vista) |
| `/cuentas/{c}/diario/preguntas` | `list[PreguntaDiarioEstado]` | Todavía no |
| `/cuentas/{c}/conversaciones` | `ConversacionesEstado` | Todavía no |

Además usa `/cuentas`, `/cuentas/{c}/progreso/...`, `/cuentas/{c}/desbloqueos` (no vistos y marcar vistos), las acciones `ingresar`, `completar-actividad` y `responder-items`, y las consultas de instrumentos (ítems, respuestas, avance y resultado). Todas están descritas en `motor.md` e `instrumentos.md`.

**`BloqueActividades`:** bloques por `numero` y `codigo`; actividades por `orden` y `codigo`. Cada actividad trae `codigo`, `titulo`, `tipo`, `orden`, `contenido`, `visibilidad`, `visible` y `estado` (BLOQUEADA, DISPONIBLE, EN_CURSO o COMPLETADA).

**Visibilidad:**

- `SIEMPRE`: se ve aunque esté bloqueada. `AL_DESBLOQUEAR`: solo aparece cuando deja de estar bloqueada. `visible = visibilidad == SIEMPRE or estado != BLOQUEADA`. Las actividades no visibles también se envían, con su título.
- Si el front no tiene el contenido indicado, la actividad no se muestra ni cuenta en el progreso (en desarrollo se avisa en consola) y se anota en `pendientes-interfaz.md`.
- El progreso de un bloque cuenta solo las actividades `SIEMPRE` con contenido en el front.
- En el mapa, las actividades consecutivas de un bloque que comparten `contenido` forman un solo punto («Interacción n de total»), que representa la primera no completada.

**Qué se vuelve a pedir:**

| Momento | Se pide | Se marca vencido |
|---|---|---|
| Ingreso | `/cuentas`, `ingresar` y, en paralelo, `resumen`, `actividades` y desbloqueos no vistos. El resultado RIASEC, solo si `act-tip-final` no está bloqueada. | — |
| Después de `completar-actividad` o `responder-items` | `actividades` y desbloqueos no vistos | Según `nuevos_desbloqueos[].tipo_objetivo`: FICHA → `fichas`; INSIGNIA → `logros`; NIVEL → `logros` y `resumen`. |
| Reinicio de datos de prueba | Todo vuelve a «sin cargar» y se repite el ingreso | — |

Una sección vencida con una vista montada se vuelve a pedir enseguida; si no, al abrir su vista.

El portal del apoderado tiene su propia sesión en `ov_frontend/src/store/servidor/apoderado.ts`, separada del estado del estudiante. Al ingresar consulta `/cuentas`, elige la cuenta `APODERADO` que coincide con el usuario escrito (o la primera por código), envía `ingresar` y consulta solo sus `actividades`. Tras completar vuelve a pedir `actividades`; no consulta resumen, logros ni desbloqueos del estudiante. La cuenta se conserva en memoria y se vuelve a seleccionar al recargar. Se descartan respuestas de otra sesión y se reutilizan pedidos en curso; durante una finalización solo se admite un envío, compartido si es del mismo código.

## Finalizar actividades desde el front

- El estudiante informa la finalización solo al llegar al nodo `$fin` del reproductor (`useActivityCompletion.ts`). Consultar, revelar o revisar no completa nada.
- Repetir una actividad del estudiante siempre llega al servidor (registra otro COMPLETA_ACTIVIDAD).
- El apoderado sigue la misma regla de confirmación remota en api: al terminar el último nodo, `useParentActivitySession` envía `completar-actividad` y espera la nueva consulta de `actividades` antes de mostrar el cierre. Con error conserva el nodo y permite reintentar; repasar una actividad ya completada no envía otra finalización.
- La disponibilidad, los candados y el diploma del apoderado usan el estado remoto. Los nodos JSON siguen en el front; `ov.parent-missions.v1` conserva nodo, intentos y elecciones en `accounts[codigo]`, proyectando el estado del servidor sin alterar esos datos. En local conserva `apo-prototipo`, los requisitos del JSON y la completitud local.
- Mara: cada interacción guarda sus respuestas con `responder-items` y se puede retomar. El resultado se revela cuando existe un resultado vigente en el servidor.

## Conjuntos de datos

**`plataforma`** (`datos/plataforma.py`): cuentas `est-ana`, `est-luis` y `apo-rosa` (vínculo `VIN-ANA`); bloque CAMINO con 9 actividades en secuencia; bloque CIUDAD, que se abre al completar el Camino, con las 14 interacciones de Mara (`act-tip-01`…`14`, RIASEC de 60 ítems repartidos) y `act-tip-final` (Elena); 4 fichas; insignias I1–I10 (I10 oculta); 5 niveles; RIASEC y el universo de ocupaciones y carreras del catálogo del front. Las insignias y reglas de funciones futuras (Crew, casos, entrevistas, conversaciones) ya tienen regla, para que no aparezcan como obtenidas. `mission-compass` se completa en el servidor, pero sus respuestas siguen locales.

**`piloto`** (`datos/piloto.py`): reutiliza `plataforma` con un Camino de 5 actividades, la Ciudad abierta al completar la segunda, `act-tip-final` como `AL_DESBLOQUEAR` y `cdd-sin-contenido` (una actividad cuyo contenido no existe en el front). Sirve para probar visibilidad y contenido faltante.

Ambos conjuntos incluyen el bloque `FAMILIA` («Actividades para familias»), audiencia `APODERADO`, espacio `PORTAL_FAMILIA`, disponible desde el inicio. Para `apo-rosa` contiene `pad-01-rol` («Acompañar sin decidir por él o ella», contenido `pad_01_acompanar`) y después `pad-02-info` («Conversar con información de hoy», contenido `pad_02_informacion`). Ambas son `INFORMATIVA` y `SIEMPRE`, sin ítems de instrumento ni registro; sus preguntas de práctica se evalúan en el front. La regla `R-pad-02-info` abre la segunda al completar la primera. No se agregan fichas, insignias ni niveles del apoderado; completar las dos registra `COMPLETA_BLOQUE FAMILIA` una sola vez.

## Fixtures de contrato

`scripts/exportar_fixtures_front.py --destino <ov_frontend>/tests/fixtures/servidor` crea bases temporales con `plataforma` y `piloto`, recorre los momentos de prueba y escribe 22 JSON: `resumen-inicial`; `actividades`, `fichas` y `logros` al inicio y con la Ciudad abierta; tres finalizaciones del estudiante (`completar-*`); `items-act-tip-01`; `resultado-riasec`; `desbloqueos-no-vistos`, y tres momentos de `piloto-actividades-*`. Incluye también `cuentas.json`, consultado al inicio, y cinco del apoderado con `plataforma`: `apoderado-actividades-inicial.json`, `apoderado-completar-pad-01-rol.json`, `apoderado-actividades-pad-01.json`, `apoderado-completar-pad-02-info.json` y `apoderado-actividades-final.json`. Las pruebas `tests/servidor/` del front los usan. Si cambia una respuesta del contrato, se regeneran en la misma tarea; nunca se editan a mano.

## Reinicio de datos de prueba

`POST /desarrollo/reiniciar` → `{"mensaje": "Datos de prueba reiniciados"}`, solo con `ENTORNO=desarrollo`. Borra en una transacción las tablas de `TABLAS_DE_ESTADO` (`app/services/desarrollo.py`) y conserva el catálogo (incluidas las cartas del vínculo). El front lo ofrece en el menú del estudiante solo en desarrollo y modo `api`; después borra `ov.missions.v2.api` y `ov.student-adventure.v1.api` del navegador, prepara un nuevo ingreso y recarga.

## Pendientes de interfaz

Lo que el backend entrega y ninguna vista muestra, o lo que una vista necesita y el backend no entrega, se anota en `ov_frontend/docs/pendientes-interfaz.md` con este formato y se avisa al usuario:

```markdown
## <fecha> · <dato>

- **Dato:** campo y respuesta (`ActividadCuenta.visibilidad`, `GET /cuentas/{c}/actividades`).
- **Dónde se mostraría:** vista y elemento.
- **Opciones:** 2 o 3, en una línea cada una.
- **Si no se muestra:** qué pasa hoy.
- **Estado:** pendiente.
```
