# AGENTS.md

## Proyecto

Backend en FastAPI de una plataforma gamificada de orientación vocacional. `ov_frontend` consume esta API.

Documentos vigentes (lee los que toque la tarea):

| Documento | Qué define |
|---|---|
| `docs/sistema/motor.md` | Eventos, reglas, disponibilidad, acciones y progreso. |
| `docs/sistema/instrumentos.md` | Cuestionarios, cálculo de resultados, coincidencias O*NET y carreras. |
| `docs/sistema/registro.md` | Respuestas de registro, preguntas de seguimiento y evaluador (Gemini o falso). |
| `docs/sistema/integracion.md` | Contrato con el front, conjuntos de datos, fixtures y reinicio. |
| `docs/specs/` | La spec en curso. |
| `docs/decisiones.md` | Decisiones de la spec en curso. |

## Estructura

Esta estructura es fija. No crees carpetas ni módulos sueltos fuera de ella; si algo no encaja, detente y pregunta.

```
app/                    solo la aplicación; no lee archivos de datos
  main.py               crear_aplicacion(): configuración, lifespan, routers
  config.py             Configuracion y cargar_configuracion()
  database.py           motor, sesiones y todo lo que depende del dialecto
  dependencies.py       dependencias compartidas (SesionBD, ejecutar_accion, cuenta)
  exceptions.py         excepciones de dominio y su traducción a HTTP
  api/                  rutas, un archivo por grupo; sin lógica de negocio
  models/               tablas SQLAlchemy por dominio; __init__ reexporta todo
  schemas/              Pydantic de entrada y salida por dominio
  services/             lógica de negocio por dominio
    motor/              núcleo de desbloqueos
    instrumentos/       cálculo, consultas y resultados
    registro/           registro con evaluador de respuestas
  core/                 parámetros, caché de definiciones y contexto de consultas
datos/                  lo que llena la base: plataforma.py, piloto.py, ocupaciones.py (Excel O*NET), cargar.py
migrations/             migraciones de Alembic
scripts/                herramientas manuales (exportador de fixtures)
tests/                  pruebas (ver «Pruebas»)
docs/                   sistema/, specs/, decisiones.md, plan-iteraciones.md, historico/
```

### Dónde va cada cosa

| Si agregas… | Va en… |
|---|---|
| Una consulta para una vista | `GET /cuentas/{c}/<dominio>` en `app/api/<dominio>.py`, con su esquema y servicio del mismo nombre. No agregues campos de otro dominio a una respuesta para ahorrar una petición. |
| Una actividad | `datos/<conjunto>.py`, con `contenido` (la clave de su JSON en el front) y `visibilidad`. |
| Un endpoint | `app/api/<grupo>.py`. Solo valida, llama a un servicio y devuelve. |
| Lógica de negocio | `app/services/<dominio>.py`, o `app/services/<dominio>/` si el dominio ya es carpeta. |
| Una tabla o columna | `app/models/<dominio>.py` **y** su migración en `migrations/versions/`, en el mismo commit. |
| Un enumerado | `app/models/enums.py`. |
| Un cuerpo de entrada o respuesta | `app/schemas/<dominio>.py`. |
| Un umbral o constante de método | `app/core/parametros.py`. |
| Una variable de entorno | `app/config.py` y `.env.example`. |
| Datos de prueba o catálogo | `datos/plataforma.py` o `datos/piloto.py`. Nunca en `app/`. |
| Una tabla de estado de las cuentas | Además, en `TABLAS_DE_ESTADO` de `app/services/desarrollo.py`, para que el reinicio la vacíe (una prueba exige clasificar toda tabla como catálogo o estado). |
| Un dominio nuevo (favoritos, planes…) | Un archivo en `services/`, `schemas/` y, si tiene tablas, `models/`. Un archivo pasa a carpeta solo cuando ya no cabe en uno. |

### Dependencias entre capas

- `api` → `services` → `core`, `models`. `api` también usa `schemas`, `dependencies` y `exceptions`. `datos` → `app.models`, `app.core.parametros`.
- `app/` nunca importa `datos`, `scripts` ni `tests`.
- `services/` nunca importa `api/`. `core/` y `models/` nunca importan `services/`.
- `services/instrumentos/calculo.py` no accede a la base.
- Si los nombres coinciden entre capas, importa con alias: `from app.services import actividades as servicio_actividades`.

## Base de datos

- La URL viene de `DATABASE_URL` (por defecto `sqlite:///ov.db`, relativa a la raíz). La aplicación funciona igual con SQLite y PostgreSQL.
- Nada de SQL específico de un motor fuera de `app/database.py`. Los índices parciales llevan `sqlite_where` y `postgresql_where`. No reemplaces `func.date` por `CAST(... AS DATE)`: en SQLite devuelve el año.
- El esquema lo gestiona Alembic (`render_as_batch` para SQLite; nombres de restricciones por la `naming_convention` de `Base`). La aplicación nunca llama a `create_all` ni siembra datos: si falta el esquema, no arranca y pide `alembic upgrade head`. Solo las pruebas y el exportador de fixtures usan `create_all`, sobre bases temporales, mediante `datos.cargar`.
- Todo cambio en `app/models/` lleva su migración (`uv run alembic revision --autogenerate -m "..."`), revisada a mano, en el mismo commit. `tests/integration/migraciones/test_migraciones.py` debe seguir en verde.

## Datos

| Conjunto | Para qué |
|---|---|
| `plataforma` (`datos/plataforma.py`) | Datos alineados con el front, para la integración. Sus códigos son los ids del front. |
| `piloto` (`datos/piloto.py`) | Variante pequeña de `plataforma` para probar visibilidad y contenido faltante. |

- La aplicación no sabe qué conjunto tiene la base. Se carga con `uv run python -m datos.cargar <conjunto>` (`--vaciar` para reemplazarlo). El cargador valida que `contenido` use solo `[a-z0-9_]`.
- `POST /desarrollo/reiniciar`, solo con `ENTORNO=desarrollo`, borra el estado de las cuentas y conserva el catálogo.
- Los datos inventados se marcan con `DATO DE PRUEBA`.

## Convenciones

- Carpetas estándar en inglés (`api`, `models`, `schemas`, `services`, `core`); módulos, código, tablas, columnas y funciones en español y `snake_case`. Sin sufijos como `_service` o `_repo`. Enumerados en MAYÚSCULAS.
- La API expone códigos legibles (`act-tip-01`, `est-ana`), nunca ids internos.
- Cada acción (`POST /acciones/*`) ocurre en una sola transacción, abierta por `ejecutar_accion`; los servicios solo hacen `flush`. Si algo falla, se revierten estado, eventos, desbloqueos y resultados.
- Errores: `detail: {"mensaje": ...}`. 404 si no existe la cuenta, la referencia o el objetivo, o si es de otra audiencia; 409 si la acción no está permitida en el estado actual (con `progreso` del objetivo bloqueado o `items_faltantes` cuando aplica); 422 si la entrada es inválida; 403 solo para el progreso de una insignia oculta no obtenida.
- Fechas: las acciones aceptan `fecha_hora` opcional; se guarda sin zona, conservando la hora local. Sin fecha, se usa la hora de Lima (UTC−05:00). Todos los eventos de una petición comparten la misma fecha.
- Listas ordenadas por código (contenido, reglas), número (niveles, bloques) u orden (actividades, ítems); eventos y desbloqueos por fecha descendente. Los GET nunca escriben.
- Consultas: definiciones en la caché (`core/definiciones.py`), lecturas agrupadas por cuenta (`core/contexto.py`), escrituras en lote y ninguna consulta dentro de bucles. Las pruebas de presupuesto exigen que el número de consultas no crezca con el tamaño del catálogo.

## Secretos y servicios externos

- La clave de Gemini se lee de `.env`, que nunca se versiona. No la escribas en código, logs, respuestas, errores ni documentación.
- `EVALUADOR=falso` (por defecto) o `EVALUADOR=gemini`. Las pruebas usan siempre el evaluador falso y nunca acceden a la red (salvo las de marca `postgres`, que se omiten sin `TEST_POSTGRES_URL`).
- No ejecutes nada que llame a la API real de Gemini salvo que el usuario lo pida explícitamente.

## Stack y comandos

Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, SQLite (desarrollo y pruebas), PostgreSQL opcional (extra `postgres`), pytest. Dependencias solo con `uv add` (`uv add --dev` para pruebas); no uses `pip` ni `requirements.txt`.

- Instalar: `uv sync` (con PostgreSQL: `uv sync --extra postgres`)
- Esquema: `uv run alembic upgrade head`
- Datos: `uv run python -m datos.cargar plataforma` (o `piloto`)
- Levantar: `uv run uvicorn app.main:app --reload`
- Fixtures para el front: `uv run python scripts/exportar_fixtures_front.py --destino <carpeta de ov_frontend>/tests/fixtures/servidor`

## Pruebas

```text
tests/
  conftest.py        solo autouse sin base (evaluador falso)
  soporte/           ayudas compartidas; ninguna prueba importa un test_*.py
  unit/              arquitectura, configuracion, instrumentos, motor, registro
  integration/
    conftest.py      plantillas SQLite por sesión y proceso; cada prueba copia la suya
    actividades/ cuentas/ desarrollo/ fichas/ instrumentos/ logros/ motor/
    datos/ migraciones/ contrato/
    escenarios/plataforma/ escenarios/piloto/
```

- `unit/` no usa TestClient ni bases sembradas (permite falsos y SQLite en memoria sin conjunto). Lo que use una base sembrada, migraciones, PostgreSQL o TestClient va en `integration/`; ante la duda, también.
- Las pruebas nuevas usan los fixtures de plantilla (`aplicacion` con `plataforma`, `aplicacion_piloto`, `cliente`, `sesion`). Solo las pruebas de carga, migraciones y atomicidad de la carga preparan bases propias.
- Solo se crean carpetas con pruebas. Los nombres `test_*.py` son únicos en todo `tests/` (`--import-mode=importlib`).

| Si cambias… | Corre primero |
|---|---|
| `app/services/<dominio>*`, `app/api/<dominio>.py`, `app/schemas/<dominio>.py` | `tests/unit/<dominio>` y `tests/integration/<dominio>`, si existen |
| `app/services/motor/*`, `app/services/eventos.py`, `app/services/comun.py` | `tests/unit/motor`, `tests/integration/motor`, `tests/integration/actividades` y `tests/integration/escenarios` |
| `app/models/*`, `migrations/*` | `tests/integration/migraciones` y `tests/integration/datos` |
| `datos/*` | `tests/integration/datos` y `tests/integration/escenarios` |
| `app/main.py`, `config.py`, `database.py`, `dependencies.py`, `exceptions.py`, `app/core/*` | `tests/unit` y `tests/integration/escenarios` |
| Una respuesta que consume el front | `tests/integration/contrato`, regenerar fixtures y `npm run test:servidor` en ov_frontend |

Ejemplo: `uv run pytest tests/integration/instrumentos -q`. En Windows, si falla el lanzador, usa `uv run python -m pytest`. Temporales y logs fuera del repo (por ejemplo, `--basetemp="$env:TEMP/ov-pruebas" -p no:cacheprovider`).

## Reglas compartidas entre ov_backend y ov_frontend

> Esta sección es idéntica en el `AGENTS.md` de ambos repos. Si la cambias en uno, cámbiala en el otro en la misma tarea.

**Los repos.** `ov_backend` (FastAPI) y `ov_frontend` (React + Vite + TypeScript) son repos git separados, en carpetas independientes. Para referirte al otro, usa su nombre de carpeta; no asumas una ruta relativa entre ellos.

**Qué leer.**

1. La spec de la tarea, en `ov_backend/docs/specs/`. Define el alcance y prevalece sobre todo lo demás.
2. Este `AGENTS.md` y, del repo que toques, los documentos vigentes que nombre la tarea: `ov_backend/docs/sistema/` y `ov_frontend/docs/`.
3. `ov_backend/docs/plan-iteraciones.md`, solo para no cerrar caminos a las iteraciones siguientes. No se adelanta trabajo de otra iteración.

No leas `docs/historico/` de ningún repo salvo que el usuario lo pida: es el registro del trabajo terminado. Si algo de ahí contradice un documento vigente, prevalece el vigente. Si dos fuentes vigentes se contradicen, detente y explica la contradicción; no la resuelvas en el código.

**Cómo se trabaja.**

- Lee la spec completa antes de escribir código. No agregues endpoints, vistas ni funciones que la spec no pida.
- Por fases, en el orden de la spec. Al terminar cada fase, detente y resume qué hiciste, qué carpetas de pruebas corriste en cada repo y qué queda pendiente.
- Si la spec no define algo, elige la opción más simple, anótala en `ov_backend/docs/decisiones.md` y sigue.
- Una prueba existente solo se adapta cuando la spec lo autoriza; anótalo también en `decisiones.md`. Si un escenario falla, se corrige la implementación, no el escenario.
- Datos de prueba: si el dato existe en el front, úsalo adaptado. Si no existe, créalo y márcalo con `DATO DE PRUEBA` (comentario en código) o `"_dato_de_prueba": true` (JSON).
- Ninguna dependencia nueva en ninguno de los repos sin avisar antes.

**Documentación.**

- `ov_backend/docs/decisiones.md` es el único registro de decisiones, para los dos repos, y solo de la spec en curso. Una viñeta por decisión: qué se decidió y por qué, en una o dos líneas. No registra conteos de pruebas, tiempos, líneas base ni el relato de cada fase; eso va en el resumen al usuario.
- Al cerrar una spec, lo que siga vigente de ella y de `decisiones.md` se incorpora al `AGENTS.md` o al documento vigente que corresponda. Después, la spec y `decisiones.md` se mueven a `ov_backend/docs/historico/<nombre-de-la-spec>/` y `decisiones.md` vuelve a quedar con su encabezado.
- Ningún documento vigente remite a uno histórico.

**Política de pruebas.** Las tablas de impacto de cada `AGENTS.md` indican qué carpetas corresponden a cada archivo.

| Momento | Qué se corre |
|---|---|
| Durante el desarrollo, tras cada cambio | Solo las carpetas de la tabla de impacto. |
| Al terminar una fase | Las carpetas de impacto de todo lo que tocó la fase, más `tests/integration/escenarios` (back) o `npm run test:servidor` (front). |
| Al cerrar una spec o antes de integrar una rama | Todo, en los dos repos: `uv run pytest -n auto -q`; `npm test`, `npm run build`, `npm run lint` y `npm run check:estructura`. |

**Una sola base de datos.**

- La base del backend es la única fuente de disponibilidad, progreso, respuestas de cuestionario, resultados, fichas obtenidas, insignias y nivel.
- En modo `VITE_DATOS=api`, el front nunca decide si algo está disponible, completado u obtenido: lo lee del servidor. Si el servidor no responde, lo dice; no inventa un estado.
- El contenido narrativo de las actividades (nodos JSON) está en el front. El backend guarda estructura y estado, y no interpreta ese contenido.
- El modo `local` del front debe seguir funcionando igual.

**Contrato.** El detalle está en `ov_backend/docs/sistema/integracion.md`.

- El backend lista bloques y actividades con su orden, tipo, `contenido` y `visibilidad`. El front guarda el contenido de cada actividad en `src/data/activities/contenidos/<clave>.json` y lo encuentra por la clave `contenido`. Una actividad cuyo contenido no existe en el front no se muestra, y se anota en `ov_frontend/docs/pendientes-interfaz.md`.
- Cada dominio tiene su propia consulta de lectura (`GET /cuentas/{c}/<dominio>`). El front pide al ingresar solo lo que se ve siempre, y el resto al abrir su vista.
- Los códigos del backend son los ids del front (`mission-welcome`, `act-tip-01`, `I1`, `psychologist`). No hay tablas de traducción.
- El JSON usa los nombres en español y `snake_case` de los esquemas Pydantic. El front los copia tal cual en `src/types/servidor.ts`, accede al backend solo desde `src/services/api/` (un archivo por router) y las vistas leen esos datos a través de `src/store/servidor/`.
- Si el backend entrega un dato que ninguna vista muestra, o una vista necesita un dato que el backend no entrega, no se crea ni se modifica interfaz para cubrirlo: se registra en `ov_frontend/docs/pendientes-interfaz.md` y se avisa al usuario, que decide (detalle en «Datos del servidor sin vista» del `AGENTS.md` del front). Vale también al trabajar solo en el backend.
- Si una tarea cambia una respuesta que consume el front, en la misma tarea se actualizan: el esquema y las pruebas del backend; `src/types/servidor.ts`, `src/services/api/` y `src/lib/servidor/adaptadores.ts` del front; los fixtures (se regeneran con `scripts/exportar_fixtures_front.py`), y las pruebas del front.

**Git.** No hagas push salvo que se pida. Trabaja en la rama que indique la spec, con un commit por fase y por repo y mensaje en español (`Iteración 2 · F1: semilla de registros`). Nunca versiones `.env`, `.env.local` ni archivos `*.db`, y no dejes en los repos logs, bases temporales ni carpetas temporales de pruebas.

**Idioma.** Documentación, mensajes al usuario y commits en español.
