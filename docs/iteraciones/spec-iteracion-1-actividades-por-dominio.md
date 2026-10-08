# Iteración 1 · Actividades desde el backend y consultas por dominio

> Especificación para `ov_backend` y `ov_frontend`, ramas `iteracion-1` (backend `a54e200`, front `a2d638f`). Se ejecuta desde un chat con **`ov_backend` como carpeta principal** y `ov_frontend` como segunda carpeta. Se guarda en `ov_backend/docs/iteraciones/spec-iteracion-1-actividades-por-dominio.md` y extiende `spec-iteracion-1.md`: donde hablen de lo mismo, **prevalece esta**. Primero se hace el backend (fases B) y después el front (fases F); la fase X cierra los dos.

## 0. Cómo usar este documento

- **Dónde estás.** La carpeta principal es `ov_backend`: su `AGENTS.md` es el que se lee por defecto. `ov_frontend` es otra carpeta del mismo proyecto; refiérete a ella por su nombre, sin asumir una ruta relativa. En §5 y en las fases B, `app/`, `datos/`, `tests/` y `docs/` son de `ov_backend`. En §6, §7, §9 y en las fases F, `src/`, `tests/` y `docs/` son de `ov_frontend`, y sus comandos (`npm …`) se corren dentro de esa carpeta.
- Lee completos este documento, `spec-iteracion-1.md` y `ov_backend/AGENTS.md` antes de empezar, y **también `ov_frontend/AGENTS.md` antes de la primera fase F**: el front tiene reglas propias (estructura, verificador, áreas de presentación) que no están en el `AGENTS.md` del backend.
- Se trabaja en `iteracion-1` de cada repo. Un commit por fase y por repo: `Iteración 1 · B2: consultas por dominio`.
- Al terminar cada fase, detente y resume: qué cambiaste, conteo de pruebas antes y después en cada repo tocado y qué queda.
- Si algo no está definido aquí, elige lo más simple y anótalo en `ov_backend/docs/iteraciones/decisiones-iteracion-1.md`.
- **Nada de vistas nuevas ni modificadas.** Rige desde ya la regla del Anexo A, «Datos del servidor sin vista», aunque todavía no esté en los `AGENTS.md` (B0 la agrega). En resumen: si el backend devuelve un dato que el front no tiene cómo mostrar, el dato llega hasta el hook del dominio y **no se pinta**. Se anota en `ov_frontend/docs/pendientes-interfaz.md` y se avisa en el resumen de la fase. Si una tarea parece imposible sin tocar una vista, detente **antes** y pide autorización. Esta spec no autoriza ningún cambio de interfaz (§8).

## 1. Objetivo

1. **Que el backend liste las actividades.** Bloques, actividades, orden, tipo, visibilidad y estado salen del backend. El front solo guarda el contenido de cada actividad (un JSON por contenido) y lo encuentra por la clave que el backend indica.
2. **Que cada pantalla pida lo que muestra.** `GET /cuentas/{c}/estado`, que hoy devuelve todo de una vez, se reemplaza por consultas por dominio. Al iniciar sesión solo se carga lo que se ve siempre (mapa, panel y menú); el resto se pide al abrir su vista.
3. **Probarlo con un conjunto chico:** 5 actividades en el Camino y la Ciudad abierta al completar la segunda.

## 2. Situación actual

| Tema | Hoy |
|---|---|
| Consulta de estado | `GET /cuentas/{c}/estado` devuelve cuenta, nivel, niveles, bloques con actividades, fichas, testimonios, preguntas del diario, conversaciones e insignias. El front la pide al ingresar y **después de cada** `completar-actividad` y `responder-items`, junto con los desbloqueos no vistos y, si corresponde, el resultado RIASEC. |
| Qué usa el front | `cuenta`, `nivel_actual`, `bloques`, `fichas`, `insignias` y `niveles`. Nunca lee `testimonios`, `preguntas_diario` ni `conversaciones`. |
| Actividad en el backend | `codigo`, `titulo`, `tipo` (`INFORMATIVA`, `REGISTRO`, `CUESTIONARIO`, `CASO`), `orden`, `bloque_id`, `puntaje_minimo`. No sabe qué contenido usa ni si se ve en el mapa. |
| Actividad en el front | El Camino sale de `baseRoute` y `fieldMissions` (posición, etiqueta e ícono por misión); la Ciudad, de `ciudadPoints.ts`, donde las 14 interacciones de Mara son un solo punto. En modo `api`, el front cruza su lista con el estado del servidor por código. |
| Contenidos | 5 en JSON (`encuentro_mitos`, `registro_mis_pregones`, `registro_linea_tiempo`, `instrumento_mara` y los dos del apoderado) y 7 escritos en TypeScript (`standardActivities.ts` y `finalActivity` en `content.ts`). Las 14 interacciones de Mara usan el mismo contenido. |
| Bloques | Se ordenan por `codigo` (CAMINO antes que CIUDAD por orden alfabético, no por diseño). |
| Señal de hoy | Local en los dos modos (`features/adventure/lib/checkIn.ts`). El backend tiene `POST /acciones/check-in`, que el front no usa, y ninguna lectura. |
| `AGENTS.md` del backend | Su sección «Reglas compartidas» todavía menciona `src/features/servidor/`; la del front ya está actualizada. |

## 3. Decisiones

- **D1. Contenido por clave.** Cada actividad tiene un campo `contenido`: la clave del JSON que la presenta en el front. Varias actividades pueden compartir contenido (las 14 de Mara usan `instrumento_mara`). La clave no es el código de la actividad.
- **D2. Visibilidad aparte de la disponibilidad.** Cada actividad tiene `visibilidad`: `SIEMPRE` (se ve aunque esté bloqueada) o `AL_DESBLOQUEAR` (solo aparece cuando deja de estar bloqueada). La API devuelve además `visible`, ya calculado: `visibilidad == SIEMPRE or estado != BLOQUEADA`.
- **D3. Sin contenido, invisible.** Si el front no tiene el contenido que indica el backend, la actividad no se muestra ni cuenta en el progreso, aunque el backend diga `visible`. En desarrollo se avisa en consola, una vez por actividad, y una prueba lo detecta con los fixtures (§9.3).
- **D4. Progreso del bloque.** El porcentaje de un bloque cuenta solo las actividades con `visibilidad == SIEMPRE` y con contenido en el front. Las `AL_DESBLOQUEAR` son extras: completarlas no sube ni baja el porcentaje.
- **D5. Un endpoint de lectura por dominio**, todos bajo `/cuentas/{c}/`. Ninguna respuesta incluye datos de otro dominio para ahorrar una petición. Lo que se ve siempre (mapa, panel, menú) son dos consultas: `resumen` y `actividades`.
- **D6. Las acciones no se mueven.** `POST /acciones/*` sigue en `api/acciones.py` con el mismo contrato. Cambia lo que el front vuelve a pedir después (§7.3).
- **D7. `/estado` se retira al final** (fase X), cuando el front ya no lo use. Mientras tanto, convive con las consultas nuevas.
- **D8. El modo `local` no cambia.** Sigue armando el Camino con `baseRoute` y `fieldMissions`. Lo nuevo solo rige en modo `api`. Para que las dos fuentes no se separen, una prueba compara posiciones y etiquetas (§9.3).
- **D9. La señal de hoy sigue local.** Conectarla exige leer **y** escribir el check-in en el servidor, y eso es de la iteración 3 (diario y check-in). Aquí no se toca: queda anotada en §11.
- **D10. Los casos y desafíos de la Ciudad** («Disponible en una próxima iteración») siguen siendo marcadores del front. No son actividades del backend todavía.
- **D11. Conjunto `piloto` para probar**, aparte de `plataforma`. `plataforma` conserva sus 9 + 15 actividades y sus reglas, para que la integración de la iteración 1 y sus fixtures no cambien de comportamiento.

## 4. Contrato nuevo

Todas las rutas son `GET`, reciben el código de la cuenta y responden 404 «Cuenta no encontrada» si no existe (como hoy). Para una cuenta `APODERADO`, las listas propias del estudiante salen vacías, igual que hoy en `/estado`.

| Ruta | Respuesta | Dominio (`api/`, `schemas/`, `services/`) | La usa el front |
|---|---|---|---|
| `/cuentas/{c}/resumen` | `ResumenCuenta` | `cuentas` | Al ingresar: menú y panel |
| `/cuentas/{c}/actividades` | `list[BloqueActividades]` | `actividades` | Al ingresar: mapa y panel |
| `/cuentas/{c}/fichas` | `list[ContenidoEstado]` | `fichas` | Al abrir la mochila o un recurso |
| `/cuentas/{c}/logros` | `LogrosCuenta` | `logros` | Al abrir el pasaporte, el perfil o una insignia |
| `/cuentas/{c}/testimonios` | `list[ContenidoEstado]` | `testimonios` | No (todavía no hay vista) |
| `/cuentas/{c}/diario/preguntas` | `list[PreguntaDiarioEstado]` | `diario` | No (iteración 3) |
| `/cuentas/{c}/conversaciones` | `ConversacionesEstado` | `comunidad` | No (iteración 4) |

Las rutas que no usa el front existen para que esos datos no desaparezcan de la API al retirar `/estado`. El front no las llama ni agrega sus tipos hasta que una iteración les dé una vista.

### 4.1 `ResumenCuenta`

```json
{
  "cuenta": { "codigo": "est-ana", "nombre": "Ana", "rol": "ESTUDIANTE" },
  "nivel_actual": { "numero": 1, "titulo": "Observador del horizonte" }
}
```

`nivel_actual` va aquí y no solo en `logros` porque el panel lo muestra siempre.

### 4.2 `BloqueActividades`

```json
[
  {
    "codigo": "CAMINO", "nombre": "El camino", "numero": 1, "espacio": "MISIONES_CAMPO", "estado": "DISPONIBLE",
    "actividades": [
      {
        "codigo": "mission-welcome", "titulo": "El inicio del viaje", "tipo": "INFORMATIVA", "orden": 1,
        "contenido": "mision_bienvenida", "visibilidad": "SIEMPRE", "visible": true, "estado": "DISPONIBLE"
      }
    ]
  }
]
```

- Bloques ordenados por `numero` y luego `codigo`; actividades por `orden` y luego `codigo`. Solo los bloques de la audiencia de la cuenta (como hoy).
- `estado` de la actividad: `BLOQUEADA`, `DISPONIBLE`, `EN_CURSO` o `COMPLETADA`, con la misma regla de hoy: bloqueada si su bloque o ella no están disponibles.
- Las actividades `AL_DESBLOQUEAR` bloqueadas **también se envían**, con `visible: false`, para que el front sepa que existen (por ejemplo, para contar). Su `titulo` sí viaja: no es secreto como una insignia oculta. Si alguna debe ser secreta, eso es otra decisión.

### 4.3 `LogrosCuenta`

```json
{ "insignias": [ /* InsigniaEstado, igual que hoy, ocultas como "???" */ ], "niveles": [ /* NivelEstado */ ] }
```

### 4.4 Sin cambios

`ContenidoEstado`, `PreguntaDiarioEstado`, `ConversacionesEstado`, `InsigniaEstado` y `NivelEstado` conservan su forma actual; solo cambian de archivo (§5.3). `/cuentas`, `/progreso`, `/eventos`, `/desbloqueos`, `/acciones/*`, `/instrumentos` y `/actividades/{a}/items` no cambian.

## 5. Backend

### 5.1 Modelo

En `app/models/contenido.py`, `Actividad` gana dos columnas:

| Columna | Tipo | Regla |
|---|---|---|
| `contenido` | `str`, no nula | Clave del contenido en el front: minúsculas, dígitos y `_` (`CHECK` con `^[a-z0-9_]+$`, implementado de forma portable o validado en el cargador si el `CHECK` no es portable; anótalo). |
| `visibilidad` | `Visibilidad`, no nula, por defecto `SIEMPRE` | Nuevo `StrEnum` en `app/models/enums.py`: `SIEMPRE`, `AL_DESBLOQUEAR`. |

- Migración `0002_contenido_y_visibilidad.py` generada con `--autogenerate` y revisada a mano. Para filas existentes: `contenido = codigo.lower().replace("-", "_")`, y `visibilidad = 'SIEMPRE'`. El código original no cambia. Usa `render_as_batch` (SQLite).
- `tests/test_migraciones.py` sigue en verde.

### 5.2 Datos

| Conjunto | Cambio |
|---|---|
| `plataforma` | Cada actividad recibe su `contenido` según la tabla de abajo; todas `SIEMPRE`. No cambia nada más (actividades, reglas, títulos). |
| `demo` | `contenido = codigo.lower().replace("-", "_")`; todas `SIEMPRE`. Los códigos originales y los escenarios E1–E17, I1–I14 y de registro no cambian. |
| `piloto` (nuevo, `datos/piloto.py`) | Ver §5.5. |

Contenidos de `plataforma` (los nombres de los JSON que se crean en F1 están marcados con *):

| Actividades | `contenido` |
|---|---|
| `mission-welcome` | `mision_bienvenida`* |
| `enc-mitos` | `encuentro_mitos` |
| `act-07` | `registro_mis_pregones` |
| `mission-story` | `registro_huellas`* |
| `mission-future` | `registro_horizonte`* |
| `mission-compass` | `mision_brujula`* |
| `act-06` | `registro_linea_tiempo` |
| `mission-expectations` | `registro_mochila`* |
| `mission-next-step` | `registro_siguiente_paso`* |
| `act-tip-01` … `act-tip-14` | `instrumento_mara` |
| `act-tip-final` | `encuentro_resultado_elena`* |

Estas claves son el contrato con el front: si el front cambia el nombre de un JSON, cambia también aquí.

### 5.3 Código por dominio

Sigue la estructura del `AGENTS.md` del backend: un archivo por dominio en `api/`, `schemas/` y `services/`.

| Dominio | `api/` | `schemas/` | `services/` |
|---|---|---|---|
| cuentas | `cuentas.py`: agrega `/resumen`; conserva `/cuentas`, `/progreso`, `/eventos`, `/desbloqueos` | `cuentas.py`: `CuentaResumen`, `NivelActual`, `ResumenCuenta` y lo de progreso, eventos y desbloqueos | `cuentas.py`: `resumen_cuenta` |
| actividades | `actividades.py` (nuevo): `/cuentas/{c}/actividades` | `actividades.py` (nuevo): `ActividadCuenta`, `BloqueActividades` | `actividades.py`: agrega `listar_bloques_cuenta`. Si el archivo pasa de unas 300 líneas, conviértelo en carpeta `services/actividades/` (`consultas.py`, `acciones.py`) |
| fichas | `fichas.py` (nuevo) | — (usa `ContenidoEstado` de `schemas/comun.py`) | `fichas.py` (nuevo): `listar_fichas_cuenta` |
| testimonios | `testimonios.py` (nuevo) | — (usa `ContenidoEstado`) | `testimonios.py` (nuevo) |
| diario | `diario.py` (nuevo): `/cuentas/{c}/diario/preguntas` | `diario.py` (nuevo): `PreguntaDiarioEstado` | `diario.py`: agrega `listar_preguntas_cuenta` |
| logros | `logros.py` (nuevo) | `logros.py` (nuevo): `InsigniaEstado`, `NivelEstado`, `LogrosCuenta` | `logros.py` (nuevo): `logros_cuenta` |
| comunidad | `comunidad.py` (nuevo): `/cuentas/{c}/conversaciones` | `comunidad.py` (nuevo): `ConversacionesEstado` | `comunidad.py`: agrega `estado_conversaciones` |

- `ContenidoEstado` y `estado_contenido(sesion, cuenta, modelo, tipo)` (genérico para fichas y testimonios) pasan a `schemas/comun.py` y `services/comun.py`.
- `api/router.py` incluye los routers nuevos. `obtener_cuenta_demo` (la dependencia `CuentaDemo`) se mueve a `app/dependencies.py` para que la usen todos.
- Cada lectura reutiliza exactamente la lógica que hoy está en `estado_cuenta`; se mueve, no se reescribe. Siguen las reglas de consultas del `AGENTS.md`: definiciones en caché, lecturas agrupadas por cuenta, ninguna consulta en bucles.
- Mientras exista, `estado_cuenta` se arma llamando a esas mismas funciones, para que las dos vías no se separen.

### 5.4 Fixtures para el front

`scripts/exportar_fixtures_front.py` agrega, sin quitar los actuales (se quitan en X):

| Fixture | Petición | Conjunto | Momento |
|---|---|---|---|
| `resumen-inicial.json` | `GET /cuentas/est-ana/resumen` | `plataforma` | Inicio |
| `actividades-inicial.json` | `GET /cuentas/est-ana/actividades` | `plataforma` | Inicio |
| `actividades-ciudad.json` | `GET /cuentas/est-ana/actividades` | `plataforma` | Con el Camino completo (el mismo momento de `estado-ciudad.json`) |
| `fichas-inicial.json`, `fichas-ciudad.json` | `GET /cuentas/est-ana/fichas` | `plataforma` | Inicio y Camino completo |
| `logros-inicial.json`, `logros-ciudad.json` | `GET /cuentas/est-ana/logros` | `plataforma` | Inicio y Camino completo |
| `piloto-actividades-inicial.json` | `GET /cuentas/est-ana/actividades` | `piloto` | Inicio |
| `piloto-actividades-ciudad.json` | ídem | `piloto` | Con `mission-welcome` y `enc-mitos` completas |
| `piloto-actividades-final.json` | ídem | `piloto` | Con `act-tip-14` completa (`act-tip-final` deja de estar bloqueada) |

La carga de cada conjunto sigue usando bases temporales, como hoy.

### 5.5 Conjunto `piloto`

`datos/piloto.py` reutiliza de `plataforma` todo lo que no sea el Camino y la regla de la Ciudad (cuentas, Ciudad, fichas, insignias, niveles, RIASEC, ocupaciones, carreras y demás reglas). Se agrega a `CONJUNTOS` en `datos/cargar.py`: `uv run python -m datos.cargar piloto`. Todo lo propio va marcado `DATO DE PRUEBA`.

| Bloque | Actividades (en orden) | Reglas |
|---|---|---|
| CAMINO | `mission-welcome`, `enc-mitos`, `act-07`, `mission-story`, `mission-compass`, con los mismos títulos, tipos y contenidos de `plataforma`; todas `SIEMPRE` | Secuenciales, como en `plataforma`. |
| CIUDAD | Las 14 de Mara y `act-tip-final` como en `plataforma`, pero **`act-tip-final` con `AL_DESBLOQUEAR`**. Además `cdd-sin-contenido` («Actividad de prueba sin contenido», `INFORMATIVA`, orden 16, `contenido = 'sin_contenido_prueba'`, `SIEMPRE`), disponible con la Ciudad. | `R-ciudad` se cumple con `COMPLETA_ACTIVIDAD` de `enc-mitos` (la segunda del Camino). |

Las insignias y niveles que dependen de completar el Camino siguen funcionando con 5 actividades. Si alguna regla de `plataforma` no tiene sentido con este Camino, no la cambies: anótalo.

### 5.6 Pruebas del backend

- `tests/test_consultas_dominio.py` (nueva): para cada ruta de §4, forma y valores con `plataforma` al inicio y con el Camino completo; 404 con cuenta inexistente; listas vacías para `apo-rosa`.
- `tests/test_piloto.py` (nueva):
  - Al inicio: 5 actividades en CAMINO; la Ciudad está bloqueada.
  - Al completar `enc-mitos`, la Ciudad pasa a `DISPONIBLE`, aunque el Camino no esté completo.
  - `act-tip-final` llega con `visible: false` hasta completar `act-tip-14`, y con `visible: true` después.
  - `cdd-sin-contenido` llega con `visible: true`; el backend no sabe si el contenido existe.
- `tests/test_estado_equivalente.py` (temporal, se borra en X): para `plataforma` y `piloto`, en tres momentos, `/estado` coincide campo por campo con lo que devuelven las rutas nuevas.
- Ninguna prueba existente cambia sus aserciones en las fases B, salvo las adaptaciones siguientes: listas exactas de columnas que comprueban el esquema (agregan `contenido` y `visibilidad`) y pruebas que fijan la revisión de Alembic (comparan con `ScriptDirectory.from_config(...).get_current_head()` en lugar de una revisión literal). Anótalas en `docs/decisiones.md`; las demás aserciones no cambian.

## 6. Front: contenidos

### 6.1 Un JSON por contenido

- Los contenidos viven en `src/data/activities/contenidos/<clave>.json`. Se mueven ahí los 6 JSON actuales y se crean los 7 de §5.2 a partir de `standardActivities.ts` y de `finalActivity`.
- La conversión se comprueba con una prueba temporal: el objeto que producía el TypeScript y el JSON nuevo son `deepEqual`. Después se borran `standardActivities.ts` (salvo `compassInstrument`, que es catálogo de instrumentos y se queda) y la definición de `finalActivity`.
- `catalogo.json` (personajes, recursos e instrumentos) no es un contenido de actividad: se queda en `src/data/activities/`.
- `src/data/activities/contenidos.ts` registra cada JSON con un import explícito y exporta `contenidos: Record<string, ContenidoActividad>` y `contenidoPorClave(clave)`. **Sin `import.meta.glob`**: los cargadores de las pruebas no lo resuelven. Una prueba comprueba que todo archivo de la carpeta esté registrado y viceversa.
- `content.ts` arma el catálogo local a partir de `contenidos.ts`. El catálogo resultante debe ser idéntico al actual (`activities`, `parentActivities`, `finalActivity`, `activityById`), y las pruebas lo comprueban sin cambios.

### 6.2 Presentación en el mapa

Cada contenido que se dibuja como punto del mapa gana un campo `mapa`, con los valores que hoy pone el código, para que nada cambie a la vista:

```json
"mapa": { "x": 130, "y": 140, "etiqueta": "Informativa · 4 min", "icono": "informativa" }
```

- Camino: `x`, `y` vienen de `fieldMissions`; `etiqueta`, de `getActivityType` + `getMissionMeta`; `icono` (`informativa`, `test` o `registro`), de `getMissionIcon`.
- `instrumento_mara`: `{ "x": 875, "y": 530, "icono": "test" }`, sin etiqueta: la arma la secuencia (§7.2).
- `encuentro_resultado_elena`: `{ "x": 1030, "y": 610, "etiqueta": "Encuentro con Elena", "icono": "informativa" }`.
- Los nombres de ícono se traducen a los de `lucide-react` en un solo mapa en `features/adventure/lib/`.
- El tipo `ContenidoActividad` (en `src/types/activities.ts`) agrega `mapa?`.

## 7. Front: consultas por dominio

### 7.1 Servicios y tipos

- `src/types/servidor.ts`: agrega `ResumenCuenta`, `ActividadCuenta` (con `contenido`, `visibilidad`, `visible`), `BloqueActividades` y `LogrosCuenta`, copiados de los esquemas Pydantic. `ContenidoEstado`, `InsigniaEstado` y `NivelEstado` ya existen.
- `src/services/api/`: `cuentas.ts` agrega `obtenerResumen`; nuevos `actividades.ts` (`obtenerActividades`), `fichas.ts` (`obtenerFichas`) y `logros.ts` (`obtenerLogros`). Todos con `obtener(...)`.
- En F2 se retira `obtenerEstado` y su caso de prueba se sustituye por las consultas nuevas (decisión autorizada por el usuario). `EstadoCuenta`, los fixtures `estado-*.json` y el endpoint del backend se conservan hasta X.
- No se agregan servicios para testimonios, preguntas ni conversaciones (§4).

### 7.2 Estado en `store/servidor/`

El almacén deja de guardar un `estado` único y pasa a guardar una **sección por dominio**:

```ts
type Seccion<T> = {
  datos: T | null
  estado: 'sin_cargar' | 'cargando' | 'listo' | 'vencido' | 'error'
  error: ErrorServidor | null
}
// almacen: { resumen, actividades, fichas, logros, noVistos, …lo demás igual }
```

- `estadoServidor.ts` se divide si pasa de 400 líneas: `sesion.ts` (cuenta activa, revisiones, `prepararAlmacenesApi`), `secciones.ts` (carga, vencimiento y suscripción de cada sección), `avisos.ts` (no vistos y marcado) y `resultado.ts` (RIASEC). Las reglas de hoy se conservan: descartar respuestas de otra cuenta o sesión y no duplicar pedidos en curso.
- `asegurarSeccion(nombre)`: si la sección está `sin_cargar` o `vencido`, la pide; si está `cargando`, reutiliza la promesa en curso. Un hook por sección (`useResumenServidor`, `useActividadesServidor`, `useFichasServidor`, `useLogrosServidor`) la llama al montarse y devuelve la sección.
- Mientras una sección carga, cada vista muestra lo que muestra hoy cuando `estado` todavía no llegó. No hay estados visuales nuevos.
- `lib/servidor/adaptadores.ts` cambia sus entradas de `EstadoCuenta` a la sección que corresponde (`BloqueActividades[]` para `actividadServidor`, `ciudadDisponible`, `siguienteActividad`, `progresoCamino`, `interaccionMara`, `misionesCompletadas` y `proyectarJourney`; `ContenidoEstado[]` para `fichaDisponible`; `LogrosCuenta` para `insigniasServidor` e `insigniasOcultasPendientes`). Sigue importando solo tipos.

### 7.3 Qué se pide y cuándo

| Momento | Se pide | Se marca vencido |
|---|---|---|
| Ingreso | `GET /cuentas`, `POST /acciones/ingresar` y, en paralelo, `resumen`, `actividades` y desbloqueos no vistos. Después, el resultado RIASEC solo si `act-tip-final` no está `BLOQUEADA` (como hoy). | — |
| Abrir mochila o un recurso | `fichas`, si no está `listo` | — |
| Abrir pasaporte, perfil o una insignia | `logros`, si no está `listo` | — |
| Después de `completar-actividad` o `responder-items` | `actividades` y desbloqueos no vistos | Según `nuevos_desbloqueos[].tipo_objetivo`: `FICHA` → `fichas`; `INSIGNIA` → `logros`; `NIVEL` → `logros` y `resumen` (y se vuelve a pedir `resumen`, porque el panel lo muestra siempre). |
| Reinicio de datos de prueba | Todo vuelve a `sin_cargar` y se repite el ingreso | — |

Una sección vencida que tiene una vista montada se vuelve a pedir de inmediato; si no, al abrir su vista.

### 7.4 Mapa desde el backend (modo `api`)

`caminoPoints.ts` y `ciudadPoints.ts`, en su rama de modo `api`, dejan de partir de `fieldMissions` y de los puntos fijos de Mara y Elena, y arman los puntos desde `actividades`:

1. Para cada actividad, busca `contenidoPorClave(actividad.contenido)`. Si no existe, la descarta (D3) y llama a `avisarContenidoFaltante(codigo, clave)`: en desarrollo, un `console.warn` por actividad y sesión; en producción, nada.
2. Descarta las que tienen `visible: false`.
3. **Secuencias:** dentro de un bloque, las actividades consecutivas que comparten `contenido` forman un solo punto. El punto representa la primera no completada (o la última, si todas lo están), y su etiqueta es `Test · Interacción {n} de {total}`, que es lo que hoy hace `interaccionMara`, generalizado. Su `specActivityId` es el código de esa actividad.
4. El resto: un punto por actividad, con posición, etiqueta e ícono de `contenido.mapa`, título de `actividad.titulo` y estado de `estadoPunto(actividad)`.
5. Un contenido sin `mapa` no se dibuja: se anota en `docs/pendientes-interfaz.md` (no se inventa una posición).
6. El punto de la llave de la Ciudad en el Camino y los marcadores de casos y desafíos de la Ciudad (D10) se quedan como están; la llave toma su estado del bloque `CIUDAD`.
7. Progreso del bloque (D4) y «siguiente paso» usan solo los puntos visibles, en el orden del backend.

Al abrir una actividad en modo `api`, el reproductor recibe el contenido de `contenidoPorClave(actividad.contenido)` con `id` igual al código de la actividad. Con `plataforma`, eso da exactamente las mismas actividades que hoy; las interacciones de Mara siguen pasando por `MaraInteractionPlayer`. Si alguna prueba de reproducción cambia de resultado, detente y avisa.

En modo `local` no cambia nada (D8).

## 8. Interfaz: qué cambia y qué no

**Única excepción de texto autorizada (2026-10-08, F3):** prevalecen los títulos del servidor (§7.4). Los puntos `enc-mitos` y `act-06` muestran «La plaza de los rumores» y «Mi mapa de ruta», respectivamente, tanto en modo `api` como en modo `local` (`src/data/content/adventure.ts`). Son los títulos que ya muestran la actividad y los avisos de desbloqueo. No se autoriza ningún otro cambio de texto, marcado, estilo ni estado visual.

Esta spec **no autoriza** cambios de marcado, texto, estilo ni estados visuales. Con `plataforma`, el mapa, el panel y el menú se ven idénticos en `local` y en `api`. Las vistas las cambia el usuario aparte, con los datos que ya llegan; tu trabajo termina en el hook del dominio. El punto 7.4 no es un cambio de interfaz: arma los mismos puntos del mapa desde otra fuente.

Lo que ya se sabe que no tiene vista o queda raro va a `docs/pendientes-interfaz.md`:

- Con `piloto`, la llave de la Ciudad dice «Destino al completar el camino» aunque se abra a la segunda actividad. El texto viene de hoy y no se cambia.
- Una actividad `AL_DESBLOQUEAR` que aparece no tiene animación de revelado (las misiones adicionales del piloto sí la tienen, pero es otro mecanismo).
- `testimonios`, `preguntas del diario` y `conversaciones` tienen consulta pero ninguna vista en modo `api`.
- La señal de hoy sigue siendo local (D9).

## 9. Pruebas del front

### 9.1 Línea base

Antes de F1, anota en `docs/refactor/decisiones.md` el conteo de `npm test` (total, pasan, fallan y los nombres de las fallas previas). Esas fallas deben seguir con el mismo nombre.

### 9.2 Adaptaciones autorizadas

Anótalas en `docs/refactor/decisiones.md`, con la lista de pruebas tocadas. Ninguna cambia un texto, un marcado ni un resultado esperado:

1. **Fixtures.** Las pruebas `servidor-*` que hoy simulan `/estado` con `estado-inicial.json` o `estado-ciudad.json` pasan a simular `resumen`, `actividades`, `fichas` y `logros` con los fixtures equivalentes de §5.4.
2. **Rutas.** Cambian las rutas a los JSON movidos a `contenidos/` y los imports de lo que salió de `standardActivities.ts`.
3. **Peticiones contadas.** Las aserciones que cuentan o enumeran peticiones después de una acción se ajustan a §7.3.

### 9.3 Pruebas nuevas

- `servidor-secciones.test.mjs`: carga perezosa, reutilización de la promesa en curso, vencimiento según `nuevos_desbloqueos` y descarte al cambiar de cuenta.
- `servidor-mapa.test.mjs`:
  - **Con `plataforma`:** los puntos del Camino y de la Ciudad en modo `api` coinciden en id, título, posición, etiqueta, ícono y estado con los de hoy (lo que muestran los fixtures).
  - **Con `piloto`:**
    - 5 puntos en el Camino.
    - Llave de la Ciudad disponible tras `enc-mitos`.
    - Punto de Elena ausente hasta `act-tip-14` y presente después.
    - `cdd-sin-contenido` ausente y con aviso en consola.
    - Porcentaje del Camino sobre 5.
- `contenidos.test.mjs`:
  - Todo JSON de `contenidos/` está registrado.
  - Todo `contenido` de los fixtures de `plataforma` existe en el registro.
  - En los fixtures de `piloto`, el único `contenido` faltante es `sin_contenido_prueba`.
  - Para las 9 del Camino, `contenido.mapa` coincide con `fieldMissions` y con las etiquetas de hoy (D8).

## 10. Fases

| Fase | Repo | Contenido | Para terminar |
|---|---|---|---|
| B0 | ambos | Línea base del backend (`uv run pytest -q`, anota el conteo). Copia en `ov_backend/AGENTS.md` la sección «Reglas compartidas» de `ov_frontend/AGENTS.md` tal cual (hoy está desactualizada). Después agrega lo del Anexo A: la sección «Datos del servidor sin vista» en `ov_frontend/AGENTS.md` (antes de «Interfaz del estudiante») y la viñeta compartida en «Contrato» de los dos. Crea `ov_frontend/docs/pendientes-interfaz.md` con el formato del Anexo A y sin entradas. Un commit por repo. | Conteo registrado; `diff` de «Reglas compartidas» entre los dos repos vacío; la sección nueva está en el front. |
| B1 | backend | Modelo y migración (§5.1); `contenido` y `visibilidad` en `plataforma` y `demo` (§5.2). | Pruebas en verde; `alembic upgrade head` sobre una base nueva y sobre una con la `0001`. |
| B2 | backend | Consultas por dominio (§4, §5.3) y `test_consultas_dominio.py`, `test_estado_equivalente.py`. `/estado` sigue. | Pruebas en verde. |
| B3 | backend | Conjunto `piloto` (§5.5), `test_piloto.py` y fixtures nuevos (§5.4), exportados a `ov_frontend/tests/fixtures/servidor/`. | Pruebas en verde; fixtures en el front (commit en el front: `Iteración 1 · B3: fixtures por dominio`). |
| F0 | front | Línea base (§9.1). | Conteo registrado. |
| F1 | front | Contenidos en JSON y registro (§6), sin cambiar el modo `local`. | Las mismas pruebas que en F0, más `contenidos.test.mjs`. |
| F2 | front | Servicios, tipos, secciones y adaptadores (§7.1–7.3). El front deja de pedir `/estado` y retira `obtenerEstado` y su caso de prueba. | Pruebas en verde con las adaptaciones de §9.2; `servidor-secciones.test.mjs`. `grep -rn "/estado" src` vacío. |
| F3 | front | Mapa desde el backend (§7.4). | `servidor-mapa.test.mjs` en verde; mismas pruebas que en F2. |
| F4 | ambos | Prueba manual con `plataforma` y con `piloto` (§12); `docs/pendientes-interfaz.md` con lo de §8. | Recorrido de §12 hecho y anotado. |
| X | ambos | **Backend:** borra `/estado`, `EstadoCuenta`, `estado_cuenta`, `test_estado_equivalente.py` y los fixtures `estado-*.json` del script. Las pruebas que consultaban `/estado` pasan a las rutas nuevas, con las mismas aserciones sobre los mismos datos (anótalo). **Front:** borra `EstadoCuenta` de `types/servidor.ts` y los fixtures `estado-*.json`; `obtenerEstado` ya se retiró en F2. **Los dos:** agrega a los `AGENTS.md` lo de §13. | Pruebas en verde en los dos repos; `grep -rn "estado_cuenta\|EstadoCuenta\|/estado\b" app tests scripts src` vacío. |

## 11. Fuera de alcance

- Señal de hoy en el servidor (lectura y escritura del check-in): iteración 3.
- Vistas para testimonios, preguntas del diario y conversaciones en modo `api`.
- Casos y desafíos como actividades del backend.
- Que el modo `local` lea la lista de actividades de un fixture en lugar de `baseRoute` y `fieldMissions` (cuando eso pase, el campo `x`/`y` de `fieldMissions` desaparece).
- Animación de revelado para actividades `AL_DESBLOQUEAR`.
- Insignias o actividades secretas que no deban enviar su título.

## 12. Prueba manual (F4)

Backend:

```powershell
uv run python -m datos.cargar piloto --vaciar
uv run uvicorn app.main:app --reload
```

Front: en `.env.local`, `VITE_DATOS=api`; `npm run dev`. Ingresa como `est-ana` y revisa:

1. **Peticiones.** En la pestaña Red del navegador, al ingresar solo salen `/cuentas`, `/acciones/ingresar`, `/resumen`, `/actividades` y `/desbloqueos?solo_no_vistos=true`. No sale `fichas` ni `logros`.
2. **Camino.** Muestra 5 actividades y la llave de la Ciudad cerrada.
3. **Apertura de la Ciudad.** Completa `mission-welcome` y `enc-mitos`: la llave se abre y la Ciudad muestra la interacción 1 de 14.
4. **Elena y la actividad sin contenido.** El punto de Elena no aparece. Tampoco aparece «Actividad de prueba sin contenido», y en la consola hay un aviso por ella.
5. **Mochila.** Al abrirla sale `/fichas` una sola vez, y las fichas desbloqueadas coinciden con lo completado.
6. **Pasaporte.** Al abrirlo sale `/logros`.
7. **Elena al final.** Completa las 14 interacciones (o usa `POST /eventos` para acelerar): aparece el punto de Elena.

Repite con `uv run python -m datos.cargar plataforma --vaciar`. El mapa, el panel y el menú deben verse igual que antes de esta spec.

## 13. Cambios en los `AGENTS.md` (fase X)

**Backend**, en «Dónde va cada cosa»:

- «Una consulta para una vista → `GET /cuentas/{c}/<dominio>` en `app/api/<dominio>.py`, con su esquema y servicio del mismo nombre. No agregues campos de otro dominio a una respuesta para ahorrar una petición.»
- «Una actividad nueva → `datos/<conjunto>.py`, con `contenido` (la clave de su JSON en el front) y `visibilidad`.»

**Front**, en «Dónde va cada cosa»:

- «Un contenido de actividad → `src/data/activities/contenidos/<clave>.json`, registrado en `contenidos.ts`. La clave es la que indica el backend en `contenido`.»
- «Una sección nueva de datos del servidor → `services/api/<dominio>.ts` y una sección en `store/servidor/` que se pide al abrir su vista.»

**Los dos**, en «Reglas compartidas», sección «Contrato» (idéntica en ambos repos):

> - El backend lista bloques y actividades, con su orden, tipo, `contenido` y `visibilidad`. El front solo guarda el contenido de cada actividad (`src/data/activities/contenidos/<clave>.json`) y lo encuentra por la clave `contenido`. Una actividad cuyo contenido no existe en el front no se muestra y se anota en `ov_frontend/docs/pendientes-interfaz.md`.
> - Cada dominio tiene su propia consulta de lectura (`GET /cuentas/{c}/<dominio>`). El front pide al ingresar solo lo que se ve siempre y el resto al abrir su vista.

## Anexo A. Regla «Datos del servidor sin vista»

Rige desde el inicio de esta spec. En B0 se copia a los `AGENTS.md`.

### A.1 Sección para `ov_frontend/AGENTS.md`

Va antes de «Interfaz del estudiante»:

````markdown
## Datos del servidor sin vista

La interfaz la decide el usuario. Un agente conecta datos a la interfaz que ya existe; no diseña interfaz nueva para mostrarlos.

- **Conectar sí:** que un elemento que ya existe (un contador, una insignia, un estado de candado, un texto) pase a tomar su valor del servidor en lugar del dato local, con el mismo marcado, los mismos textos y el mismo estilo.
- **Agregar no:** si el backend entrega un dato que ninguna vista muestra hoy, o mostrarlo exige algo que no existe (una pantalla, sección, tarjeta, columna, pestaña, texto, ícono, estado visual o ruta), **no crees ni modifiques interfaz para mostrarlo**. Tampoco lo resuelvas reutilizando un componente en otro lugar ni con un texto provisional.
- Hasta ahí sí puedes llevar el dato: `types/servidor.ts`, `services/api/`, `store/servidor/`, `lib/servidor/adaptadores.ts` y el hook del dominio. Se queda sin pintar.
- **Detente y avisa.** Al terminar la fase (o antes, si bloquea), lista cada dato en `docs/pendientes-interfaz.md` y en tu resumen, con: dato y campo de la respuesta (`LogrosCuenta.insignias[].requisito`), petición que lo trae, dónde crees que se mostraría, 2 o 3 opciones de interfaz y qué pasa si no se muestra. El usuario decide; no implementes ninguna opción hasta que responda.
- **Lo mismo al revés:** si una vista necesita un dato que el servidor no entrega, no lo inventes ni lo calcules en el front para cubrir el hueco; anótalo en el mismo documento y avisa.
- Si crees que la tarea no se puede terminar sin tocar una vista, **detente antes de tocarla** y pide autorización. Nunca cambies una vista esperando aprobarla después: el usuario prefiere hacer esos cambios aparte, con los datos que ya llegan del backend.
- Solo se agrega o cambia interfaz cuando el usuario lo pide o la spec vigente lo describe expresamente (qué vista, qué elemento, qué texto). Cita en el resumen la línea de la spec que lo autoriza.
- Estados de carga y error: usa los mensajes y componentes que ya existen (`mensajeErrorServidor`, los avisos actuales). Un estado visual nuevo también se consulta.
````

### A.2 Viñeta compartida

Va en «Reglas compartidas → Contrato» de los **dos** `AGENTS.md`, antes de la viñeta que empieza con «Si una tarea cambia una respuesta que consume el front»:

```markdown
- Si el backend entrega un dato que ninguna vista del front muestra, o una vista necesita un dato que el backend no entrega, no se crea ni se modifica interfaz para cubrirlo: se registra en `ov_frontend/docs/pendientes-interfaz.md` y se avisa al usuario, que decide la interfaz (detalle en «Datos del servidor sin vista» del `AGENTS.md` del front). Vale también al trabajar solo en el backend: si agregas o cambias un campo de una respuesta, revisa si el front tiene dónde mostrarlo y, si no, anótalo igual.
```

### A.3 Formato de `ov_frontend/docs/pendientes-interfaz.md`

```markdown
# Pendientes de interfaz

Datos que el backend entrega (o que una vista necesita) y que la interfaz todavía no muestra. Los resuelve el usuario.

## <fecha> · <dato>

- **Dato:** campo y respuesta (`ActividadCuenta.visibilidad`, `GET /cuentas/{c}/actividades`).
- **Dónde se mostraría:** vista y elemento.
- **Opciones:** 2 o 3, en una línea cada una.
- **Si no se muestra:** qué pasa hoy.
- **Estado:** pendiente.
```
