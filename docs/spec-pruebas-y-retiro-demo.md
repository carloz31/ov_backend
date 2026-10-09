# Spec: retiro de la demo y reorganización de pruebas

Va en `ov_backend/docs/spec-pruebas-y-retiro-demo.md`. Afecta a `ov_backend` y `ov_frontend` (rama `iteracion-1`). No cambia ninguna HU ni el comportamiento visible de la plataforma en modo `api`.

## 1. Objetivo

1. **Retirar la demo del backend.** El conjunto `demo`, sus páginas HTML, sus rutas y sus pruebas ya cumplieron su función: validar el motor, los instrumentos y el registro con Gemini. A partir de esta spec, **los datos del backend vienen únicamente de la base de datos a la que se conecta** (`DATABASE_URL`). La carpeta `app/` no lee archivos de datos.
2. **Ordenar las pruebas** de los dos repos por tipo y por dominio, para que durante el desarrollo se ejecuten solo las afectadas.
3. **Acelerar la suite del backend**, que hoy gasta la mayor parte del tiempo en preparar bases.

## 2. Línea base medida (referencia)

Medida en `iteracion-1` (backend `550f119`, front `7df1b17`). La fase P0 la vuelve a medir en tu máquina.

| Repo | Pruebas | Resultado | Tiempo | Observación |
|---|---|---|---|---|
| backend | 1099 recolectadas | 1095 pasan, 4 omitidas (`test_postgres.py`) | 6 min 13 s | 278 s de *setup* contra 90 s de ejecución: el costo está en sembrar una base por prueba. |
| front | 463 | 449 pasan, 14 fallan (todas en `adventure-rendering.test.mjs`) | 76 s | Las fallas son previas a esta spec. |

Uso del conjunto `demo` en el backend (clasificación por fixture y por llamadas a `preparar_base`):

| Grupo | Pruebas aprox. | Archivos principales |
|---|---|---|
| Usan `demo` | ~650 | `test_consultas`, `test_registro*`, `test_instrumentos`, `test_motor`, `test_acciones`, `test_escenarios`, `test_invariantes`, `test_fase1`, `test_semilla_instrumentos`, `test_demo*`, `test_configuracion_base`, `test_configuracion_metodos` |
| Sin base de datos | ~290 | `test_calculo_instrumentos`, `test_evaluador_respuestas`, parte de `test_evaluador_gemini`, `test_migraciones`, `test_configuracion` |
| `plataforma` o `piloto` | ~110 | `test_plataforma`, `test_consultas_dominio`, `test_semilla_plataforma`, `test_piloto`, `test_descripciones_dimensiones`, `test_fixtures_dominio`, `test_exportar_fixtures_front`, `test_postgres` |
| Otras bases temporales | ~70 | `test_configuracion`, `test_migraciones`, `test_evaluador_gemini`, `test_carga_datos` |

## 3. Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Conjunto `demo` | Se elimina con todos sus datos (E1–E17, I1–I14, registro, bloque `LAB`). |
| Pruebas del registro con Gemini | Pueden quedar sin cobertura. Se escriben pruebas nuevas en la iteración 2, sobre `plataforma`. Las pruebas que **no** dependen de `demo` (por ejemplo, `test_evaluador_respuestas`) se conservan. |
| Catálogo O*NET | Ya vive en `datos/ocupaciones.py` y se carga en la base con `datos.cargar`. Se confirma que nada de `app/` lee el Excel. |
| Reinicio de datos | `POST /demo/reiniciar` pasa a `POST /desarrollo/reiniciar`, solo en `ENTORNO=desarrollo`, con el mismo comportamiento: borra el estado de las cuentas y conserva el catálogo. |
| `app/static/` | Se elimina completa, incluido `contenido/REG-ACT08.json`. |
| Posiciones de registro | Hoy salen de `REG-ACT08.json`; con `plataforma` ya quedan vacías. Se eliminan junto con la ruta `POST /acciones/guardar-posicion`, que el front no usa. La columna `progreso_actividad.posicion` se conserva y la iteración 2 define las posiciones en la base. |
| Esquema | No cambia. No hay migración nueva. |
| `demo` del front | `src/data/demo/` y `demoAccess` son del modo `local` del front y **no se tocan**. |

## 4. Retiro de la demo (backend)

### 4.1 Se elimina

| Elemento | Detalle |
|---|---|
| `datos/demo/` | Carpeta completa. |
| `datos/cargar.py` | `'demo'` de `CONJUNTOS` y del mensaje de error, la importación de `datos.demo.registro` y `preparar_base_registro_en_memoria`. |
| `scripts/evaluar_gemini.py` | Depende del registro de la demo. `docs/evaluacion_gemini.md` se conserva como registro histórico. |
| `app/static/` | Carpeta completa. |
| `app/api/demo.py`, `app/services/demo.py`, `app/schemas/demo.py` | Se reemplazan por los de §4.2. Desaparecen `GET /demo`, `/demo/instrumentos`, `/demo/registro`, `/demo/catalogo` y `consultar_catalogo`. |
| `app/api/registro.py` | `router_demo` y la ruta `GET /demo/registro/{cuenta}/{actividad}/evaluaciones`. |
| `app/services/registro/consultas.py` | `consultar_evaluaciones`. |
| `app/schemas/registro.py` | `EvaluacionRegistroDemo`, `GuardarPosicionEntrada` y `PosicionGuardada`, si no se usan en otro lugar. |
| `app/services/registro/contenido.py` | Archivo completo. |
| `app/services/registro/acciones.py` | `guardar_posicion`. |
| `app/api/registro.py` | `POST /acciones/guardar-posicion`. |
| `app/main.py` | El montaje de `StaticFiles` en `/demo/recursos`, la carga de `posiciones_registro` y `app.state.posiciones_registro`. |
| `tests/soporte/servidor_registro_ui.py`, `tests/soporte/validar_registro_ui.cjs` | Probaban las páginas HTML. |

### 4.2 Se crea o se renombra

- `app/api/desarrollo.py`: `router = APIRouter(prefix="/desarrollo", tags=["Desarrollo"])` con una sola ruta, `POST /reiniciar` → `ReinicioDesarrollo(mensaje="Datos de prueba reiniciados")`.
- `app/services/desarrollo.py`: `TABLAS_DE_ESTADO` (misma lista) y `reiniciar_estado(sesion)`, el antiguo `reiniciar_demo` sin cambios de lógica.
- `app/schemas/desarrollo.py`: `ReinicioDesarrollo(mensaje: str)`.
- `app/api/router.py` incluye `desarrollo.router` solo si `entorno == 'desarrollo'`.
- `app/main.py`: `FastAPI(title="Plataforma de orientación vocacional", ...)`.
- `pyproject.toml`: la `description` deja de decir «Demo».

### 4.3 Front (mismo commit lógico, porque cambia el contrato)

- `src/services/api/demo.ts` → `src/services/api/desarrollo.ts`, con `enviar('/desarrollo/reiniciar', {})`.
- `src/store/servidor/operaciones.ts`: importa `* as apiDesarrollo from '@/services/api/desarrollo'`.
- `tests/servidor-servicios.test.mjs`: la ruta esperada pasa a `/desarrollo/reiniciar`. Es la única aserción que se adapta en el front.
- Si `scripts/verificar-estructura.mjs` lista los archivos de `services/api`, se actualiza.
- `docs/refactor/*.md` del front **no** se reescriben: son históricos.

### 4.4 Invariantes nuevos

1. `app/` no lee archivos de datos. Las únicas lecturas de disco permitidas son las de `.env` en `app/config.py`.
2. No existe ninguna ruta bajo `/demo`.
3. `grep -rni "demo" app datos scripts tests` solo devuelve coincidencias justificadas: nombres en inglés de terceros o textos históricos. Se listan en `docs/decisiones.md`.

Se agrega una prueba unitaria, `tests/unit/arquitectura/test_sin_archivos_en_app.py`, que recorre `app/**/*.py` y falla si encuentra `read_text(`, `open(`, `json.load`, `StaticFiles` o `FileResponse` fuera de `app/config.py`.

## 5. Ajuste de las pruebas del backend al retiro

Cada prueba que hoy usa `demo` cae en una de estas tres categorías:

| Cat. | Criterio | Acción |
|---|---|---|
| **A** | No depende de `demo`. | Se conserva igual. Si estaba parametrizada con `['demo', 'plataforma']` (`test_carga_datos`, `test_migraciones`, `test_contenido_actividades`), se quita `'demo'`. |
| **B** | Usa `demo` solo como base cualquiera: sus aserciones no mencionan códigos, cuentas, conteos ni textos de la demo. | Se cambia el fixture a `plataforma`. **La aserción no cambia.** |
| **C** | Sus aserciones dependen de datos de la demo: códigos E*/I*, `LAB`, `REG-ACT08`, cuentas o conteos de la demo. | Se elimina, salvo las aprobadas en el inventario de P1, que se reescriben sobre `plataforma`. |

**Pruebas de registro** (`test_registro*.py`, `test_demo_registro.py`): categoría C completa, sin portar.

**Criterio para proponer un port en P1.** Una prueba de categoría C se propone para portar solo si cumple las dos condiciones:

1. Cubre un comportamiento del motor, de las consultas o de los instrumentos que se usa en la iteración 1 o en una iteración planificada. Por ejemplo: un tipo de evaluador, una regla con varias condiciones, la atomicidad de una acción, un presupuesto de consultas (`ContadorConsultas`) o la recomendación.
2. Ninguna prueba de `plataforma` o `piloto` cubre ese comportamiento: ni P1–P16, ni `test_consultas_dominio`, ni `test_piloto`.

El inventario agrupa por comportamiento, no por prueba. Por ejemplo: «presupuesto de consultas de `/actividades`: 12 pruebas en demo; propuesta: 1 prueba en plataforma». Como referencia, se espera **no más de unas 40 pruebas portadas** en total.

**Utilidades compartidas.** Las importaciones entre módulos de prueba (`from test_registro import`, `from test_instrumentos import`, `from test_consultas import`, `import test_plataforma`) se resuelven moviendo lo compartido a `tests/soporte/`. Ninguna prueba importa otro archivo `test_*.py`.

## 6. Estructura de pruebas del backend

### 6.1 Criterio de tipo

| Tipo | Regla verificable |
|---|---|
| `unit/` | No crea motor de base de datos, no usa `TestClient` ni `tmp_path` para bases. Se permiten objetos falsos y SQLite en memoria **solo** si la prueba no siembra un conjunto de datos. |
| `integration/` | Usa una base sembrada (`plataforma` o `piloto`), `TestClient`, migraciones o PostgreSQL. |

Si una prueba no encaja en ninguno de los dos, va en `integration/`.

### 6.2 Carpetas (copian la estructura de `app/` y `datos/`)

```text
tests/
├── conftest.py                 # solo autouse sin base: evaluador falso
├── soporte/                    # ayudas compartidas (pythonpath)
├── unit/
│   ├── arquitectura/           # §4.4: app sin archivos, dependencias entre capas
│   ├── configuracion/          # app/config.py
│   ├── instrumentos/           # app/services/instrumentos/calculo.py
│   ├── motor/                  # app/services/motor/* sin base
│   └── registro/               # app/services/registro/evaluacion.py, gemini.py, prompt.py
└── integration/
    ├── conftest.py             # fixtures con base (§7)
    ├── actividades/            # services/actividades.py, api/actividades.py, acciones.py
    ├── cuentas/                # services/cuentas.py
    ├── desarrollo/             # services/desarrollo.py (reinicio y clasificación de tablas)
    ├── fichas/                 # services/fichas.py
    ├── instrumentos/           # services/instrumentos/consultas.py, resultados.py; carreras.py
    ├── logros/                 # services/logros.py
    ├── motor/                  # services/motor/*, services/eventos.py
    ├── datos/                  # datos/cargar.py, plataforma.py, piloto.py, ocupaciones.py
    ├── migraciones/            # migrations/, test_migraciones, test_postgres
    ├── contrato/               # scripts/exportar_fixtures_front.py y fixtures por dominio
    └── escenarios/
        ├── plataforma/         # P1–P16
        └── piloto/
```

- Solo se crean las carpetas que tienen pruebas. Si un dominio no tiene ninguna (por ejemplo, `comunidad`, `diario` o `testimonios`), no se crea.
- Un archivo que mezcla tipos se divide. Los nombres de archivo describen lo que prueban (`test_evaluadores.py`, no `test_fase1.py`).
- Los nombres de archivo de prueba son **únicos en todo `tests/`**. Además, `pyproject.toml` usa `addopts = "--import-mode=importlib"` para que la ubicación no afecte las importaciones. `pythonpath = [".", "tests/soporte"]` se mantiene.

### 6.3 Tabla de impacto (va en `AGENTS.md`)

| Si cambias… | Corre primero |
|---|---|
| `app/services/<dominio>*`, `app/api/<dominio>.py`, `app/schemas/<dominio>.py` | `tests/unit/<dominio>` y `tests/integration/<dominio>` |
| `app/services/motor/*`, `app/services/eventos.py`, `app/services/comun.py` | `tests/unit/motor`, `tests/integration/motor`, `tests/integration/actividades` y `tests/integration/escenarios` |
| `app/models/*`, `migrations/*` | `tests/integration/migraciones` y `tests/integration/datos` |
| `datos/*` | `tests/integration/datos` y `tests/integration/escenarios` |
| `app/main.py`, `app/config.py`, `app/database.py`, `app/dependencies.py`, `app/exceptions.py`, `app/core/*` | `tests/unit` completo y `tests/integration/escenarios` |
| Una respuesta que consume el front | `tests/integration/contrato` + regenerar fixtures + `npm run test:servidor` en el front |
| Cierre de fase o de iteración | Suite completa: `uv run pytest -n auto -q` |

## 7. Aceleración del backend

1. **Base plantilla por conjunto.** En `tests/integration/conftest.py`, un fixture de sesión (`scope="session"`) crea una vez `plantilla-plataforma.db` y `plantilla-piloto.db` con `preparar_base(..., crear_tablas=True)` dentro de `tmp_path_factory`. Para cada prueba, los fixtures `aplicacion` (plataforma) y `aplicacion_piloto` **copian** el archivo de la plantilla a `tmp_path` y llaman a `crear_aplicacion(url)` sobre la copia. Cada prueba sigue teniendo su propia base.
   - Las pruebas que miden la carga en sí (`preparar_base`, `--vaciar`, fallos atómicos) **no** usan la plantilla.
   - Desaparecen `aplicacion_plataforma` y las redefiniciones de `aplicacion`, `cliente` y `sesion` en `soporte_plataforma.py`, porque `aplicacion` ya es `plataforma`.
2. **Ejecución en paralelo.** `uv add --dev pytest-xdist` (autorizado por esta spec). La suite completa se ejecuta con `uv run pytest -n auto -q`. La plantilla funciona por proceso, porque cada proceso de xdist tiene su propia sesión.
3. **Marca `postgres`.** `test_postgres.py` lleva `pytest.mark.postgres`, registrada en `pyproject.toml`. Se sigue omitiendo sin `TEST_POSTGRES_URL`.
4. Después de P5, ninguna prueba debe superar 1 s de *setup*. Las que lo superen se listan en `docs/decisiones.md` con el motivo.

## 8. Estructura de pruebas del front

### 8.1 Carpetas

```text
tests/
├── local/                        # modo VITE_DATOS=local, sin servidor
│   ├── actividades/              # mission-logic, mission-store, contenidos,
│   │                             # student-reflection-pilot, student-progress-challenges
│   ├── aventura/                 # adventure-rendering, adventure-state
│   ├── casos/                    # forest-fire-case
│   ├── perfil/                   # student-profile
│   └── portales/                 # counselor-portal, parent-missions, staff-palette
├── servidor/                     # modo api, con los fixtures del backend
│   ├── actividades/              # servidor-flujo, -cierre, -secciones, -servicios, -adaptadores, -local
│   ├── mapa/                     # servidor-mapa
│   ├── instrumentos/             # servidor-mara, -resultado, -resultados, -descripciones
│   ├── logros/                   # servidor-logros, -avisos
│   └── perfil/                   # servidor-perfil
├── despliegue/                   # deployment-assets
├── fixtures/servidor/            # no se mueve: lo escribe el script del backend
└── soporte/                      # no se mueve
```

La asignación de cada archivo es la propuesta inicial. Si el contenido de un archivo indica otro destino, se ajusta y se anota.

### 8.2 Reglas

- Los archivos conservan su nombre y su contenido. Solo cambian las rutas relativas a `soporte/` (`./soporte/...` → `../../soporte/...`).
- Las rutas `tests/fixtures/servidor/...` y `src/...` ya son relativas a la raíz del repo, así que no cambian.
- `package.json`:

  ```json
  "test": "node --test \"tests/**/*.test.mjs\"",
  "test:local": "node --test \"tests/local/**/*.test.mjs\"",
  "test:servidor": "node --test \"tests/servidor/**/*.test.mjs\"",
  "test:despliegue": "node --test \"tests/despliegue/**/*.test.mjs\""
  ```

  Para una sola carpeta: `node --test "tests/servidor/instrumentos/**/*.test.mjs"`. Las comillas son obligatorias para que el glob lo expanda Node (Node 22) y no la terminal; así funciona igual en PowerShell.
- Si `scripts/verificar-estructura.mjs` controla `tests/`, se actualiza para aceptar esta estructura.
- Las 14 fallas previas de `adventure-rendering` **no se corrigen en esta spec**. Si en P0 también fallan en tu máquina, quedan anotadas como previas. Si pasan, se anota que la falla depende del entorno.

### 8.3 Tabla de impacto del front (va en su `AGENTS.md`)

| Si cambias… | Corre primero |
|---|---|
| `src/features/servidor/`, `src/store/servidor/`, `src/lib/servidor/`, `src/services/api/`, `src/types/servidor.ts` | `npm run test:servidor` |
| `src/features/<área>/`, `src/lib/activities/`, `src/data/activities/` | la carpeta de `tests/local/` y de `tests/servidor/` de esa área |
| Fixtures regenerados desde el backend | `npm run test:servidor` |
| Cierre de fase o de iteración | `npm run build`, `npm run lint`, `npm test`, `npm run check:estructura` |

## 9. Política de ejecución (los dos `AGENTS.md`)

Reemplaza «Corre `uv run pytest -q` antes de dar por terminada cualquier fase» y su equivalente del front por:

| Momento | Qué se corre |
|---|---|
| Durante el desarrollo, tras cada cambio | Solo las carpetas de la tabla de impacto. |
| Al terminar una fase de una spec | Las carpetas de impacto de **todo** lo que tocó la fase, más `escenarios` (back) o `servidor` (front). Se informa qué carpetas se corrieron. |
| Al cerrar una iteración o antes de integrar una rama | Suite completa de los dos repos: `uv run pytest -n auto -q`; `npm test`, `build`, `lint` y `check:estructura`. |

Si la sección «Reglas compartidas» de los `AGENTS.md` cambia, debe quedar idéntica en los dos repos.

## 10. Fases

| Fase | Repo | Contenido | Para terminar |
|---|---|---|---|
| P0 | ambos | Línea base: `uv sync`; `uv run pytest -q --durations=25`; `uv run pytest --collect-only -q`; `npm ci`; `npm test`. Anota conteos, tiempos y fallas en `ov_backend/docs/decisiones.md`, sección «Pruebas y retiro de demo». | Línea base anotada. |
| P1 | back | **Solo lectura.** Inventario de §5: por archivo, cuántas pruebas A/B/C; para C, los comportamientos agrupados y cuáles se proponen portar (con criterio y destino); utilidades compartidas que pasan a `soporte/`. Va en `docs/inventario-retiro-demo.md`. | **Detente y espera aprobación** del inventario. |
| P2 | ambos | Retiro (§4) y ajuste de pruebas (§5) según el inventario aprobado. Front: §4.3. | `uv run pytest -q` en verde; `npm test` igual que en P0 (salvo la aserción de §4.3); `grep -rn "/demo" app src` vacío; nuevo conteo anotado. |
| P3 | back | Mover las pruebas a la estructura de §6, dividir archivos mixtos, renombrar y configurar `importlib`. **Sin cambiar ninguna aserción.** | `--collect-only` da **exactamente** el conteo de P2; suite en verde. |
| P4 | back | Aceleración (§7): plantilla, xdist, marca `postgres`. | Mismo conteo; `uv run pytest -n auto -q` en verde; tiempos antes y después anotados. |
| P5 | front | Mover las pruebas (§8) y actualizar los scripts. | `npm test` descubre las mismas 463 pruebas con el mismo resultado de P2; `build`, `lint` y `check:estructura` en verde. |
| P6 | ambos | Documentación: `AGENTS.md` de los dos repos (estructura de `tests/`, tablas de impacto, §9, quitar `demo` de «Datos» y de las fuentes de verdad), README de los dos, `.env.example` y `docs/decisiones.md`. En `docs/spec-demo-*.md` se agrega al inicio una nota: «Los datos y escenarios de esta spec se retiraron; sus reglas de comportamiento siguen vigentes». | Informe final: conteos y tiempos de P0 frente a P4, pruebas eliminadas, portadas y adaptadas, y comandos por carpeta. |

## 11. Adaptaciones autorizadas

Anótalas en `ov_backend/docs/decisiones.md`, bajo «Pruebas y retiro de demo».

1. Eliminar pruebas de categoría C no aprobadas para portar, y las pruebas de páginas HTML, `/demo/*`, `guardar-posicion` y `evaluar_gemini`.
2. Cambiar el fixture de las pruebas de categoría B sin cambiar sus aserciones.
3. Quitar `'demo'` de las parametrizaciones por conjunto.
4. Cambiar la ruta del reinicio en `servidor-servicios.test.mjs` y en las pruebas del reinicio del backend.
5. Ajustar listas exactas de rutas expuestas que incluyan `/demo`.
6. Mover utilidades compartidas a `tests/soporte/` y actualizar las importaciones.

Cualquier otra prueba que falle se arregla en la implementación. Si no se puede, detente y pregunta.
