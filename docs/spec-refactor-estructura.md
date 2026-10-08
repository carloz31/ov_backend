# Refactor de estructura de `ov_backend`

> Especificación para ejecutar con Codex sobre la rama `iteracion-1`. Es un refactor: **el contrato HTTP no cambia** (rutas, cuerpos, respuestas, códigos de estado y mensajes de error), y `ov_frontend` no se toca. Lo que sí cambia es dónde vive cada cosa, cómo se crea la base y cómo se llenan los datos.

## 0. Cómo usar este documento

- Lee el documento completo y el `AGENTS.md` vigente antes de empezar.
- Trabaja en una rama nueva `refactor-estructura` creada desde `iteracion-1`. Al terminar, la rama se integra en `iteracion-1` (no lo hagas tú; deja la rama lista).
- Se ejecuta por fases (§9). Al terminar cada fase: corre `uv run pytest -q`, haz un commit (`Refactor · R2: nueva estructura de app`) y detente con un resumen (qué moviste, conteo de pruebas antes y después, qué queda pendiente).
- Esta spec **prevalece** sobre las secciones 4.1 (selección de semilla), 4.2 (esquema 5, `esquema_version` y su validación), el escenario P15 y la decisión «Semillas» de §8 de `docs/iteraciones/spec-iteracion-1.md`, y sobre la sección «Semillas» del `AGENTS.md` anterior. Todo lo demás de las specs sigue vigente.
- Si algo no está definido aquí, elige lo más simple, anótalo en `docs/decisiones.md` bajo «Refactor de estructura» y sigue.

## 1. Objetivo

1. Que cualquiera entienda dónde va cada cosa con solo mirar el árbol de carpetas.
2. Que `app/` contenga solo la aplicación: ni datos de prueba, ni lógica de semillas, ni código específico de SQLite.
3. Que la misma aplicación funcione con SQLite (desarrollo y pruebas) y con PostgreSQL cambiando solo `DATABASE_URL`.
4. Que el esquema de la base se gestione con migraciones (Alembic), no con una validación propia.

## 2. Situación actual (lo que se reemplaza)

- 33 archivos `.py` sueltos en `app/` con prefijos y sufijos mezclados (`consultas_instrumentos.py`, `esquemas_instrumentos.py`, `schemas_registro.py`, `semilla_*.py`, `seed.py`, `configuracion_*.py`).
- La aplicación siembra la base al arrancar y en `/demo/reiniciar`, según `SEMILLA=demo|plataforma`, con un archivo `.db` distinto por semilla y una tabla `esquema_version` que guarda versión y semilla.
- `database.py` valida el esquema leyendo restricciones `CHECK` con expresiones regulares y usa `PRAGMA`, `check_same_thread` y `BEGIN` explícito: todo específico de SQLite.
- `calculo_instrumentos.py` importa una constante de `semilla_instrumentos.py` (la lógica depende de los datos).
- Hay basura versionada: `.f6-cierre-pytest.log`, `.f6-cierre-servidor.log` y la carpeta `.pytest-f6-cierre-tmp/`.

## 3. Estructura objetivo

```
ov_backend/
├── app/                          # SOLO la aplicación
│   ├── __init__.py
│   ├── main.py                   # crear_aplicacion(): configuración, lifespan, routers, estáticos
│   ├── config.py                 # Configuracion + cargar_configuracion() (antes configuracion_base y configuracion_registro)
│   ├── database.py               # crear_motor_bd(), obtener_sesion(); ajustes de SQLite solo si el dialecto es sqlite
│   ├── dependencies.py           # SesionBD, ejecutar_accion (transacción + IntegrityError)
│   ├── exceptions.py             # ErrorAccion, ConsultaPendiente y su traducción a HTTPException
│   ├── api/                      # un archivo por grupo de rutas; sin lógica de negocio
│   │   ├── __init__.py
│   │   ├── router.py             # incluye todos los routers
│   │   ├── cuentas.py            # /reglas, /cuentas, /cuentas/{c}/estado|progreso|eventos|desbloqueos
│   │   ├── acciones.py           # /acciones/* del motor y /eventos
│   │   ├── instrumentos.py       # /instrumentos, /actividades/{a}/items, /cuentas/{c}/instrumentos/...
│   │   ├── registro.py           # /acciones/registro/*, /acciones/guardar-posicion, items-registro, registro
│   │   └── demo.py               # /demo/* (solo con ENTORNO=desarrollo)
│   ├── models/                   # tablas SQLAlchemy, agrupadas por dominio
│   │   ├── __init__.py           # importa y reexporta todos los modelos (lo usan Alembic y las pruebas)
│   │   ├── base.py               # Base (con naming_convention) y enumerado()
│   │   ├── enums.py              # todos los StrEnum, incluidos los de tipos_registro.py
│   │   ├── cuentas.py            # Cuenta, VinculoFamiliar
│   │   ├── contenido.py          # Bloque, Actividad, Ficha, Testimonio, PreguntaDiario, Conversacion, Insignia, Nivel, FamiliaCarrera, Carrera
│   │   ├── motor.py              # EventoUso, ReglaDesbloqueo, CondicionDesbloqueo, Desbloqueo
│   │   ├── progreso.py           # ProgresoActividad, ResultadoCaso, EntradaDiario, CheckIn, Entrevista, EntrevistaAutor, ConversacionVinculo
│   │   ├── instrumentos.py       # Instrumento, Dimension, EscalaRespuesta, OpcionEscala, ItemInstrumento, ActividadItem, Aplicacion, AplicacionActividad, Ocupacion, PuntajeOcupacion, CarreraOcupacion, RespuestaItem, ResultadoInstrumento, ResultadoDimension, Coincidencia
│   │   └── registro.py           # ItemRegistro, CriterioCompletitud, ActividadItemRegistro, RespuestaRegistro, TurnoSeguimiento, EvaluacionRespuesta
│   ├── schemas/                  # Pydantic: lo que entra y sale por la API
│   │   ├── __init__.py
│   │   ├── motor.py              # ObjetivoLegible, CondicionLegible, ReglaLegible, ProgresoCondicion, ResultadoEvaluador, ResultadoRegla, DesbloqueoNuevo
│   │   ├── cuentas.py            # CuentaResumen, NivelActual, *Estado, EstadoCuenta, ObjetivoProgreso, ProgresoRegla, ProgresoObjetivo, EventoLegible, DesbloqueoLegible, DesbloqueosMarcados
│   │   ├── acciones.py           # FechaAccion, AccionCuenta, todas las *Entrada, RespuestaAccion, RespuestaItemsGuardados, RespuestaCompletarActividad, ResultadoGenerado, ResultadoAnulado, RespuestaReiniciarInstrumento, RespuestaAgrupada
│   │   ├── instrumentos.py       # antes esquemas_instrumentos.py
│   │   ├── registro.py           # antes schemas_registro.py
│   │   └── demo.py               # ReinicioDemo
│   ├── services/                 # lógica de negocio, agrupada por dominio
│   │   ├── __init__.py
│   │   ├── comun.py              # buscar_por_codigo, fecha_accion, exigir_estudiante, exigir_disponible, existe_evento, responder_con_eventos, responder_varias_cuentas
│   │   ├── motor/                # núcleo de desbloqueos
│   │   │   ├── __init__.py
│   │   │   ├── reglas.py         # antes motor.py: evaluar_regla, registrar_eventos, objetivo_disponible, nivel_actual…
│   │   │   ├── evaluadores.py    # evaluadores especiales
│   │   │   └── referencias.py
│   │   ├── cuentas.py            # antes consultas.py: estado, progreso, eventos, desbloqueos
│   │   ├── eventos.py            # ingresar, registrar_evento_crudo
│   │   ├── actividades.py        # completar_progreso, items_de_actividad, progreso_de_actividad, responder_items, completar_actividad, reiniciar_instrumento, resolver_caso
│   │   ├── diario.py             # responder_registro, escribir_entrada, registrar_check_in
│   │   ├── carreras.py           # ver_carrera
│   │   ├── comunidad.py          # publicar_entrevista, vinculo_de_cuenta, escribir_carta, completar_conversacion
│   │   ├── instrumentos/
│   │   │   ├── __init__.py
│   │   │   ├── calculo.py        # antes calculo_instrumentos.py (puro, sin BD)
│   │   │   ├── consultas.py      # antes consultas_instrumentos.py
│   │   │   └── resultados.py     # antes resultados_instrumentos.py
│   │   ├── registro/
│   │   │   ├── __init__.py
│   │   │   ├── acciones.py       # antes acciones_registro.py
│   │   │   ├── consultas.py      # antes consultas_registro.py
│   │   │   ├── contenido.py      # antes contenido_registro.py
│   │   │   ├── evaluacion.py     # antes evaluador_respuestas.py (protocolo, EvaluadorFalso, validación)
│   │   │   ├── gemini.py         # antes evaluador_gemini.py
│   │   │   └── prompt.py         # antes prompt_registro.py
│   │   └── demo.py               # reiniciar estado de prueba, catálogo de formularios
│   ├── core/                     # piezas transversales que usan todos los servicios
│   │   ├── __init__.py
│   │   ├── parametros.py         # antes configuracion_metodos.py, más DIMENSIONES_RIASEC
│   │   ├── definiciones.py       # caché de catálogo por Engine (sin cambios de lógica)
│   │   └── contexto.py           # antes contexto_consultas.py (sin cambios de lógica)
│   └── static/                   # tablero de demo (sin cambios)
├── datos/                        # TODO lo que llena la base, fuera de app
│   ├── __init__.py
│   ├── cargar.py                 # CLI y preparar_base(); ver §6
│   ├── plataforma.py             # antes app/semilla_plataforma.py
│   ├── ocupaciones.py            # lector del Excel O*NET y validar_distribucion_items
│   ├── demo/
│   │   ├── __init__.py           # cargar(sesion): motor + instrumentos + registro
│   │   ├── motor.py              # antes app/seed.py (sin cargar_semilla_si_vacia ni obtener_cargador_semilla)
│   │   ├── instrumentos.py       # antes la parte de definiciones y catálogo de semilla_instrumentos.py
│   │   └── registro.py           # antes app/semilla_registro.py
│   └── archivos/
│       └── Career_Interest_RIASEC_Clean.xlsx   # antes data/
├── migrations/                   # Alembic
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_esquema_inicial.py
├── scripts/                      # herramientas manuales
│   ├── evaluar_gemini.py
│   └── exportar_fixtures_front.py
├── tests/
│   ├── conftest.py
│   ├── soporte/                  # ayudas de prueba (antes soporte_*.py, servidor_registro_ui.py, validar_registro_ui.cjs)
│   └── test_*.py
├── docs/
├── alembic.ini
├── pyproject.toml
├── .env.example
├── AGENTS.md
└── README.md
```

Decisiones de forma:

- **Carpetas en inglés, como la guía de referencia** (`api`, `models`, `schemas`, `services`, `core`), para que sean reconocibles; **módulos, funciones, tablas y columnas en español**, como hasta ahora. Los archivos no llevan sufijos (`_service`, `_repo`): la carpeta ya dice qué son. Para evitar choques de nombres, importa módulos con alias: `from app.services import actividades as servicio_actividades`.
- **Sin `api/v1/`**: el front consume las rutas sin prefijo de versión y el contrato no cambia. Si algún día hay v2, se crea la carpeta entonces.
- **Sin capa `repositories/`**: SQLAlchemy ya es la capa que aísla la base de datos, y la caché de definiciones y el contexto de consultas (`core/`) cumplen el papel de lectura agrupada. Agregar repositorios obligaría a reescribir todas las consultas sin ganar portabilidad.
- **`datos/` en Python con el ORM, no en `.sql`**: el mismo archivo funciona igual en SQLite y PostgreSQL (un `.sql` a mano tropieza con ids, booleanos y secuencias), el catálogo RIASEC se lee del Excel y las pruebas reutilizan los cargadores.
- **Un archivo por dominio; una carpeta solo cuando el dominio tiene más de un archivo** (`motor/`, `instrumentos/`, `registro/`).

## 4. Reglas de dependencias

```
api  →  services  →  core, models
 │         │
 └→ schemas, dependencies, exceptions
datos   →  app.models, app.core.parametros   (nunca al revés)
scripts, tests  →  app, datos
```

- `app/` **nunca** importa `datos`, `scripts` ni `tests`.
- `services/` nunca importa `api/` ni `fastapi` (excepto tipos neutros si ya ocurre hoy; no agregues nuevos).
- `core/` y `models/` nunca importan `services/`.
- `services/motor/` no importa nada de `api/` (equivale a la regla anterior «`motor.py` no importa nada de los routers»).
- `services/instrumentos/calculo.py` sigue sin acceso a la base. `DIMENSIONES_RIASEC` pasa a `core/parametros.py` y deja de vivir en los datos.
- `models/__init__.py` es el único lugar con reexportaciones. En `schemas/` y `services/` se importa desde el módulo concreto.

## 5. Base de datos

### 5.1 Configuración (`app/config.py`)

Un solo `Configuracion` (dataclass congelada) y `cargar_configuracion(entorno=None, ruta_env=RUTA_ENV)`, que fusiona `configuracion_base.py` y `configuracion_registro.py`. Lee de variables de entorno y de `.env` (como hoy, con `dotenv_values`).

| Variable | Por defecto | Efecto |
|---|---|---|
| `DATABASE_URL` | `sqlite:///ov.db` | URL de SQLAlchemy. Si es SQLite con ruta relativa, se resuelve desde la raíz del repo (igual que hoy `RUTA_BD`). |
| `ENTORNO` | `desarrollo` | `desarrollo` o `produccion`. En `produccion` no se incluye el router `/demo`. |
| `EVALUADOR`, `GEMINI_API_KEY`, `GEMINI_MODELO`, `GEMINI_TIMEOUT_SEGUNDOS` | sin cambios | Se conservan validaciones y mensajes de error exactos de `configuracion_registro.py`. |

`SEMILLA` y `RUTA_BD` desaparecen. Se usa `DATABASE_URL` (no `URL_BD`) porque es el nombre que inyectan los servicios de hosting con PostgreSQL. `crear_aplicacion(url_bd: str | None = None)` conserva su primer argumento para las pruebas y pierde `semilla`.

### 5.2 Motor y sesiones (`app/database.py`)

- `crear_motor_bd(url)`: `check_same_thread=False` y `PRAGMA foreign_keys=ON` **solo si** `make_url(url).get_backend_name() == "sqlite"`. Para cualquier otro dialecto, `create_engine(url, pool_pre_ping=True)`.
- `obtener_sesion` sin cambios de comportamiento (crea el `ContextoConsultas`).
- `es_bloqueo_temporal(error: OperationalError) -> bool`: reconoce `SQLITE_BUSY`, `SQLITE_BUSY_SNAPSHOT`, `SQLITE_LOCKED` y, en PostgreSQL, los `pgcode` `40001` y `55P03`. `api/registro.py` lo usa en lugar de leer `sqlite_errorname` directamente.
- Se eliminan `RUTA_BASE`, `URL_BASE`, `VERSION_ESQUEMA`, `MENSAJE_ESQUEMA_ANTERIOR` y `validar_version_esquema`.
- Se elimina el modelo `EsquemaVersion` y su tabla. Alembic guarda la versión en `alembic_version`.

### 5.3 Portabilidad de los modelos

- `Base` usa `MetaData(naming_convention=...)` con la convención estándar de Alembic (`ix`, `uq`, `ck`, `fk`, `pk`). Los `CHECK` de enumerados conservan su nombre base (`tipoeventouso`, etc.) dentro de la convención.
- Los dos índices parciales (`entrada_guiada_unica` en `entrada_diario` y el de `resultado_instrumento` con `anulado_en IS NULL`) llevan `sqlite_where` **y** `postgresql_where` con la misma expresión.
- `func.date(...)` en `core/contexto.py` se queda: funciona en SQLite y PostgreSQL. **No** lo reemplaces por `CAST(... AS DATE)`: en SQLite ese cast devuelve el año como número y rompe el conteo de días distintos.
- `insert(...).returning(...)` se queda (lo soportan ambos).
- Ninguna consulta nueva usa SQL específico de un motor. Si fuera inevitable, va en `database.py` con ramas por dialecto.

### 5.4 Migraciones (Alembic)

- Dependencia nueva autorizada por esta spec: `uv add alembic`.
- `alembic.ini` en la raíz y carpeta `migrations/`. `migrations/env.py` toma la URL de `cargar_configuracion().url_bd` (no de `alembic.ini`), usa `app.models.Base.metadata` como `target_metadata` y `render_as_batch=True` (necesario para alterar tablas en SQLite).
- `0001_esquema_inicial.py` se genera con `uv run alembic revision --autogenerate -m "esquema inicial"` sobre una base vacía y se revisa a mano: deben estar todas las tablas, los `CHECK` de enumerados, las claves foráneas y los índices parciales con sus dos variantes de dialecto.
- Desde ahora, **todo cambio de modelos va con su migración en el mismo commit**.
- La aplicación **no** llama a `create_all` ni siembra. En el `lifespan`, si falta alguna tabla del modelo, falla con: «La base no tiene el esquema. Ejecuta `uv run alembic upgrade head` y carga datos con `uv run python -m datos.cargar plataforma`.»
- Con el esquema presente y el catálogo vacío, la aplicación arranca (responde listas vacías).

### 5.5 PostgreSQL

- Dependencia opcional autorizada: `uv add --optional postgres "psycopg[binary]"`. Se instala con `uv sync --extra postgres`.
- URL de ejemplo en `.env.example` (comentada): `DATABASE_URL=postgresql+psycopg://ov:ov@localhost:5432/ov`.
- Prueba de humo `tests/test_postgres.py`, que se **omite** si no existe la variable `TEST_POSTGRES_URL`: aplica `alembic upgrade head`, carga `plataforma`, recorre P1, P2, P7 y P10 por HTTP y compara con lo esperado. Si en tu entorno no hay PostgreSQL, deja la prueba escrita y anótalo en el resumen.

## 6. Datos (`datos/`)

### 6.1 Contenido

| Archivo | Viene de | Contiene |
|---|---|---|
| `datos/plataforma.py` | `app/semilla_plataforma.py` | `cargar(sesion)`. Mismos datos, sin `EsquemaVersion`. |
| `datos/demo/motor.py` | `app/seed.py` | `cargar_motor(sesion)`: cuentas, bloques, actividades, contenido, reglas de la demo. |
| `datos/demo/instrumentos.py` | `app/semilla_instrumentos.py` | `cargar_definiciones_instrumentos`, `relaciones_carreras`, `cargar_catalogo_ocupaciones`. |
| `datos/demo/registro.py` | `app/semilla_registro.py` | `cargar_definiciones_registro`. |
| `datos/demo/__init__.py` | — | `cargar(sesion)`: llama a los tres, en el mismo orden que hoy `cargar_semilla`. |
| `datos/ocupaciones.py` | `app/semilla_instrumentos.py` | `RUTA_OCUPACIONES`, `OcupacionArchivo`, `leer_ocupaciones`, `validar_distribucion_items`. |

Los datos, reglas y resultados esperados de `demo` y `plataforma` **no cambian**. Las marcas `DATO DE PRUEBA` se conservan.

### 6.2 `datos/cargar.py`

```
uv run python -m datos.cargar plataforma            # carga en la base de DATABASE_URL
uv run python -m datos.cargar demo
uv run python -m datos.cargar plataforma --vaciar   # borra todas las filas y vuelve a cargar
```

- `CONJUNTOS = {"demo": datos.demo.cargar, "plataforma": datos.plataforma.cargar}`.
- `preparar_base(url, conjunto, *, crear_tablas=False, vaciar=False)`: si `crear_tablas`, hace `Base.metadata.create_all` (solo lo usan pruebas y el script de fixtures); si `vaciar`, borra las filas de todas las tablas en orden inverso de dependencias; carga el conjunto en **una** transacción. Si la base ya tiene catálogo y no se pasó `--vaciar`, falla con un mensaje que lo explica.
- Si falta el esquema, el mensaje dice que se ejecute `uv run alembic upgrade head`.
- Al terminar imprime cuántas filas quedaron en las tablas principales.

### 6.3 `/demo/reiniciar`

Mismo contrato (`POST /demo/reiniciar` → `{"mensaje": "Demo reiniciada"}`), nueva implementación en `services/demo.py`:

- **Borra solo el estado de las cuentas** y deja intacto el catálogo. No hay DDL, `drop_all`, `create_all` ni `BEGIN` explícito, y no depende de qué conjunto de datos se cargó.
- `TABLAS_DE_ESTADO` es una lista explícita en `services/demo.py`: `progreso_actividad`, `resultado_caso`, `entrada_diario`, `check_in`, `entrevista`, `entrevista_autor`, `conversacion_vinculo`, `evento_uso`, `desbloqueo`, `respuesta_item`, `resultado_instrumento`, `resultado_dimension`, `coincidencia`, `respuesta_registro`, `turno_seguimiento`, `evaluacion_respuesta` (ajusta los nombres a los `__tablename__` reales). Se borran en orden inverso de dependencias dentro de una transacción.
- Una prueba nueva comprueba que **toda** tabla del modelo está clasificada como catálogo o como estado, para que una tabla nueva de la iteración 2 no quede fuera del reinicio sin que nadie lo note.
- Como el catálogo no cambia, no hace falta recargar la caché de definiciones ni las posiciones de registro.

### 6.4 Contenido de registro (`REG-ACT08.json`)

En el arranque, `cargar_posiciones_registro` se ejecuta solo si la actividad que nombra el JSON existe en la base. Si existe y el JSON no coincide, la aplicación no arranca (como hoy). Si no existe (por ejemplo, con `plataforma`), `posiciones_registro` queda vacío. Ya no se mira ninguna variable de semilla.

## 7. Cambios en `main.py`

`crear_aplicacion(url_bd=None)`:

1. `cargar_configuracion()`; si se pasa `url_bd`, prevalece.
2. Crea motor y `sessionmaker`.
3. `lifespan`: crea el evaluador (como hoy), comprueba que el esquema exista (§5.4), calcula `posiciones_registro` (§6.4), crea `CacheDefiniciones` y al salir cierra motor y evaluador.
4. `app.include_router(api.router.router)`; `api/router.py` incluye `demo` solo si `ENTORNO == "desarrollo"`.
5. Monta `/demo/recursos` sobre `app/static` solo en desarrollo.

Desaparece `app.state.semilla`.

## 8. Pruebas

### 8.1 Preparación

- `tests/conftest.py`: el fixture `aplicacion` prepara una base SQLite temporal con `preparar_base(url, "demo", crear_tablas=True)` y luego `crear_aplicacion(url)`. Se agrega `aplicacion_plataforma` con el conjunto `plataforma`; las pruebas de `plataforma` dejan de pasar `semilla='plataforma'`.
- `pyproject.toml`: `pythonpath = [".", "tests/soporte"]` para que las ayudas sigan importándose por su nombre (`from soporte_consultas import ...`).
- El fixture que omite el catálogo si falta el Excel apunta a `datos.demo.instrumentos.cargar_catalogo_ocupaciones`.
- `tests/test_migraciones.py` (nueva): aplica `alembic upgrade head` sobre una SQLite temporal y comprueba con `alembic.autogenerate.compare_metadata` que no hay diferencias con `Base.metadata`.

### 8.2 Adaptaciones autorizadas por adelantado

Anótalas en `docs/decisiones.md`, bajo «Refactor de estructura», con la lista de pruebas eliminadas y las que las reemplazan.

1. **Rutas de importación y objetivos de `monkeypatch`** (por ejemplo, `monkeypatch.setattr(acciones, "registrar_eventos", ...)` pasa a apuntar a `app.services.comun`). Solo el destino; la aserción no cambia.
2. **Selección de semilla y archivo de base**: se eliminan las pruebas de `SEMILLA`/`RUTA_BD` de `test_configuracion_base.py` y se reemplazan por pruebas de `cargar_configuracion` (`DATABASE_URL` por defecto, ruta relativa resuelta desde la raíz, URL explícita que prevalece, `ENTORNO` inválido).
3. **Versión de esquema y semilla guardada**: se eliminan las pruebas que validan `esquema_version`, la versión 5, el rechazo de bases con esquema anterior o de otra semilla y los `CHECK` leídos por regex (`test_configuracion_base.py`, `test_semilla_instrumentos.py`, `test_semilla_plataforma.py`, `test_fase1.py`, P15 en `test_plataforma.py`). Las reemplazan `test_migraciones.py` y una prueba de que el arranque sin esquema falla con el mensaje de §5.4 sin crear tablas.
4. **Siembra al arrancar y en el reinicio**: las pruebas que esperaban que el arranque sembrara, que el reinicio recargara la semilla o que un fallo de semilla revirtiera DDL y caché pasan a probar `preparar_base` (carga atómica: si falla, la base queda sin filas de catálogo) y el nuevo reinicio (borra todo el estado, conserva el catálogo, y la caché sigue válida).
5. **Listas exactas de tablas, columnas, índices y restricciones**: sin `esquema_version` y con los nombres que produce la `naming_convention`.
6. **Contenido de registro**: las pruebas que lo validaban según la semilla pasan a validarlo según exista o no la actividad del JSON (§6.4).

Cualquier otra prueba que falle se arregla en la implementación. Si no se puede, detente y pregunta.

## 9. Fases

| Fase | Contenido | Para terminar |
|---|---|---|
| R0 | Línea base: `uv sync`, `uv run pytest -q`, anota el conteo (hoy 1006) en `docs/decisiones.md`. | Conteo registrado. |
| R1 | Limpieza: `git rm -r` de `.f6-cierre-pytest.log`, `.f6-cierre-servidor.log` y `.pytest-f6-cierre-tmp/`; agrega `*.log` y `.pytest-*/` a `.gitignore`. | Pruebas iguales que en R0. |
| R2 | **Solo mover** a la estructura de §3 (`app/` y `tests/soporte/`), con `git mv` para conservar el historial: `models/`, `schemas/`, `services/`, `core/`, `api/`, `config.py` (por ahora, solo reexportando lo de los dos módulos de configuración), `dependencies.py`, `exceptions.py`. Las semillas pasan a `datos/` tal cual, y `app/main.py` todavía las llama a través de una función puente en `main.py` (temporal). Actualiza imports y objetivos de `monkeypatch` (adaptación 1). Sin cambios de comportamiento. | **Mismo número de pruebas que en R0, todas en verde.** Ningún archivo `.py` suelto en `app/` salvo los seis de §3. |
| R3 | Datos fuera de la aplicación: §5.1, §6 y §7. Elimina el puente de R2, `SEMILLA`, `RUTA_BD`, la siembra en el arranque, `app.state.semilla`; reinicio nuevo; `datos.cargar`; `conftest` con `preparar_base`; `scripts/exportar_fixtures_front.py` y `scripts/evaluar_gemini.py` usan `datos`. Adaptaciones 2, 4 y 6. | Pruebas en verde; los fixtures del front que genera el script son idénticos byte a byte a los actuales (genera en una carpeta temporal y compara con los de `ov_frontend/tests/fixtures/servidor/` si la carpeta está disponible; si no, compara contra una generación hecha en R0). |
| R4 | Portabilidad: §5.2, §5.3, §5.4 y §5.5. Elimina `EsquemaVersion` y `validar_version_esquema`, agrega Alembic y la migración inicial, `naming_convention`, índices parciales para ambos dialectos, `es_bloqueo_temporal`, extra `postgres`, `test_migraciones.py` y `test_postgres.py`. Adaptaciones 3 y 5. | Pruebas en verde; `uv run alembic upgrade head` sobre una base nueva + `uv run python -m datos.cargar plataforma` + `uv run uvicorn app.main:app` responde `GET /cuentas`. |
| R5 | Documentación: reemplaza `AGENTS.md` por el del Anexo A; actualiza en `README.md` las secciones «Instalación y ejecución» y «Selección de semilla y base» (esta última pasa a «Base de datos y datos de prueba») y agrega «Estructura del proyecto» con el árbol de §3; en `docs/iteraciones/spec-iteracion-1.md` agrega al inicio de 4.1, 4.2 y P15 la nota «Sustituido por `docs/spec-refactor-estructura.md`»; en `docs/iteraciones/plan-iteraciones.md` cambia los comandos de arranque (`$env:SEMILLA=...`) por los de §10; actualiza `.env.example`. Si `ov_frontend` está disponible y su documentación menciona `SEMILLA`, actualiza solo esa documentación en la misma tarea. | `grep -rn "SEMILLA\|RUTA_BD\|semilla_plataforma\|app/seed" --include=*.py --include=*.md .` solo devuelve menciones históricas en `docs/decisiones.md` y en las notas de sustitución. |

## 10. Comandos finales

```bash
uv sync                                         # instalar
uv run alembic upgrade head                     # crear o actualizar el esquema
uv run python -m datos.cargar plataforma        # datos para el front (o: demo)
uv run python -m datos.cargar plataforma --vaciar   # empezar de cero
uv run uvicorn app.main:app --reload            # levantar
uv run pytest -q                                # pruebas
uv run alembic revision --autogenerate -m "..." # después de cambiar un modelo
uv run python scripts/exportar_fixtures_front.py --destino <ov_frontend>/tests/fixtures/servidor
```

PowerShell: los mismos comandos; para otra base, `$env:DATABASE_URL="sqlite:///otra.db"` antes de ejecutar.

## 11. Invariantes del refactor

1. Ninguna ruta, cuerpo, respuesta, código de estado ni mensaje de error de la API cambia (salvo que `/demo/*` no existe con `ENTORNO=produccion`).
2. Los escenarios E1–E17, I1–I14, los de registro y P1–P14 y P16 pasan sin cambiar sus aserciones.
3. Los fixtures del front no cambian.
4. `app/` no importa `datos`, `scripts` ni `tests`.
5. El único código que conoce el dialecto de la base está en `app/database.py` (y los `*_where` de los índices parciales).
6. Las pruebas nunca acceden a la red (salvo `test_postgres.py` contra la base indicada en `TEST_POSTGRES_URL`) ni a Gemini.

---

## Anexo A. `AGENTS.md` nuevo

En la fase R5, reemplaza el contenido completo de `AGENTS.md` por el texto siguiente. La sección «Reglas compartidas entre ov_backend y ov_frontend» es idéntica a la actual (y a la de `ov_frontend`), así que el `AGENTS.md` del front no cambia.

````markdown
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

- Los códigos del backend son los ids del front (`mission-welcome`, `act-tip-01`, `I1`, `psychologist`). No hay tablas de traducción.
- El JSON usa los nombres en español y `snake_case` de los esquemas Pydantic. El front los copia tal cual en `src/features/servidor/tipos.ts` y accede al backend solo desde `src/features/servidor/`.
- Si una tarea cambia una respuesta que consume el front, en la misma tarea se actualizan el esquema y las pruebas del backend, `tipos.ts` y los adaptadores del front, los fixtures (`scripts/exportar_fixtures_front.py` de `ov_backend`, con `--destino` apuntando a `tests/fixtures/servidor/` de `ov_frontend`) y las pruebas del front.

**Git.** No hagas push salvo que se pida. Trabaja en una rama `iteracion-N` en cada repo, con un commit por fase y por repo y mensaje en español (`Iteración 1 · F2: semilla plataforma`). Nunca versiones `.env`, `.env.local` ni archivos `*.db`.

**Idioma.** Documentación, mensajes al usuario y commits en español.
````
