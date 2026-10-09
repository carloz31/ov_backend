# AGENTS.md

## Proyecto

Backend en FastAPI de una plataforma gamificada de orientación vocacional. `ov_frontend` consume esta API.

Las especificaciones son la fuente de verdad, y cada una extiende a la anterior sin cambiarla:

1. `docs/spec-demo-motor-desbloqueos.md`: motor de desbloqueos, acciones y consultas.
2. `docs/spec-demo-instrumentos.md`: instrumentos, resultados y recomendación de carreras.
3. `docs/spec-demo-registro-gemini.md`: actividades de registro con preguntas de seguimiento mediante Gemini.
4. `docs/iteraciones/spec-iteracion-N.md` de la iteración vigente (hoy la 1): datos `plataforma`, integración con el front y adaptaciones de pruebas autorizadas.
5. `docs/spec-refactor-estructura.md`: estructura del repo, base de datos, migraciones y carga de datos. Prevalece sobre lo que las anteriores dicen de semillas, `SEMILLA`, `RUTA_BD` y versión de esquema.

Si dos especificaciones parecen contradecirse, detente y explica la contradicción antes de cambiar nada.

## Estructura

Esta estructura es fija. No crees carpetas ni módulos sueltos fuera de ella; si algo no encaja, detente y pregunta.

```
app/                    solo la aplicación
  main.py               crear_aplicacion(): configuración, lifespan, routers
  config.py             Configuracion y cargar_configuracion()
  database.py           motor, sesiones y todo lo que depende del dialecto
  dependencies.py       dependencias compartidas de FastAPI (SesionBD, ejecutar_accion)
  exceptions.py         excepciones de dominio y su traducción a HTTP
  api/                  rutas, un archivo por grupo; sin lógica de negocio
  models/               tablas SQLAlchemy por dominio; __init__ reexporta todo
  schemas/              Pydantic de entrada y salida por dominio
  services/             lógica de negocio por dominio
    motor/              núcleo de desbloqueos
    instrumentos/       cálculo, consultas y resultados
    registro/           registro con LLM
  core/                 parámetros, caché de definiciones y contexto de consultas
  static/               tablero de demo
datos/                  todo lo que llena la base (plataforma, demo, Excel O*NET)
migrations/             migraciones de Alembic
scripts/                herramientas manuales
tests/                  pruebas; ayudas en tests/soporte/
docs/                   especificaciones y decisiones
```

### Dónde va cada cosa

| Si agregas… | Va en… |
|---|---|
| Una consulta para una vista | `GET /cuentas/{c}/<dominio>` en `app/api/<dominio>.py`, con su esquema y servicio del mismo nombre. No agregues campos de otro dominio a una respuesta para ahorrar una petición. |
| Una actividad nueva | `datos/<conjunto>.py`, con `contenido` (la clave de su JSON en el front) y `visibilidad`. |
| Un endpoint | `app/api/<grupo>.py`. Solo valida, llama a un servicio y devuelve. |
| Lógica de negocio | `app/services/<dominio>.py`, o `app/services/<dominio>/` si el dominio ya es carpeta. |
| Una tabla o columna | `app/models/<dominio>.py` **y** una migración en `migrations/versions/` en el mismo commit. |
| Un enumerado | `app/models/enums.py`. |
| Un cuerpo de entrada o respuesta | `app/schemas/<dominio>.py`. |
| Un umbral o constante de método | `app/core/parametros.py`. |
| Una variable de entorno | `app/config.py` y `.env.example`. |
| Datos de prueba o catálogo | `datos/plataforma.py` (o `datos/demo/`). Nunca en `app/`. |
| Una tabla de estado de las cuentas | Además, en `TABLAS_DE_ESTADO` de `app/services/demo.py`, para que el reinicio la vacíe. |

Si un dominio nuevo llega con la iteración (por ejemplo, favoritos o planes), créale un archivo en `services/`, `schemas/` y, si tiene tablas, en `models/`. Convierte un archivo en carpeta solo cuando ya no cabe en uno.

### Dependencias entre capas

- `api` → `services` → `core`, `models`. `api` también usa `schemas`, `dependencies` y `exceptions`.
- `app/` nunca importa `datos`, `scripts` ni `tests`.
- `services/` nunca importa `api/`. `core/` y `models/` nunca importan `services/`.
- `services/instrumentos/calculo.py` no accede a la base.
- Importa módulos con alias cuando los nombres coinciden entre capas: `from app.services import actividades as servicio_actividades`.

## Base de datos

- La URL viene de `DATABASE_URL` (por defecto `sqlite:///ov.db` en la raíz). La aplicación debe funcionar igual con SQLite y PostgreSQL.
- Nada de SQL específico de un motor fuera de `app/database.py`. Los índices parciales llevan `sqlite_where` y `postgresql_where`. No reemplaces `func.date` por `CAST(... AS DATE)` (en SQLite devuelve el año).
- El esquema lo gestiona Alembic. La aplicación nunca llama a `create_all` ni siembra datos; solo las pruebas, `scripts/exportar_fixtures_front.py` y `scripts/evaluar_gemini.py`, sobre bases temporales, usan `create_all` (mediante los auxiliares de `datos.cargar`).
- Todo cambio en `app/models/` lleva su migración (`uv run alembic revision --autogenerate -m "..."`), revisada a mano, en el mismo commit. `tests/test_migraciones.py` debe seguir en verde.

## Datos

| Conjunto | Para qué | Reglas |
|---|---|---|
| `demo` (`datos/demo/`) | La demo original y sus pruebas (E1–E17, I1–I14, registro). | No cambies sus datos, reglas ni los resultados esperados de sus escenarios. |
| `plataforma` (`datos/plataforma.py`) | Datos alineados con el front, para integrarlo. | Los define la spec de la iteración vigente. Sus códigos son los ids del front. |

- La aplicación no sabe qué conjunto tiene la base. Se carga con `uv run python -m datos.cargar <conjunto>`.
- `POST /demo/reiniciar` borra el estado de las cuentas y conserva el catálogo.
- Los datos inventados se marcan con `DATO DE PRUEBA`.

## Reglas de trabajo

- Lee la especificación completa antes de escribir código.
- Si un test de escenario falla, corrige la implementación, no el test. Solo se adaptan tests existentes cuando la spec vigente lo autoriza de forma explícita, y se anota en `docs/decisiones.md`.
- Si algo no está definido en la especificación, elige la opción más simple, anótala en `docs/decisiones.md` y sigue. Si afecta también al front, anótala en `docs/iteraciones/decisiones-iteracion-N.md`.
- No agregues endpoints que la spec no pida.
- No dejes archivos de log, carpetas temporales de pytest ni bases `.db` en el repo.

## Stack

- Python 3.14 (como fijan `.python-version` y `pyproject.toml`), FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, SQLite (desarrollo y pruebas) y PostgreSQL (opcional, extra `postgres`), pytest.
- Dependencias gestionadas con `uv` en `pyproject.toml` (con `uv.lock`). Agrégalas solo con `uv add` (`uv add --dev` para herramientas de prueba). No uses `pip` ni `requirements.txt`, y no agregues dependencias sin avisar.

## Comandos

- Instalar: `uv sync` (con PostgreSQL: `uv sync --extra postgres`)
- Crear o actualizar el esquema: `uv run alembic upgrade head`
- Cargar datos: `uv run python -m datos.cargar plataforma` (o `demo`; `--vaciar` para empezar de cero)
- Levantar: `uv run uvicorn app.main:app --reload`
- Tests: `uv run pytest -q`
- Nueva migración: `uv run alembic revision --autogenerate -m "<descripción>"`
- Fixtures para el front: `uv run python scripts/exportar_fixtures_front.py --destino <carpeta de ov_frontend>/tests/fixtures/servidor`

Corre `uv run pytest -q` antes de dar por terminada cualquier fase.

## Convenciones

- Carpetas estándar en inglés (`api`, `models`, `schemas`, `services`, `core`); módulos, código, tablas, columnas y funciones en español y `snake_case`. Sin sufijos como `_service` o `_repo` en los archivos.
- La API expone códigos legibles (`act-tip-01`, `est-ana`), nunca ids internos.
- `app/services/motor/` no importa nada de `app/api/`.
- Consultas: definiciones en caché, lecturas agrupadas por cuenta, escrituras en lote y ninguna consulta dentro de bucles.

## Secretos y servicios externos

- La clave de Gemini se lee de `.env`, que nunca se versiona. No la escribas en código, logs, respuestas, errores ni documentación.
- La aplicación admite `EVALUADOR=gemini` o `EVALUADOR=falso`, como define `docs/spec-demo-registro-gemini.md`. El valor por defecto es `falso`.
- Los tests usan siempre el evaluador falso y nunca acceden a la red (salvo `tests/test_postgres.py`, que se omite si no hay `TEST_POSTGRES_URL`).
- No ejecutes nada que llame a la API real de Gemini (la aplicación con `EVALUADOR=gemini` o `scripts/evaluar_gemini.py`) salvo que yo lo pida explícitamente.

## Reglas compartidas entre ov_backend y ov_frontend

> Esta sección es idéntica en el `AGENTS.md` de ambos repos. Si la cambias en uno, cámbiala en el otro en la misma tarea.

**Los repos.** `ov_backend` (FastAPI, rama `master`) y `ov_frontend` (React + Vite + TypeScript, rama `main`) están en carpetas independientes y son repos git separados. Para referirte al otro, usa su nombre de carpeta; no asumas una ruta relativa entre ellos.

**Fuentes de verdad, en este orden:**

1. La especificación de la iteración vigente, `ov_backend/docs/iteraciones/spec-iteracion-N.md` (hoy la **1**), para el alcance, la integración entre repos y los datos de prueba.
2. Las especificaciones de cada repo para su propio dominio.
3. Este `AGENTS.md`, para convenciones y áreas protegidas.

Si dos fuentes se contradicen, detente y explica la contradicción. No la resuelvas en el código.

**Cómo se trabaja.**

- Solo se implementa la iteración vigente. `ov_backend/docs/iteraciones/plan-iteraciones.md` muestra lo que viene después para no cerrar caminos, no para adelantarlo.
- Por fases, en el orden de la spec. Al terminar cada fase, detente y resume qué hiciste, qué pruebas pasan en cada repo y qué queda pendiente. Si la fase tocó ambos repos, corre las pruebas de los dos.
- Las decisiones que afectan a ambos repos van en `ov_backend/docs/iteraciones/decisiones-iteracion-N.md`.
- Datos de prueba: si el dato existe en el front, úsalo adaptándolo. Si no existe, créalo y márcalo con `DATO DE PRUEBA` (comentario en código) o `"_dato_de_prueba": true` (JSON).
- Sin dependencias nuevas en ninguno de los repos sin avisar antes.

**Una sola base de datos.**

- La base del backend es la única fuente de disponibilidad, progreso, respuestas de cuestionario, resultados, fichas obtenidas, insignias y nivel.
- En modo `VITE_DATOS=api`, el front nunca decide si algo está disponible, completado u obtenido: lo lee del servidor. Si el servidor no responde, lo dice; no inventa un estado.
- El contenido narrativo de las actividades (nodos JSON) sigue en el front. El backend guarda estructura y estado, y no interpreta ese contenido.
- El modo `local` del front debe seguir funcionando igual que antes.

**Contrato.**

- El backend lista bloques y actividades, con su orden, tipo, `contenido` y `visibilidad`. El front solo guarda el contenido de cada actividad (`src/data/activities/contenidos/<clave>.json`) y lo encuentra por la clave `contenido`. Una actividad cuyo contenido no existe en el front no se muestra y se anota en `ov_frontend/docs/pendientes-interfaz.md`.
- Cada dominio tiene su propia consulta de lectura (`GET /cuentas/{c}/<dominio>`). El front pide al ingresar solo lo que se ve siempre y el resto al abrir su vista.
- Los códigos del backend son los ids del front (`mission-welcome`, `act-tip-01`, `I1`, `psychologist`). No hay tablas de traducción.
- El JSON usa los nombres en español y `snake_case` de los esquemas Pydantic. El front los copia tal cual en `src/types/servidor.ts` y accede al backend solo desde `src/services/api/` (un archivo por router del backend); las vistas leen esos datos a través de `src/store/servidor/`.
- Si el backend entrega un dato que ninguna vista del front muestra, o una vista necesita un dato que el backend no entrega, no se crea ni se modifica interfaz para cubrirlo: se registra en `ov_frontend/docs/pendientes-interfaz.md` y se avisa al usuario, que decide la interfaz (detalle en «Datos del servidor sin vista» del `AGENTS.md` del front). Vale también al trabajar solo en el backend: si agregas o cambias un campo de una respuesta, revisa si el front tiene dónde mostrarlo y, si no, anótalo igual.
- Si una tarea cambia una respuesta que consume el front, en la misma tarea se actualizan el esquema y las pruebas del backend, `src/types/servidor.ts`, `src/services/api/` y `src/lib/servidor/adaptadores.ts` del front, los fixtures (`scripts/exportar_fixtures_front.py` de `ov_backend`, con `--destino` apuntando a `tests/fixtures/servidor/` de `ov_frontend`) y las pruebas del front.

**Git.** No hagas push salvo que se pida. Trabaja en una rama `iteracion-N` en cada repo, con un commit por fase y por repo y mensaje en español (`Iteración 1 · F2: semilla plataforma`). Nunca versiones `.env`, `.env.local` ni archivos `*.db`.

**Idioma.** Documentación, mensajes al usuario y commits en español.
