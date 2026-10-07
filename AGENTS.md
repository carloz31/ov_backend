# AGENTS.md

## Proyecto

Demo en FastAPI de una plataforma gamificada de orientación vocacional. Las especificaciones son la fuente de verdad, y cada una extiende a la anterior sin cambiarla:

1. `docs/spec-demo-motor-desbloqueos.md`: motor de desbloqueos, acciones y consultas.
2. `docs/spec-demo-instrumentos.md`: instrumentos, resultados y recomendación de carreras.
3. `docs/spec-demo-registro-gemini.md`: actividades de registro con repregunta mediante Gemini.

Si dos especificaciones parecen contradecirse, detente y explica la contradicción antes de cambiar nada.

## Reglas de trabajo

- Lee la especificación completa antes de escribir código.
- Implementa por fases, según la sección 11 de la especificación. Al terminar cada fase, detente y resume qué hiciste, qué tests pasan y qué queda pendiente.
- No cambies la semántica del motor (sección 4), los datos semilla (sección 7) ni los resultados esperados de los escenarios (sección 9).
- Si un test de escenario falla, corrige la implementación, no el test. Si crees que la especificación se contradice, detente y explica la contradicción antes de cambiar nada.
- Si algo no está definido en la especificación, elige la opción más simple, anótala en `docs/decisiones.md` y sigue.
- No agregues funcionalidades fuera de alcance (sección 10): autenticación, LLM, instrumentos, panel de la orientadora.

## Stack

- Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, SQLite, pytest.
- Dependencias gestionadas con `uv` en `pyproject.toml` (con `uv.lock`). Agrégalas solo con `uv add` (`uv add --dev` para pytest). No uses `pip` ni `requirements.txt`, y no agregues dependencias sin avisar.

## Comandos

- Instalar: `uv sync`
- Levantar: `uv run uvicorn app.main:app --reload`
- Tests: `uv run pytest -q`

Corre `uv run pytest -q` antes de dar por terminada cualquier fase.

## Convenciones

- Código, tablas, columnas y funciones en español y `snake_case`.
- La API expone códigos legibles (`ACT-05`, `est-ana`), nunca ids internos.
- `motor.py` no importa nada de los routers.

## Secretos y servicios externos

- La clave de Gemini se lee de `.env`, que nunca se versiona. No la escribas en código, logs, respuestas, errores ni documentación.
- La aplicación admite `EVALUADOR=gemini` o `EVALUADOR=falso`, como define `docs/spec-demo-registro-gemini.md`. El valor por defecto es `falso`.
- Los tests usan siempre el evaluador falso y nunca acceden a la red.
- No ejecutes nada que llame a la API real de Gemini (la aplicación con `EVALUADOR=gemini` o `scripts/evaluar_gemini.py`) salvo que yo lo pida explícitamente.

