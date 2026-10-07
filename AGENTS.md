# AGENTS.md

## Proyecto

Backend en FastAPI de una plataforma gamificada de orientación vocacional. `ov_frontend` consume esta API.

Las especificaciones son la fuente de verdad, y cada una extiende a la anterior sin cambiarla:

1. `docs/spec-demo-motor-desbloqueos.md`: motor de desbloqueos, acciones y consultas.
2. `docs/spec-demo-instrumentos.md`: instrumentos, resultados y recomendación de carreras.
3. `docs/spec-demo-registro-gemini.md`: actividades de registro con preguntas de seguimiento mediante Gemini.
4. `docs/iteraciones/spec-iteracion-N.md` de la iteración vigente (hoy la 1): semilla `plataforma`, integración con el front y adaptaciones de pruebas autorizadas.

Si dos especificaciones parecen contradecirse, detente y explica la contradicción antes de cambiar nada.

## Semillas

| Semilla | Para qué | Reglas |
|---|---|---|
| `demo` | La demo original y sus pruebas (E1–E17, I1–I14, registro). | No cambies la semántica del motor, sus datos semilla ni los resultados esperados de sus escenarios. |
| `plataforma` | Datos de prueba alineados con el front, para integrarlo. | La define la spec de la iteración vigente. Sus códigos son los ids del front. |

`SEMILLA` (por defecto `demo`) elige cuál se carga al crear la base y en `/demo/reiniciar`. Cada semilla usa su propio archivo de base.

## Reglas de trabajo

- Lee la especificación completa antes de escribir código.
- Si un test de escenario falla, corrige la implementación, no el test. Solo se adaptan tests existentes cuando la spec vigente lo autoriza de forma explícita, y se anota en `docs/decisiones.md`.
- Si algo no está definido en la especificación, elige la opción más simple, anótala en `docs/decisiones.md` y sigue. Si afecta también al front, anótala en `docs/iteraciones/decisiones-iteracion-N.md`.
- No agregues endpoints que la spec no pida.

## Stack

- Python 3.14 (como fijan `.python-version` y `pyproject.toml`), FastAPI, Pydantic v2, SQLAlchemy 2.0, SQLite, pytest.
- Dependencias gestionadas con `uv` en `pyproject.toml` (con `uv.lock`). Agrégalas solo con `uv add` (`uv add --dev` para herramientas de prueba). No uses `pip` ni `requirements.txt`, y no agregues dependencias sin avisar.

## Comandos

- Instalar: `uv sync`
- Levantar con la demo: `uv run uvicorn app.main:app --reload`
- Levantar para el front: `SEMILLA=plataforma uv run uvicorn app.main:app --reload` (PowerShell: `$env:SEMILLA="plataforma"`, luego el comando)
- Tests: `uv run pytest -q`
- Fixtures para el front: `uv run python scripts/exportar_fixtures_front.py --destino <carpeta de ov_frontend>/tests/fixtures/servidor`

Corre `uv run pytest -q` antes de dar por terminada cualquier fase.

## Convenciones

- Código, tablas, columnas y funciones en español y `snake_case`.
- La API expone códigos legibles (`act-tip-01`, `est-ana`), nunca ids internos.
- `motor.py` no importa nada de los routers.
- Consultas: definiciones en caché, lecturas agrupadas por cuenta, escrituras en lote y ninguna consulta dentro de bucles.

## Secretos y servicios externos

- La clave de Gemini se lee de `.env`, que nunca se versiona. No la escribas en código, logs, respuestas, errores ni documentación.
- La aplicación admite `EVALUADOR=gemini` o `EVALUADOR=falso`, como define `docs/spec-demo-registro-gemini.md`. El valor por defecto es `falso`.
- Los tests usan siempre el evaluador falso y nunca acceden a la red.
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

- Los códigos del backend son los ids del front (`mission-welcome`, `act-tip-01`, `I1`, `psychologist`). No hay tablas de traducción.
- El JSON usa los nombres en español y `snake_case` de los esquemas Pydantic. El front los copia tal cual en `src/features/servidor/tipos.ts` y accede al backend solo desde `src/features/servidor/`.
- Si una tarea cambia una respuesta que consume el front, en la misma tarea se actualizan el esquema y las pruebas del backend, `tipos.ts` y los adaptadores del front, los fixtures (`scripts/exportar_fixtures_front.py` de `ov_backend`, con `--destino` apuntando a `tests/fixtures/servidor/` de `ov_frontend`) y las pruebas del front.

**Git.** No hagas push salvo que se pida. Trabaja en una rama `iteracion-N` en cada repo, con un commit por fase y por repo y mensaje en español (`Iteración 1 · F2: semilla plataforma`). Nunca versiones `.env`, `.env.local` ni archivos `*.db`.

**Idioma.** Documentación, mensajes al usuario y commits en español.
