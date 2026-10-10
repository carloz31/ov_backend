# Plataforma de orientación vocacional · backend

API FastAPI de Orientación Explora, consumida por `ov_frontend`. La base de datos es la fuente de disponibilidad, progreso, respuestas, resultados, fichas, insignias y nivel; el contenido narrativo de las actividades está en el frontend.

## Preparar y ejecutar

Requisitos: Python 3.14 y uv. Crea `.env` a partir de [.env.example](.env.example) y, sobre una base nueva:

```powershell
uv sync
uv run alembic upgrade head
uv run python -m datos.cargar plataforma
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

La aplicación no crea tablas ni carga datos al arrancar: la migración y la carga se hacen una vez. Después basta con Uvicorn. Documentación interactiva: `http://127.0.0.1:8000/docs`.

- `DATABASE_URL` elige la base (por defecto `sqlite:///ov.db` en la raíz). Para PostgreSQL: `uv sync --extra postgres` y la URL antes de migrar y cargar.
- Conjuntos de datos: `plataforma` y `piloto` (`uv run python -m datos.cargar piloto`); `--vaciar` reemplaza los datos de la base.
- `POST /desarrollo/reiniciar` (solo con `ENTORNO=desarrollo`) borra el estado de las cuentas y conserva el catálogo.
- El evaluador de registros es `falso` por defecto. Para usar Gemini, configura `EVALUADOR=gemini` y `GEMINI_API_KEY` en `.env`; nunca publiques la clave.

## Pruebas

```powershell
uv run pytest tests/integration/instrumentos -q   # una carpeta
uv run pytest -n auto -q                          # todo
```

Qué carpeta corresponde a cada cambio: tabla de impacto en [AGENTS.md](AGENTS.md). Las pruebas `postgres` se omiten si no existe `TEST_POSTGRES_URL`.

## Fixtures del frontend

```powershell
uv run python scripts/exportar_fixtures_front.py --destino "<ruta de ov_frontend>/tests/fixtures/servidor"
```

## Documentación

- [AGENTS.md](AGENTS.md): estructura, reglas y convenciones.
- [docs/sistema/](docs/sistema/): cómo funcionan hoy el motor, los instrumentos, el registro y la integración con el front.
- [docs/plan-iteraciones.md](docs/plan-iteraciones.md) y [docs/specs/](docs/specs/): plan y spec en curso.
- [docs/historico/](docs/historico/): specs, decisiones y validaciones de trabajos terminados.
