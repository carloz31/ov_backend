# Plataforma de orientación vocacional · backend

API FastAPI de Orientación Explora, consumida por `ov_frontend`. La base de datos es la fuente de disponibilidad, progreso, respuestas, resultados, fichas, insignias y nivel. El contenido narrativo de las actividades permanece en el frontend.

## Preparar y ejecutar

Requisitos: Python 3.14 y uv. Desde la raíz de ov_backend, crea `.env` a partir de [.env.example](.env.example) y prepara una base nueva:

```powershell
uv sync
$env:EVALUADOR="falso"
uv run alembic upgrade head
uv run python -m datos.cargar plataforma
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

La aplicación no crea tablas ni carga datos al arrancar. Alembic gestiona el esquema; la carga se hace explícitamente una vez sobre una base nueva. En los siguientes arranques basta con Uvicorn. La documentación interactiva está en `http://127.0.0.1:8000/docs`.

`DATABASE_URL` selecciona la única base que consulta la aplicación; su valor predeterminado es `sqlite:///ov.db`, relativo a la raíz del repo. Para PostgreSQL, instala `uv sync --extra postgres`, configura la URL antes de migrar y cargar y utiliza una base disponible. No versiones `.env` ni bases `*.db`.

El evaluador predeterminado es `falso`. La aplicación admite Gemini mediante la configuración de `.env`, pero las pruebas nunca llaman a ese servicio. No ejecutes el evaluador real sin autorización explícita ni publiques su clave.

## Datos y reinicio

| Conjunto | Uso |
|---|---|
| `plataforma` | Datos alineados con los códigos y contenidos del frontend, definidos por la iteración vigente. |
| `piloto` | Datos del piloto de evaluación y sus pruebas de integración. |

Para cargar el piloto, usa `uv run python -m datos.cargar piloto`. El cargador admite `--vaciar` para vaciar y volver a cargar la base seleccionada; úsalo únicamente cuando quieras reemplazar sus datos. Los datos inventados se marcan con `DATO DE PRUEBA`.

`POST /desarrollo/reiniciar` está disponible solo en `ENTORNO=desarrollo`: borra las 16 tablas de estado de cuentas y conserva catálogo y cartas familiares. Responde `{"mensaje":"Datos de prueba reiniciados"}`. En producción no se incluye esta ruta.

El conjunto, páginas, recursos y rutas HTTP de demo del backend se retiraron. El modo local y los datos de demostración de ov_frontend siguen funcionando.

## Estructura

Las reglas completas están en [AGENTS.md](AGENTS.md).

```text
app/             # aplicación; no lee archivos de datos
  api/           # rutas sin lógica de negocio
  services/      # lógica por dominio; motor/, instrumentos/, registro/
  schemas/       # contrato Pydantic
  models/        # tablas y enumerados
  core/          # parámetros, caché y contexto
  main.py, config.py, database.py, dependencies.py, exceptions.py
datos/           # plataforma, piloto y catálogo O*NET
migrations/      # Alembic
scripts/         # herramientas manuales, incluido el exportador de fixtures
tests/
  conftest.py     # evaluador falso, sin base
  soporte/       # ayudas compartidas
  unit/          # arquitectura, configuracion, instrumentos, motor, registro
  integration/   # actividades, cuentas, desarrollo, fichas, instrumentos, logros,
                 # motor, datos, migraciones, contrato, escenarios/plataforma y piloto
docs/            # especificaciones y decisiones
```

Las pruebas de integración copian una plantilla SQLite por conjunto, creada una vez por sesión y proceso. Cada prueba tiene una base independiente. Las pruebas de carga y migraciones preparan sus propias bases para comprobar el proceso real.

## Pruebas

```powershell
uv run pytest tests/unit -q
uv run pytest tests/integration/instrumentos -q
uv run pytest tests/integration/escenarios -q
uv run pytest tests/integration/contrato -q
uv run pytest -n auto -q
```

Durante el desarrollo se ejecutan las carpetas de impacto; al cerrar una fase se añaden los escenarios. Para cerrar una iteración o integrar se ejecuta toda la suite de ambos repos. La tabla por dominio y la política compartida están en [AGENTS.md](AGENTS.md).

Si falla el lanzador de pytest en Windows, usa `uv run python -m pytest` con los mismos argumentos. Mantén temporales y logs fuera del repo; puedes añadir `--basetemp="$env:TEMP/ov-pruebas" -p no:cacheprovider` con una carpeta exclusiva para esa ejecución.

Las cuatro pruebas con marca `postgres` se omiten si no existe `TEST_POSTGRES_URL`. Para ejecutarlas, configura una base PostgreSQL de pruebas y usa `uv run pytest tests/integration/migraciones -m postgres -q`.

La suite final recoge 530 pruebas: 526 pasan y 4 se omiten sin PostgreSQL. En P0 había 1099; se retiraron 607 casos ligados a la demo y 3 variantes parametrizadas, se portaron 40 comportamientos aprobados y se añadió un invariante de arquitectura. P4 redujo el tiempo de 788,50 s (P0) a 143,86 s secuencial o 46,18 s con `-n auto`. Los conteos, adaptaciones, excepciones de setup y mediciones se detallan en [decisiones](docs/decisiones.md), sección «Pruebas y retiro de demo», y el [inventario aprobado](docs/inventario-retiro-demo.md).

## Fixtures del frontend

Desde ov_backend, indicando la ubicación real del otro repo:

```powershell
uv run python scripts/exportar_fixtures_front.py --destino "<ruta de ov_frontend>/tests/fixtures/servidor"
```

El exportador prepara una base temporal y genera los 16 fixtures reproducibles del contrato. En ov_frontend, valida con `npm run test:servidor`. Si cambia una respuesta, actualiza también tipos, servicios, adaptadores y pruebas en ambos repos, según AGENTS.md.

## Especificaciones

- [Iteración 1](docs/iteraciones/spec-iteracion-1.md): alcance y contrato de integración vigente.
- [Decisiones compartidas](docs/iteraciones/decisiones-iteracion-1.md).
- [Estructura, base y carga](docs/spec-refactor-estructura.md).
- [Retiro de demo y organización de pruebas](docs/spec-pruebas-y-retiro-demo.md).
- Reglas de comportamiento: [motor](docs/spec-demo-motor-desbloqueos.md), [instrumentos](docs/spec-demo-instrumentos.md) y [registro](docs/spec-demo-registro-gemini.md). Sus datos y escenarios son históricos y ya no se cargan.
- [Evaluación histórica de Gemini](docs/evaluacion_gemini.md): registro de una evaluación anterior, no instrucciones operativas actuales.

No se adelantan las siguientes iteraciones ni se hace push sin petición explícita.
