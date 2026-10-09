# Demo del motor de desbloqueos

## Integración con ov_frontend · iteración 1

La [especificación vigente](docs/iteraciones/spec-iteracion-1.md) define los datos `plataforma` y el contrato con el frontend. Para una base nueva, preparar y arrancar desde este repo, en PowerShell:

```powershell
uv sync
$env:EVALUADOR="falso"
uv run alembic upgrade head
uv run python -m datos.cargar plataforma
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

La preparación de la base y la estructura actuales se definen en
[la especificación del refactor](docs/spec-refactor-estructura.md).

En ov_frontend, configurar `.env.local` con `VITE_DATOS=api` y `VITE_API_URL=/api`, y ejecutar `npm run dev`. Su proxy de desarrollo quita `/api` y llama a 8000. Usar `est-ana` o `est-luis`; son cuentas de prueba. El backend decide estados, respuestas, resultado, fichas, insignias y nivel; el frontend conserva contenido narrativo y borradores locales. La aplicación usa la base indicada por `DATABASE_URL`; cada conjunto se carga explícitamente. Después de prepararla, basta con volver a arrancar Uvicorn. No versiones `.env` ni `*.db`.

**Cierre F6 · 2026-10-07:** avisos, pasaporte, nivel y requisitos completos. HU-073 y HU-074 corregidas y revalidadas; las catorce HU del recorrido F7 pasan en el alcance comprobado. Backend: 1006 pruebas pasan, dos advertencias previas, con evaluador falso. Frontend: build/lint pasan; 340 de 356 pruebas pasan, con solo las 16 fallas previas. Ver [decisiones F6](docs/iteraciones/decisiones-iteracion-1.md#f6) y el informe `ov_frontend/docs/student-experience/informe-f7.md`. La aprobación formal de la iteración corresponde al usuario.

El resto de este README documenta la demo y las ampliaciones anteriores, con sus cifras históricas de validación.

Backend en FastAPI para demostrar cómo las acciones de una plataforma de
orientación vocacional desbloquean actividades, contenido, insignias y niveles.
Cada acción confirma su estado y sus eventos, evalúa reglas y devuelve los nuevos
desbloqueos con su explicación en una transacción. El envío de registro primero
lee su contexto y libera la conexión para evaluar, antes de confirmar los cambios.

**Registro v2 tiene implementadas las fases 1–8.** El esquema actual contiene
44 tablas de aplicación y la tabla de revisión de Alembic; incluye
la evaluación, las acciones/consultas de conversaciones y su
finalización, con hasta dos seguimientos y respaldo por longitud solo después
de un fallo. Rehacer conserva conversaciones y auditoría; los seguimientos
enviados permiten obtener LOG-PENSADOR mediante la regla existente.
Los presupuestos SQL se mantienen al añadir 100 reglas reflexivas y 500 eventos.
El adaptador y el script de los 16 casos, incluidos seguimientos, están comprobados
con clientes simulados. La ejecución real autorizada está en
[el reporte Gemini](docs/evaluacion_gemini.md): 17 llamadas, 12 salidas válidas y
5 respaldos. La aceptación semántica es parcial: los casos 7 y 11 marcaron C1
además de C2, y el seguimiento de 15 no se evaluó por fallo del inicial.
La interfaz muestra conversaciones con hasta dos seguimientos, borradores y
edición de respuestas finales. El esquema se prepara con Alembic antes del
arranque; conservar las bases anteriores como respaldo y usar una base nueva
para la revisión inicial. Las diferencias están en
[Registro v2](docs/decisiones.md#registro-v2).

Validación de cierre de fase 8 v2: **947 tests pasando, 2 avisos de deprecación** con
`uv run pytest -q`, SQLite temporal y sin llamadas reales a Gemini.
La comprobación de navegador completa 257 peticiones de interfaz sin errores
JavaScript, en escritorio y móvil. `uv lock --check` pasa. La ejecución real
se realiza por separado y su revisión registra la aceptación semántica parcial.

La fuente de verdad es la [especificación](docs/spec-demo-motor-desbloqueos.md).
Las seis fases de implementación y la página opcional `/demo` están completas.
Puedes usar el tablero visual o Swagger para probar el mismo motor.

La ampliación de [instrumentos](docs/spec-demo-instrumentos.md) tiene terminadas
las fases 1–6: modelos, escalas, ítems, aplicaciones, bloque LAB, catálogo O*NET,
cálculos, acciones de respuesta y finalización, consultas y reinicio individual.
La interfaz `/demo/instrumentos` permite probar los cuatro instrumentos.
LAB está disponible para estudiantes
desde el inicio y no modifica la ruta original de desbloqueos.

La [especificación de registro](docs/spec-demo-registro-gemini.md) vigente es v2.
El historial de v1 permanece en [Decisiones](docs/decisiones.md#registro) y
[Validación](docs/validacion.md#registro-fase-8-cierre-consolidado); sus campos,
ampliación única y script de 14 casos fueron reemplazados. Las instrucciones
de esta página describen las conversaciones v2 y su script de 16 casos.

## Instalación y ejecución

Requisitos: `uv` y Python 3.14, como fijan `.python-version` y `pyproject.toml`.
Las dependencias se gestionan con `uv.lock`. Desde la raíz del repositorio,
preparar una base nueva y cargar los datos de integración:

```powershell
uv sync
$env:EVALUADOR = 'falso'
uv run alembic upgrade head
uv run python -m datos.cargar plataforma
uv run uvicorn app.main:app --reload
```

La preparación se ejecuta una vez. En los siguientes arranques basta con
`uv run uvicorn app.main:app --reload`; conserva el estado guardado.
Abrir [Swagger UI](http://127.0.0.1:8000/docs) o
[OpenAPI](http://127.0.0.1:8000/openapi.json). `Ctrl+C` detiene el servidor.

La aplicación abre una base previamente preparada. Si falta alguna tabla,
falla con el mensaje que pide ejecutar Alembic y cargar datos. Un esquema
completo con catálogo vacío permite arrancar y responde listas vacías.
Las migraciones crean 44 tablas de aplicación y `alembic_version`.
La revisión inicial prepara bases nuevas; conservar las bases anteriores
como respaldo y elegir otra URL para este esquema.

Con `ENTORNO=desarrollo`, también están disponibles
[el tablero](http://127.0.0.1:8000/demo),
[los instrumentos](http://127.0.0.1:8000/demo/instrumentos) y
[el registro](http://127.0.0.1:8000/demo/registro).
Los recorridos de laboratorio y registro de este README requieren el conjunto
`demo`, cuya preparación se muestra abajo. Con `ENTORNO=produccion` no se
incluye ningún endpoint `/demo/*`, su auditoría de registro ni sus estáticos.

`uv.toml` configura la caché local `.uv-cache`. La caché, `.venv`, `.env` y
las bases SQLite están ignoradas por Git. El evaluador predeterminado es
`falso`; las comprobaciones automáticas no llaman a Gemini.

## Base de datos y datos de prueba

`cargar_configuracion()` lee el proceso, después `.env` en la raíz y finalmente
los valores predeterminados, sin interpolar ni modificar el entorno.

| Variable | Valores | Por defecto |
|---|---|---|
| `DATABASE_URL` | URL SQLAlchemy; las rutas relativas SQLite se resuelven desde la raíz del repo | `sqlite:///ov.db` |
| `ENTORNO` | `desarrollo`, `produccion` | `desarrollo` |
| `EVALUADOR` | `falso`, `gemini` | `falso` |

`crear_aplicacion(url_bd=None)` admite una URL explícita que prevalece sobre
la configuración. La aplicación desconoce el conjunto cargado.

| Conjunto | Contenido |
|---|---|
| `plataforma` | Integración con el front: 3 cuentas, 2 bloques, 24 actividades, 4 fichas, 10 insignias, 5 niveles, 44 reglas y 53 condiciones. RIASEC con 60 ítems en 14 encuentros de Mara, 36 ocupaciones con códigos del front y 6 carreras. |
| `piloto` | Variante de prueba de plataforma: 5 actividades en el Camino y 16 en la Ciudad. La Ciudad se abre tras `enc-mitos`; Elena usa `AL_DESBLOQUEAR` y `cdd-sin-contenido` prueba una clave ausente del front. Se carga con `uv run python -m datos.cargar piloto` (con `--vaciar` solo para reemplazar los datos existentes). |
| `demo` | Escenarios originales: 3 cuentas, 11 bloques, 30 actividades, 8 carreras, 47 reglas y 58 condiciones; los cuatro instrumentos, registro con Lumi y catálogo O*NET. |

Los datos de prueba están marcados en los cargadores. La carga de `demo`
necesita `datos/archivos/Career_Interest_RIASEC_Clean.xlsx`; si falta o es
inválido, falla explícitamente y revierte la carga. `openpyxl` se instala con
`uv sync`. El arranque y el reinicio no vuelven a leer el Excel.

Para preparar la demo original en otra base, desde PowerShell:

```powershell
$env:DATABASE_URL = 'sqlite:///demo_pruebas.db'
$env:EVALUADOR = 'falso'
uv run alembic upgrade head
uv run python -m datos.cargar demo
uv run uvicorn app.main:app --reload
```

Para cambiar de base, definir `DATABASE_URL` antes de migrar, cargar o arrancar.
La CLI rechaza cargar sobre una base poblada. Para reemplazar todo su contenido,
detener el servidor, ejecutar `uv run python -m datos.cargar plataforma --vaciar`
(o `demo --vaciar`) y volver a iniciarlo. El vaciado y la carga forman una
transacción: un fallo conserva las filas anteriores. La CLI no crea tablas;
siempre se preparan con Alembic.

`POST /demo/reiniciar` borra únicamente las 16 tablas de estado de las cuentas.
Conserva catálogo, cuentas, vínculos y sus cartas, la revisión de Alembic,
la caché y las posiciones de registro. Funciona con ambos conjuntos y no
recarga archivos. El JSON `app/static/contenido/REG-ACT08.json` se valida al
arrancar cuando existe su actividad en la base; si no existe, las posiciones
quedan vacías. El reinicio conserva las posiciones ya cargadas.

Para PostgreSQL, instalar el extra y configurar la URL antes de usar los
mismos comandos de migración, carga y arranque:

```powershell
uv sync --extra postgres
$env:DATABASE_URL = 'postgresql+psycopg://ov:ov@localhost:5432/ov'
uv run alembic upgrade head
uv run python -m datos.cargar plataforma
uv run uvicorn app.main:app --reload
```

El servidor PostgreSQL y la base indicada deben estar disponibles.
`tests/test_postgres.py` usa `TEST_POSTGRES_URL` y se omite si no está definida.
Los cambios de modelos incluyen una migración en el mismo commit:

```powershell
uv run alembic revision --autogenerate -m 'descripción del cambio'
```

Revisar a mano la revisión generada, incluidos CHECK, predeterminados e índices.

### Fixtures del frontend

Desde la raíz del backend, indicar explícitamente la carpeta del otro repo:

```powershell
uv run python scripts/exportar_fixtures_front.py --destino 'C:/ruta/a/ov_frontend/tests/fixtures/servidor'
```

`--destino` es obligatorio y la carpeta se crea si falta. El script prepara
bases temporales separadas para `plataforma` y `piloto`, fuerza el evaluador
falso y usa fechas y respuestas fijas. Guarda 16 respuestas JSON reproducibles:
seis respuestas de acciones/instrumentos, siete consultas por dominio de plataforma y tres
momentos del piloto (inicio, Ciudad abierta y Mara completa). Los avisos no
vistos corresponden al cierre del Camino de plataforma, antes de Mara.
No modifica bases existentes ni llama a Gemini. Si cambia el contrato,
regenerar los fixtures en la misma tarea. El uso programático existente
`exportar_fixtures(destino)` exporta los trece archivos de plataforma;
`por_dominio=True` añade los tres de piloto, como hace siempre el comando.

### Historial de validación de la iteración 1

Las cifras F1–F6 conservan sus resultados históricos en
[las decisiones de la iteración](docs/iteraciones/decisiones-iteracion-1.md).
El cierre de R4 tiene **1023 pruebas aprobadas, 4 omitidas y 2 avisos**;
las omisiones corresponden a PostgreSQL sin configurar. Los detalles del
refactor están en [Decisiones](docs/decisiones.md#refactor-de-estructura).

## Estructura del proyecto

```text
ov_backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── exceptions.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── cuentas.py
│   │   ├── acciones.py
│   │   ├── instrumentos.py
│   │   ├── registro.py
│   │   └── demo.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── enums.py
│   │   ├── cuentas.py
│   │   ├── contenido.py
│   │   ├── motor.py
│   │   ├── progreso.py
│   │   ├── instrumentos.py
│   │   └── registro.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── motor.py
│   │   ├── cuentas.py
│   │   ├── acciones.py
│   │   ├── instrumentos.py
│   │   ├── registro.py
│   │   └── demo.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── comun.py
│   │   ├── motor/
│   │   │   ├── __init__.py
│   │   │   ├── reglas.py
│   │   │   ├── evaluadores.py
│   │   │   └── referencias.py
│   │   ├── cuentas.py
│   │   ├── eventos.py
│   │   ├── actividades.py
│   │   ├── diario.py
│   │   ├── carreras.py
│   │   ├── comunidad.py
│   │   ├── instrumentos/
│   │   │   ├── __init__.py
│   │   │   ├── calculo.py
│   │   │   ├── consultas.py
│   │   │   └── resultados.py
│   │   ├── registro/
│   │   │   ├── __init__.py
│   │   │   ├── acciones.py
│   │   │   ├── consultas.py
│   │   │   ├── contenido.py
│   │   │   ├── evaluacion.py
│   │   │   ├── gemini.py
│   │   │   └── prompt.py
│   │   └── demo.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── parametros.py
│   │   ├── definiciones.py
│   │   └── contexto.py
│   └── static/
├── datos/
│   ├── __init__.py
│   ├── cargar.py
│   ├── plataforma.py
│   ├── piloto.py
│   ├── ocupaciones.py
│   ├── demo/
│   │   ├── __init__.py
│   │   ├── motor.py
│   │   ├── instrumentos.py
│   │   └── registro.py
│   └── archivos/
│       └── Career_Interest_RIASEC_Clean.xlsx
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_esquema_inicial.py
├── scripts/
│   ├── evaluar_gemini.py
│   └── exportar_fixtures_front.py
├── tests/
│   ├── conftest.py
│   ├── soporte/
│   └── test_*.py
├── docs/
├── alembic.ini
├── pyproject.toml
├── .env.example
├── AGENTS.md
└── README.md
```

`api/` valida y delega en servicios; `core/` reúne parámetros y lecturas
compartidas; `models/` define tablas y `schemas/` los contratos HTTP.
`app/` no importa cargadores. `datos/` contiene catálogos y conjuntos;
Alembic administra el esquema. Los estáticos de demo se sirven solo en desarrollo.

## Configuración del registro y prueba Gemini

`uv sync` instala también `google-genai` y `python-dotenv`. La configuración se
lee al arrancar desde `.env` en la raíz; las variables del proceso tienen
prioridad. [.env.example](.env.example) contiene los valores predeterminados:
`EVALUADOR=falso`, `GEMINI_MODELO=gemini-3.1-flash-lite` y
`GEMINI_TIMEOUT_SEGUNDOS=8`, con la clave vacía. `.env` permanece ignorado.

Para usar Gemini, preparar localmente `.env` con `EVALUADOR=gemini` y una clave
en `GEMINI_API_KEY`. La aplicación rechaza el arranque si falta esa clave.
Seleccionar `gemini` hará que cada envío inicial válido llame primero al servicio,
incluso si es corto. La longitud solo decide el respaldo después de un fallo o
timeout. Los seguimientos del LLM evalúan la conversación completa; responder
una pregunta genérica y editar FINAL no llaman al proveedor. Las pruebas usan el
falso o clientes simulados, sin llamadas reales. Cada llamada usa prompt v2,
salida JSON validada, temperatura 0.2 y un solo intento. La evaluación ocurre
después de cerrar la primera transacción, sin conexión tomada.

Para preparar un servidor con Gemini, configurar `.env` con `EVALUADOR=gemini`
y la clave local, y preparar una base independiente. Este arranque se reserva
a una petición explícita de uso de Gemini:

```powershell
$env:DATABASE_URL = 'sqlite:///demo_registro_gemini.db'
uv run alembic upgrade head
uv run python -m datos.cargar demo
uv run uvicorn app.main:app --host 127.0.0.1 --port 8788
```

La base `demo_registro_gemini.db` conserva respuestas entre arranques y está
ignorada por Git. Su esquema procede de Alembic y sus datos del conjunto `demo`.
El servidor de comprobación del puerto 8787 siempre fuerza el falso, aunque
se cambie `.env`; para Gemini usar este arranque. Las variables del proceso
siguen teniendo prioridad sobre `.env`. El arranque no evalúa respuestas.
La página `/demo/registro` usa las conversaciones v2. Sus comprobaciones visuales
se realizaron con el evaluador falso. La evaluación semántica real del script
se ejecutó por petición explícita y sus resultados están en
[el reporte revisado](docs/evaluacion_gemini.md#revisión-de-esta-ejecución-real).

El siguiente comando queda reservado para una petición explícita de evaluación
real. Se ejecutó una vez para el cierre v2; las futuras ejecuciones requieren
otra petición y reemplazan la tabla del reporte, que debe revisarse de nuevo:

```powershell
uv run python -m scripts.evaluar_gemini --pausa 5
```

El script requiere la clave y siempre usa Gemini, independientemente del proveedor
seleccionado para la aplicación. Envía los 16 casos de §10, incluidos el caso 12
corregido y el texto inicial corregido del caso 16, con contexto adecuado de los
casos 2 y 6. En los casos 15 y 16 responde el turno 1 a la pregunta recibida y
evalúa la conversación completa, siempre que el inicial haya generado seguimiento
del LLM. Puede realizar hasta 18 llamadas. El caso 16 termina al observar la
segunda pregunta; la especificación no proporciona una respuesta para ese turno.
Si el inicial finaliza no se inventa un seguimiento; si falla y genera una pregunta
genérica, su respuesta se acepta sin otra llamada. Se usan el mínimo y la pregunta
genérica oficiales para aplicar el mismo respaldo que en la aplicación.

Usa una base en memoria con las definiciones oficiales; no abre las bases
persistentes ni guarda respuestas o eventos. Genera `docs/evaluacion_gemini.md`
con una fila por inicial/turno 1, preguntas recibidas y generadas, resultados,
atención, latencia, origen y errores saneados. Las filas sin nueva evaluación
explican por qué no se llamó al LLM. La revisión semántica de los criterios y
preguntas figura en el reporte real revisado; los clientes simulados comprueban
el contrato y el recorrido. La pausa se aplica entre todas las llamadas, incluidos
los seguimientos, y es configurable según la cuota; los fallos no se reintentan.
`uv run python -m scripts.evaluar_gemini --help` solo muestra la ayuda.

## Probar el plan con Lumi

Con el servidor iniciado y `EVALUADOR=falso`, abrir
[la actividad de registro](http://127.0.0.1:8000/demo/registro), también enlazada
desde `/demo`.

Para visualizarla desde cero sin modificar la base habitual, se puede
iniciar una sesión independiente desde la raíz del proyecto:

```powershell
uv run python tests/soporte/servidor_registro_ui.py
```

Si el puerto está ocupado, elegir otro con `--puerto 8790` y abrir la misma ruta
en ese puerto.

Abrir [la demo independiente](http://127.0.0.1:8787/demo/registro). Este servidor
fuerza el evaluador falso y prepara una SQLite temporal con el conjunto `demo`
mediante los auxiliares de `datos.cargar`. Conserva los cambios mientras permanece activo; al detenerlo con
`Ctrl+C` se elimina esa base temporal. No modifica la base habitual ni `.env`. Para
conservar respuestas entre arranques, usar el servidor habitual con una base
compatible; respaldar primero cualquier base anterior antes de recrearla.

1. Elegir Ana o Luis y una fecha simulada opcional. Rosa ve que la actividad
   corresponde a estudiantes.
2. Leer la explicación de Lumi y pulsar **Continuar**. Se guarda la posición
   `plan`; **Volver a escuchar a Lumi** permite recuperar también la explicación.
3. Elegir uno de los tres íconos. **Guardar borrador** conserva el texto sin
   enviarlo; **Enviar** puede dejar una pregunta de Lumi. La respuesta inicial
   sigue visible en el hilo y aparece un campo nuevo. **Responder** envía ese
   turno; puede haber hasta dos preguntas por ítem. Se pueden guardar borradores
   de ambos turnos y recuperarlos al recargar. **Prefiero seguir** finaliza sin
   responder la pregunta pendiente; el hilo conserva esa pregunta.
4. Con las tres respuestas listas, **Completar actividad** registra los eventos
   del motor. En cada ítem FINAL, **Editar respuesta inicial** o **Editar respuesta
   1/2** elige el mensaje; **Guardar cambios** lo modifica sin una nueva evaluación.
   Las preguntas omitidas no se pueden editar. **Volver a completar** reutiliza
   la finalización existente.
5. Abrir **Detalle técnico** para ver las evaluaciones, sus criterios, latencia,
   modelo, versión del prompt, preguntas y conversación evaluada. Permanece
   plegado y no se consulta hasta abrirlo.
   Las novedades de desbloqueos se pueden marcar como vistas con su propio botón.

Al recargar se recuperan posición, conversaciones y borradores desde el servidor.
La URL conserva la cuenta, el ítem elegido y la fecha, sin incluir textos. Los
cambios aún sin guardar se conservan al cambiar de ítem o actualizar la vista,
pero se descartan al recargar o cambiar de cuenta. No se guardan respuestas en
`localStorage` ni se realizan guardados automáticos.

Para probar desde cero, pulsar **Reiniciar demo**, junto a **Actualizar**, y
confirmar **Sí, reiniciar demo**. Borra las respuestas, borradores, seguimientos
y evaluaciones de **todas las cuentas**, además del progreso del motor y los
instrumentos, y devuelve a la explicación de Lumi. También descarta el texto
sin guardar de esta vista. Conserva la cuenta, fecha simulada y configuración
de Gemini. **Conservar progreso** o Escape cancelan sin borrar. El reinicio no
evalúa textos; el siguiente envío comienza como evaluación 1.

Las [comprobaciones visuales v2](docs/validacion.md#registro-v2-fase-7) incluyen
escritorio y tamaños móviles de 390 y 360 px con el falso, errores de conexión
simulados, aislamiento y recuperación. No se llama a Gemini en esta validación.

Para ver una pregunta de seguimiento, enviar **Asertividad [vaga]** en el primer
ítem. **Asertividad [falla]** permite probar la pregunta genérica de respaldo.
El falso clasifica ADECUADA por defecto, incluso con textos cortos; sus marcadores
para simular otras respuestas se explican en
[el recorrido desde Swagger](#probar-los-registros-desde-docs).

## Probar con el tablero visual

En [la página `/demo`](http://127.0.0.1:8000/demo):

1. Seleccionar Ana, Luis o Rosa para ver su propio recorrido y progreso.
2. Pulsar **Completar** en Bienvenida, o en la sugerencia **Tu siguiente paso**.
   ACT-02 se abrirá y la columna **Qué cambió** mostrará el evento y la regla.
3. Seguir completando actividades. En **Ver requisitos** se ve el avance de
   cada condición; las actividades bloqueadas también permiten probar el rechazo 409.
4. Abrir **La ciudad**, **Contenido y diario**, **Insignias** o **Historial de
   eventos** para revisar los cambios. Los nuevos objetivos se resaltan.
5. Usar **Simular una acción** para casos, check-in, diario, carreras,
   entrevistas con coautores, cartas y conversaciones. Para los casos, elegir
   el puntaje; para los check-in de E6, usar **+ Un día** entre envíos.
6. Cambiar de cuenta para comprobar la coautoría o el avance familiar.
   **Novedades** permite marcar leídos los desbloqueos de la cuenta seleccionada.

La fecha simulada empieza el 1 de octubre de 2026 a las 10:00. Puede editarse
o vaciarse con **Usar hora actual**. **Reiniciar demo** pide confirmar el borrado
del progreso de las tres cuentas. **Actualizar** vuelve a consultar los datos,
por ejemplo después de actuar desde otra pestaña o Swagger.

El tablero usa los endpoints reales de acciones y consultas. Su catálogo
auxiliar de opciones públicas es `GET /demo/catalogo`; no hay lógica de
desbloqueo alternativa en el navegador. Abrir la página no registra eventos.

## Probar los instrumentos

Abrir [el laboratorio](http://127.0.0.1:8000/demo/instrumentos), también enlazado
como **Probar instrumentos** desde `/demo`:

1. Elegir Ana o Luis, la fecha simulada y un instrumento. El avance muestra
   actividades completadas, respuestas guardadas y resultado vigente por aplicación.
2. Elegir una actividad disponible y marcar sus opciones. **Guardar respuestas**
   permite envíos parciales; **Completar actividad** exige todas las respuestas
   guardadas. Los requisitos de las actividades bloqueadas se consultan aparte.
3. Para probar RIASEC, abrir **Relleno rápido de prueba** y elegir **Cadena A**,
   **Cadena B** o **Perfil plano**. También puede pegarse una cadena propia.
   Esto rellena el formulario sin escribir en el servidor. **Guardar disponibles**
   guarda la cadena únicamente en actividades abiertas. Después de completar una,
   se selecciona la siguiente disponible y se conserva la cadena para rellenarla.
   Guardar sus respuestas y completarla; repetir hasta terminar la aplicación.
4. Revisar dimensiones, porcentajes, código de interés, coincidencias y carreras.
   Inteligencias y habilidades destacan la mayor proporción de puntaje sobre
   máximo; si hay empate muestran todas las dimensiones empatadas en su orden.
   Autopercepción requiere
   elegir y completar **Entrada** y **Salida**, y muestra la comparación por ítem.
   Cada instrumento tiene ejemplos de relleno con las opciones de su escala.
5. **Ver historial** permite desplegar resultados vigentes y anulados.
   **Reiniciar instrumento** pide confirmar la aplicación seleccionada: borra
   sus respuestas, anula su resultado vigente y conserva historial y desbloqueos.
   En autopercepción, reiniciar salida conserva entrada. Un reinicio vacío devuelve 409.
6. Abrir las entradas del **Registro de la API** para inspeccionar respuestas,
   eventos, desbloqueos, resultados generados y errores reales. Los controles se
   bloquean mientras se procesa una operación. **Actualizar** consulta de nuevo
   el servidor; Rosa recibe 404 porque los instrumentos son para estudiantes.

Las respuestas quedan fijas después de obtener un resultado vigente; en
autopercepción, después de completar la actividad. **Completar actividad** sigue
permitiendo rehacerla sin recalcular. En pantallas pequeñas, los enlaces a
preguntas, resultado e historial facilitan la navegación; las tablas anchas
se desplazan horizontalmente dentro de su panel.

## Probar los registros desde `/docs`

Los ocho endpoints del grupo **Registro** funcionan con el evaluador falso.
Usar `cuenta = est-ana`, `actividad = REG-ACT08` e `item = REG-HAB-1`:

1. Consultar `GET /actividades/REG-ACT08/items-registro` para ver las consignas.
2. Guardar `posicion = plan` en `POST /acciones/guardar-posicion`.
3. Guardar un texto con `POST /acciones/registro/guardar-borrador`. Puede estar vacío.
4. Enviar `texto = Asertividad [vaga]` con `POST /acciones/registro/enviar` para
   recibir una pregunta. Responderla con `POST /acciones/registro/responder-seguimiento`
   (sin `orden`), o usar `POST /acciones/registro/continuar-sin-responder`.
   Si el turno sigue VAGO, puede haber una segunda pregunta; al responderla se
   finaliza aunque siga VAGA. El texto inicial no se reemplaza.
5. Consultar `GET /cuentas/est-ana/actividades/REG-ACT08/registro` para recuperar
   posición y conversaciones, incluidos los borradores del turno pendiente.
   En FINAL, **enviar** edita el inicial; **responder-seguimiento** con `orden = 1`
   o `2` edita un turno ya respondido. No se producen evaluaciones ni eventos nuevos.
6. Revisar `GET /demo/registro/est-ana/REG-ACT08/evaluaciones` para el análisis
   técnico. La clasificación y la marca de atención solo aparecen en esta consulta.
7. Cuando los tres ítems estén FINAL, usar `POST /acciones/completar-actividad`.
   Antes devuelve 409 con `items_faltantes` en orden, sin escribir ni registrar
   eventos. Completar guarda COMPLETA_ACTIVIDAD y, la primera vez, COMPLETA_BLOQUE(REG).
   Rehacer conserva posición, respuestas y evaluaciones y registra otra finalización
   de actividad. Las respuestas FINAL se pueden editar después.

El falso usa `[vaga]` para preguntar por los criterios restantes, `[falta:C2]`
para preguntar solo por C2, `[atencion]` para finalizar con marca técnica y `[falla]`
para simular un error sin bloquear. Sin marcadores clasifica ADECUADA, sea cual
sea la longitud. Solo ante fallo se usa el mínimo (40 caracteres; 30 para REG-HAB-3):
un inicial corto genera una pregunta genérica cuya respuesta se acepta sin otra
evaluación; uno suficiente finaliza NO_EVALUADA. Todos los POST
aceptan `fecha_hora` opcional. Un cambio concurrente de la respuesta devuelve 409
y descarta la evaluación del envío que perdió el conflicto.

La condición para completar es el estado FINAL, también si se continuó sin responder
o falló el evaluador. Las pruebas cuentan ambas transacciones del envío juntas:
posición ≤4 consultas, borrador ≤6, envío y responder seguimiento ≤12 cada uno,
continuar ≤8, ítems ≤1, estado ≤4 y completar ≤15. Las mediciones y el crecimiento
se detallan en [validación v2](docs/validacion.md#registro-v2-fase-5).
La página `/demo/registro` permite realizar este mismo recorrido visualmente.

## Preparar una demostración en `/docs`

1. Abrir el grupo **Demo**, desplegar `POST /demo/reiniciar`, pulsar
   **Try it out** y **Execute**. No requiere cuerpo. Devuelve
   `{"mensaje":"Demo reiniciada"}`.
2. En **Consultas**, ejecutar `GET /cuentas` y `GET /reglas` para revisar
   las cuentas y las reglas con códigos públicos.
3. Ejecutar las consultas por dominio (`resumen`, `actividades`, `fichas`,
   `logros`, `testimonios`, `diario/preguntas` y `conversaciones`) con `cuenta = est-ana`.
4. En **Acciones**, desplegar el POST elegido, pulsar **Try it out**, reemplazar
   el cuerpo por uno de los ejemplos de abajo y pulsar **Execute**.
5. Leer `eventos_registrados` y `nuevos_desbloqueos`, y volver a ejecutar la
   consulta del dominio o progreso para observar el cambio.

El reinicio **borra el estado de las cuentas**, incluidos eventos, progresos,
entradas, respuestas y desbloqueos. Conserva catálogo, cuentas, vínculos y cartas. Ejecutarlo entre escenarios y sin
otras peticiones en curso. Reiniciar el servidor conserva los datos.

| Cuenta | Rol | Vínculo |
|---|---|---|
| `est-ana` | ESTUDIANTE | `VIN-ANA`, con Rosa |
| `est-luis` | ESTUDIANTE | Sin vínculo; permite demostrar coautoría |
| `apo-rosa` | APODERADO | `VIN-ANA`, con Ana |

Todas las acciones aceptan `fecha_hora` opcional en ISO 8601. Para reproducir
el guion, usar fechas como `2026-10-01T10:00:00`; si se omite, se usa la hora
actual de Lima. Una fecha con zona conserva su calendario y hora local al
almacenarse: el conteo por días usa ese calendario.

## Cuerpos de las acciones

Los ejemplos se copian en el endpoint indicado. Las acciones que exigen
desbloqueos deben ejecutarse después de sus prerrequisitos del guion.

`POST /acciones/ingresar`

```json
{"cuenta":"est-ana","fecha_hora":"2026-10-01T10:00:00"}
```

`POST /acciones/completar-actividad`

```json
{"cuenta":"est-ana","actividad":"ACT-01","fecha_hora":"2026-10-01T10:00:00"}
```

Cambiar `actividad` y repetir la petición para recorrer una ruta. Los casos se
completan con `/acciones/resolver-caso`.

`POST /acciones/responder-items`

```json
{"cuenta":"est-ana","actividad":"LAB-RIA1","respuestas":[{"item":"RIASEC-01","opcion":5},{"item":"RIASEC-02","opcion":1}],"fecha_hora":"2026-10-01T10:00:00"}
```

Este ejemplo guarda dos respuestas y deja la actividad EN_CURSO, con avance
2/15. `opcion` es el orden de la opción en la escala del ítem. Puede enviarse
un lote parcial y reemplazar respuestas; un lote inválido no guarda nada.
Guardar respuestas no registra eventos.

Para finalizar, responder los 15 ítems de `LAB-RIA1` y usar
`/acciones/completar-actividad` con esa actividad. Si faltan respuestas,
devuelve 409 con `detail.items_faltantes`. Al finalizar se desbloquea el
siguiente bloque de preguntas. RIASEC genera el resultado al completar
`LAB-RIA4`; la respuesta incluye
`"resultados_generados":[{"instrumento":"TEST-RIASEC","aplicacion":"APL-RIASEC"}]`.
Antes de finalizar la aplicación pueden corregirse respuestas; después quedan
fijas. Rehacer una actividad permite observar nuevos eventos sin recalcular.
Las puntuaciones y coincidencias pueden consultarse en el grupo **Instrumentos**
de Swagger, con las rutas de la tabla siguiente.

`POST /acciones/reiniciar-instrumento`

```json
{"cuenta":"est-ana","instrumento":"TEST-RIASEC","fecha_hora":"2026-10-02T10:00:00"}
```

Anula el resultado vigente, borra las respuestas de esa aplicación y deja
los progresos existentes en EN_CURSO. Conserva los desbloqueos, los eventos
anteriores y todos los resultados del historial. La respuesta incluye
`resultado_anulado` (o null), `actividades_reiniciadas`, eventos y desbloqueos.
Puede iniciarse de nuevo la aplicación con las acciones de respuesta y
finalización; genera un resultado nuevo y conserva el anterior como anulado.

Para TEST-AUTO es obligatorio elegir una aplicación:

```json
{"cuenta":"est-ana","instrumento":"TEST-AUTO","aplicacion":"APL-AUTO-SAL","fecha_hora":"2026-10-02T10:00:00"}
```

Reiniciar salida conserva las respuestas de entrada. Su comparación devuelve
409 hasta volver a completar salida. Omitir la selección cuando hay varias
aplicaciones devuelve 422; reiniciar sin respuestas ni resultado vigente
devuelve 409 y no registra eventos. Una aplicación ajena o inexistente y una
cuenta de apoderado devuelven 404. Con una sola aplicación se puede omitir
`aplicacion`, o indicar su código explícitamente.

`POST /acciones/resolver-caso`

```json
{"cuenta":"est-ana","actividad":"CASO-01","puntaje":50,"fecha_hora":"2026-10-01T10:00:00"}
```

Un intento completa la actividad con cualquier puntaje válido, de 0 a 100.
El mínimo para superar los dos casos de la semilla es 70. Cada intento guarda
un resultado; `SUPERA_CASO` se registra solo la primera vez que se supera.

`POST /acciones/responder-registro`

```json
{"cuenta":"est-ana","clasificacion":"VAGA","ampliada":false,"fecha_hora":"2026-10-01T10:00:00"}
```

Usar `ADECUADA` o `ampliada: true` para registrar una respuesta reflexiva.

`POST /acciones/escribir-entrada`, guiada:

```json
{"cuenta":"est-ana","origen":"GUIADA","pregunta":"PD-HISTORIA","texto":"Lo que descubrí de mi historia","fecha_hora":"2026-10-01T10:00:00"}
```

La pregunta debe estar disponible y cada estudiante puede responderla una vez.
Para una entrada libre, omitir `pregunta`:

`POST /acciones/escribir-entrada`, libre:

```json
{"cuenta":"est-ana","origen":"LIBRE","texto":"Una reflexión libre","fecha_hora":"2026-10-01T10:00:00"}
```

`POST /acciones/check-in`

```json
{"cuenta":"est-ana","nivel_seguridad":3,"fecha_hora":"2026-10-01T10:00:00"}
```

Seguridad admite enteros de 1 a 5; hay un check-in por estudiante y día.

`POST /acciones/ver-carrera`

```json
{"cuenta":"est-ana","carrera":"CAR-ENF","fecha_hora":"2026-10-01T10:00:00"}
```

`POST /acciones/publicar-entrevista`

```json
{"autores":["est-ana","est-luis"],"resumen":"Entrevista conjunta sobre una profesión","fecha_hora":"2026-10-01T10:00:00"}
```

Los autores deben ser estudiantes, sin duplicados. La entrevista recibe un
código público `ENT-...` y la respuesta agrupa los resultados en `por_cuenta`.

`POST /acciones/escribir-carta`

```json
{"cuenta":"est-ana","texto":"Lo que espero de mi futuro","fecha_hora":"2026-10-01T10:00:00"}
```

Cambiar `cuenta` a `apo-rosa` para guardar su carta. Cada rol actualiza su propio
texto; `ESCRIBE_CARTA` se registra solo en la primera escritura.

`POST /acciones/completar-conversacion`

```json
{"cuenta":"apo-rosa","conversacion":"CONV-01","fecha_hora":"2026-10-01T10:00:00"}
```

La sección CONVERSACIONES debe estar disponible para quien marca. La primera
vez registra eventos en Ana y Rosa y devuelve `por_cuenta`; repetirla no
registra eventos ni cambia la fecha de la conversación.

## Consultas para observar los resultados

| Método y ruta | Uso |
|---|---|
| `GET /cuentas` | Cuentas y roles de la demo |
| `GET /reglas` | Reglas, objetivos, condiciones y evaluadores especiales |
| `GET /cuentas/{cuenta}/resumen` | Cuenta y nivel actual |
| `GET /cuentas/{cuenta}/actividades` | Bloques y actividades del rol, en orden |
| `GET /cuentas/{cuenta}/fichas` | Fichas y disponibilidad |
| `GET /cuentas/{cuenta}/logros` | Insignias y niveles |
| `GET /cuentas/{cuenta}/testimonios` | Testimonios disponibles |
| `GET /cuentas/{cuenta}/diario/preguntas` | Preguntas y respuestas del diario |
| `GET /cuentas/{cuenta}/conversaciones` | Disponibilidad de conversaciones |
| `GET /cuentas/{cuenta}/progreso/{tipo_objetivo}/{codigo}` | Avance de cada condición y evaluador |
| `GET /cuentas/{cuenta}/eventos` | Historial, del evento más reciente al más antiguo |
| `GET /cuentas/{cuenta}/desbloqueos?solo_no_vistos=true` | Novedades pendientes |
| `POST /cuentas/{cuenta}/desbloqueos/marcar-vistos` | Marca las novedades; repetir devuelve `{"marcados":0}` |

Consultas de instrumentos (grupo **Instrumentos** en Swagger):

| Método y ruta | Uso |
|---|---|
| `GET /instrumentos` | Definiciones, dimensiones, escalas, aplicaciones y actividades |
| `GET /actividades/{actividad}/items` | Preguntas en orden, con las opciones de cada escala |
| `GET /cuentas/{cuenta}/actividades/{actividad}/respuestas` | Respuestas actuales, opción elegida y fechas |
| `GET /cuentas/{cuenta}/instrumentos` | Avance por aplicación y existencia de resultado vigente |
| `GET /cuentas/{cuenta}/instrumentos/{instrumento}/resultado?aplicacion=` | Resultado vigente, dimensiones y, para RIASEC, código de interés, coincidencias y carreras |
| `GET /cuentas/{cuenta}/instrumentos/{instrumento}/historial` | Todos los resultados del instrumento, incluidos los anulados |
| `GET /cuentas/{cuenta}/instrumentos/TEST-AUTO/comparacion` | Opciones, puntajes y diferencias entre entrada y salida |

Por ejemplo, consultar `GET /actividades/LAB-RIA1/items`, guardar respuestas
y revisar `GET /cuentas/est-ana/instrumentos`. Cada aplicación incluye
`estado`, `actividades` (completadas, total y faltantes), `items` (respondidos
y total) y `hay_resultado_vigente`. Sus estados son NO_INICIADO, EN_PROGRESO
y COMPLETADO; guardar todas las respuestas todavía requiere completar la
actividad con la acción correspondiente.

Tras finalizar las cuatro actividades de RIASEC, consultar
`GET /cuentas/est-ana/instrumentos/TEST-RIASEC/resultado`. Mientras falte un
resultado, devuelve 409 con `detail.avance`. Con una sola aplicación se puede
omitir `aplicacion`; con varias es obligatoria y omitirla devuelve 422.
TEST-AUTO no genera resultados: consultar su comparación después de completar
entrada y salida. Antes devuelve 409 con el avance de ambas aplicaciones.

El historial incluye `anulado_en`, nulo para los resultados vigentes, y conserva
dimensiones y coincidencias de los anulados. El código de interés y las carreras
se derivan al consultar; las vías se ordenan por posición y las correlaciones se
exponen a seis decimales. Las consultas de cuenta rechazan a Rosa con 404.
Todos estos GET son de lectura y no registran eventos.

TEST-INT y TEST-HAB incluyen `dimensiones_destacadas` en resultado e historial,
con el mismo formato que `dimensiones`. Se deriva de los puntajes guardados:
compara `puntaje / puntaje_maximo` sin usar el porcentaje redondeado, conserva
todas las dimensiones empatadas y su orden; si todas están en cero, destaca todas.

En progreso, usar `tipo_objetivo` en mayúsculas: BLOQUE, ACTIVIDAD, FICHA,
TESTIMONIO, PREGUNTA_DIARIO, CONVERSACIONES, INSIGNIA o NIVEL. Los códigos de
nivel son `N1`–`N5`; para CONVERSACIONES, el código es `-`.

Por ejemplo, consultar `cuenta = est-ana`, `tipo_objetivo = ACTIVIDAD`,
`codigo = ACT-17` después de llegar a la ciudad: ACT-13 estará cumplida y
faltará completar C1. Para la familia, consultar `CONVERSACIONES` / `-`
en Ana y Rosa por separado.

Una acción no permitida responde **409**, con `detail.mensaje` y, cuando aplica,
`detail.progreso`. Datos inválidos responden **422**; cuentas u objetivos
inexistentes y consultas de otra audiencia, **404**. Consultar el progreso de
una insignia oculta pendiente responde **403**. En el estado se muestra como
`???` hasta obtenerla; después se revela su nombre, descripción y requisito.

Los desbloqueos son permanentes y se conceden por cuenta y regla. Todas las
condiciones de una regla deben cumplirse; varias reglas para un objetivo son
alternativas. Las actividades también requieren su bloque disponible. Rehacer
una actividad registra otro COMPLETA_ACTIVIDAD y conserva COMPLETADA, pero
no aumenta el conteo de referencias distintas.

La API expone códigos públicos. Entradas de diario y check-in carecen de código
en el modelo, por lo que sus eventos muestran `referencia: null`; sus
referencias permanecen almacenadas internamente.

## Guion de los 17 escenarios

Estos escenarios requieren el conjunto `demo`. Cada escenario empieza con
`POST /demo/reiniciar`. El reinicio conserva las cartas; para reproducir también
su estado inicial, detener el servidor, ejecutar
`uv run python -m datos.cargar demo --vaciar` y volver a arrancarlo antes del
escenario. Repetir la preparación desde cero: los
prerrequisitos de la tabla se ejecutan después de ese reinicio,
sin reiniciar entre la preparación y la acción demostrada. Todas las acciones
son de Ana salvo que se indique otra cuenta.

Preparaciones utilizadas en el guion, mediante `/acciones/completar-actividad`:

- **Inicio**: completar `ACT-01`, `ACT-02` y `ACT-03`, en ese orden.
- **Ciudad (E7)**: completar Inicio, después `ACT-04`, `ACT-05`, `ACT-06`,
  `ACT-12` y `ACT-13`.
- **Helena (E8)**: completar Ciudad, después `HEL-01`, `HEL-02` y `HEL-03`.
- **Casos (E9)**: completar Helena, después resolver `CASO-01` con 50, 85 y 95.
- **Familia (E10)**: completar Ciudad; escribir las cartas de Ana y Rosa;
  completar `ACT-P01` y `ACT-P02` como Rosa.

| Escenario | Preparación | Pasos y resultado esperado |
|---|---|---|
| E1. Estado inicial | Solo reinicio | Consultar estado de Ana y Rosa. Ana: ACT-01 disponible, resto bloqueado, ciudad bloqueada, nivel 1 y cuatro logros `???`. Rosa: ACT-P01 disponible, ACT-P02 bloqueada y su insignia; no ve contenido de estudiantes. |
| E2. Primer desbloqueo | Solo reinicio | Completar ACT-01. Se obtiene R-ACT-02, con 1/1; ACT-01 queda COMPLETADA y ACT-02 DISPONIBLE. |
| E3. Saltarse la ruta | Solo reinicio | Intentar ACT-04. Devuelve 409, con ACT-03 en 0/1, y no registra eventos. |
| E4. Varios desbloqueos | Completar ACT-01 | Completar ACT-02 y ACT-03. La última registra COMPLETA_ACTIVIDAD y COMPLETA_BLOQUE(B0), concede R-ACT-04, R-INS-PRIMER-PASO y R-NIV-2; nivel 2. |
| E5. Rehacer no suma | Inicio | Rehacer ACT-01 cinco veces. Hay cinco eventos más, ningún desbloqueo nuevo y un solo COMPLETA_BLOQUE(B0); siguen siendo tres actividades distintas. |
| E6. Días distintos | Solo reinicio | Check-in el 1 de octubre, otro ese día (409), luego el 2 y el 3. Al tercero válido se revela LOG-CONSTANCIA. Usar las fechas indicadas abajo. |
| E7. Llegada a la ciudad | Inicio | Completar ACT-04, ACT-05, ACT-06, ACT-12 y ACT-13. En la última respuesta: C1–C4, INS-CIUDAD, FIC-MERCADO, N3 y LOG-INCANSABLE. HEL-01, HEL-03, CASO-01 y COMP-13 quedan disponibles; HEL-02, CASO-02 e INV-01 siguen bloqueadas. |
| E8. Condición compuesta | Ciudad | Consultar progreso de ACT-17: ACT-13 cumplida y C1 en 0/1. Completar HEL-01, HEL-02 y HEL-03. La última completa C1 y abre ACT-17. |
| E9. Caso y reintentos | Helena | Resolver CASO-01 con 50, 85 y 95. Con 50 se completa y abre CASO-02; con 85 se supera y concede TES-HOSPITAL, INS-PRIMER-CASO, INV-01 y N4; con 95 solo se agrega intento y COMPLETA_ACTIVIDAD. |
| E10. Familia a destiempo | Ciudad | Ana escribe carta: sus conversaciones disponibles y las de Rosa bloqueadas. Rosa escribe carta: siguen bloqueadas. Rosa completa ACT-P01 y ACT-P02: se abren sus conversaciones y obtiene INS-CONOZCO-MI-ROL. |
| E11. Dos cuentas | Familia | Rosa marca CONV-01. Eventos en ambas cuentas; Ana obtiene PD-CONV-01 y Rosa no. Ana vuelve a marcarla: sin eventos nuevos. |
| E12. Coautoría | Solo reinicio | Publicar entrevista con autores est-ana y est-luis. Ambos reciben PUBLICA_ENTREVISTA e INS-INVESTIGADOR, agrupados por cuenta. |
| E13. Evaluador especial | Solo reinicio | Ver CAR-ENF, CAR-MED y CAR-CIV: dos familias, insignia pendiente. Consultar progreso de INS-EXPLORADOR: conteo cumplido, evaluador falso. Ver CAR-DIS: tercera familia, se concede INS-EXPLORADOR. |
| E14. Diario | Ciudad | Escribir GUIADA de PD-HISTORIA; repetir devuelve 409. Escribir LIBRE: dos eventos y LOG-PLUMA. Intentar GUIADA de PD-CONV-01: 409 porque aún está bloqueada. |
| E15. Reflexión | Solo reinicio | Enviar VAGA/false, VAGA/true, ADECUADA/false y ADECUADA/false. La primera no emite evento; la cuarta concede LOG-PENSADOR por las tres reflexivas. |
| E16. Nivel 5 | Casos | Completar ACT-17 y ACT-18. La última concede R-ACT-19 y R-NIV-5; nivel actual 5 y los cinco niveles OBTENIDO. |
| E17. Novedades vistas | Completar ACT-01 | Consultar desbloqueos con solo_no_vistos=true, marcar vistos y consultar otra vez: lista vacía. |

Para E6, usar `fecha_hora` en este orden:

```text
2026-10-01T10:00:00
2026-10-01T18:00:00
2026-10-02T10:00:00
2026-10-03T10:00:00
```

En E5, el progreso público de LOG-INCANSABLE sigue respondiendo 403 porque
es oculto y aún no se obtuvo. El historial permite comprobar las tres
referencias distintas; el test del escenario verifica además el 3/8
directamente con el motor. E7 revela el logro al alcanzar ocho distintas.

## Depuración de reglas

`POST /eventos` registra eventos crudos y evalúa reglas sin actualizar el
estado de dominio. Por ejemplo:

```json
{"cuenta":"est-ana","tipo":"COMPLETA_ACTIVIDAD","referencia":"ACT-04","fecha_hora":"2026-10-01T10:00:00"}
```

Este ejemplo puede desbloquear ACT-05 sin crear un progreso COMPLETADA para
ACT-04. El endpoint omite disponibilidad e idempotencia de las acciones;
usarlo para reglas aisladas y reiniciar antes de volver al guion. Las referencias
son códigos de entidades existentes; para diario y check-in deben omitirse o
ser null.

## Pruebas y documentación

Ejecutar en otra terminal, desde la raíz:

```powershell
uv run pytest -q
```

Para ejecutar solo los escenarios o los invariantes:

```powershell
uv run pytest -q tests/test_escenarios.py
uv run pytest -q tests/test_invariantes.py
```

Los tests preparan explícitamente bases temporales independientes de la base
configurada para el servidor. La suite cubre
E1–E17 del motor, I1–I14 de instrumentos y R1–R17 de registro, los nueve
invariantes, la semilla, restricciones, conteos, consultas y reversión de
transacciones. La fixture general fuerza `EVALUADOR=falso`; el adaptador Gemini
se comprueba exclusivamente con clientes y transportes simulados. El mapa está en
[Validación](docs/validacion.md); las opciones no definidas por la especificación
están registradas en [Decisiones](docs/decisiones.md).

La suite de cierre de fase 8 v2 tiene **947 tests pasando, 2 avisos
de deprecación**, en 1038.05 segundos (17:18), con `uv run pytest -q`.
`uv lock --check` también pasa. Las evidencias visuales usan el falso y
el adaptador se prueba con clientes simulados. La evaluación real del cierre se
ejecutó separadamente con autorización y está en `docs/evaluacion_gemini.md`.

La demo combina el motor de eventos y desbloqueos, los instrumentos con sus
consultas, reinicio e interfaz, y las ocho fases de actividades de registro.
El [cierre de Registro v2](docs/validacion.md#registro-v2-fase-8-cierre-consolidado)
distingue las comprobaciones con falso y clientes simulados de la ejecución real.
Las clasificaciones válidas del modelo coinciden con lo esperado; la revisión de
criterios y preguntas conserva las discrepancias y los casos sin salida válida.
Autenticación y panel de orientadora siguen fuera de alcance. La evaluación
de completitud con Gemini se limita a los ítems de registro especificados.
