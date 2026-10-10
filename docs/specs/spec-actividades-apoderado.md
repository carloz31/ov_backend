# Actividades del apoderado desde el backend

> Especificación para `ov_backend` y `ov_frontend`, rama `iteracion-1` en los dos (backend `0ad18d6`, front `95ddd88`). Se ejecuta desde un chat con **`ov_backend` como carpeta principal** y `ov_frontend` como segunda carpeta. Se guarda en `ov_backend/docs/specs/spec-actividades-apoderado.md`. Aplica al apoderado el mismo modelo que ya usan las actividades del estudiante, descrito en `ov_backend/docs/sistema/integracion.md` y `motor.md`. Es autocontenida: **no hace falta leer `docs/historico/`** de ningún repo. Primero se hace el backend (fases B), después el front (fases F); la fase X cierra los dos.

## 0. Cómo usar este documento

- **Dónde estás.** La carpeta principal es `ov_backend`. `ov_frontend` es otra carpeta del mismo proyecto; refiérete a ella por su nombre, sin asumir una ruta relativa. En §4 y en las fases B, `app/`, `datos/`, `tests/` y `docs/` son de `ov_backend`. En §5, §6, §8 y en las fases F, `src/`, `tests/` y `docs/` son de `ov_frontend`, y sus comandos (`npm …`) se corren dentro de esa carpeta.
- Lee completos este documento y los dos `AGENTS.md` antes de empezar. Del backend, lee también `docs/sistema/integracion.md` y `docs/sistema/motor.md`; del front, `docs/origen-de-datos.md` y `docs/contenidos-actividades.md`. La regla «Datos del servidor sin vista» del `AGENTS.md` del front rige en todas las fases.
- Las referencias a la implementación del estudiante (`useActivityCompletion.ts`, `store/servidor/secciones.ts`, `proyectarJourney`, el bloque `CAMINO`) son al **código actual**, que es la referencia; no a documentos.
- Un commit por fase y por repo: `Iteración 1 · AP-B1: bloque FAMILIA`.
- Al terminar cada fase, detente y resume al usuario: qué cambiaste, qué carpetas de prueba corriste (según la política de los `AGENTS.md`), conteos antes y después en cada repo tocado y qué queda. Los conteos y líneas base van **solo en el resumen**, no en documentos.
- Al empezar, cambia el comentario de `ov_backend/docs/decisiones.md` a `<!-- Spec en curso: spec-actividades-apoderado. -->`. Si algo no está definido aquí, elige lo más simple y anótalo ahí (una viñeta por decisión), igual que las pruebas adaptadas con autorización de esta spec.
- **Nada de vistas nuevas ni modificadas**, salvo lo que §7 autoriza expresamente. Si una tarea parece imposible sin tocar una vista, detente **antes** y pide autorización.

## 1. Objetivo

1. **Que el backend liste y guarde las actividades del apoderado**, igual que ya hace con las del estudiante (`integracion.md`, «Consultas por dominio»): bloque, actividades, orden, tipo, `contenido`, `visibilidad`, estado y regla de desbloqueo salen del backend, y completar una actividad se registra con `POST /acciones/completar-actividad`.
2. **Que el front deje solo el JSON.** Las dos actividades que hoy existen (`pad_01_acompanar.json` y `pad_02_informacion.json`) siguen en `src/data/activities/contenidos/`. En modo `api`, el portal del apoderado arma su lista, su progreso, sus candados y su completitud con lo que dice el backend, y encuentra cada contenido por la clave `contenido`.
3. **Sin endpoints nuevos.** Se reutilizan `GET /cuentas`, `POST /acciones/ingresar`, `GET /cuentas/{c}/actividades` y `POST /acciones/completar-actividad`, que ya filtran por audiencia.

## 2. Situación actual

| Tema | Hoy |
|---|---|
| Backend: bloques | `plataforma` tiene `CAMINO` y `CIUDAD`, ambos con audiencia `ESTUDIANTE`. No hay ningún bloque `APODERADO`. |
| Backend: cuenta del apoderado | `apo-rosa` (`APODERADO`), vinculada a `est-ana` por `VIN-ANA`. `GET /cuentas/apo-rosa/actividades` devuelve `[]`. |
| Backend: lógica | Ya soporta la audiencia: `listar_bloques_cuenta` filtra por `bloque.audiencia == cuenta.rol`; `objetivo_corresponde_a_cuenta` compara la audiencia del bloque de la actividad con el rol; `completar_actividad` solo rechaza al apoderado si la actividad tiene ítems de instrumento o de registro. `NIVEL` y `FICHA` corresponden solo al estudiante; las insignias de `plataforma` son `ESTUDIANTE`. |
| Backend: `Espacio` | `MISIONES_CAMPO` y `CIUDAD`, guardado como `Enum(native_enum=False, create_constraint=True)`: agregar un valor requiere migración. |
| Front: contenidos | `pad_01_acompanar.json` (`id: "pad-01-rol"`, `orden: 1`, `requisitos: []`) y `pad_02_informacion.json` (`id: "pad-02-info"`, `orden: 2`, `requisitos: ["pad-01-rol"]`), ambos `audiencia: "apoderado"`, registrados en `contenidos.ts`. |
| Front: lista | `parentActivities` en `src/data/activities/content.ts`: filtra `audiencia === 'apoderado'` de una lista fija de claves y ordena por `orden`. La reexporta `features/parent/data/parentPortal.ts`. |
| Front: progreso y candados | 100 % local en `features/parent/store/parentJourneyStore.ts` (`localStorage` `ov.parent-missions.v1`, cuenta fija `apo-prototipo`). La disponibilidad sale de `requisitos` (`parentActivityAvailable`) y la completitud, de `nodoActualId === '$fin'` y de las preguntas bloqueantes resueltas (`isParentActivityComplete`, `applyCompletion`). |
| Front: sesión con el servidor | Solo existe para el estudiante: `seleccionarCuenta` elige siempre una cuenta `ESTUDIANTE` (por defecto `est-ana`), y `asegurarSeccion('actividades')` hidrata `journeyStore` y `adventureStore` del estudiante. El portal del apoderado nunca llama al backend. |
| Front: quién usa la lista | `ParentPortalModule` (ids completados para el contexto), `ParentActivitiesView` (tarjetas, candados, progreso), `ParentActivityView` (acceso por enlace y repaso), `useParentActivitySession` (reproductor y ruta) y `useParentOverview` (resumen de inicio y diploma). |

## 3. Decisiones

- **DA1. Mismo modelo que el estudiante.** Un bloque de audiencia `APODERADO` con sus actividades, contenidos por clave y reglas de desbloqueo. El front no decide en modo `api` si una actividad del apoderado está disponible o completada.
- **DA2. Códigos = ids del front.** Las actividades se llaman en el backend `pad-01-rol` y `pad-02-info`, los `id` actuales de los JSON (regla «Los códigos del backend son los ids del front»). El campo `codigo` interno de los JSON (`ACT-P01`, `ACT-P02`) no se usa en el contrato y no cambia.
- **DA3. Bloque `FAMILIA`.** `codigo = 'FAMILIA'`, `numero = 1`, `nombre = 'Actividades para familias'`, `espacio = 'PORTAL_FAMILIA'` (valor nuevo de `Espacio`), `audiencia = 'APODERADO'`. Sin regla de bloque: está disponible desde el inicio.
- **DA4. Actividades.** Las dos `INFORMATIVA` y `SIEMPRE`, sin ítems de instrumento ni de registro. Sus preguntas son de práctica y las evalúa el front; el backend no las conoce.
- **DA5. Una regla.** `R-pad-02-info`: `ACTIVIDAD pad-02-info` con `COMPLETA_ACTIVIDAD pad-01-rol`, `EVENTOS`, 1. Es la misma dependencia que hoy expresa `requisitos` en el JSON. En modo `api`, `requisitos` **no** se lee; en modo `local` se sigue leyendo.
- **DA6. Qué guarda cada lado.** El backend guarda estado (disponible, completada) y eventos. El nodo actual, los intentos de pregunta y las elecciones registrables siguen en `ov.parent-missions.v1`, **con el mismo formato**, bajo el código de la cuenta del servidor (`apo-rosa`) en lugar de `apo-prototipo`. Es otra entrada de `accounts`; no hace falta migración.
- **DA7. Sesión del apoderado aparte.** El apoderado usa su propio estado de servidor (`src/store/servidor/apoderado.ts`), sin tocar el almacén, `journeyStore` ni `adventureStore` del estudiante. Comparte con él solo `services/api/` y el usuario escrito al ingresar.
- **DA8. Selección de cuenta.** De `GET /cuentas`, la cuenta `APODERADO` cuyo `codigo` coincide con el usuario escrito al ingresar; si no hay, la primera `APODERADO` por `codigo` (en `plataforma`, `apo-rosa`). Sin cuentas `APODERADO`, error.
- **DA9. Completar.** En modo `api`, llegar al final de la actividad no la marca completada en local: el front llama a `completar-actividad` y la completitud llega al volver a pedir `actividades`, como hace hoy el estudiante (`features/activities/hooks/useActivityCompletion.ts`; `integracion.md`, «Finalizar actividades desde el front»).
- **DA10. `plataforma` y `piloto`.** Los dos conjuntos reciben el bloque `FAMILIA` (piloto ya reutiliza `_cargar_estructura`). Las actividades y reglas del estudiante no cambian.
- **DA11. El modo `local` no cambia.** Sigue usando `parentActivities`, `requisitos`, `apo-prototipo` y la completitud local.
- **DA12. Sin contenido, invisible.** Como en el estudiante (`integracion.md`, «Visibilidad»): si el front no tiene el `contenido` que indica el backend, la actividad no se muestra ni cuenta en el progreso; en desarrollo se avisa en consola una vez por actividad.

## 4. Backend

### 4.1 Modelo y migración

- `app/models/enums.py`: `Espacio` agrega `PORTAL_FAMILIA = "PORTAL_FAMILIA"`.
- `migrations/versions/0003_espacio_portal_familia.py`, generada con `--autogenerate` y **revisada a mano**: el `CHECK` del enumerado de `bloque.espacio` pasa a aceptar el valor nuevo, con `render_as_batch` (SQLite). Si `--autogenerate` no detecta el cambio del `CHECK` (es habitual con `native_enum=False`), escríbelo a mano con `batch_alter_table` y anótalo. El `downgrade` vuelve al `CHECK` anterior y falla si existe un bloque `PORTAL_FAMILIA` (anótalo así; no borra datos).
- `tests/integration/migraciones/` sigue en verde: base nueva, base en `0002` actualizada a `0003`, y un bloque con `espacio = 'OTRO'` sigue rechazado.

### 4.2 Datos (`datos/plataforma.py`)

```python
BLOQUES = (('CAMINO', 1, 'El camino', 'MISIONES_CAMPO', 'ESTUDIANTE'),
           ('CIUDAD', 2, 'La ciudad', 'CIUDAD', 'ESTUDIANTE'),
           ('FAMILIA', 1, 'Actividades para familias', 'PORTAL_FAMILIA', 'APODERADO'))

ACTIVIDADES_FAMILIA = (('pad-01-rol', 'Acompañar sin decidir por él o ella', 'INFORMATIVA'),
                       ('pad-02-info', 'Conversar con información de hoy', 'INFORMATIVA'))
```

- Los títulos son los `titulo` actuales de los JSON. Si cambian en el front, cambian aquí.
- `CONTENIDOS_ACTIVIDADES` agrega `'pad-01-rol': 'pad_01_acompanar'` y `'pad-02-info': 'pad_02_informacion'`.
- `REGLAS` agrega `('R-pad-02-info', 'ACTIVIDAD', 'pad-02-info', (('COMPLETA_ACTIVIDAD', 'pad-01-rol', 'EVENTOS', 1),), None)`.
- `_cargar_estructura` recibe un parámetro `familia=ACTIVIDADES_FAMILIA` y recorre `(('CAMINO', camino), ('CIUDAD', ciudad), ('FAMILIA', familia))`. `numero` se repite (1) entre bloques de audiencias distintas: nunca se listan juntos y el orden secundario por `codigo` lo desempata.
- `datos/piloto.py` no necesita cambios si llama a `_cargar_estructura` sin `familia`; compruébalo.
- No se agregan insignias, niveles ni fichas del apoderado.

### 4.3 Comportamiento esperado (sin cambios de código salvo que una prueba lo exija)

| Caso | Resultado |
|---|---|
| `GET /cuentas/apo-rosa/actividades` al inicio | Un bloque `FAMILIA` `DISPONIBLE`; `pad-01-rol` `DISPONIBLE`, `pad-02-info` `BLOQUEADA`, las dos `visible: true`. |
| `GET /cuentas/est-ana/actividades` | Idéntico a hoy (no ve `FAMILIA`). |
| `completar-actividad` de `pad-01-rol` por `apo-rosa` | 200; `eventos_registrados` con `COMPLETA_ACTIVIDAD pad-01-rol`; `nuevos_desbloqueos` con solo `R-pad-02-info`. |
| `completar-actividad` de `pad-02-info` por `apo-rosa` antes de `pad-01-rol` | 409, igual que cualquier actividad bloqueada. |
| `completar-actividad` de `pad-02-info` después | 200; eventos `COMPLETA_ACTIVIDAD pad-02-info` y `COMPLETA_BLOQUE FAMILIA`; `nuevos_desbloqueos` vacío. |
| `completar-actividad` de `pad-01-rol` por `est-ana` | 409 (la actividad no corresponde a su audiencia). |
| Completar de nuevo una actividad del apoderado | Igual que una del estudiante hoy (no duplica `COMPLETA_BLOQUE`). |
| Resumen, logros, fichas de `apo-rosa` | Sin cambios: `nivel_actual: null`, listas vacías. Completar actividades del apoderado no desbloquea niveles, insignias ni fichas: `R-I2`, `R-NIV-*` y demás usan `COMPLETA_ACTIVIDAD` sin referencia, pero sus objetivos no corresponden al apoderado. **Pruébalo**; si alguno se desbloquea, detente y avisa. |

Si alguno de estos casos falla con el código actual, corrige lo mínimo en `app/services/` y anótalo.

### 4.4 Pruebas del backend

- **Nueva** `tests/integration/actividades/test_actividades_apoderado.py`: todos los casos de §4.3, con `plataforma` y con `piloto`.
- **Adaptaciones autorizadas** (anótalas en `docs/decisiones.md`, una viñeta con la lista de pruebas tocadas; ninguna otra aserción cambia):
  1. Las que afirman que `apo-rosa` no tiene bloques o actividades (`test_apoderado_sin_listas_estudiantiles` para la ruta `actividades`, `test_invariantes_plataforma`, `test_p14_audiencia` y las que encuentres con el mismo sentido) pasan a esperar **solo** el bloque `FAMILIA` con sus dos actividades. Las demás listas del apoderado siguen vacías.
  2. Conteos de filas de `plataforma` y `piloto` (`actividad` +2, `bloque` +1, `regla_desbloqueo` +1) y listas exactas de bloques o reglas.
  3. Pruebas que fijan la cabeza de Alembic (si alguna quedó con una revisión literal).

### 4.5 Fixtures para el front

`scripts/exportar_fixtures_front.py` agrega, con `plataforma` y bases temporales como hoy:

| Fixture | Petición | Momento |
|---|---|---|
| `cuentas.json` | `GET /cuentas` | Inicio (si ya existe uno equivalente, reutilízalo y anótalo) |
| `apoderado-actividades-inicial.json` | `GET /cuentas/apo-rosa/actividades` | Inicio |
| `apoderado-completar-pad-01-rol.json` | `POST /acciones/completar-actividad` | Primera actividad |
| `apoderado-actividades-pad-01.json` | `GET /cuentas/apo-rosa/actividades` | Tras `pad-01-rol` |
| `apoderado-completar-pad-02-info.json` | `POST /acciones/completar-actividad` | Segunda actividad |
| `apoderado-actividades-final.json` | `GET /cuentas/apo-rosa/actividades` | Tras las dos |

Los fixtures actuales del estudiante no cambian; si alguno cambia, detente y avisa. `tests/integration/contrato/test_exportar_fixtures_front.py` se amplía con los nuevos. Como siempre, los fixtures se regeneran con el script y nunca se editan a mano.

## 5. Front: datos del servidor

### 5.1 Tipos y servicios

- `src/types/servidor.ts`: `BloqueEstado.espacio` agrega `'PORTAL_FAMILIA'`. No hay tipos nuevos: el apoderado usa `CuentaResumen`, `BloqueActividades`, `ActividadCuenta` y `RespuestaCompletarActividad`.
- `src/services/api/`: sin cambios. Se reutilizan `listarCuentas`, `ingresar`, `obtenerActividades` y `completarActividad`.

### 5.2 Estado: `src/store/servidor/apoderado.ts` (nuevo)

Un almacén pequeño y aislado del estudiante (DA7), con las mismas reglas de `store/servidor/`: descartar respuestas de otra cuenta o sesión y no duplicar pedidos en curso.

```ts
type AlmacenApoderado = {
  cuenta: string | null
  actividades: Seccion<BloqueActividades[]>   // Seccion se importa de ./sesion
  error: ErrorServidor | null                 // del ingreso
  enviando: string | null                     // código en completar-actividad
}
```

| Función | Hace |
|---|---|
| `ingresarApoderado()` | Si ya hay un ingreso en curso o hecho en esta sesión, lo reutiliza. Si no: `listarCuentas` → elige la cuenta (DA8, con el usuario que guarda `store/servidor/cuenta.ts`; exporta para eso un `usuarioIngreso()`) → `ingresar(cuenta)` → `asegurarActividadesApoderado()`. |
| `asegurarActividadesApoderado()` | Pide `obtenerActividades(cuenta)` si la sección está `sin_cargar` o `vencido`; con la respuesta, hidrata el almacén local del apoderado para esa cuenta con `proyectarJourney(bloques, actual, cuenta)` (§5.4). |
| `completarActividadApoderado(codigo)` | Si `enviando` ya es `codigo`, reutiliza la promesa. `completarActividad(cuenta, codigo)`; con 200, vence y vuelve a pedir `actividades` y devuelve la respuesta; con error, lo devuelve sin tocar nada. |
| `limpiarEstadoApoderado()` | Vuelve todo al estado inicial y sube la revisión de sesión. Se llama donde hoy se llama `limpiarEstadoServidor` (`prepararIngreso` y el reinicio de datos de desarrollo). |
| `useEstadoApoderado()` | `useSyncExternalStore` sobre el almacén. |

- Nada se guarda en `sessionStorage` ni `localStorage` nuevo: la cuenta se vuelve a elegir al recargar (una petición a `/cuentas`).
- **Movimiento de `parentJourneyStore`.** La hidratación la hace `store/servidor/apoderado.ts`, y `store/` no puede importar `features/`. Por eso la persistencia de `ov.parent-missions.v1` se mueve tal cual de `features/parent/store/parentJourneyStore.ts` a `src/store/parentJourneyStore.ts` (estado persistente que ahora usan dos capas, como `journeyStore`). Agrega ahí `hidratarParentJourney(cuenta, transformar)`, que escribe solo la entrada de esa cuenta. Clave, formato y validación de lectura **idénticos**: las pruebas `parent-missions` pasan sin cambiar aserciones, solo la ruta del import. Si la carpeta `features/parent/store/` queda vacía, se borra. Actualiza la fila de `ov.parent-missions.v1` en `docs/origen-de-datos.md` (tabla de claves).

### 5.3 Contenidos (`src/lib/servidor/contenidos.ts`)

Agrega `actividadesApoderado(bloques)`:

1. Toma las actividades del bloque con `espacio === 'PORTAL_FAMILIA'` (no por código: el código del bloque es un dato), en el orden del backend.
2. Descarta las `visible: false` y las que no tienen contenido (`contenidoPorClave`). Devuelve aparte la lista de códigos sin contenido para que el hook avise (DA12; `lib/` no importa `store/`).
3. Para cada una, devuelve el `Actividad` del JSON (sin `mapa`) con `id = actividad.codigo`, `titulo = actividad.titulo`, `orden` = su posición en la lista del backend (1, 2, …) y `requisitos = []`.

También agrega `disponiblesApoderado(bloques): Set<string>` (estado distinto de `BLOQUEADA`) y `completadasApoderado(bloques): string[]` (estado `COMPLETADA`). Si prefieres ponerlas en `adaptadores.ts`, solo pueden importar tipos.

### 5.4 Progreso local en modo `api`

- La entrada de `ov.parent-missions.v1` que se usa es la de la cuenta del servidor (`apo-rosa`).
- `proyectarJourney` (ya existe y solo importa tipos) fija `estado` desde el servidor y conserva `nodoActualId`, intentos y elecciones. Úsalo tal cual para el apoderado; si necesita un ajuste, que no cambie su resultado para el estudiante.
- Los registros locales que valida la lectura (`estudianteId === accountId`) quedan coherentes porque `proyectarJourney` escribe `estudianteId = cuenta`.

## 6. Front: dominio del apoderado

### 6.1 Un hook que elige la fuente: `features/parent/hooks/useParentActivities.ts` (nuevo)

Es el único lugar que mira `modoApi` en el dominio (regla «Elegir entre dato del servidor y dato local»). Devuelve el mismo modelo en los dos modos; las vistas no reciben `modoApi` (lo que solo aplica en `api` va como bandera con nombre del dominio, aquí `loading`).

```ts
type ParentActivitiesSource = {
  activities: Actividad[]          // ordenadas
  accountId: string                // 'apo-prototipo' en local; código del servidor en api
  journey: JourneyState            // del almacén local del apoderado, para accountId
  completedIds: string[]
  available: (activity: Actividad) => boolean
  loading: boolean                 // solo api: ingreso o actividades sin 'listo'
  error: ErrorServidor | null      // solo api
}
```

| | Modo `local` (igual que hoy) | Modo `api` |
|---|---|---|
| `activities` | `parentActivities` | `actividadesApoderado(bloques)`; avisa con `avisarContenidoFaltante` por cada código sin contenido |
| `accountId` | `parentAccountId` | `useEstadoApoderado().cuenta` |
| `completedIds` | `completedParentActivities(parentActivities, journey)` | `completadasApoderado(bloques)` |
| `available` | `parentActivityAvailable(activity, journey)` | `disponiblesApoderado(bloques).has(activity.id)` |
| Efecto al montar | — | `ingresarApoderado()` |

### 6.2 `features/parent/lib/missionLogic.ts`

La lógica pura no cambia para `local`. Agrega un último parámetro opcional `opciones?: { disponible?: boolean; servidor?: boolean }`:

- `disponible`: si viene, reemplaza a `parentActivityAvailable(activity, state)` en `startParentActivity`, `answerParentQuestion`, `retreatParentActivity` y `advanceParentActivity`.
- `servidor: true`: `advanceParentActivity` **no** llama a `applyCompletion` (DA9). Avanza `nodoActualId` hasta `'$fin'` como hoy, con `estado: 'en_curso'` si no estaba completada.
- `parentRoute(activities, children, completedIds, available?)`: si viene `available`, `next` es la primera no completada con `available(activity)`; si no, la regla de `requisitos` de hoy.

Agrega una función pura `readyToCompleteOnServer(activity, state)`: verdadera si `isParentActivityComplete` lo sería con `nodoActualId === '$fin'` (todas las preguntas bloqueantes resueltas). La usa el hook al terminar.

### 6.3 Quién cambia de fuente

| Archivo | Cambio |
|---|---|
| `pages/parent/ParentPortalModule.tsx` | `completedActivityIds` sale de `useParentActivities()`. El contexto del `Outlet` agrega `activities`, `available` y `accountId` (actualiza `ParentPortalContext`). Marcado y navegación sin cambios. |
| `pages/parent/ParentActivitiesView.tsx` | Usa `activities`, `available` y `journey` del contexto en lugar de `parentActivities`, `parentActivityAvailable` y `useParentJourney()`. `parentRoute` recibe `available`. Marcado sin cambios. |
| `pages/parent/ParentActivityView.tsx` | Busca la actividad en `activities` y usa `available`. Repaso: `journey.progress[id]?.estado === 'completada'` (en `api`, proyectado del servidor). Ver §7 para el estado de carga. |
| `features/parent/hooks/useParentActivitySession.ts` | Recibe `activities`, `available`, `accountId` y `journey` (del contexto o de `useParentActivities`). Pasa `{ disponible, servidor: modoApi }` a la lógica. **Al terminar en `api`:** en el último nodo, si `readyToCompleteOnServer`, llama a `completarActividadApoderado(activity.id)` antes de `setCelebrate` y `showNext`; mientras envía, `advance` no hace nada; con 200 sigue como hoy (celebra y pasa a la pantalla final); con error, se queda en el nodo y el mensaje `mensajeErrorServidor(error)` sale por el mismo `error` que ya muestra `ParentActivitySession`. Volver a pulsar reintenta. |
| `features/parent/hooks/useParentOverview.ts` | `parentRoute` con `activities`, `completedIds` y `available` del contexto. El resto (hijos, cuestionarios, conversaciones) sigue con los datos de demostración. |
| `features/parent/data/parentPortal.ts` | Deja de reexportar `parentActivities` si ya nadie lo importa desde aquí; `content.ts` lo sigue exportando para `local`. |

`src/data/activities/content.ts` y `contenidos.ts` no cambian: los JSON se quedan, y la lista fija de claves sigue armando el catálogo local (DA11).

## 7. Interfaz: qué cambia y qué no

**Única excepción autorizada:** en modo `api`, mientras `useParentActivities().loading` sea verdadero, `ParentActivityView` devuelve `null` en lugar de `ActivityUnavailable` (para que un enlace directo no muestre «no disponible» antes de que lleguen los datos). Sin marcado, texto ni estilo nuevos.

Todo lo demás se ve idéntico en `local` y en `api` con `plataforma`: misma lista, mismos candados, mismo progreso, mismo diploma. Lo que no tiene dónde mostrarse va a `ov_frontend/docs/pendientes-interfaz.md`, con el formato de `integracion.md` («Pendientes de interfaz»):

- **Carga y error del portal del apoderado en `api`.** No existe un aviso de carga ni de error de servidor en la lista ni en el inicio: mientras carga se ve «0 de 0 actividades»; si falla, la lista queda vacía. El error sí llega al hook (`useParentActivities().error`).
- **Nombre del apoderado.** `ResumenCuenta.cuenta.nombre` (o `CuentaResumen.nombre` de `/cuentas`) podría reemplazar a `parentProfile.name` de demostración; no se conecta en esta spec.
- **Hijos y progreso del hijo.** Siguen saliendo de `parentPortal.ts` y `studentProfiles` (demostración); el vínculo `VIN-ANA` no tiene consulta de lectura.
- **`COMPLETA_BLOQUE FAMILIA`.** Llega en `eventos_registrados` y no tiene vista propia (el diploma sigue saliendo de `route.complete`).

## 8. Pruebas del front

### 8.1 Línea base

Antes de AP-F1, corre `npm test` e informa el conteo en el resumen de la fase (no en un documento). Las fallas previas conocidas son las 14 de `tests/local/aventura/adventure-rendering.test.mjs`; deben seguir siendo esas y ninguna más.

### 8.2 Adaptaciones autorizadas

Solo rutas de import (por el movimiento de `parentJourneyStore` a `src/store/`) y la firma nueva de `parentRoute` y de `ParentPortalContext` en las pruebas que los construyen. **Ninguna aserción de `tests/local/portales/parent-missions.test.mjs` cambia.** Anótalas en `ov_backend/docs/decisiones.md`.

### 8.3 Pruebas nuevas

`tests/servidor/actividades/servidor-apoderado.test.mjs`, con los fixtures de §4.5:

- **Selección de cuenta:** con `cuentas.json` y usuario `apo-rosa` → `apo-rosa`; con usuario `est-ana` o vacío → la primera `APODERADO`; sin cuentas `APODERADO` → error. El almacén del estudiante (`obtenerEstadoServidor()`) no cambia.
- **Lista inicial:** `actividadesApoderado(inicial)` da dos actividades, ids `pad-01-rol` y `pad-02-info`, títulos del servidor, nodos idénticos (`deepEqual`) a los de los JSON; `pad-01-rol` disponible y `pad-02-info` no, aunque su JSON diga `requisitos`.
- **Completar:** con `apoderado-completar-pad-01-rol.json` y luego `apoderado-actividades-pad-01.json`, `pad-01-rol` queda completada y `pad-02-info` disponible; la entrada `apo-rosa` de `ov.parent-missions.v1` conserva intentos y elecciones y no se toca la de `apo-prototipo`.
- **Sin completitud local en `api`:** `advanceParentActivity(..., { servidor: true })` en el último nodo deja `nodoActualId: '$fin'` y `estado` distinto de `'completada'`.
- **Error al completar:** con un 409 simulado, el progreso no cambia y `completarActividadApoderado` devuelve el error; un segundo intento simultáneo reutiliza la promesa.
- **Contenido faltante:** un bloque `PORTAL_FAMILIA` con una actividad `contenido: 'sin_contenido_prueba'` (armado en la prueba, `DATO DE PRUEBA`) se descarta y se informa su código.
- **Descarte por sesión:** una respuesta que llega después de `limpiarEstadoApoderado()` no se publica.
- **Ruta y diploma:** con `apoderado-actividades-final.json`, `parentRoute(...).complete` es verdadero y `percent` es 100.

`contenidos.test.mjs` agrega: todo `contenido` de los fixtures `apoderado-*` existe en el registro.

## 9. Fases

| Fase | Repo | Contenido | Para terminar |
|---|---|---|---|
| AP-B0 | ambos | Línea base: `uv run pytest -n auto -q` en el backend y `npm test` en el front. Encabezado de `docs/decisiones.md` (§0). Sin commit si no cambia nada más que el comentario (va en el de AP-B1). | Conteos informados en el resumen. |
| AP-B1 | backend | `Espacio.PORTAL_FAMILIA` y migración `0003` (§4.1); bloque, actividades, contenidos y regla (§4.2); `test_actividades_apoderado.py` y adaptaciones (§4.4). | Carpetas de impacto + `tests/integration/escenarios` en verde; `alembic upgrade head` sobre base nueva y sobre una en `0002`. |
| AP-B2 | backend | Fixtures (§4.5), exportados a `ov_frontend/tests/fixtures/servidor/`. | Pruebas del exportador en verde; commit en el front: `Iteración 1 · AP-B2: fixtures del apoderado`. |
| AP-F1 | front | `espacio` en `types/servidor.ts`; `parentJourneyStore` a `src/store/` (§5.2); `store/servidor/apoderado.ts`; `actividadesApoderado`, `disponiblesApoderado`, `completadasApoderado` (§5.3). Ninguna vista cambia todavía. | `npm run test:servidor`, `tests/local/portales`, `tests/local/perfil` y `npm run check:estructura` en verde. |
| AP-F2 | front | `useParentActivities`, parámetros nuevos de `missionLogic` y `parentRoute`, y cambio de fuente de §6.3; excepción de §7. `servidor-apoderado.test.mjs`. | Mismas pruebas que AP-F1 más la nueva; `grep -rn "parentActivities" src/pages src/features/parent` solo encuentra el hook. |
| AP-F3 | ambos | Prueba manual (§10). `docs/pendientes-interfaz.md` con lo de §7. `docs/origen-de-datos.md`: las actividades del apoderado pasan de «local» a «servidor (estado) + front (contenido)». | Recorrido hecho e informado en el resumen. |
| AP-X | ambos | Suite completa de los dos repos (`uv run pytest -n auto -q`; `npm test`, `npm run build`, `npm run lint`, `npm run check:estructura`). Cierre de la spec (§11). | Todo en verde; spec y decisiones movidas a `docs/historico/`. |

## 10. Prueba manual (AP-F3)

Backend:

```powershell
uv run python -m datos.cargar plataforma --vaciar
uv run uvicorn app.main:app --reload
```

Front: `VITE_DATOS=api` en `.env.local`; `npm run dev`. Ingresa con el usuario `apo-rosa` y elige «Madre, padre o apoderado».

1. **Peticiones.** En la pestaña Red, al entrar al portal salen `/cuentas`, `/acciones/ingresar` (con `apo-rosa`) y `/cuentas/apo-rosa/actividades`. No sale nada de `est-ana`.
2. **Lista.** «Mis actividades» muestra las dos actividades con los mismos textos de hoy; la segunda, con candado; progreso «0 de 2».
3. **Enlace directo.** Abre `/parent/activities/pad-02-info`: muestra «no disponible» con candado (tras la carga, sin parpadeo).
4. **Completar la primera.** Recorre `pad-01-rol` hasta el final: sale `completar-actividad` y luego `actividades`; la pantalla final aparece después de la respuesta. Al volver, «1 de 2» y la segunda abierta.
5. **Recarga.** Recarga a mitad de `pad-02-info`: retoma el nodo y los intentos guardados; la primera sigue completada (viene del servidor).
6. **Error.** Detén el backend y termina `pad-02-info`: se queda en el último paso con el mensaje de conexión; vuelve a levantarlo y pulsa de nuevo: se completa. Inicio muestra el diploma.
7. **Estudiante intacto.** Sal, ingresa como `est-ana` en el portal del estudiante: el mapa y el panel se ven igual que antes de esta spec.
8. **Local.** Con `VITE_DATOS=local`, el portal del apoderado funciona exactamente como antes (cuenta `apo-prototipo`, candado por `requisitos`).

Repite 1–4 con `uv run python -m datos.cargar piloto --vaciar`.

## 11. Cierre de la spec (fase AP-X)

Según «Documentación» de las reglas compartidas, lo que siga vigente se incorpora a los documentos vigentes; después la spec y las decisiones pasan al histórico.

**Backend:**

- `docs/sistema/integracion.md`: en «Conjuntos de datos», el bloque `FAMILIA` del apoderado (`apo-rosa`) con `pad-01-rol` y `pad-02-info` en secuencia, en `plataforma` y `piloto`; en «Fixtures de contrato», el nuevo total de JSON y los `apoderado-*` y `cuentas`; en «Finalizar actividades desde el front», que el apoderado sigue la misma regla (finaliza solo en el servidor en modo `api`; intentos y nodo actual quedan en local).
- `docs/sistema/motor.md`: en el catálogo, `bloque.espacio` también puede ser `PORTAL_FAMILIA`.
- `AGENTS.md`, en «Dónde va cada cosa», fila «Una actividad»: agrega «Si es del apoderado, en un bloque de audiencia `APODERADO` y espacio `PORTAL_FAMILIA`.»
- Mueve esta spec y `docs/decisiones.md` a `docs/historico/actividades-apoderado/` y deja `docs/decisiones.md` solo con su encabezado (`<!-- Spec en curso: ninguna. -->`).

**Front:**

- `AGENTS.md`, en «Dónde va cada cosa», fila «Estado que viene del servidor»: agrega «El del portal del apoderado, en `store/servidor/apoderado.ts`; no reutiliza el almacén del estudiante.»
- `docs/origen-de-datos.md` ya quedó actualizado en AP-F1 y AP-F3; compruébalo.

«Reglas compartidas» no cambia: el «Contrato» ya cubre las dos audiencias. Ningún documento vigente debe remitir a esta spec después de moverla.

## 12. Fuera de alcance

- Guardar en el backend los intentos de pregunta, las elecciones o el nodo actual del apoderado.
- Insignias, niveles o fichas del apoderado.
- Conectar el nombre del apoderado, sus hijos (`VinculoFamiliar`) o el progreso del hijo.
- Conversaciones en familia y carta del apoderado (iteración 4).
- Recursos de las actividades del apoderado (`recursoIds`) como fichas del servidor: siguen en `catalogo.json`.
- Quitar `requisitos` de los JSON o la lista fija de claves de `content.ts` (los usa el modo `local`).
