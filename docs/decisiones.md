# Decisiones de implementación

## Refactor de estructura

### 2026-10-08 · R0: línea base

- Se leen completos `AGENTS.md` y `docs/spec-refactor-estructura.md` y se crea
  `refactor-estructura` desde `iteracion-1`, según §0 de la especificación.
- `uv sync` completa correctamente: 44 paquetes resueltos y 43 comprobados.
  El lanzador local de pytest falla al resolver su ruta bajo el aislamiento de
  Windows; se reinstala la misma versión fijada (`pytest==9.1.1`) con
  `uv sync --reinstall-package pytest` y se ejecuta la suite fuera de esa
  restricción. No cambian `pyproject.toml` ni `uv.lock`.
- La suite se ejecuta con `EVALUADOR=falso`. Las rutas de `PYTEST_ADDOPTS`
  pierden las barras de Windows al interpretarse y los temporales y la caché
  quedan dentro del repo; al terminar se verifican y eliminan ambos directorios
  generados. No se llama a Gemini ni quedan nuevos logs o bases en el repo.
- Resultado de `uv run pytest -q`: **1006 passed, 2 warnings en 1095.20 s
  (18 min 15 s)**. La línea base coincide con las 1006 pruebas indicadas en §9;
  no hay pruebas fallidas ni omitidas. Los avisos corresponden a las
  deprecaciones de Starlette/httpx y de Google GenAI en Python 3.14.
  Antes y después de R0 se conserva la misma suite, sin cambios de aserciones.
- Los ocho fixtures de `ov_frontend/tests/fixtures/servidor/` están disponibles
  para la comparación de R3; no hace falta generar una copia alternativa en R0.
- No se mueve ni modifica código, datos, pruebas o archivos del frontend.
  Los cambios previos en `AGENTS.md` y el archivo de especificación se conservan
  fuera del commit de esta fase. R1 y las fases siguientes quedan pendientes.

## Iteración 1 · F3

### 2026-10-07 · Exportación de fixtures de contrato

- El script de §4.5 recibe `--destino` obligatorio, sin asumir una ruta entre
  repos. Esta ejecución usa `ov_frontend/tests/fixtures/servidor`.
- Se usa una base nueva dentro de un directorio temporal, semilla explícita
  `plataforma` y `EVALUADOR=falso`, incluso si el entorno selecciona Gemini.
  No se abre ni reinicia ninguna base del usuario.
- DATO DE PRUEBA: fecha fija `2026-10-07T10:00:00` y respuestas de §4.6
  (I=5, R=4, A=3, S/E/C=1) para reproducir los mismos bytes al regenerar.
- Se capturan P1, P2 y P7 en un recorrido; el fixture de no vistos corresponde
  a P12 justo después de P7. Se marcan y se comprueba que la consulta queda
  vacía; después se responden las 14 interacciones para capturar P10.
  Así se conserva el prerrequisito explícito de P12 sin agregar avisos de Mara.
- Los ocho JSON conservan las respuestas de la API, sin campos adicionales:
  la marca DATO DE PRUEBA queda en el código generador. Se completa el
  recorrido antes de escribir archivos, para no publicar respuestas parciales
  si falla la aplicación. No se adaptan pruebas existentes ni contratos.

### Implementación y verificación de F3

`scripts/exportar_fixtures_front.py` consulta la aplicación con TestClient,
ejecuta las acciones existentes y serializa sus respuestas en UTF-8, con
acentos legibles, indentación y salto final. El directorio temporal y su base
se eliminan al terminar, incluso al fallar. La variable EVALUADOR previa se
restaura tras cada exportación. El script funciona como archivo ejecutable
desde cualquier directorio y no depende de auxiliares de pytest.

Se ejecutó:

```powershell
uv run python scripts/exportar_fixtures_front.py --destino C:/Users/mauri/Documents/GitHub/ov_frontend/tests/fixtures/servidor
```

Se generaron exactamente `estado-inicial.json`, `completar-mission-welcome.json`,
`completar-mission-next-step.json`, `estado-ciudad.json`, `items-act-tip-01.json`,
`completar-act-tip-14.json`, `resultado-riasec.json` y `desbloqueos-no-vistos.json`.
El último contiene los 19 avisos del camino, aún no vistos. El resultado
RIASEC es IRA, con diez coincidencias y `geologist` primero; las carreras son
ambiental, civil y veterinaria, como P10.

Las tres pruebas nuevas de `tests/test_exportar_fixtures_front.py` pasan en
3,56 segundos, con una advertencia conocida de Starlette/httpx. Comprueban el
argumento obligatorio desde otro directorio, los esquemas Pydantic y estados
de los escenarios, la regeneración con bytes idénticos, conservación de otros
archivos del destino, limpieza temporal, base ajena intacta, evaluador falso
ante `EVALUADOR=gemini` y ausencia de salida ante un fallo del recorrido.

Frontend: `npm run build` y `npm run lint` pasan. `npm test` da 276 pases y
16 fallas entre 292 pruebas, en 18,86 segundos. Se compararon los nombres y
líneas reportados con F0: son las mismas 16 de `adventure-rendering.test.mjs`.
No se cambian código ni pruebas existentes del front; solo se agregan los
ocho JSON. El build conserva su aviso previo sobre chunks mayores de 500 kB.

**Cierre · 2026-10-07.** F3 completa. `uv run pytest -q`, con `SEMILLA=demo`,
`EVALUADOR=falso` y temporales propios, dio **1006 passed, 2 warnings** en
774,55 segundos (12 min 54 s). Incluye las tres pruebas del exportador,
P1–P16 y las pruebas anteriores. Las advertencias son las deprecaciones
conocidas de Starlette/httpx y Google en Python 3.14. Ambos repos continúan
en `iteracion-1`, con un commit de F3 por repo. No se agregan dependencias,
endpoints ni llamadas a Gemini, ni se hace push. F4–F7 y las 16 fallas
previas del frontend quedan pendientes.

## Iteración 1 · F2

### 2026-10-07 · Decisiones aprobadas antes de implementar

- Una base de esquema 5 creada en F1 cuyo CHECK de `TipoEventoUso` no admite
  los tres eventos nuevos se rechaza al arrancar con el mensaje de esquema
  incompatible y el nombre real del archivo, sin modificarla ni migrarla.
  Se comprobarán `evento_uso.tipo` y `condicion_desbloqueo.tipo_evento`.
- El catálogo sigue §4.3.8: se agregan las ocupaciones propias de las carreras
  a las relaciones del frontend y se excluye `drone-operator`, sin cambiar el
  catálogo local. Solo se cargan las 36 ocupaciones especificadas.
- Se verificó que `11-3012.00` está presente en el Excel del repositorio;
  se utiliza para `public-administrator`, sin alternativa ni sustitución.
- La descripción nueva de I10 será «Venciste al enemigo sin perder destellos
  en tu primera victoria», marcada como DATO DE PRUEBA.
- La única eliminación prevista de pruebas existentes es
  `test_rechazo_temporal_plataforma_antes_de_crear_o_reiniciar_tablas`
  (sus tres casos), autorizada en F1 y en el plan aprobado de F2. Se conserva
  el resto de las expectativas de la demo. F3 y el frontend quedan pendientes.

### Implementación y verificación de F2

- `app/semilla_plataforma.py` contiene tablas estáticas adaptadas del frontend
  y de §4.3. La lectura del Excel valida las 36 referencias antes de insertar.
  Las etapas usan mapas de objetos, `add_all` e inserciones en lote, sin
  consultas por objeto ni `commit` propio. La marca es `(1, 5, 'plataforma')`.
- Se cargan 3 cuentas, 1 vínculo, 2 bloques, 24 actividades, 4 fichas,
  10 insignias, 5 niveles, 44 reglas y 53 condiciones. RIASEC tiene 60 ítems,
  una escala y una aplicación en 14 interacciones. Se cargan 36 ocupaciones,
  216 puntajes, 6 familias, 6 carreras y 23 relaciones carrera–ocupación.
- Los resúmenes de fichas y mensajes de I1–I9 se copian del frontend; los
  títulos nuevos de Mara, los enunciados y la descripción de I10 se marcan
  DATO DE PRUEBA. `nurse` usa el título «Enfermero/a»; la anotación documental
  de §4.3.8 se conserva como comentario, no como parte del título público.
- El cargador no llama a `cargar_definiciones_instrumentos`, a
  `cargar_catalogo_ocupaciones` ni a la semilla demo. No se crean LAB, otros
  instrumentos, definiciones de registro, testimonios, preguntas ni
  conversaciones. `mission-compass` no presenta ítems. Las posiciones de
  registro quedan vacías y el reinicio vuelve a cargar plataforma.
- `misiones_camino_sin_inicio` usa la regla y su parámetro, las definiciones
  en caché y los conteos agrupados de la cuenta. Filtra las referencias de
  COMPLETA_ACTIVIDAD por CAMINO y excluye orden 1; las repeticiones no suman.
  Conserva la memoización por nombre y umbral y la invalidación existente,
  sin cambios en `motor.py`. Sin regla o parámetro positivo válido falla
  explícitamente; sin CAMINO devuelve falso.
- Los CHECK de ambos campos de eventos se inspeccionan antes de leer estado
  o cargar caché, comparando sus valores con `TipoEventoUso`. Se conserva el
  esquema 5 y se rechazan restricciones antiguas o ausentes sin migración.

Pruebas nuevas: `tests/test_plataforma.py` contiene exactamente P1–P16,
independientes y con fechas explícitas. `tests/test_semilla_plataforma.py`
verifica catálogos, puntajes, enunciados, distribución, independencia del
cargador (guardia dinámica y revisión AST), errores de Excel, rollback
tardío de datos y DDL, CHECK antiguo/ausente en ambas tablas con conservación
de bytes, parámetros y memoización del evaluador y cero SQL adicional con
conteos precargados. También verifica permanencia y unicidad de desbloqueos,
nivel monótono, audiencias, repetición, unicidad de eventos de bloque y
carta, aislamiento de check-in y unicidad de entradas guiadas. La pregunta
sintética de este último caso está marcada DATO DE PRUEBA y solo existe en
su fixture; no se agrega a la semilla.

Se eliminan únicamente los tres casos de la prueba temporal de rechazo
identificada en F1. No se adaptan otras pruebas ni resultados de demo.
Las fixtures de plataforma se limitan a los módulos nuevos mediante
`tests/soporte_plataforma.py`; no se cambia `tests/conftest.py`.

Validación dirigida: colección de 16 escenarios en 0,08 s; P1–P16 pasan
en 10,81 s, con una advertencia previa. Las pruebas complementarias y de
configuración dieron 39 pases y una aserción nueva de diario fallida; se
corrigió para seguir §5 del motor (LIBRE también emite DIARIO), sin cambiar
producción, y la prueba corregida pasó en 0,80 s.

**Cierre · 2026-10-07.** F2 completa: `uv run pytest -q` con `SEMILLA=demo`,
`EVALUADOR=falso` y temporales propios dio **1003 passed, 2 warnings** en
654,01 segundos (10 min 54 s). La suite incluye exactamente los 16 escenarios
P1–P16 y 21 casos complementarios nuevos; se retiraron los tres casos del
rechazo temporal autorizado. Las dos advertencias son las deprecaciones
conocidas de Starlette/httpx y Google en Python 3.14.

El frontend no se modifica ni se reejecutan sus pruebas: conserva la línea
base de F0 (276 pasan, 16 fallan; build y lint pasan). No se agregan
dependencias, endpoints ni llamadas reales a Gemini. F3–F7 quedan pendientes.

## Iteración 1 · F1

### 2026-10-07 · Decisiones aprobadas antes de implementar

- **Mensajes de esquema incompatible.** Por autorización explícita del usuario,
  se agrega a §4.2 de `docs/iteraciones/spec-iteracion-1.md` la adaptación de
  expectativas del mensaje fijo con `demo.db` al mensaje con el archivo real.
  Se conservan el rechazo y la comprobación de que la base no se modifica.
  Afecta a `test_arranque_rechaza_esquema_anterior_sin_modificar_base` de
  `tests/test_semilla_instrumentos.py` y a
  `test_rechaza_version_dos_completa_sin_modificar_archivo` de
  `tests/test_configuracion_metodos.py`.
- **`SEMILLA=plataforma` en F1.** Se preparan configuración y selección, pero
  su carga falla con un mensaje claro antes de crear o reiniciar tablas. Nunca
  se carga `demo` como sustituto. En F2 se reemplaza este rechazo temporal por
  la carga real y se elimina la prueba que comprueba dicho rechazo.

### Implementación y adaptaciones realizadas

- `app/configuracion_base.py` concentra la selección sin abrir la base.
  `SEMILLA` y `RUTA_BD` se leen del entorno del proceso; los argumentos
  explícitos de la fábrica prevalecen sobre su variable correspondiente.
  Como opción simple para rutas relativas, se resuelven desde la raíz del
  repositorio, igual que los archivos predeterminados. No se agrega otra
  carga de `.env` a la configuración de la base.
- El esquema 5 conserva las 45 tablas y añade `esquema_version.semilla`
  no nula y `ocupacion.codigo` único y nullable. La demo solo escribe su
  marca `(1, 5, 'demo')`; sus datos, reglas y resultados se conservan y
  todas sus ocupaciones mantienen `codigo = NULL`.
- El arranque comprueba tablas y columnas antes de leer la marca; rechaza
  esquemas incompatibles y semillas distintas sin migración ni modificación
  del archivo. La selección de cargador ocurre antes del DDL tanto al
  arrancar como al reiniciar. El rechazo temporal de `plataforma` no toca
  tablas, caché ni posiciones; `/demo/reiniciar` conserva su tratamiento
  existente de errores de carga como 422.
- `CoincidenciaPublica.codigo` sale de la ocupación ya leída, sin consultas
  adicionales, y aparece en resultado vigente, historial y `via` de las
  carreras recomendadas. La validación narrativa de `REG-ACT08` sigue
  restringida a la demo. Los eventos de §4.3.4 quedan para F2.

Los puntos siguientes corresponden a las viñetas de adaptaciones autorizadas
de §4.2, en su orden (el punto 5 es la ampliación aprobada arriba):

| Archivo y prueba existente | Adaptación efectuada | Autorización |
|---|---|---|
| `tests/test_semilla_instrumentos.py` · `test_catalogos_y_estado_inicial_de_instrumentos` | Versión vigente esperada 4 → 5; mismos catálogos y conteos. | Punto 1: versión vigente. |
| `tests/test_semilla_instrumentos.py` · `test_version_unica_y_dos_resultados_vigentes_prohibidos` | La fila deliberadamente inválida de id 2 incluye `semilla='demo'`, para seguir comprobando la restricción de id y no fallar por la columna nueva. | Punto 2: adaptación al esquema de columnas. |
| `tests/test_semilla_instrumentos.py` · `test_arranque_rechaza_esquema_anterior_sin_modificar_base` | Versión futura inválida 5 → 6; las filas preparadas incluyen `semilla`; mensaje exacto con `prueba.db`. Conserva los rechazos de versiones anteriores y la comparación del archivo. | Puntos 1, 2 y 5. |
| `tests/test_semilla_instrumentos.py` · `test_reinicio_escribe_version_dos_y_catalogo_completo` | Versión vigente esperada 4 → 5; mismos conteos y distribución. | Punto 1: versión vigente. |
| `tests/test_semilla_instrumentos.py` · `test_reinicio_con_excel_invalido_conserva_estado_y_muestra_error` | Versión vigente esperada 4 → 5; conserva las comprobaciones del estado tras rollback. | Punto 1: versión vigente. |
| `tests/test_configuracion_metodos.py` · `test_rechaza_version_dos_completa_sin_modificar_archivo` | La fila de versión 2 incluye `semilla`; mensaje exacto con `anterior.db`; mantiene versión antigua, rechazo y comparación del archivo. | Puntos 2 y 5. |
| `tests/test_registro.py` · `test_rechaza_estructura_registro_v1_con_version_cuatro_sin_modificar_base` | La fila preparada incluye `semilla`; conserva versión 4, todas las variantes y comparación del archivo. | Punto 2: adaptación al esquema de columnas. |
| `tests/test_instrumentos.py` · `test_i4_riasec_genera_resultado_solo_en_la_cuarta_actividad` | Incluye `codigo = None` en las coincidencias públicas; conserva posiciones, O*NET, correlaciones, ajuste y dimensiones. | Punto 3: coincidencias con `codigo: null` en demo. |
| `tests/test_instrumentos.py` · `test_i5_coincidencias_de_luis_contra_el_notebook` | Incluye `codigo = None` en las coincidencias públicas; conserva los valores numéricos originales y las carreras. | Punto 3: coincidencias con `codigo: null` en demo. |

No se adaptan enumerados (punto 4) ni otras pruebas existentes. Las pruebas
nuevas de `tests/test_configuracion_base.py` cubren configuración y precedencia,
restricciones de columnas, conservación de bases incompatibles o de otra
semilla y propagación del código a resultado, historial y recomendaciones.
`test_rechazo_temporal_plataforma_antes_de_crear_o_reiniciar_tablas`, con tres
casos, queda identificado para eliminarlo en F2 al incorporar la carga real.
El caso de código no nulo usa una modificación sintética, marcada como
`DATO DE PRUEBA`, solo en la base temporal; no añade datos a la semilla demo.

Validación dirigida: 38 pruebas pasan, 291 no seleccionadas por `-k`,
1 advertencia de deprecación; 18,72 segundos.

### Cierre de F1 · 2026-10-07

`uv run pytest -q`, con `SEMILLA=demo`, `EVALUADOR=falso` y temporales propios:
**969 pruebas pasan, 0 fallas, 2 advertencias; 901,12 segundos (15 min 1 s)**.
Son las 947 pruebas de la línea base y 22 casos nuevos. Las advertencias son
las previas de `starlette.testclient` y `google.genai.types`; no se añaden
dependencias ni se hacen llamadas reales a Gemini.

F1 completa en el backend, rama `iteracion-1`. El frontend no se modifica ni
se reejecutan sus pruebas en esta fase; conserva la línea base de F0 con sus
16 fallas previas documentadas. F2–F7 quedan pendientes. En F2 se sustituye
el rechazo temporal de `plataforma` por la carga real y se elimina su prueba.

## Fase 1

- Se conserva Python 3.14, ya configurado en el proyecto; cumple Python 3.11+.
- La base SQLite se guarda como `demo.db` en la raíz del proyecto. Cada conexión activa `PRAGMA foreign_keys=ON`. La fábrica `crear_aplicacion(url_bd)` permite bases temporales para tests.
- El arranque carga la semilla en una transacción solo si todas las tablas están vacías. Si existen datos, los conserva. Una base parcialmente poblada no se repara automáticamente; `/demo/reiniciar` restaura la demo. No hay migraciones de esquemas existentes.
- `/demo/reiniciar` elimina y recrea las tablas en orden de dependencias, y carga toda la semilla con una transacción de conexión. Es una herramienta para uso secuencial en una demo local; no debe ejecutarse mientras se realizan otras peticiones.
- `bloque.numero` es el sufijo numérico del código (B0 → 0, C1 → 1, P1 → 1); el orden de las actividades comienza en 1 dentro de cada bloque.
- Los campos no especificados usan textos demostrativos: fichas `Contenido de demo: {titulo}.`, testimonios `Descripción de demo: {titulo}.` y enlaces `https://example.com/{codigo_en_minusculas}`, conversaciones con su título como tema, insignias `Logro de demo: {nombre}.`. Las familias se llaman Salud, Ingeniería, Arte y Negocios. Estos textos no participan en las reglas.
- Los requisitos de insignias ocultas guardan el texto de la sección 7.4 sin la anotación editorial `(oculto)`. La ocultación en el estado corresponde a la fase 3.
- Los nombres de reglas, no especificados, son `Desbloquear {codigo_objetivo}`; CONVERSACIONES usa `-`. Los códigos, objetivos y condiciones son los de la especificación.
- `/reglas` devuelve una lista ordenada por código, con `regla`, `nombre`, `tipo_objetivo`, `objetivo` (`codigo`, `nombre`), `condiciones` (`tipo_evento`, `referencia`, `tipo_conteo`, `cantidad_minima`) y `evaluador_especial` (nombre o null). No evalúa condiciones. Los niveles se representan por N1–N5 y CONVERSACIONES por `-`. El reinicio devuelve `{"mensaje": "Demo reiniciada"}`.
- `id_objetivo` e `id_referencia` son referencias polimórficas sin FK SQL; la semilla resuelve códigos a ids por tipo. Las referencias convencionales sí tienen FK. Los tests comprueban todos los objetivos y referencias de las reglas.
- Las entradas GUIADA tienen un índice único parcial por cuenta y pregunta; las LIBRE tienen pregunta nula. Puntajes y nivel de seguridad incluyen restricciones de rango. `desbloqueo.visto` y `conversacion_vinculo.conversado` empiezan en falso.
- La especificación contiene 42 reglas y **53 condiciones**, no las 52 indicadas por error en el plan inicial: R-ACT-17 tiene dos condiciones. Se conserva la especificación íntegra.
- La caché de uv se configura en `uv.toml` como `.uv-cache`, dentro del proyecto, para evitar problemas de permisos en la caché global de Windows.

## Fase 2

- `registrar_eventos` recibe la sesión, cuenta, pares `(tipo, id_referencia)` y fecha explícita. Inserta todos los eventos antes de evaluar las reglas; usa `flush`, sin `commit` ni `rollback`. El llamador confirma o revierte toda la acción en una sola transacción. El motor registra eventos crudos; las validaciones y los eventos que ocurren solo la primera vez corresponden a las acciones de la fase 4.
- `evaluar_regla` devuelve `ResultadoRegla` con `cumple`, el progreso de todas las condiciones (`actual`, `requerido`, `cumplida`) y el resultado independiente del evaluador especial. Los nuevos desbloqueos incluyen los códigos y nombres públicos, con la explicación de esas condiciones. Una regla sin condiciones o un evaluador desconocido provoca `ValueError`, para evitar conceder objetivos por una configuración inválida.
- Los conteos se realizan en SQLite, filtrando cuenta, tipo y referencia cuando corresponde. `REFERENCIAS_DISTINTAS` excluye referencias nulas: null no identifica un objeto. `DIAS_DISTINTOS` usa la fecha calendario almacenada en `fecha_hora`, sin convertirla a UTC. El avance no se limita al mínimo requerido.
- Una lista de eventos vacía no evalúa reglas. Las candidatas se ordenan por código; solo se evalúan las pendientes relacionadas con los tipos registrados y de la audiencia de la cuenta. No hay segunda pasada ni eventos derivados de desbloqueos.
- El bloque contenedor se verifica al consultar disponibilidad, no al crear el desbloqueo de una regla de actividad (secciones 4.3 y 4.4). Una regla ya obtenida permanece obtenida. Varias reglas del mismo objetivo son alternativas, y cada desbloqueo sigue siendo por cuenta y regla.
- Objetivos inexistentes o con ids inapropiados para su tipo no están disponibles. CONVERSACIONES usa id interno nulo para ambos roles; no requiere vínculo en el motor. `nivel_actual` devuelve el mayor nivel disponible, o None para apoderados.
- Se mueve la resolución compartida de códigos a `referencias.py`, para que motor y consultas no dependan entre sí. No se agregan endpoints ni dependencias en esta fase.

## Fase 3

- Se implementan estado y progreso, junto con las consultas de cuentas, eventos y desbloqueos de la sección 6.4. Marcar desbloqueos como vistos es la única escritura nueva: actualiza los pendientes de una cuenta en una transacción y devuelve `{"marcados": cantidad}`; repetirla devuelve cero.
- El estado conserva las mismas claves para ambos roles. Para apoderados, `nivel_actual` es null y fichas, testimonios, preguntas de diario y niveles son listas vacías. Los bloques y las insignias se filtran por audiencia; las actividades siguen el orden definido dentro de su bloque.
- La disponibilidad proviene del motor. Una actividad se muestra COMPLETADA solo si está disponible y tiene progreso COMPLETADA; las actividades de bloques bloqueados siempre se muestran BLOQUEADA. La decisión original de no mostrar EN_CURSO queda **reemplazada por Instrumentos, fase 3**, según la sección 5.9 de su especificación.
- Las insignias ocultas pendientes se muestran como código `???`, nombre genérico `Logro oculto`, descripción y requisito null. Al obtenerlas se muestran completas. Los niveles disponibles usan OBTENIDO y los pendientes BLOQUEADO. El estado incluye el texto de cada pregunta y su indicador `respondida`, obtenido de las entradas GUIADA de esa cuenta.
- Progreso acepta códigos públicos (N1–N5 para niveles, `-` para CONVERSACIONES). Cuenta u objetivo inexistentes, códigos inválidos y objetivos de otra audiencia devuelven 404; un tipo de objetivo inválido devuelve 422. Insignias ocultas no obtenidas devuelven 403. Se devuelven todas las reglas del objetivo, incluidas ambas alternativas de CONVERSACIONES; no se inventan reglas para el bloque contenedor.
- En progreso, `cumplida` es el resultado actual de evaluar la regla, y `disponible` consulta los desbloqueos persistidos y el bloque contenedor. `evaluador_especial` se incluye solo cuando existe; las referencias nulas de condiciones se conservan como null.
- Las colecciones de contenido y reglas se ordenan por código; niveles por número. Eventos y desbloqueos van por fecha descendente, con el id interno como desempate sin exponerlo. El filtro `solo_no_vistos` es false por defecto. Los GET no registran eventos ni crean desbloqueos.
- El modelo no define códigos públicos para entradas de diario o check-in. Por simplicidad, sus eventos muestran `referencia: null` en la línea de tiempo; los ids siguen almacenados internamente. Los demás eventos con referencia exponen el código de la entidad correspondiente. No se agregan columnas ni se fabrican códigos a partir de ids internos.

## Fase 4

- Las diez acciones y `/eventos` se ejecutan dentro de `sesion.begin()` en el router. Las funciones de dominio solo usan `flush`: cualquier fallo revierte estado, eventos y desbloqueos, incluso cuando participan varias cuentas. Conflictos de integridad responden 409; las validaciones de entrada responden 422 y cuentas/referencias inexistentes, 404.
- Los errores de dominio usan `detail: {"mensaje": ...}`. Si el objetivo está bloqueado y corresponde a la audiencia, agregan `progreso` con el formato de la sección 6.3. No se exponen ids internos ni detalles SQL.
- Cada acción devuelve `eventos_registrados` y `nuevos_desbloqueos`. Entrevistas y conversaciones usan `{"por_cuenta": {"codigo_cuenta": {"eventos_registrados": [...], "nuevos_desbloqueos": [...]}}}`. El evaluador especial ausente se omite; referencias sin código público siguen siendo null.
- Fechas suministradas conservan su calendario/hora local y se almacenan sin zona, como los conteos de fase 2. Sin fecha, se usa la hora de Lima (UTC−05:00). Una petición comparte la misma fecha entre todos sus eventos y cuentas.
- Las entradas GUIADA requieren pregunta y las LIBRE no la admiten. Puntajes aceptan números finitos entre 0 y 100; seguridad, enteros de 1 a 5. Clasificaciones son ADECUADA o VAGA. Los autores deben formar una lista no vacía sin duplicados. Los textos no tienen restricciones adicionales no definidas en la especificación.
- Las entrevistas reciben un código nuevo `ENT-` seguido de un UUID aleatorio; no depende de su id interno. Si hubiese varios vínculos por cuenta, se utiliza el primero por código; la semilla solo tiene VIN-ANA. Una conversación exige vínculo y disponibilidad únicamente de la cuenta que marca.
- Rehacer actividades siempre registra COMPLETA_ACTIVIDAD. COMPLETA_BLOQUE y SUPERA_CASO consultan el historial para evitar repeticiones; los casos completan la actividad con cualquier puntaje y guardan todos los intentos. Cambiar una carta actualiza su texto sin repetir ESCRIBE_CARTA. Repetir una conversación ya marcada no cambia su fecha ni registra eventos.
- `/eventos` omite validaciones de dominio, estado e idempotencia; solo resuelve cuenta, tipo y referencias públicas existentes. Una referencia es opcional. Para eventos sin entidad con código público, debe omitirse o ser null. Escribir eventos crudos no modifica progresos, diarios, cartas, check-in ni conversaciones.
- Los escenarios E4 y E7 ejecutan antes la ruta de B0; E5 también parte de B0 completado. E5 verifica el 3/8 del logro oculto directamente con `evaluar_regla`, manteniendo el 403 del endpoint de progreso exigido en la sección 6.3. Los resultados esperados de los escenarios no cambian.

## Página opcional de demostración

- `/demo` sirve HTML, CSS y JavaScript locales, sin dependencias nuevas ni servicios externos. El tablero consulta el estado, progreso, eventos y novedades existentes; las acciones usan los mismos endpoints y validaciones de dominio que Swagger. No se usan eventos crudos para avanzar la ruta.
- `/demo/catalogo` es una consulta auxiliar para poblar los formularios: tipos y mínimos de actividades, nombres/familias de carreras, conversaciones y códigos de las cuentas vinculadas. No expone ids, cartas ni datos de insignias ocultas. La disponibilidad y audiencia del tablero siguen viniendo de `/cuentas/{cuenta}/estado`.
- La fecha simulada inicia en `2026-10-01T10:00`, para reproducir el guion. Puede editarse, adelantarse un día o vaciarse para usar la hora actual del backend. No avanza sola ni registra eventos por abrir la página o cambiar de cuenta.
- Las actividades bloqueadas permiten consultar requisitos, incluidos los de su bloque contenedor, y probar explícitamente un intento que debe responder 409. Los formularios permiten reintentos para observar la validación del backend. Los logros ocultos no tienen botón de progreso hasta obtenerse.
- Cada acción muestra eventos y explicaciones agrupadas por cuenta cuando corresponde. El tablero resalta los objetivos recién obtenidos y las actividades que heredan la apertura de su bloque; el historial y las novedades se leen del servidor. Marcar novedades leídas solo afecta a la cuenta seleccionada.
- El reinicio requiere una confirmación dentro de la interfaz que explica qué se borrará de las tres cuentas. Cambiar de cuenta, navegar y actualizar no escriben estado. Durante las escrituras se bloquean nuevos envíos y el selector de cuenta; los textos se insertan con `textContent`.

## Instrumentos

### Fase 1: modelos, semilla y esquema

- `spec-demo-instrumentos.md` amplía el alcance de la primera demo. Se conserva la semántica del motor, todos los elementos anteriores de la semilla y los resultados de E1–E17 para sus actividades originales. Los instrumentos se agregan exclusivamente en LAB.
- Se agregan las 15 tablas de la sección 3.2 y `esquema_version`: 39 tablas en total. Los conteos exactos son 10 bloques, 29 actividades (27 de estudiante y 2 de apoderado), 8 carreras, 47 reglas y 58 condiciones. El usuario confirmó que 27 corresponde al catálogo de estudiante, no al total.
- `esquema_version` tiene una fila, con `id = 1` protegido por restricción SQL, y `version = 2`. Se escribe junto con la semilla, en su misma transacción. No hay migraciones, reparación, carga incremental ni respaldo de la base anterior.
- Antes de `create_all`, el arranque comprueba las bases existentes: deben tener las 39 tablas y exactamente la fila `(1, 2)`. Una base sin tabla de versión, con otra versión, sin fila o con estructura incompleta se conserva sin cambios y provoca: `La base demo.db tiene un esquema anterior. Bórrala y vuelve a iniciar la aplicación.` Una ruta nueva se crea y carga normalmente; un archivo preexistente vacío también se considera incompatible.
- Al terminar la fase y aprobar la suite se elimina la antigua `demo.db` y sus archivos `demo.db-wal` y `demo.db-shm`, si existen, con el servidor detenido. El siguiente arranque crea la base versión 2.
- LAB usa `numero = 0`, porque su código carece de sufijo numérico. No tiene regla de bloque: está disponible desde el inicio para estudiantes. Las nueve actividades conservan títulos, orden y reglas de la sección 4.1.
- Las descripciones y nombres de escalas y aplicaciones que no define el documento son textos simples de demostración. Las dimensiones de habilidades mantienen en nombre y descripción su carácter oficial o provisional. Los enunciados, rejillas y cuatro ítems inversos siguen exactamente la especificación.
- La validación de distribución exige todos los ítems del instrumento exactamente una vez por aplicación, sin faltantes, repeticiones ni ítems ajenos. AUT-01 a AUT-10 son las mismas filas en las dos aplicaciones; su presentación se vincula a cada actividad.
- Se agrega únicamente `openpyxl` mediante `uv add`; su dependencia transitiva es `et-xmlfile`. La lectura usa la primera hoja, modo de solo lectura y valores calculados. Exige las ocho columnas en el orden indicado, códigos y títulos no vacíos, valores numéricos finitos (sin booleanos) y códigos únicos. Solo ignora filas completamente vacías. No se fabrican ocupaciones.
- El Excel incluido tiene 923 ocupaciones, 5538 puntajes y todos los códigos requeridos. CAR-MED usa 29-1216.00; no hizo falta sustitución. Si otro archivo carece de ese código, se toma el primer `29-12` en el orden del archivo y se informa el código seleccionado en el registro de carga; la excepción es únicamente para Medicina.
- `/demo/reiniciar` recrea las 39 tablas y escribe la versión 2. Inicia explícitamente la transacción SQLite antes del DDL para poder restaurar también las tablas y el estado anterior si falla la semilla. Un error del catálogo responde 422 con `detail.mensaje`; no destruye el progreso previo.
- Las pruebas sin Excel usan una fixture automática que omite exclusivamente la carga de ocupaciones, conservando definiciones y carreras; esta excepción solo existe en tests. Las pruebas del catálogo real se omiten con un mensaje claro. La carga de producción continúa exigiendo el archivo. Los archivos sintéticos de las pruebas de validación nunca se cargan en la demo real.

### Adaptaciones autorizadas de tests existentes

- **Conteos y listas de catálogo:** `test_tablas_indices_y_claves_foraneas` agrega las 16 tablas; `test_bloques_y_actividades_segun_especificacion` incorpora LAB y sus nueve actividades; `test_contenido_familias_y_carreras_segun_especificacion` agrega las tres carreras; `test_reglas_completas_segun_especificacion` agrega las cinco reglas y condiciones. Las igualdades siguen siendo exactas y los datos anteriores se contrastan íntegros.
- **Conteos:** `test_reversion_de_accion_incluye_estado_eventos_y_desbloqueos` de `test_motor.py` conserva sus verificaciones de rollback y actualiza únicamente el total de reglas de 42 a 47.
- **Listas y conteos de catálogo:** `test_catalogo_solo_expone_opciones_publicas_sin_logros_ocultos` agrega las tres carreras y actualiza el total de actividades a 29; `test_audiencias_se_conservan_tras_eventos_compartidos` amplía las listas exactas de estudiante con LAB, sin cambiar las de Rosa.
- **E1, catálogo ampliado:** `test_e1_estado_inicial` verifica las 27 actividades de estudiante, filtra las 18 originales y conserva ACT-01 DISPONIBLE y las otras 17 BLOQUEADA. Comprueba por separado los nueve estados de LAB. La lista de Rosa sigue siendo únicamente P1, sin LAB. No se cambia ningún otro resultado de E1–E17.
- `TABLAS_ESTADO` de las pruebas de semilla se amplía con respuestas, resultados, dimensiones de resultados y coincidencias para incluirlas en la comprobación de estado vacío tras reiniciar.
- **Tercera excepción autorizada, aplicada en Instrumentos, fase 3:** se renombra `test_estado_no_expone_en_curso` a `test_estado_expone_en_curso_con_progreso_parcial` y se exige EN_CURSO para actividades disponibles con ese progreso. Se conserva BLOQUEADA cuando falta disponibilidad, incluido el bloqueo del contenedor. No se adapta ningún otro resultado de E1–E17 en esta fase.

### Fase 2: funciones puras de cálculo

- `app/calculo_instrumentos.py` usa exclusivamente la biblioteca estándar. No importa modelos SQLAlchemy, esquemas Pydantic, FastAPI, routers ni la semilla; no lee el Excel, no escribe resultados y no registra eventos. Los datos de entrada y salida se representan con dataclasses inmutables. La conexión con las acciones y la persistencia corresponde a la fase 3.
- El cálculo de un ítem recibe el puntaje de la opción y los límites mínimo y máximo de su escala, nunca el orden de la opción. La inversión usa `maximo + minimo - puntaje`, incluidos los casos con mínimo distinto de cero. El cálculo de dimensión suma los puntajes y los máximos individuales; únicamente el porcentaje se redondea a dos decimales, con `round`.
- Los vectores RIASEC tienen seis valores finitos en el orden R, I, A, S, E, C. Pearson se calcula con `statistics.correlation`, sin redondearlo ni transformar los vectores. Las correlaciones negativas se descartan; cero pertenece a GOOD_FIT y los límites 0.608 y 0.729 se incluyen en GREAT_FIT y BEST_FIT respectivamente.
- El top 10 se ordena por correlación sin redondear, descendente, y código O*NET ascendente para empates exactos. Se asignan posiciones consecutivas desde 1; si hay menos de diez ocupaciones elegibles, se devuelven todas. El título original acompaña cada coincidencia. El redondeo a seis decimales se reservará para las consultas de la fase 4.
- Un vector de estudiante constante devuelve `perfil_plano = True` y ninguna coincidencia, sin iterar el catálogo ni intentar Pearson. Su código de interés sigue calculándose: RIA con empate. `hay_empate` compara exclusivamente las dimensiones tercera y cuarta después de ordenar; un empate entre las dos primeras no lo activa por sí solo.
- Entradas matemáticas inválidas, como puntajes fuera de escala, valores no finitos, vectores con otro tamaño y dimensiones vacías o con máximo no positivo, producen `ValueError`; no se inventan porcentajes ni correlaciones.
- La especificación no define el caso de una ocupación con sus seis puntajes iguales. Se elige el comportamiento más simple: Pearson falla con `ValueError` que identifica el código O*NET, sin omitir silenciosamente esa ocupación. En la fase 3 este fallo revertirá la acción, según 5.2. El Excel actual no contiene ocupaciones de vector constante.
- No se agregan dependencias, tablas ni endpoints y no se modifican los tests anteriores. Las 64 pruebas nuevas de `tests/test_calculo_instrumentos.py` se ejecutan sin sesiones ni catálogo de ocupaciones y mantienen los valores esperados de la sección 9.1.

### Fase 3: respuestas y finalización

- `POST /acciones/responder-items` recibe cuenta, actividad, respuestas con códigos de ítem y orden de opción, y fecha opcional. Devuelve los códigos públicos, `respuestas_guardadas` y `progreso` con estado, respondidos y total. No registra eventos ni evalúa reglas.
- El lote debe ser no vacío, sin ítems repetidos y con opciones enteras estrictas; estas validaciones responden 422. Una opción fuera de la escala también responde 422. Un ítem que no se presenta en la actividad, incluido un código inexistente, responde 409: se interpreta como pertenencia inválida del lote. Una actividad sin ítems responde 409. Cuentas o actividades inexistentes y cuentas de apoderado responden 404 en esta acción.
- Se valida todo el lote antes de escribir. La primera respuesta crea progreso EN_CURSO; reemplazar una respuesta conserva su fila y `creada_en`, y actualiza opción y `actualizada_en`. Todas las respuestas de un envío comparten la fecha local definida por las acciones anteriores. Se cuentan únicamente los ítems presentados en esa actividad y progreso.
- Las respuestas quedan fijas cuando alguna aplicación que incluye la actividad tiene resultado vigente para esa cuenta. Para instrumentos sin dimensiones quedan fijas al completar la actividad. Mientras una aplicación con dimensiones está incompleta, responder una actividad ya completada conserva su progreso COMPLETADA, como establece 5.1.
- Completar con respuestas faltantes devuelve 409 con `detail.mensaje` y `detail.items_faltantes`, en orden de presentación. No crea progreso ni eventos. Completar una actividad de instrumentos como apoderado devuelve 404; las acciones anteriores conservan sus validaciones de audiencia.
- Solo `/acciones/completar-actividad` agrega `resultados_generados`, una lista de códigos de instrumento y aplicación, vacía para actividades sin resultado nuevo. El resto de las respuestas de acciones conserva su estructura. Rehacer una actividad sigue registrando COMPLETA_ACTIVIDAD y no recalcula un resultado vigente.
- `app/resultados_instrumentos.py` reúne respuestas de los progresos completados de cada aplicación y cuenta. Comprueba cobertura exacta de los ítems, pertenencia de escala y dimensión, y toma los límites de las opciones almacenadas. Usa el módulo puro para puntajes, inversión, máximos, porcentajes y coincidencias. No relee el Excel: consulta el catálogo ya cargado en SQLite.
- Los resultados se generan tras los eventos y desbloqueos, dentro de la transacción existente del router. Las funciones de dominio solo usan `flush`; cualquier fallo del cálculo revierte también progreso, eventos, desbloqueos y resultados parciales. Las respuestas guardadas en peticiones anteriores se conservan.
- RIASEC guarda sus seis dimensiones, perfil plano y hasta diez coincidencias con correlaciones sin redondear; inteligencias y habilidades guardan únicamente sus dimensiones. Autopercepción guarda respuestas independientes por progreso de entrada y salida y no genera resultados. Un perfil plano no necesita recorrer ocupaciones, incluso en los tests que cargan definiciones sin Excel.
- `/cuentas/{cuenta}/estado` expone EN_CURSO únicamente si la actividad y su bloque están disponibles. BLOQUEADA conserva prioridad sobre cualquier progreso persistido. Esta ampliación no modifica el motor, la semilla, el esquema versión 2 ni las dependencias.
- I1–I10 se verifican mediante las acciones públicas y el estado existente; las puntuaciones y coincidencias se contrastan directamente en las tablas. Las consultas públicas de resultado, avance, catálogo, respuestas, historial y comparación, así como la derivación de carreras y código de interés al consultar, corresponden a la fase 4. El reinicio por instrumento corresponde a la fase 5.

### Fase 4: consultas públicas

- Las siete consultas de 6.2 se agregan en un router de Instrumentos, con contratos explícitos en `app/esquemas_instrumentos.py` y vistas de lectura en `app/consultas_instrumentos.py`. No importan los routers ni modifican el motor. No se agregan tablas ni dependencias; el esquema sigue en versión 2.
- Donde el documento no fija una estructura JSON, se usan listas ordenadas de instrumentos y aplicaciones, con códigos públicos. El catálogo ordena instrumentos y aplicaciones por código, dimensiones por orden y código, actividades por orden y código, e ítems por orden de presentación y número. Cada escala incluye opciones por orden; cada respuesta incluye el orden, etiqueta y puntaje de la opción elegida y sus fechas.
- Los GET de catálogo e ítems no requieren cuenta ni disponibilidad: permiten presentar definiciones de las actividades bloqueadas. Las actividades de apoderado se rechazan con 404. Una actividad de estudiante existente sin ítems devuelve una lista vacía; su consulta de respuestas devuelve cuenta, actividad y respuestas vacías. Las consultas con cuenta rechazan cuentas inexistentes y apoderados con 404 antes de consultar datos de instrumentos.
- El avance se devuelve por instrumento y aplicación, con `actividades: {completadas, total, faltantes}`, `items: {respondidos, total}` y `hay_resultado_vigente`. Los conteos de respuestas se limitan a la cuenta, las actividades y los ítems del instrumento presentados en esa aplicación. Tener todas las respuestas no completa automáticamente una actividad.
- NO_INICIADO significa que no hay progresos para las actividades de la aplicación. EN_PROGRESO incluye progresos EN_CURSO sin respuestas, como ocurrirá después de reiniciar. Para instrumentos con dimensiones, COMPLETADO exige resultado vigente; los anulados solo cuentan en historial. Para autopercepción, COMPLETADO exige las actividades completadas, sin resultado.
- Una consulta de resultado sin vigente devuelve 409 con `detail: {mensaje, avance}`, incluso para autopercepción. Si hay varias aplicaciones, se exige `aplicacion` y su omisión responde 422; si hay una sola, se usa automáticamente. Una aplicación inexistente o ajena al instrumento responde 404. El historial consulta todas las aplicaciones del instrumento, sin exigir selección.
- El resultado utiliza las dimensiones y coincidencias almacenadas, sin recalcular ni consultar las respuestas actuales. El código de interés se deriva de los puntajes guardados en orden RIASEC. Las carreras se derivan de las relaciones con las ocupaciones del resultado consultado, incluyendo el histórico; se ordenan por mejor posición y código para empates. Cada vía se ordena por posición y conserva exactamente los datos de la coincidencia correspondiente.
- Las correlaciones se redondean a seis decimales únicamente al construir la respuesta JSON; el número no añade ceros finales como texto. El orden y ajuste siguen los valores almacenados sin redondear. RIASEC plano devuelve código RIA con empate y listas vacías. Inteligencias y habilidades omiten `codigo_interes`, `coincidencias` y `carreras_recomendadas`.
- El historial incluye `anulado_en` (null en vigentes) y el contenido íntegro del resultado. Se ordena por fecha de cálculo descendente y por id interno descendente como desempate, sin exponer ese id. Las pruebas preparan anulaciones y copias únicamente en su base temporal; el reinicio público permanece pendiente de fase 5.
- La comparación exige ambas aplicaciones de TEST-AUTO completas; en caso contrario devuelve 409 con el avance de ambas. Cada fila muestra código y enunciado del ítem, opciones de entrada y salida con sus puntajes y diferencia salida menos entrada. No genera ni guarda resultados.
- Se amplían los tests de I1–I10 de instrumentos con afirmaciones sobre los endpoints GET, conservando sus expectativas numéricas y verificaciones de persistencia. No se cambian tests anteriores del motor, los escenarios E1–E17 ni sus resultados esperados. Se agregan pruebas de selección de aplicación, audiencia, referencias, aislamiento, historial, orden y ausencia de escrituras en las 39 tablas.

### Fase 5: reinicio e invariantes

- `POST /acciones/reiniciar-instrumento` utiliza la selección de aplicación de las consultas: con varias aplicaciones su omisión responde 422; una aplicación ajena o inexistente responde 404. La cuenta debe ser estudiante; apoderados, cuentas e instrumentos inexistentes responden 404. No requiere disponibilidad de las actividades para reiniciar sus progresos existentes.
- La respuesta incluye cuenta, instrumento, aplicación, `resultado_anulado` (metadatos de cálculo y anulación, o null), códigos de `actividades_reiniciadas`, eventos y nuevos desbloqueos. Los metadatos no exponen ids; el contenido íntegro del resultado permanece consultable en historial. Las actividades reiniciadas siguen el orden de la aplicación y solo incluyen progresos que ya existían.
- Dentro del `sesion.begin()` existente se anula únicamente el vigente de la cuenta y aplicación, se borran únicamente respuestas de ese instrumento en sus progresos y se pasan esos progresos a EN_CURSO. No se crean progresos para las actividades aún no iniciadas. Resultados anteriores, dimensiones, coincidencias, eventos y desbloqueos se conservan.
- El reinicio con respuestas parciales y sin resultado también está permitido. Sin respuestas del instrumento ni resultado vigente responde 409 con `Nada que reiniciar`, aunque existan progresos EN_CURSO vacíos o resultados anulados. El rechazo no escribe ni registra eventos.
- Se registra REINICIA_INSTRUMENTO con referencia al código del instrumento y la fecha local de la acción; el motor evalúa las reglas normalmente. Ninguna regla de la semilla usa ese evento. Un fallo después de borrar respuestas, cambiar progresos, anular y registrar el evento revierte toda la operación, como las demás acciones.
- El invariante de aplicación completa se comprueba sobre resultados **vigentes**, conforme al plan aprobado. Los anulados siguen existiendo mientras sus progresos se rehacen; no se exige COMPLETADA a sus actividades actuales. Los ciclos de respuesta, finalización y reinicio verifican único vigente, distribución exacta de ítems y correlaciones y ajustes almacenados de todos los resultados, incluidos históricos.
- I11 verifica cadena A, reinicio y cadena B con una fecha de cálculo posterior; I12 reinicia solo salida de autopercepción y conserva entrada; I13 intercala Ana y Luis y comprueba que el reinicio de Ana no afecta ningún dato público de Luis; I14 fuerza un fallo del cálculo al finalizar LAB-RIA4 y conserva respuestas y progreso anterior. I14 usa un perfil plano para ejecutarse también sin Excel.
- Se extiende el auxiliar de cadenas únicamente para aceptar fecha explícita en los tests; los valores y expectativas de I1–I10 permanecen iguales. No se cambian tests anteriores del motor, E1–E17, semilla, dependencias ni esquema versión 2. La interfaz queda para fase 6 y la validación final para fase 7.

### Fase 6: interfaz mínima

- `/demo/instrumentos` sirve HTML, CSS y JavaScript locales, reutilizando los
  estilos de `/demo`, que incorpora un enlace al laboratorio. No se agregan
  dependencias ni consultas auxiliares de backend. El catálogo, los ítems,
  respuestas, resultados, historial y comparación usan los endpoints existentes;
  cuenta, disponibilidad y requisitos se consultan mediante `/cuentas`, `/estado`
  y `/progreso`. Las acciones mantienen sus validaciones y transacciones reales.
- La selección incluye las tres cuentas para poder observar el 404 de Rosa.
  Cambiar a una cuenta sin acceso vacía los paneles y deshabilita acciones;
  respuestas, borradores y cadenas se separan por cuenta y aplicación.
- Los botones de ejemplo y Rellenar formulario solo marcan opciones locales.
  Guardar respuestas envía el formulario actual, incluso parcial; completar es
  otra acción y nunca guarda implícitamente. Guardar disponibles reparte la cadena
  por número de ítem y envía una petición por actividad disponible y editable,
  en secuencia. Usa la cadena elegida, aunque existan borradores anteriores.
  Completar selecciona la siguiente actividad disponible y conserva la cadena.
- Los borradores y cadenas viven únicamente en memoria del navegador. Reiniciar
  con confirmación elimina los de la aplicación reiniciada después de recibir
  éxito; recargar la página recupera respuestas guardadas del servidor. Los
  formularios fijos se deshabilitan; rehacer la actividad sigue disponible.
- Se bloquean botones, selectores, radios y campos durante una operación,
  también al consultar, y una guarda impide envíos simultáneos. El registro
  conserva las últimas 25 respuestas de acciones, consultas de resultados,
  historial y requisitos, y todos los errores. Los textos usan textContent.
- Puntajes, porcentajes, código de interés, empates, carreras y diferencias vienen
  del backend. El navegador solo presenta barras y correlaciones a seis decimales.
  El historial permite desplegar cada resultado y marca los anulados. En móvil,
  las tablas anchas se desplazan dentro de su panel, con acceso por teclado, y hay
  enlaces a preguntas, resultado e historial. La fecha simulada sigue `/demo`.
- No se modifican tests anteriores, el motor, la semilla ni el esquema versión 2.
  La verificación funcional de esta interfaz se realiza en el navegador, además
  de ejecutar la suite completa. La documentación final corresponde a fase 7.

### Ampliación 5.6.1: dimensiones destacadas

- Se incorpora la actualización de `spec-demo-instrumentos.md`: TEST-INT y
  TEST-HAB derivan `dimensiones_destacadas` al consultar resultado vigente e
  historial, incluidos los anulados. No se guarda el campo ni se recalculan
  puntuaciones, respuestas o coincidencias; funciona con bases versión 2 existentes.
- La función pura `calcular_dimensiones_destacadas` compara proporciones con
  `fractions.Fraction`, de la biblioteca estándar, desde puntaje y máximo
  almacenados, sin dividir como float ni utilizar porcentajes redondeados.
  Devuelve los códigos empatados en el orden recibido. Una lista vacía devuelve
  una tupla vacía; puntajes y máximos inválidos usan la validación existente.
  Las consultas presentan objetos con el mismo formato que `dimensiones`.
  Si todas tienen puntaje cero, todas quedan destacadas.
- La interfaz muestra sus nombres y porcentajes en el resultado y al desplegar
  el historial; la selección viene del backend. RIASEC y autopercepción conservan
  sus contratos. No se añaden tablas, versiones ni dependencias.
- Adaptaciones autorizadas por la nueva especificación: I8 e I9 agregan el campo
  a sus listas exactas y comprueban INT-INTRA y HAB-VAL, respectivamente; mantienen
  todas sus puntuaciones anteriores. I8b comprueba INT-ESP e INT-MUS en ese orden
  y conserva su representación histórica tras reiniciar. Se añade el caso de
  inteligencias en cero y cinco casos puros para empates, proporciones diferentes
  que redondean igual, proporciones equivalentes y orden. E1–E17 no se modifican.

## Consultas

### Fase 1: contador y medición inicial

- `tests/soporte_consultas.py` aporta `ContadorConsultas(motor_bd)`, usable con
  `with`, y `MedidorPeticiones`. Las fixtures `contador_consultas` y
  `medidor_peticiones` los hacen disponibles para los tests. El listener usa
  `before_cursor_execute` en el Engine de la prueba, incluyendo las consultas
  del hilo de TestClient. No modifica el motor ni los endpoints.
- Se cuenta cada ejecución SQL observada por ese evento: SELECT, INSERT,
  UPDATE, DELETE y cualquier otra sentencia. Una ejecución executemany suma
  uno, independientemente del número de parámetros; si SQLAlchemy divide la
  operación en varias ejecuciones, todas se cuentan. No se confunde el número
  de filas con el número de sentencias. Los commits de DBAPI no pasan por este
  evento y no se incluyen en este indicador.
- El contador conserva las sentencias y el indicador de lote para diagnosticar
  fallos, sin guardar parámetros. Retira su listener al salir, también ante
  excepciones; reutilizarlo inicia una medición nueva. Los contadores de motores
  distintos son independientes y se permiten contextos separados sobre un
  mismo motor.
- El contexto envuelve únicamente `cliente.request(...)`. El arranque, carga
  de semilla, reinicio y pasos previos del escenario quedan fuera. La medición
  de estado inicial se hace en la primera petición después del arranque, sin
  calentamiento. Las mediciones usan SQLite temporal; no modifican `demo.db`.
- Quedan excluidos de los presupuestos `/demo/reiniciar`, `/eventos`, `/reglas`,
  `/demo/catalogo` y las páginas estáticas. Los demás endpoints normales de
  consultas y acciones sí quedan dentro del alcance aprobado.
- Los escenarios están añadidos al final de `tests/test_consultas.py`; las
  pruebas existentes conservan sus verificaciones. No se fijan como asserts
  los conteos antiguos: los presupuestos se exigirán en las fases de
  optimización. Si falta el Excel, se omiten exclusivamente los dos recorridos
  nuevos que necesitan un RIASEC no plano; la medición de estado, progreso y
  actividades ordinarias sigue ejecutándose.

Para reproducir las mediciones y ver los conteos por tipo de sentencia:

```powershell
uv run pytest -q -s tests/test_consultas.py -k 'contador or medicion_base'
```

Medición inicial con el catálogo real de 923 ocupaciones y 5538 puntajes,
antes de modificar el código de producción:

| Escenario | Ejecuciones SQL iniciales | Presupuesto aprobado, pendiente de exigir |
|---|---:|---:|
| Estado inicial de Ana | 141 | 10 |
| Estado después de ACT-13 | 162 | 10 |
| Progreso de ACT-17, inicial o tras ACT-13 | 17 | 10 |
| Completar ACT-01 por primera vez | 148 | 10 |
| Completar ACT-13 por primera vez | 120 | 10 |
| Responder los 15 ítems de LAB-RIA1 por primera vez | 29 | 10 |
| Volver a enviar las mismas 15 respuestas de LAB-RIA1 | 13 | 10 |
| Completar LAB-RIA4 con cadena B y diez coincidencias | 92 | 20 |
| Resultado vigente de TEST-RIASEC, cadena B | 7 | 7 |
| Responder los 24 ítems de LAB-HAB por primera vez | 38 | 10 |
| Estado tras RIASEC y respuestas de LAB-HAB | 162 | 10 |
| Listar cuentas | 1 | 1 |
| Catálogo de instrumentos | 22 | 10 |
| Ítems de LAB-RIA1 | 63 | 10 |
| Avance de instrumentos, inicial o con resultado | 36 | 10 |
| Respuestas de LAB-RIA1, vacío o con 15 respuestas | 4 | 10 |
| Resultado pendiente de TEST-RIASEC, HTTP 409 | 10 | 10 |
| Ingresar | 3 | 10 |
| Responder registro ADECUADA por primera vez | 6 | 10 |
| Primera entrada libre | 10 | 10 |
| Primer check-in | 8 | 10 |
| Ver CAR-ENF por primera vez | 8 | 10 |
| Publicar entrevista con Ana y Luis | 18 | 10 |
| Resolver CASO-01 con 85 por primera vez | 104 | 12 |
| Primera carta de Ana después de ACT-13 | 14 | 10 |
| Completar CONV-01 desde Ana por primera vez | 21 | 10 |
| Desbloqueos después del recorrido ampliado | 66 | 10 |
| Marcar desbloqueos vistos | 2 | 2 |
| Historial RIASEC con un resultado vigente | 7 | 10 |
| Reiniciar RIASEC con resultado vigente y respuestas | 12 | 12 |
| Comparación de autopercepción completa | 21 | 10 |

- El recorrido principal completa ACT-01 a ACT-13 en orden; el recorrido RIASEC
  prepara esa misma ruta y aplica la cadena B de la especificación. El envío
  repetido de 15 respuestas usa las mismas opciones, por lo que no genera UPDATE.
  Las actualizaciones reales y los lotes mixtos tendrán pruebas adicionales.
- El recorrido ampliado parte de otra base: consulta las vistas iniciales,
  registra ingreso, respuesta reflexiva, entrada libre, check-in, vista de
  carrera y entrevista; completa la ruta, supera CASO-01, escribe la carta de
  Ana y marca CONV-01. Después mide desbloqueos y marcado, completa RIASEC,
  consulta historial, respuestas y avance, lo reinicia y completa ambas
  aplicaciones de autopercepción. Cada petición se mide por separado.
- Los presupuestos son requisitos para las próximas fases, no resultados ya
  alcanzados. Quedan pendientes caché, agregaciones, lecturas y escrituras en
  lote, límites automáticos y pruebas de crecimiento con 100 reglas y 500 eventos.
- Validación al cerrar la fase 1: las seis pruebas nuevas pasan y reproducen
  todos los conteos de la tabla. `uv run pytest -q` devuelve **392 passed**
  (los 386 anteriores más seis nuevos), con el aviso de deprecación de
  Starlette/httpx ya existente. La comprobación aislada con ruta de Excel
  ausente devuelve **4 passed, 2 skipped** entre las pruebas nuevas. No se
  cambian dependencias, esquema, semilla ni código de producción.

### Optimización y presupuestos automáticos

- La aprobación posterior de fase 1 reemplaza los presupuestos principales:
  estado 10, progreso 8, completar sin cálculo 15, completar LAB-RIA4 con RIASEC
  20, responder ítems 10 y resultado de instrumento 10. Las otras rutas normales
  conservan los presupuestos aprobados inicialmente, salvo completar conversación:
  su límite se amplía a 12 por escribir y evaluar en dos cuentas, igual que el
  presupuesto de resolver caso. Las exclusiones y el
  contexto de medición de fase 1 siguen vigentes.
- `app/definiciones.py` carga al arrancar reglas, condiciones y los catálogos
  fijos de contenido e instrumentos. Guarda registros e índices inmutables
  independientes de las sesiones ORM, por Engine. `/demo/reiniciar` publica una
  nueva caché solo tras confirmar el reinicio; un fallo conserva la anterior.
  Cambios de definiciones mediante ORM, incluidas escrituras agrupadas con
  `Session.execute`, reconstruyen la caché después de commit. Rollback no la
  modifica. Esto permite que los tests agreguen reglas y aplicaciones sin
  alterar sus fixtures ni necesitar una petición de calentamiento.
- `app/contexto_consultas.py` conserva los datos dinámicos únicamente durante
  una petición o llamada al núcleo. Carga todos los progresos de una cuenta en
  una consulta y sus desbloqueos en otra. No comparte progreso, respuestas,
  conteos ni desbloqueos entre cuentas o peticiones.
- Los conteos usan una CTE y UNION ALL en una única ejecución SQL: agregados por
  cuenta/tipo y por cuenta/tipo/referencia, con EVENTOS, REFERENCIAS_DISTINTAS y
  DIAS_DISTINTOS. Las referencias nulas no cuentan como objetos distintos. Los
  días distintos totales se calculan directamente, sin sumar los días de las
  referencias. Se conserva la fecha calendario almacenada, sin conversión UTC.
- Disponibilidad, audiencia, bloque contenedor, selección de candidatas y
  evaluación se resuelven en memoria. El estado no necesita leer eventos: sigue
  dependiendo de desbloqueos persistidos, progresos y entradas guiadas. Progreso
  sí evalúa los conteos actuales, aunque todavía no exista desbloqueo. Se
  invalidan conteos y evaluadores cuando se insertan eventos dentro de la acción.
  La diversidad de familias se deriva de las referencias agrupadas y del
  catálogo de carreras, sin una consulta por regla.
- Eventos, desbloqueos y respuestas nuevas se insertan con lotes Core sin pedir
  ids innecesarios. Las respuestas existentes se actualizan con executemany,
  conservando id y `creada_en`, y actualizando opción y `actualizada_en`. Todo el
  envío se valida antes de escribir; el número de respondidos se deriva de los
  ítems existentes y validados. Enviar 1 o 24 respuestas nuevas cuesta 6
  ejecuciones; reemplazar 1 o 24 cuesta 5. Un lote mixto usa como máximo una
  inserción y una actualización agrupadas, independientemente de su tamaño.
- RIASEC lee ocupaciones y todos sus puntajes con una sola consulta outer join;
  conserva las validaciones de catálogo vacío y puntajes faltantes. Reutiliza
  esos ids al guardar coincidencias, sin volver a buscar cada ocupación. Un
  perfil plano no consulta el catálogo. Dimensiones y coincidencias se guardan
  en lote. Si varias aplicaciones terminan juntas, se cargan sus respuestas y
  se guardan sus resultados agrupados, manteniendo la transacción completa y
  los puntos de interceptación de los tests existentes.
- Catálogo e ítems se construyen desde definiciones; avance comparte lecturas
  por cuenta. Historial carga en lote dimensiones, coincidencias y relaciones
  con carreras para todos sus resultados. Comparación lee las respuestas de
  ambas aplicaciones juntas. Las referencias dinámicas de reglas y eventos se
  precargan por tabla, evitando búsquedas por objeto en los bucles.
- Entrevistas y conversaciones cargan las cuentas y sus datos en lotes, insertan
  eventos agrupados y conservan la evaluación individual por cuenta y las
  respuestas agrupadas en el orden original. Marcar vistos sigue usando una
  actualización. Reiniciar instrumento conserva respuestas y resultados
  históricos según el contrato existente.
- No se agregan dependencias, tablas, migraciones ni índices. No se modifican
  los instrumentos, cálculo matemático, semilla, escenarios ni contratos HTTP.

Resultados del mismo recorrido de fase 1, incluyendo lecturas y escrituras:

| Petición o escenario | Antes | Después | Límite exigido |
|---|---:|---:|---:|
| Estado inicial | 141 | 4 | 10 |
| Estado tras ACT-13 o RIASEC | 162 | 4 | 10 |
| Progreso ACT-17, inicial o tras ACT-13 | 17 | 3 | 8 |
| Completar ACT-01 por primera vez | 148 | 7 | 15 |
| Completar ACT-13 por primera vez | 120 | 8 | 15 |
| Completar LAB-RIA4, cadena B y diez coincidencias | 92 | 13 | 20 |
| Responder 1 ítem nuevo de LAB-HAB | 15 | 6 | 10 |
| Responder 15 ítems nuevos de LAB-RIA1 | 29 | 6 | 10 |
| Responder 24 ítems nuevos de LAB-HAB | 38 | 6 | 10 |
| Reenviar las mismas 15 respuestas de LAB-RIA1 | 13 | 5 | 10 |
| Resultado vigente de TEST-RIASEC | 7 | 5 | 10 |
| Listar cuentas | 1 | 1 | 1 |
| Catálogo de instrumentos | 22 | 0 | 10 |
| Ítems de LAB-RIA1 | 63 | 0 | 10 |
| Avance de instrumentos, inicial o con resultado | 36 | 4 | 10 |
| Respuestas de LAB-RIA1, vacío o con 15 respuestas | 4 | 2 | 10 |
| Resultado pendiente de TEST-RIASEC, HTTP 409 | 10 | 5 | 10 |
| Ingresar | 3 | 3 | 10 |
| Responder registro ADECUADA | 6 | 4 | 10 |
| Primera entrada libre | 10 | 6 | 10 |
| Primer check-in | 8 | 6 | 10 |
| Ver CAR-ENF por primera vez | 8 | 4 | 10 |
| Publicar entrevista con Ana y Luis | 18 | 7 | 10 |
| Resolver CASO-01 con 85 por primera vez | 104 | 9 | 12 |
| Primera carta de Ana después de ACT-13 | 14 | 8 | 10 |
| Completar CONV-01 desde Ana por primera vez | 21 | 10 | 12 |
| Desbloqueos del recorrido ampliado | 66 | 2 | 10 |
| Marcar desbloqueos vistos | 2 | 2 | 2 |
| Historial RIASEC con un resultado vigente | 7 | 5 | 10 |
| Reiniciar RIASEC con resultado y respuestas | 12 | 9 | 12 |
| Comparación de autopercepción completa | 21 | 5 | 10 |

La medición de 1 ítem nuevo se reprodujo también con la copia del código
anterior en una base temporal. Los demás valores iniciales son los registrados
en fase 1. Cero consultas en catálogo e ítems significa que sus definiciones ya
se cargaron en el arranque, fuera de la petición.

### SQL de completar ACT-01 y ACT-13

Captura con `before_cursor_execute` del mismo recorrido medido: primera
finalización de ACT-01 y, tras completar ACT-02, ACT-03, ACT-04, ACT-05, ACT-06
y ACT-12, primera finalización de ACT-13. Solo se cuenta la petición; se excluyen
arranque y preparación. Los números indican el orden real de ejecución. Los
parámetros usan `?`, como en SQLite; `AGREGACIÓN` representa la sentencia completa
mostrada después de la tabla.

| N.º | Completar ACT-01: 7 ejecuciones | Completar ACT-13: 8 ejecuciones |
|---|---|---|
| 1 | `SELECT cuenta.id, cuenta.codigo, cuenta.nombre, cuenta.rol FROM cuenta WHERE cuenta.codigo = ?` | `SELECT cuenta.id, cuenta.codigo, cuenta.nombre, cuenta.rol FROM cuenta WHERE cuenta.codigo = ?` |
| 2 | `SELECT progreso_actividad.id, progreso_actividad.cuenta_id, progreso_actividad.actividad_id, progreso_actividad.estado FROM progreso_actividad WHERE progreso_actividad.cuenta_id = ?` | `SELECT desbloqueo.cuenta_id, desbloqueo.regla_id FROM desbloqueo WHERE desbloqueo.cuenta_id IN (?)` |
| 3 | `INSERT INTO progreso_actividad (cuenta_id, actividad_id, estado) VALUES (?, ?, ?)` | `SELECT progreso_actividad.id, progreso_actividad.cuenta_id, progreso_actividad.actividad_id, progreso_actividad.estado FROM progreso_actividad WHERE progreso_actividad.cuenta_id = ?` |
| 4 | `INSERT INTO evento_uso (cuenta_id, tipo, fecha_hora, id_referencia) VALUES (?, ?, ?, ?)` | `INSERT INTO progreso_actividad (cuenta_id, actividad_id, estado) VALUES (?, ?, ?)` |
| 5 | `SELECT desbloqueo.cuenta_id, desbloqueo.regla_id FROM desbloqueo WHERE desbloqueo.cuenta_id IN (?)` | **`AGREGACIÓN` antes de insertar eventos: evita repetir COMPLETA_BLOQUE B3** |
| 6 | `AGREGACIÓN` después de insertar eventos | `INSERT INTO evento_uso (cuenta_id, tipo, fecha_hora, id_referencia) VALUES (?, ?, ?, ?)` (lote de dos eventos) |
| 7 | `INSERT INTO desbloqueo (cuenta_id, regla_id, fecha_hora, visto) VALUES (?, ?, ?, ?)` | `AGREGACIÓN` después de insertar eventos |
| 8 | — | `INSERT INTO desbloqueo (cuenta_id, regla_id, fecha_hora, visto) VALUES (?, ?, ?, ?)` (lote) |

Sentencia `AGREGACIÓN`, idéntica en las tres ejecuciones señaladas:

```sql
WITH eventos_cuenta AS (
    SELECT evento_uso.cuenta_id AS cuenta_id,
           evento_uso.tipo AS tipo,
           evento_uso.id_referencia AS id_referencia,
           evento_uso.fecha_hora AS fecha_hora
    FROM evento_uso
    WHERE evento_uso.cuenta_id IN (?)
)
SELECT eventos_cuenta.cuenta_id, eventos_cuenta.tipo, ? AS referencia,
       count(*) AS count_1,
       count(DISTINCT eventos_cuenta.id_referencia) AS count_2,
       count(DISTINCT date(eventos_cuenta.fecha_hora)) AS count_3
FROM eventos_cuenta
GROUP BY eventos_cuenta.cuenta_id, eventos_cuenta.tipo
UNION ALL
SELECT eventos_cuenta.cuenta_id, eventos_cuenta.tipo,
       eventos_cuenta.id_referencia,
       count(*) AS count_1,
       count(DISTINCT eventos_cuenta.id_referencia) AS count_2,
       count(DISTINCT date(eventos_cuenta.fecha_hora)) AS count_3
FROM eventos_cuenta
WHERE eventos_cuenta.id_referencia IS NOT NULL
GROUP BY eventos_cuenta.cuenta_id, eventos_cuenta.tipo,
         eventos_cuenta.id_referencia
```

La consulta adicional es la ejecución 5 de ACT-13. `completar_progreso` verifica
en memoria que todas las actividades de B3 están completadas; entonces llama a
`existe_evento(..., COMPLETA_BLOQUE, B3)` para conservar la idempotencia del evento
de bloque. Esa comprobación carga los conteos anteriores a la escritura. ACT-01
todavía no completa B0 y omite esa comprobación.

`registrar_eventos` inserta COMPLETA_ACTIVIDAD ACT-13 y COMPLETA_BLOQUE B3 con un
único `executemany`, invalida los conteos y vuelve a agregarlos para evaluar las
reglas con los eventos recién escritos (ejecución 7). Los desbloqueos también
se insertan en lote. La diferencia de una ejecución procede de comprobar el
evento de bloque previo; no de la cantidad de eventos o desbloqueos insertados.
La lectura de desbloqueos ocurre antes en ACT-13 porque su disponibilidad exige
reglas persistidas, pero es una sola lectura en ambos recorridos.

### Pruebas de límites y crecimiento

- `LIMITES_SQL` y una fixture automática en `tests/test_consultas.py` exigen los
  presupuestos al finalizar cada recorrido medido de fase 1. No se editaron los
  cuerpos ni las expectativas de esas pruebas ni de los otros tests anteriores.
- Dos pruebas comparan bases independientes, antes de ACT-01 y antes de ACT-13.
  Una base recibe exactamente 100 reglas sintéticas activas y 500 eventos, con
  referencias repetidas y distintas y fechas compartidas y diferentes. Las
  reglas apuntan a fichas válidas y requieren la actividad bajo prueba. Se
  verifica igualdad exacta del conteo de estado, progreso y finalización, además
  de evaluación única de las 100 reglas y persistencia de sus 100 desbloqueos.
- Responder 1 frente a 24 ítems compara igualdad exacta tanto en inserciones
  como en reemplazos. Se verifican respuestas, opciones, total y fechas. El lote
  mixto verifica validación completa antes de escribir y presupuesto de consultas.
- Las pruebas adicionales verifican igualdad de consultas con 100 fichas más,
  100 ocupaciones más, 20 resultados históricos más, 20 autores frente a 2 y
  6 aplicaciones frente a 1. Los objetos y resultados adicionales se reflejan
  en las respuestas, para impedir que ignorarlos haga pasar la medición.
- Se prueban aislamiento de cachés, reconstrucción tras commit, conservación
  tras rollback y reinicio exitoso o fallido. El primer estado tras reiniciar
  satisface el presupuesto sin una petición de calentamiento.
- Validación: **54 passed** en `tests/test_consultas.py`; con ruta de Excel
  ausente, **50 passed, 4 skipped**, exclusivamente los recorridos no planos
  que requieren ocupaciones. La suite completa devuelve **404 passed**:
  los 392 tests anteriores más 12 nuevos. Sigue el aviso de Starlette/httpx ya
  existente; la ejecución programática sin Excel agrega el aviso de anyio.
- Una comparación adicional de 75 respuestas con el código previo, en bases
  temporales independientes, conserva exactamente JSON y códigos HTTP. Solo se
  normaliza el UUID aleatorio de entrevista. Incluye estados, progreso, errores,
  ruta, casos, diario, familia, coautoría, RIASEC, reinicio, historial y comparación.
  Las huellas de los archivos anteriores confirman que se conservan sin cambios;
  `test_consultas.py` conserva íntegro su contenido anterior y añade las pruebas.

## Configuración de métodos y esquema 3

La auditoría de constantes y los ajustes posteriores aprobados sustituyen las
decisiones anteriores únicamente en los puntos de esta sección. Se mantienen
los catálogos, valores semilla, escenarios, idempotencia y transacciones.

- Las correspondencias entre tipos y modelos, enumerados, estados públicos,
  códigos HTTP y constantes estructurales se conservan.
- `app/configuracion_metodos.py` concentra BEST_FIT 0.729, GREAT_FIT 0.608,
  correlación mínima 0 y top 10 (§5.4 de la especificación de instrumentos),
  longitud 3 del código de interés (§5.6), porcentaje con factor 100 y dos
  decimales (§5.3), correlación pública con seis decimales (§6.2), y transformación
  de opciones O*NET 1–5 a puntajes 0–4 (§4.2). La fuente documentada es la
  especificación del proyecto; no se atribuyen los umbrales a una publicación
  adicional no identificada. Las restricciones SQL de `coincidencia` se
  construyen desde estas mismas constantes, sin duplicar sus números.
- La transformación O*NET solo construye las opciones de la semilla. El cálculo
  usa los puntajes y límites de `opcion_escala`, incluida la inversión; no aplica
  otra transformación a respuestas ni a los valores del archivo de ocupaciones.
- `instrumento.tipo_resultado` usa el enumerado COINCIDENCIAS, DESTACADAS o
  COMPARACION. La semilla asigna COINCIDENCIAS a RIASEC, DESTACADAS a inteligencias
  y habilidades sociales, y COMPARACION a autopercepción. El valor inicial ORM
  para una nueva definición es DESTACADAS; la semilla especifica todos sus tipos.
- `aplicacion.momento` usa UNICA, ENTRADA o SALIDA, con valor inicial ORM UNICA
  para conservar las aplicaciones adicionales creadas por los tests. La semilla
  marca explícitamente entrada y salida de autopercepción. Ambos campos se
  incluyen en `/instrumentos`, desde la caché de definiciones de cada aplicación.
- Generación, avance, bloqueo de respuestas y representación de resultados
  deciden por `tipo_resultado`. Los vectores del estudiante y de las ocupaciones,
  el código de interés y sus desempates usan las dimensiones ordenadas por
  `dimension.orden`, con código como desempate determinista. Se elimina
  `ORDEN_RIASEC` del cálculo. Las llamadas puras existentes sin orden explícito
  conservan compatibilidad mediante la definición canónica de dimensiones en
  `semilla_instrumentos.py`; los endpoints pasan siempre el orden persistido.
- La importación del Excel conserva la validación de su encabezado y relaciona
  cada columna de puntaje con `dimension.codigo`, independientemente del orden
  de las filas o dimensiones de la base. Identifica el instrumento por su tipo
  COINCIDENCIAS. La lectura conjunta de ocupaciones y puntajes se conserva.
- La comparación usa `/cuentas/{cuenta}/instrumentos/{instrumento}/comparacion`.
  Requiere tipo COMPARACION y exactamente una aplicación ENTRADA y una SALIDA;
  se seleccionan por `momento`, nunca por código. Un instrumento de otro tipo
  responde 404; una definición sin ambos momentos o con momentos ambiguos,
  422. Las aplicaciones válidas pendientes conservan el 409 con su avance.
  La URL de TEST-AUTO y sus respuestas existentes siguen funcionando igual.
- `regla_desbloqueo.parametro_evaluador` es entero nullable, nulo inicialmente.
  R-INS-EXPLORADOR guarda 3. El evaluador de familias exige un valor positivo y
  lo lee de la regla en evaluación; no toma `cantidad_minima`, que cuenta eventos.
  Su nombre público y la interfaz de dos argumentos del registro EVALUADORES
  se conservan, incluidos los puntos de interceptación usados por los tests.
  El contexto de petición transporta la regla y reutiliza evaluaciones por
  cuenta, nombre y parámetro; parámetros distintos no comparten el resultado.
  Una llamada directa al evaluador resuelve su única regla de definiciones.
- No se trasladan las definiciones de `semilla_instrumentos.py` ni los ejemplos
  de JavaScript. En la interfaz, características y selección de aplicaciones
  proceden del catálogo. Los códigos TEST-* del JavaScript quedan únicamente
  como claves de los ejemplos conservados. El mínimo mostrado para un caso
  procede del catálogo y se actualiza al cambiar o restaurar la selección.
  El número de cuentas procede de `/cuentas`. La validación de cadenas consulta
  los ítems de la aplicación y verifica cada opción contra su escala, conservando
  las letras de autopercepción según las etiquetas de sus opciones.
- `VERSION_ESQUEMA` pasa a 3. Una base anterior no se migra ni se modifica:
  el arranque la rechaza con el mensaje existente que indica borrarla y volver
  a iniciar. No se borra la `demo.db` del usuario durante esta tarea.

Conteos del esquema, antes y después:

| Elemento | Esquema 2 | Esquema 3 |
|---|---:|---:|
| Tablas | 39 | 39 |
| Columnas de `instrumento` | 4 | 5 |
| Columnas de `aplicacion` | 4 | 5 |
| Columnas de `regla_desbloqueo` | 6 | 7 |
| Instrumentos / aplicaciones / reglas semilla | 4 / 5 / 47 | 4 / 5 / 47 |

En los tests anteriores solo se modifican las tres expectativas de versión
vigente de `tests/test_semilla_instrumentos.py` (líneas 47, 381 y 431): 2 → 3,
y el caso de versión no válida de su parametrización (línea 338): 3 → 4.
Estos cambios fueron autorizados expresamente. Se conservan las pruebas de
rechazo de versión 1 y de versión 2 con tablas faltantes; se agrega una prueba
para rechazar versión 2 con todas las tablas sin modificar el archivo. Los
conteos anteriores de tablas y catálogo no requieren adaptar expectativas.

`tests/test_configuracion_metodos.py` añade nueve pruebas para metadatos,
versión anterior, instrumentos renombrados, momentos independientes del código,
orden de dimensiones, correspondencia del Excel y parámetros del evaluador.
La comparación adicional de 75 respuestas conserva el contrato previo salvo
los campos `tipo_resultado` y `momento` agregados al catálogo. Las comprobaciones
de JavaScript con Node verifican sintaxis, opciones obtenidas de la API,
autopercepción por letras, mínimos de caso distintos y un catálogo de siete
cuentas. Los presupuestos y pruebas de crecimiento de
`tests/test_consultas.py` se mantienen sin cambios.

Validación final: `uv run pytest -q` pasa con 413 tests: los 404 anteriores,
con únicamente las cuatro adaptaciones de versión autorizadas, y los nueve
tests nuevos. Ambas comprobaciones de sintaxis de JavaScript también pasan.

### Arranque local tras actualizar a esquema 3

La base local seguía en versión 2 y el arranque la rechazaba según la política
existente. Se conserva completa como
`demo.esquema-2.20261001-010856.db`; el siguiente arranque crea `demo.db` en
versión 3 con la semilla. El progreso anterior permanece en el respaldo.
No se cambia la validación ni se introduce una migración. Se actualiza la
versión indicada en el README y se comprueba por HTTP que el tablero,
laboratorio, cuentas, catálogo de instrumentos y estado responden 200.
La interfaz muestra el motor conectado y carga RIASEC y la comparación de
autopercepción sin errores de JavaScript. SQLite confirma la integridad de
ambos archivos y `uv run pytest -q` vuelve a pasar con 413 tests.

## Registro

### Fase 1: esquema, semilla, caché y contenido

- `VERSION_ESQUEMA` pasa de 3 a 4: 44 tablas, 11 bloques y 30 actividades.
  Se mantienen las 47 reglas y 58 condiciones existentes. El arranque rechaza
  versiones anteriores sin migrar, reparar ni eliminar la base. Las pruebas
  usan SQLite temporal; esta fase conserva la `demo.db` local y sus respaldos.
- La semilla REG se agrega después de instrumentos y ocupaciones, conservando
  las referencias anteriores. Su bloque usa `numero = 0`, como el laboratorio
  LAB, porque la especificación no asigna un número al laboratorio de registros.
  REG-ACT08 tiene orden 1; los tres ítems y seis criterios reproducen §5.2.
  Los mínimos viven en `item_registro`, no en parámetros de evaluación.
- Se agregan las cinco tablas y `progreso_actividad.posicion` nullable. Los
  enumerados tienen restricciones SQL, al igual que la unicidad de respuesta
  por progreso e ítem, criterio por ítem y código, y la asociación compuesta.
  `intento` admite exclusivamente 1 o 2. `criterios_faltantes` usa JSON no nulo
  y una restricción SQLite que exige un arreglo; la validación de códigos se
  implementará con el evaluador en la fase 2. `latencia_ms` guarda milisegundos
  enteros y admite nulo. `requiere_atencion` y `ampliada` tienen default falso.
- Las definiciones nuevas entran en la caché inmutable por Engine. Sus índices
  agrupan ítems por actividad y criterios por ítem, en orden. C1 y C2 se repiten
  legítimamente entre ítems: la búsqueda de criterio por código usa la clave
  `(item_registro_id, codigo)`, para no mezclar criterios de ítems distintos.
  Respuestas y evaluaciones no se incluyen en la caché.
- El JSON estático es la única fuente de las líneas y momentos de la actividad.
  La validación lee actividad, ítems y asociaciones de forma agrupada, comprueba
  existencia, coincidencia exacta en orden y momentos con ids únicos y no vacíos.
  Referencias repetidas o contenido ausente, ilegible o mal formado se rechazan
  con un mensaje claro. Se valida incluso al arrancar una base ya cargada.
  En el reinicio se valida dentro de la transacción que reemplaza la semilla:
  si falla, se conservan todas las tablas, estado y caché anteriores.
- Las adaptaciones a tests previos se limitan a los catálogos de
  `test_fase1.py`, `test_semilla_instrumentos.py`, `test_demo.py` y
  `test_configuracion_metodos.py`, las listas de audiencia de
  `test_invariantes.py`, los conteos de E1 y las versiones de esquema.
  E1 excluye LAB y REG al seleccionar su lista de actividades originales:
  mantiene las mismas 18 actividades y todos sus estados esperados. Se incluye
  el rechazo de versión 3 y se sustituye la versión futura inválida 4 por 5;
  los rechazos de versiones 1 y 2 se conservan. Las fixtures imponen
  `EVALUADOR=falso` para todas las pruebas.

### Aclaraciones confirmadas antes de implementar

- Gemini será configurable desde la aplicación. No se ejecutarán llamadas
  reales desde la aplicación ni el script salvo petición explícita del usuario.
- El caso 12 del script conserva ADECUADA y usa el texto corregido que incluye
  una situación personal, cumpliendo C2 sin juzgar la opinión sobre la empatía.
- La interfaz puede reutilizar los cinco endpoints existentes enumerados en
  §11, además de los nuevos, sin APIs auxiliares. Se armonizan §10 y §11 con
  estas aclaraciones expresamente autorizadas.
- En fase 3, `actualizada_en` será una marca monotónica de concurrencia; eventos
  y evaluaciones conservarán la fecha simulada. Esta fase solo agrega las
  columnas y no implementa todavía esas acciones.

Cierre de fase 1: `uv run pytest -q` devuelve **454 passed, 1 warning**,
con únicamente el aviso de Starlette/httpx ya existente. E1–E17, I1–I14,
los presupuestos SQL y las pruebas de crecimiento anteriores siguen pasando.
No se agregan dependencias ni se realizan llamadas a Gemini. La cobertura y
los escenarios pendientes se detallan en `docs/validacion.md`, bajo Registro.

### Fase 2: interfaz y evaluación pura

- `app/tipos_registro.py` concentra los tres enumerados de registro, sin
  dependencias de persistencia. `app/models.py` los importa y conserva sus
  nombres públicos, valores y restricciones SQL; no cambia el esquema 4.
- `app/evaluador_respuestas.py` define el protocolo `EvaluadorRespuestas`,
  contexto inmutable con criterios y respuestas anteriores ordenados, y el
  resultado de cuatro campos de §6.6. No importa SQLAlchemy, FastAPI ni modelos
  de persistencia, tampoco lee `.env` ni configura servicios externos.
  La acción de fase 3 construirá ese contexto desde las respuestas FINAL.
- `ResultadoEvaluacion` requiere los cuatro campos, rechaza campos adicionales
  y conversiones de tipos; solo admite ADECUADA y VAGA. La validación común
  comprueba los códigos de criterios y las dos reglas de consistencia de §6.6.
  Revalida incluso una instancia previamente construida o modificada. Conserva
  el orden de los criterios devueltos; no añade reglas de juicio semántico.
- El mínimo usa `len(texto.strip())`, contando caracteres, no bytes. El texto
  original se conserva en el contexto y en `texto_evaluado`. Texto vacío lanza
  `ErrorTextoVacio`, que la futura acción traducirá a 422. Un texto corto no llama
  al evaluador: usa la repregunta persistida, clasifica VAGA y deja los criterios
  faltantes vacíos, pues no se han evaluado. Tampoco atribuye modelo, versión
  de prompt o latencia a esa comprobación local.
- `EvaluadorFalso` guarda cada contexto antes de procesarlo, incluso si falla.
  Si coinciden marcadores, se aplica `[falla]`, luego `[atencion]`, luego `[vaga]`.
  Atención produce ADECUADA sin repregunta; una respuesta vaga usa exactamente
  la fórmula de §6.4 y todos los códigos del contexto en su orden. Esta fórmula
  se conserva aunque la consigna termine ya con signo de interrogación.
- `evaluar_respuesta` devuelve un `EvaluacionProcesada` separado del resultado
  del evaluador, incluyendo origen, NO_EVALUADA si falla, texto y metadatos de
  análisis. Los criterios se representan como tupla en este resultado inmutable;
  la futura persistencia los convertirá a lista JSON. Las transiciones de estado,
  intentos, eventos y escrituras pertenecen a fase 3 y no se implementan aquí.
- La latencia de la llamada se mide con reloj monotónico y se redondea a
  milisegundos enteros. El timeout inicial de 8 segundos se centraliza junto con
  `VERSION_PROMPT_REGISTRO = "v1"` y `MAXIMO_REPREGUNTAS_POR_ITEM = 1`.
  Se capturan `TimeoutError` y resultados que llegan después del máximo, sin
  reintentos. El adaptador Gemini de fase 6 impondrá el límite de espera en la
  llamada de red; este módulo no crea hilos ni intenta cancelar un evaluador.
- Las evaluaciones de origen LLM o FALLO llevan la versión de prompt v1 por
  defecto, también con el falso; el modelo es nulo salvo que el llamador lo
  indique. Los errores guardan una categoría fija (timeout, resultado inválido o
  fallo del evaluador), nunca el mensaje de una excepción externa ni sus datos.
  La serialización de instancias sin validar desactiva avisos que podrían mostrar
  sus valores. La marca de atención se conserva para la acción, que finalizará
  sin mostrarla ni ofrecer repregunta al estudiante según §6.3.

Cierre de fase 2: las 73 pruebas puras pasan y `uv run pytest -q` devuelve
**527 passed, 1 warning** (454 anteriores y 73 nuevas). Se mantienen E1–E17,
I1–I14, R17 y todos los presupuestos SQL y escenarios de crecimiento existentes.
No se modifican expectativas de tests anteriores, dependencias, esquema ni
base local, y no se realizan llamadas a Gemini. Pendiente: fase 3 para acciones,
consultas y persistencia de las evaluaciones.

### Fase 3: acciones, consultas y concurrencia

- Se agregan únicamente los cuatro POST y los tres GET de §7, en el grupo
  Registro. `schemas_registro.py` separa la información del estudiante de la
  auditoría de demo: los contratos públicos no contienen clasificación, criterios
  faltantes, atención, primer envío ni marcas internas de concurrencia.
- Las acciones nuevas y las consultas por cuenta devuelven 404 para apoderados,
  cuentas inexistentes y actividades inexistentes o de apoderado. Se mantiene la
  decisión de instrumentos para las acciones nuevas; la acción antigua
  `/acciones/responder-registro` conserva íntegramente su contrato. La falta de
  disponibilidad o un ítem ajeno devuelve 409, sin escrituras. Las consultas
  permiten leer actividades bloqueadas, como las consultas anteriores.
- Los ítems públicos se obtienen de la caché, en orden de presentación y sin
  criterios. Una actividad de estudiante sin ítems de registro devuelve una lista
  vacía. El registro inicial devuelve `posicion: null`, `estado: null` y
  `respuestas: []`; no crea progreso. Las respuestas guardadas se devuelven en
  orden de ítems. Los códigos y campos del historial técnico son públicos,
  excluyendo ids internos; su orden es el de inserción, aunque se repita o
  retroceda la fecha simulada.
- La validación del JSON devuelve también un mapa de posiciones por actividad,
  almacenado al arrancar y sustituido solo tras un reinicio válido. No se relee
  ni se consulta la base para validar una posición en cada petición. La función
  `validar_contenido_registro` conserva su resultado de momentos en tupla.
- Guardar posición, borrador o un primer envío crea progreso EN_CURSO si falta.
  No cambia un progreso COMPLETADA existente. La posición se valida contra los
  ids del JSON y un valor desconocido devuelve 422. Los borradores admiten texto
  vacío: reemplazan el texto sin evaluación y conservan el estado y la repregunta
  si hay ampliación pendiente. Borrador de una respuesta FINAL devuelve 409.
- El primer envío fija texto original y clasificación; el segundo conserva ambos,
  marca ampliación y siempre finaliza. Su evaluación sigue en el historial para
  análisis, incluida la repregunta que haya devuelto el evaluador, pero no se
  ofrece otra repregunta al estudiante. Finalizar o editar oculta la repregunta
  pública. Editar FINAL no evalúa ni registra eventos. Todo envío, incluso una
  edición FINAL, rechaza texto vacío con 422 antes de escribir.
- Continuar sin ampliar exige PENDIENTE_AMPLIACION. Para estados ausente,
  BORRADOR o FINAL se elige el rechazo 409, pues no hay una ampliación pendiente
  que continuar. La transición válida conserva texto, primer envío, clasificación
  y evaluaciones; finaliza con `ampliada = false`, sin eventos.
- `enviar` controla tres fases desde el núcleo: una sesión/transacción corta
  valida y toma una lectura inmutable; se cierra completamente antes de llamar
  al evaluador; una sesión/transacción nueva revalida y guarda. Cada fase crea su
  propio `ContextoConsultas`, sin reutilizar entidades ORM, conteos, progresos ni
  desbloqueos anteriores. El contexto del evaluador solo contiene título,
  consigna, criterios ordenados, texto y respuestas FINAL de otros ítems de la
  misma cuenta/actividad, con sus consignas.
- `actualizada_en` usa UTC sin zona, separada de la fecha simulada. Cada escritura
  toma el mayor valor entre el reloj actual y la marca anterior más un microsegundo.
  Así se detectan borradores iguales y envíos con la misma fecha, incluso si el
  reloj no avanza. `creada_en`, eventos y evaluaciones usan la fecha de la acción.
- La tercera fase comprueba id, estado y marca de la respuesta, incluyendo la
  ausencia inicial. Las actualizaciones también usan una condición SQL sobre
  id, estado y marca para proteger el intervalo entre relectura y escritura.
  La unicidad cubre inserciones simultáneas de progreso o respuesta. Conflictos y
  bloqueos de escritores SQLite devuelven 409 y descartan la evaluación realizada.
  Respuesta, evaluación, eventos y desbloqueos se confirman juntos o se revierten
  íntegramente; un fallo SQL no se trata como fallo del evaluador.
- Se reutiliza `responder_con_eventos` para RESPUESTA_REFLEXIVA con referencia
  nula: primer envío ADECUADA o cualquier segundo envío. Guardar borrador,
  posición, continuar y editar no registran eventos. No se cambia `motor.py`,
  semilla, reglas ni contratos anteriores. La validación de completar y R11/R12
  se implementarán en fase 4.
- La aplicación tiene un `EvaluadorFalso` por instancia, sustituible por otro
  falso en pruebas. No configura servicios externos ni interpreta `.env` todavía:
  esa configuración y Gemini pertenecen a fase 6. Las fixtures siguen imponiendo
  `EVALUADOR=falso`; no hay llamadas de red ni dependencias nuevas.

Cierre de fase 3: `uv run pytest -q` devuelve **610 passed, 1 warning**
(527 anteriores y 83 nuevas pruebas de acciones, consultas y persistencia).
Pasan R1–R10 y R13–R16 junto con R17, E1–E17, I1–I14 y las comprobaciones SQL
anteriores. Permanece el aviso previo de Starlette/httpx. No se cambia la base
local ni se ejecuta Gemini. El trabajo se detiene aquí; sigue fase 4 para exigir
los ítems obligatorios FINAL antes de completar y cubrir R11/R12.

### Fase 4: finalización e integración con el motor

- `/acciones/completar-actividad` conserva su contrato y agrega la validación
  de §6.8 antes de crear/modificar progreso o registrar eventos. Los ítems de
  registro se toman del índice ordenado de la caché y se filtran por
  `obligatorio`. Una lectura agrupada obtiene los ítems FINAL del progreso de
  esa cuenta y actividad; los ausentes, BORRADOR y PENDIENTE_AMPLIACION faltan.
  Si hay faltantes, se devuelve 409 con sus códigos en orden de presentación,
  sin escrituras. No se consulta el historial ni se llama al evaluador.
- La condición es exclusivamente el estado FINAL. NO_EVALUADA, atención,
  continuar sin ampliar y una ampliación fallida permiten completar si todos
  los obligatorios finalizaron. No se exige ADECUADA ni un evento reflexivo por
  ítem. Los opcionales pueden estar ausentes, en borrador o pendientes; una
  actividad con todos sus ítems opcionales se puede completar sin respuestas.
- Una cuenta apoderada que intenta completar una actividad con ítems de
  registro recibe 404, como la validación existente de instrumentos. La
  disponibilidad y el tratamiento de las actividades sin ítems de registro
  permanecen intactos, incluidas las actividades REGISTRO originales sin
  asociaciones nuevas. No se modifica la semilla ni se amplían los contratos
  antiguos para aceptar clasificaciones nuevas.
- Tras validar se reutiliza el flujo vigente: COMPLETA_ACTIVIDAD en cada
  finalización y COMPLETA_BLOQUE(REG) solo la primera vez. Rehacer no elimina
  posición, respuestas ni evaluaciones. Editar FINAL después de completar
  conserva clasificación inicial y primer envío, y no agrega evaluaciones ni
  RESPUESTA_REFLEXIVA.
- R12 verifica los eventos de referencia nula implementados en fase 3: los
  tres primeros envíos adecuados registran tres RESPUESTA_REFLEXIVA y el
  tercero obtiene LOG-PENSADOR. La regla R-LOG-PENSADOR y su condición de tres
  eventos no cambian; completar o rehacer no vuelve a otorgar el logro.
- Las variantes de obligatoriedad, orden y asociación de ítems se prueban
  únicamente en bases SQLite temporales. No se cambian datos semilla ni
  expectativas de los tests anteriores. Siguen pendientes para fase 5 los
  presupuestos nuevos y las mediciones de crecimiento; esta fase utiliza
  lecturas agrupadas y no añade consultas SQL dentro de bucles.

Cierre de fase 4: `uv run pytest -q` devuelve **629 passed, 1 warning**
(610 anteriores y 19 nuevas pruebas). Pasan R1–R17, incluidos R11/R12, E1–E17,
I1–I14 y las comprobaciones SQL anteriores. Permanece el aviso previo de
Starlette/httpx. No se modifica la base local ni se ejecuta Gemini. El trabajo
se detiene aquí; sigue fase 5 para presupuestos SQL nuevos y crecimiento.

### Fase 5: presupuestos SQL y crecimiento

- Se amplía `LIMITES_SQL` en `tests/test_consultas.py` con los límites de §8:
  posición 4, borrador 6, envío 12, continuar 8, ítems 1, estado del registro 4
  y completar REG-ACT08 15. No se cambian límites, mediciones ni expectativas
  anteriores. Las nuevas mediciones reutilizan el contador por Engine y la
  fixture que exige el presupuesto al terminar cada prueba.
- §8 no fija un límite para el GET técnico de evaluaciones. Para incluir también
  esta petición nueva se adopta 4, como el estado del registro; se observan
  2 consultas tanto con historial vacío como con tres y seis evaluaciones.
  Este es un presupuesto adicional de la demo, separado de los siete valores
  especificados. No se añade ninguna API.
- Cada medición cuenta toda la petición HTTP. Preparar respuestas, progreso,
  eventos o definiciones se hace antes de iniciar el contador. Enviar conserva
  un único contador durante ambas transacciones, sin reiniciarlo entre fases.
  Una prueba observa desde el propio falso que el pool está libre y el contador
  no cambia al evaluar; verifica que se incluyen la lectura inicial, la relectura
  y la inserción de la evaluación de la tercera fase.
- Se prueban primer envío sin progreso, con progreso sin respuesta, con borrador
  y segundo envío. Los orígenes cubiertos son mínimo, LLM adecuado/vago/atención
  y FALLO por excepción, timeout o resultado inconsistente. También se mide
  edición FINAL, continuación tras mínimo o LLM, creación/reemplazo de borrador,
  posición nueva/existente/completada, consultas en todos los estados, completar
  rechazado y finalización inicial/repetida. No se evalúa fuera del falso.
- El crecimiento compara dos SQLite temporales con la misma preparación de
  registro. La ampliada tiene 100 reglas adicionales activadas por
  RESPUESTA_REFLEXIVA (referencia nula, EVENTOS ≥3, objetivo FIC-PROFESIONES) y
  500 eventos reflexivos extra de la misma cuenta, distribuidos en siete días.
  Ambas bases reciben dos reflexiones de preparación para que un envío nuevo
  obtenga LOG-PENSADOR en la normal y también los 100 desbloqueos en la ampliada;
  así se compara la misma rama de escritura en lote, con distinto volumen.
- La confirmación de las definiciones reconstruye la caché antes de medir;
  la primera consulta posterior ya se cuenta, sin calentamiento. Se exige
  igualdad de consultas para el estado antes y después del envío, y para el
  envío completo en ocho casos: primera respuesta, reemplazo de borrador,
  ampliación, mínimo, VAGA, fallo, atención y edición FINAL.
- En las ramas reflexivas se verifica que las 100 reglas se evalúan exactamente
  una vez, devuelven condiciones cumplidas y sus 100 desbloqueos se persisten
  mediante una sola inserción en lote. Las ramas sin evento reflexivo no las
  evalúan ni otorgan. No se altera la regla ni la semilla originales.
- Las implementaciones de fases 3 y 4 ya cumplen estos presupuestos con caché,
  consultas agrupadas y escrituras en lote. Esta fase agrega comprobaciones y
  documentación; no cambia código de aplicación, motor, instrumentos, contratos,
  dependencias o base local. Gemini y la interfaz siguen pendientes.

Cierre de fase 5: las 58 mediciones y variantes de crecimiento focalizadas
pasan, junto con la prueba específica del contador. `uv run pytest -q` devuelve
**688 passed, 1 warning** (629 anteriores y 59 nuevas). Pasa toda la cobertura
E1–E17, I1–I14 y R1–R17, los presupuestos anteriores y los nuevos, y los escenarios
de crecimiento. Permanece únicamente el aviso previo de Starlette/httpx.
El trabajo se detiene aquí. Sigue fase 6: adaptador Gemini y script con pruebas
simuladas, avisando antes de agregar las dependencias permitidas; la ejecución
real y su reporte quedan pendientes de petición explícita.

### Fase 6: configuración, adaptador Gemini y prueba manual

- Se avisó antes de incorporar `google-genai` y `python-dotenv` mediante
  `uv add`; `uv.lock` conserva las versiones resueltas (2.26.0 y 1.2.4).
  No se añaden dependencias fuera de las autorizadas.
- La configuración se lee durante el ciclo de vida de la aplicación, desde
  `.env` en la raíz. Las variables del proceso prevalecen; no se modifica el
  entorno ni se interpolan referencias `${...}`. El proveedor predeterminado
  es falso. La clave solo se conserva cuando se selecciona Gemini y se excluye
  de la representación de la configuración. Clave ausente, proveedor inválido,
  modelo vacío o timeout no positivo/finito impiden arrancar con mensajes fijos,
  antes de crear tablas. `.env.example` contiene únicamente una clave vacía.
- `EvaluadorGemini` recibe un cliente inyectable. El cliente propio usa la API
  de Gemini (`vertexai=False`), timeout HTTP en milisegundos y
  `HttpRetryOptions(attempts=1)`: un intento total, sin reintentos del SDK.
  También se desactiva la ejecución automática de funciones y se pide un
  único candidato. No se hacen peticiones al construir el adaptador.
- Se conserva literalmente la instrucción de sistema v1 de §6.6. El cuerpo
  contiene solo los cinco campos del contexto puro de §6.5, serializados como
  JSON; la consigna y los criterios provienen de las definiciones oficiales.
  La salida usa el esquema del modelo público del evaluador, con los cuatro
  campos obligatorios, tipos estrictos y rechazo de campos adicionales. Se
  validan nuevamente los códigos y la consistencia mediante la función pura
  existente. No se agrega un juicio semántico ni un validador adicional de
  longitud de la repregunta: la instrucción v1 ya fija su máximo de 30 palabras.
- Temperatura 0.2 se conserva según la especificación. Para el modelo por
  defecto se fija `thinking_level=minimal`, compatible según la
  [guía oficial de Gemini 3](https://ai.google.dev/gemini-api/docs/gemini-3).
  Se reconocen también los modelos 3 Flash (minimal), 3 Pro (low) y 2.5
  Flash/Flash-Lite (presupuesto 0), y 2.5 Pro (128), conforme a la
  [documentación de razonamiento](https://ai.google.dev/gemini-api/docs/generate-content/thinking).
  Un nombre desconocido omite el ajuste de razonamiento; no se adivinan sus
  capacidades ni se consulta un catálogo remoto al arrancar.
- El adaptador mide la latencia en almacenamiento local por hilo para evitar
  mezclar llamadas simultáneas. La latencia que se persiste sigue midiéndose
  en el procesador puro compartido, abarcando llamada y validación. El router
  pasa modelo y timeout configurados a ese procesador; el falso conserva modelo
  nulo. Mínimo de caracteres y edición FINAL continúan sin llamada al proveedor.
- Los timeouts de transporte y HTTP 408/504 se traducen a TimeoutError seguro.
  Salidas inválidas y otros errores externos se convierten en excepciones propias
  con mensajes fijos y sin mostrar la causa. El procesador los registra como
  FALLO/NO_EVALUADA y deja continuar al estudiante. Se filtran mensajes de
  Google/httpx/httpcore que contengan la clave o su forma codificada, retirando
  también argumentos y traceback del mensaje. No se usa el accesor `.text`
  del SDK, que puede emitir avisos con partes no textuales; se extrae solo
  texto no marcado como pensamiento. El cliente propio se cierra al detener
  la aplicación, incluso si falla el arranque; el cliente inyectado pertenece
  al llamador.
- `scripts/evaluar_gemini.py` es un comando manual sin llamadas al importar o
  mostrar ayuda. Prepara contexto con una SQLite en memoria, sembrando solo
  definiciones REG, y cierra todas sus conexiones antes de evaluar. No usa
  la base local ni necesita el Excel de ocupaciones. Para comprobar §10 envía
  los 14 textos al LLM, incluso los que no alcanzarían el mínimo en la aplicación:
  se usa mínimo 0 exclusivamente en este script. Las respuestas previas son
  los casos 2 y 6 y el caso 12 tiene el texto corregido aprobado, ADECUADA.
- Como §10 no fija la pausa, se adopta 5 segundos entre casos, configurable
  mediante `--pausa` según la cuota de la cuenta, sin esperas después del último
  ni reintentos. El reporte añade origen y error saneado a las columnas pedidas,
  escapa contenido para Markdown y omite cualquier reproducción de la clave.
  Los errores no interrumpen los otros casos. El CLI solo muestra mensajes
  propios seguros, nunca mensajes de excepciones externas.
- La fixture general mantiene `EVALUADOR=falso`. Las pruebas específicas del
  adaptador inyectan clientes simulados; una prueba del SDK usa exclusivamente
  `httpx.MockTransport` para verificar que 429 produce una sola petición.
  El bloqueo de sockets externos permite únicamente el socketpair interno de
  asyncio en Windows. Los reportes simulados se escriben en directorios temporales;
  no se genera `docs/evaluacion_gemini.md` ni se afirma calidad real del modelo.
  No cambian motor, semilla anterior, instrumentos, contratos ni presupuestos SQL.

La ejecución real del script y la revisión de su reporte quedan pendientes de
petición explícita. Sigue fase 7 para `/demo/registro`; la consolidación de cierre
corresponde a fase 8.

Cierre de fase 6: `uv run pytest -q` devuelve **747 passed, 2 warnings**
en 506.40 segundos: las 688 pruebas anteriores y 59 nuevas. Pasan E1–E17,
I1–I14, R1–R17, presupuestos SQL y crecimiento. Se conserva el aviso previo
de Starlette/httpx y se añade la deprecación interna del SDK de Google en
Python 3.14. `uv lock --check` confirma la coherencia del bloqueo de dependencias.
La base local conserva su fecha de modificación y no existe reporte real.
El trabajo se detiene aquí, sin ejecutar la API de Gemini ni comenzar fase 7.

### Fase 7: interfaz de registro con Lumi

- Se agrega únicamente la página HTML `/demo/registro`, fuera de OpenAPI,
  junto con `registro.css` y `registro.js`, servidos por el montaje estático
  existente. `/demo` incorpora un enlace. Se reutilizan colores, tipografías,
  componentes y reglas de foco de `demo.css`; no se cambian instrumentos,
  motor, modelos, semilla, contratos, dependencias ni presupuestos SQL.
- La página obtiene las líneas de Lumi, momentos y orden de ítems de
  `REG-ACT08.json`. Los nombres y consignas vienen de `items-registro` y el
  título/disponibilidad del mapa de estado. No duplica las líneas ni los
  criterios del contenido en JavaScript. Los tres íconos son SVG locales;
  Lumi se identifica mediante su nombre y una chispa decorativa en CSS.
- Solo se usan las cuatro acciones y tres consultas de §7, el JSON estático
  y los cinco endpoints anteriores autorizados en §11. No se incorpora un
  catálogo ni una API auxiliar para la interfaz. La lectura de estado y
  novedades se agrupa con la del registro después de las acciones; marcar
  novedades vistas exige su botón, nunca se realiza al cargar o recargar.
- La posición recuperable es la del servidor. Sin posición se muestra la
  explicación; Continuar guarda el momento de tipo registro y volver a Lumi
  guarda el momento de tipo diálogo. No se escribe progreso al abrir la página.
  Se muestran los estados Vacío, Borrador, Pendiente de ampliar y Listo con
  texto además de color, botones nativos y `aria-pressed` para el ítem elegido.
- La URL conserva únicamente cuenta, ítem seleccionado y fecha simulada.
  Como no se define persistencia de estos selectores, se elige la URL para
  recuperar la cuenta correcta al recargar sin compartir un selector global
  mediante localStorage. La fecha inicial coincide con la demo existente;
  vaciarla omite `fecha_hora` en las acciones que la admiten.
- Los textos modificados antes de guardar quedan en un Map en memoria:
  cambiar de ítem o pulsar Actualizar los conserva; recargar o cambiar de
  cuenta los descarta. Esto se indica con “Cambios sin guardar” y en README.
  No hay guardado automático ni respuestas en URL o almacenamiento del navegador.
  Al cambiar de cuenta se borra inmediatamente texto, repregunta, novedades
  y detalle técnico, antes de hacer nuevas lecturas. Rosa no tiene formulario
  ni consulta del registro o de evaluaciones de un estudiante.
- El primer envío muestra una única repregunta si está pendiente. Un borrador
  de ampliación conserva ese estado y pregunta; ampliar o continuar retira los
  controles de repregunta cuando el servidor devuelve FINAL. En FINAL se usa
  Guardar cambios y se deshabilita Guardar borrador. La interfaz no clasifica
  respuestas, no aplica el mínimo por su cuenta ni muestra atención o fallos
  del evaluador al estudiante; el backend conserva toda esa semántica.
- Durante una operación se deshabilitan cuenta, fecha y controles de escritura.
  Enviar muestra “Lumi está leyendo tu respuesta…” con indicador de espera;
  editar FINAL muestra guardado, ya que no vuelve a evaluar. Completar se
  habilita solo cuando los obligatorios están FINAL. Una actividad completada
  conserva edición y ofrece Volver a completar mediante la misma acción existente.
- Un 409 no reenvía automáticamente: se relee el servidor y se conserva el
  texto local para revisarlo. Si el POST se confirmó y falla una lectura posterior,
  se informa que la respuesta quedó guardada y se permite Actualizar. Si falla
  la carga inicial, Actualizar vuelve a obtener las definiciones y la cuenta;
  no queda deshabilitado por la ausencia de cuentas.
- Detalle técnico se carga solo al desplegarlo; muestra origen, clasificación,
  criterios faltantes, latencia, modelo, prompt e intento. Su petición tiene
  una generación de cuenta y un número de consulta: se descartan resultados
  tardíos al cambiar de cuenta, cerrar el panel o pedir una lectura nueva.
  El contenido dinámico se inserta con `textContent`, no con HTML de la respuesta.
- Se comprobaron Edge/Chromium en escritorio 1440×1000 y emulación táctil
  móvil 390/360×844, con Node y Playwright disponibles en el entorno. No se
  incorporan estas herramientas a las dependencias de la aplicación.
  `tests/servidor_registro_ui.py` fuerza el falso y crea una SQLite temporal;
  `tests/validar_registro_ui.cjs` recorre el flujo y genera evidencias. Son
  herramientas opcionales, separadas de pytest; el script de navegador reinicia
  exclusivamente esa demo descartable. No se modifica `demo.db`.
- Las capturas y comprobaciones están en `docs/evidencias/registro`. La espera,
  el 409 y los errores de lectura de la comprobación del navegador se simulan
  mediante interceptación; la concurrencia real del backend sigue cubierta en
  R14/R15. No se atribuyen latencias, completitud semántica ni detección de riesgo
  a Gemini real a partir de estas evidencias.

La interfaz termina en esta fase; la consolidación de cobertura y documentación
corresponde a fase 8. La ejecución real y su reporte Gemini siguen pendientes
de una petición explícita.

Cierre de fase 7: `uv run pytest -q` devuelve **748 passed, 2 warnings**
en 649.36 segundos: las 747 pruebas anteriores y una nueva comprobación de
la página y sus recursos. Se conservan E1–E17, I1–I14, R1–R17 y los presupuestos
SQL. Los dos avisos son las deprecaciones conocidas de Starlette/httpx y del SDK
de Google en Python 3.14. El recorrido visual con evaluador falso termina sin
errores JavaScript en escritorio y móvil emulado. Se detiene aquí, antes de fase 8.

### Fase 8: documentación y cierre

- Se consolida la cobertura vigente de E1–E17, I1–I14, R1–R17, fronteras,
  concurrencia, reversión, caché y restricciones en `docs/validacion.md`.
  Se conserva el historial por fase y se identifica el conteo antiguo de 188
  pruebas como resultado de su etapa, para no confundirlo con la suite actual.
- Se reúne la tabla de presupuestos SQL con los máximos observados de fase 5,
  distinguiendo el límite adicional de auditoría de los siete especificados.
  El envío conserva el contador conjunto de sus dos transacciones y la igualdad
  de consultas con 100 reglas reflexivas y 500 eventos. No se cambian tests.
- README declara las ocho fases de registro, actualiza la cobertura y documenta
  los dos modos de uso: servidor habitual con base compatible y visualización
  independiente con `tests/servidor_registro_ui.py` en el puerto 8787.
- Para la petición de abrir la demo se elige esa sesión temporal ya disponible:
  fuerza `falso`, conserva respuestas mientras está activa y elimina su base al
  detenerla. Evita reemplazar la base local anterior para una visualización.
  No se cambia `.env`, no se migran ni borran datos locales y no se agrega API.
  La página abre con Lumi y registro vacío para que el usuario recorra el plan.
- Se consolidan las capturas y el recorrido de escritorio/móvil emulado de fase 7;
  los errores de red/409 allí son simulados y se distinguen de las pruebas de
  concurrencia del backend. No se presenta la emulación como un dispositivo real.
- La fase no modifica código de aplicación, semilla, motor, instrumentos,
  contratos, dependencias ni expectativas de escenarios. `uv lock --check`
  confirma coherencia de las dependencias existentes. Se ejecuta nuevamente
  `uv run pytest -q` como comprobación obligatoria de cierre.
- La ejecución real de Gemini y su reporte continúan pendientes de petición
  explícita. Los resultados con falso y clientes simulados no certifican la
  calidad de repreguntas, clasificación semántica, detección de atención ni
  latencias/cuotas reales. No se considera ese pendiente como trabajo realizado.

Cierre de fase 8: `uv run pytest -q` devuelve **748 passed, 2 warnings**
en 532.26 segundos, con los mismos avisos conocidos de Starlette/httpx y del SDK
de Google en Python 3.14. Pasan E1–E17, I1–I14, R1–R17, presupuestos SQL y
crecimiento. `uv lock --check` pasa. `demo.db` conserva 602112 bytes y su fecha
anterior; no existe `docs/evaluacion_gemini.md`. La demo de registro se abrió
en el navegador de Codex y se deja su servidor temporal activo en el puerto 8787.
Terminan las ocho fases de implementación; la evaluación real y su reporte
siguen pendientes exclusivamente de una petición explícita.

### Soporte posterior: arranque para probar Gemini

- Ante la petición del usuario tras configurar su clave se comprueba sin mostrar
  secretos que `.env` todavía seleccionaba `falso`, `demo.db` conservaba esquema 3
  y el servidor existente del puerto 8000 no exponía los endpoints de registro.
  Estos son bloqueos distintos; no se atribuye el arranque a una petición al modelo.
- Se cambia únicamente `EVALUADOR` a `gemini`, conservando los otros valores de
  `.env`. Se inicia una instancia de la fábrica existente en el puerto 8788 con
  `demo_registro_gemini.db`, una SQLite independiente y persistente, ignorada por
  Git. El archivo anterior y la sesión con falso permanecen intactos.
- Se verifica el arranque completo, GET 200 de la página, ruta de envío presente,
  ítems disponibles, esquema 4 y cero evaluaciones al comprobar la nueva base.
  La demo se abre para que el usuario haga sus envíos. No se modifica código de
  aplicación ni se ejecuta una evaluación real o el script de 14 casos como parte
  de este diagnóstico. La validez de la clave frente al proveedor solo se podrá
  comprobar con una petición real.
- README añade el comando reproducible con base independiente y distingue el
  servidor del puerto 8787, que fuerza el falso, del configurado desde `.env`.

### Soporte posterior: renovación de la base habitual

- El usuario confirma el rechazo de esquema al ejecutar
  `uv run uvicorn app.main:app --reload`. La instancia independiente del puerto
  8788 no cambia qué base usa ese comando: continúa abriendo `demo.db`.
- Para corregir ese arranque se detienen las instancias anteriores del puerto
  8000 y su proceso hijo, identificado como propietario del archivo bloqueado.
  Las sesiones independientes de registro se conservan.
- Con el archivo liberado y sin auxiliares WAL/journal, se renombra la base
  anterior a `demo.esquema3.respaldo.20261001-113605.db`, dentro del proyecto.
  Se compara SHA-256 antes y después para comprobar que el respaldo conserva
  íntegramente sus bytes. No se elimina ni migra la base anterior.
- Se crea `demo.db` mediante el ciclo de vida habitual y la semilla de esquema 4.
  Se comprueban versión, integridad SQLite, proveedor Gemini y cero evaluaciones;
  solo se realizan lecturas HTTP. La recreación inicia un progreso nuevo.
- El comando exacto del usuario se ejecuta y llega a `Application startup
  complete` en el puerto 8000. La página responde 200 y OpenAPI incluye las rutas
  de registro. No cambia código, dependencias ni contratos; ninguna evaluación
  real forma parte de esta corrección.

### Soporte posterior: conexión a Gemini desde el servidor

- El usuario comunica FALLO/NO_EVALUADA en su primer envío, con latencia de
  212 ms. El mensaje genérico no revela causas externas para proteger secretos.
  El servidor había sido iniciado en el entorno de ejecución restringido.
- Una prueba HTTPS a la raíz pública de `generativelanguage.googleapis.com`,
  sin clave ni texto de estudiante, reproduce `ConnectError` causado por
  `PermissionError`, errno 13 / WinError 10013. La misma prueba fuera del
  entorno restringido establece HTTPS y recibe 404 de la ruta raíz. Este 404
  no es un rechazo del modelo: la prueba no consulta modelos ni genera contenido.
- Se reinicia únicamente el servidor del puerto 8000 fuera de ese entorno,
  manteniendo escucha en 127.0.0.1, configuración y base. El arranque termina
  correctamente. No se cambia el evaluador ni se modifica la evaluación fallida;
  esta sigue en el historial y su respuesta FINAL conserva el contrato de edición.
- Para comprobar un nuevo envío real se debe usar otro ítem todavía sin FINAL
  u otra cuenta. Editar el ítem fallido no vuelve a evaluar. No se reinicia la
  demo ni se altera la auditoría para forzar un reintento; no se ejecuta el script
  de 14 casos como parte del diagnóstico. El acceso al proveedor y su resultado
  se comprobarán con el siguiente envío del usuario.

### Soporte posterior: diagnóstico real autorizado

- Tras otro FALLO/NO_EVALUADA de Luis (1429 ms), el usuario autoriza explícitamente
  una única llamada de diagnóstico con texto inventado. Se usa el contexto del
  caso 6 y el adaptador de aplicación, con los mismos parámetros, timeout y un
  intento total. Las definiciones se preparan en memoria y se cierran antes de
  llamar; no se abre ni modifica la base de la demo.
- Un cliente delegado captura únicamente código HTTP, tipo de excepción y
  etiquetas de una lista fija, sin imprimir mensajes, URL, cabeceras, detalles
  externos o clave. La llamada devuelve HTTP 503, `ServerError`, en 2049 ms.
  No hay resultado válido. Este es el fallo observado en la prueba diagnóstica;
  la evaluación histórica del estudiante conserva su mensaje genérico y no
  permite atribuirle retrospectivamente un código HTTP concreto.
- La [guía oficial de diagnóstico](https://ai.google.dev/gemini-api/docs/troubleshooting)
  identifica 503 UNAVAILABLE entre los errores transitorios. La conexión llega
  al servicio, superando el bloqueo local previo; esta respuesta no certifica
  una evaluación exitosa ni la calidad del modelo.
- Se consume exactamente la llamada autorizada: no se reintenta, no se cambia
  modelo/clave, no se alteran respuestas o auditoría ni se ejecutan los 14 casos.
  El reporte `docs/evaluacion_gemini.md` sigue pendiente. Para una futura prueba
  manual se requiere un ítem sin FINAL o una ampliación pendiente; editar FINAL
  sigue sin evaluar. El servidor y la configuración permanecen listos para usar.

### Registro: reinicio desde la interfaz

- El usuario pide una opción para limpiar las respuestas y probar desde cero.
  Se reutiliza `POST /demo/reiniciar`, ya existente, con su alcance completo:
  restablece la semilla y borra el progreso de todas las cuentas, incluidos
  registro e instrumentos. Esta petición autoriza usar ese endpoint adicional
  desde `/demo/registro`, ampliando la lista de §11 sin añadir una API ni cambiar
  la semántica del motor o del reinicio.
- El botón junto a Actualizar abre una confirmación que explica qué se borra;
  el foco inicial está en Conservar progreso. Cancelar o Escape conservan los
  textos locales y los datos guardados. Los controles quedan deshabilitados
  mientras se ejecuta el reinicio.
- Solo después de confirmar el POST se descartan los buffers del editor,
  la repregunta, los íconos anteriores y la auditoría, invalidando las lecturas
  técnicas pendientes. Se vuelve a cargar el contenido y la explicación de Lumi,
  conservando cuenta y fecha. La configuración y el evaluador del servidor no
  cambian; reiniciar no llama a Gemini. Una respuesta nueva puede usar intento 1.
- Si falla el POST se conserva la vista; si el POST terminó y falla la lectura
  posterior se comunica que el reinicio ocurrió y se permite recuperar con
  Actualizar. No se afirma que el reinicio falló tras haberse confirmado.
- Se comprueba el borrado de borradores, pendientes, finales, posición,
  evaluaciones y eventos de Ana y Luis en SQLite temporal con evaluador falso.
  La prueba visual usa otra base descartable, verifica cancelación, espera,
  retorno a Lumi, plan vacío y el diálogo en escritorio y a 360 px. Las bases
  persistentes del usuario no se reinician durante esta comprobación.

Resultado de esta ampliación: `uv run pytest -q` devuelve **749 passed,
2 warnings** en 604.23 segundos, con los dos avisos de deprecación conocidos.
`node --check app/static/registro.js` pasa. Se conserva el pendiente de la
evaluación real de los 14 casos; este reinicio no realiza llamadas externas.

## Registro v2

### Alcance confirmado y diferencias respecto de v1

- El usuario reemplaza la especificación por v2 y confirma las diferencias
  detectadas antes de modificar código. Se conservan REG, REG-ACT08, los tres
  ítems, sus seis criterios, mínimos y textos; también el JSON, su validación
  al arrancar/reiniciar y la caché inmutable. Motor, instrumentos, escenarios
  E1–E17 e I1–I14 y `/acciones/responder-registro` conservan sus contratos.
- La respuesta dejará de ampliarse sobrescribiendo el texto: v2 separa
  `texto_inicial` de hasta dos `turno_seguimiento`. Los turnos guardan pregunta,
  criterios objetivo, respuesta o borrador, fechas y orden. La clasificación
  inicial y las evaluaciones históricas seguirán siendo inmutables.
- V2 exige llamar primero al evaluador para todo envío no vacío, y evaluar la
  conversación al responder los turnos del LLM. La longitud será exclusivamente
  el respaldo ante fallo, timeout o resultado inválido: R4, R5, R5b, R5c y R11
  cambian según §6.3. Responder el turno genérico del respaldo no reevaluará.
- Se confirma la corrección de §6.7: fase 2 llama al evaluador y aplica respaldo
  solo ante fallo. El caso real 7 mantiene «Voy a practicar hablando más.» y
  C2 faltante; el 16 ahora usa «Voy a esforzarme más.», con C1 y C2 faltantes.
  Su incorporación al script corresponde a la fase 6; no se ejecuta Gemini real.
- Se reemplazarán los contratos del laboratorio de registro por conversaciones,
  responder-seguimiento y continuar-sin-responder, preservando el contrato previo
  del motor. La interfaz mostrará un hilo con campos nuevos por turno en fase 7.
  El reinicio global autorizado anteriormente se conserva y borrará también turnos.

### Fase 1: estructura, semilla, caché y contenido

- El esquema sigue en versión 4, tal como especifica v2, con 45 tablas.
  `item_registro.repregunta_minima` pasa a `repregunta_generica`.
  `respuesta_registro` tiene `texto_inicial` y elimina `texto` y
  `texto_primer_envio`. La auditoría pasa de `intento`/`repregunta` a
  `numero`/`pregunta_generada`. No se conservan columnas duplicadas ni alias ORM de v1.
- `turno_seguimiento` tiene FK a la respuesta, orden restringido a 1 o 2,
  unicidad por respuesta/orden y JSON obligatorio de tipo lista para criterios
  objetivo. Respuesta y fecha de respuesta son nullable para una pregunta sin
  responder o un borrador. Las evaluaciones admiten números enteros positivos,
  incluido 3, sin el límite anterior de dos evaluaciones.
- Los enumerados contienen BORRADOR/PENDIENTE_SEGUIMIENTO/FINAL y
  LLM/RESPALDO_LONGITUD, sin los valores antiguos. Se adaptan las referencias
  internas y las expectativas estructurales de tests a esos nombres.
- La caché carga `repregunta_generica` desde la misma semilla y mantiene sus
  agrupaciones, invalidación por commit y conservación por rollback. Los turnos
  son datos de cada respuesta, no definiciones: no entran en la caché fija.
- Como v1 y v2 comparten versión 4 pero tienen estructuras incompatibles, el
  arranque comprueba también los nombres de columnas antes de crear tablas o
  cargar la semilla. Una base v1 se rechaza sin modificar sus bytes. Se conservan
  los rechazos de versiones 1–3 y de la futura 5. No hay migración o borrado
  automático: para renovar una demo persistente se necesitará respaldo previo
  y recreación explícita. En esta fase solo se usan SQLite temporales.
- Las acciones y consultas existentes reciben únicamente la adaptación de
  nombres necesaria para ejecutar la suite con el nuevo esquema. Su flujo
  todavía caracteriza v1 (una ampliación y longitud previa al evaluador): las
  transiciones, conservación del texto inicial durante seguimiento y contratos
  públicos v2 corresponden a fases 2–3. La auditoría pública sigue exponiendo
  `intento`/`repregunta` hasta fase 3. El prompt v1 y el script de 14 casos
  permanecen hasta adaptar el evaluador y la integración en sus respectivas fases.
  Esta entrega de estructura no habilita aún el recorrido de usuario de v2.
- Los tests anteriores de registro conservan las comprobaciones de flujo v1
  hasta su reemplazo autorizado en fases 2–3. El primer texto enviado se
  comprueba ahora leyendo `texto_evaluado` de la primera evaluación inmutable,
  en lugar de la columna duplicada eliminada. Los tests estructurales sí exigen
  columnas, enumerados, turnos y numeración v2; no se omiten escenarios ni se
  reducen presupuestos SQL. Los conteos autorizados pasan de 44 a 45 tablas.
- Se añaden pruebas de persistencia de preguntas, borradores y turnos respondidos,
  unicidad, claves foráneas, órdenes inválidos, JSON no-lista, número 3 válido,
  números no positivos/no enteros inválidos, rechazo de cuatro variantes de
  estructura v1 con etiqueta 4, y limpieza de turnos al reiniciar con caché nueva.

Pendiente tras fase 1: evaluación pura v2 (fase 2), acciones/conversaciones y
escenarios v2 (fase 3), finalización y eventos, SQL, adaptador/prompt/script v2,
interfaz de conversación y cierre. Las llamadas reales siguen requiriendo
petición explícita.

Resultado de fase 1 de Registro v2: `uv run pytest -q` devuelve **764 passed,
2 warnings** en 593.76 segundos. Se conserva E1–E17, I1–I14 y los presupuestos
vigentes. El único fallo de la primera ejecución completa era una escritura
de la prueba de concurrencia a la columna eliminada `texto`; se adapta a
`texto_inicial`, manteniendo la exigencia de 409 y descarte total de la evaluación.
La prueba focalizada pasa y la segunda suite completa queda sin fallos.
Los dos avisos son las deprecaciones conocidas de Starlette/httpx y Google
en Python 3.14. `node --check` pasa para el JavaScript de registro y su script
de validación visual; no se atribuye esa comprobación sintáctica a una validación
visual del flujo v2. Se termina únicamente la fase 1.

### Fase 2: evaluación pura de conversaciones y respaldo

- `ContextoEvaluacion` contiene exclusivamente título, consigna, criterios en
  orden, criterios faltantes previos, conversación del ítem y conversaciones
  FINAL de otros ítems con su consigna. `ConversacionEvaluacion` separa
  `texto_inicial` de los pares pregunta/respuesta de `TurnoEvaluacion`; no incluye
  ids, cuentas ni fechas. Las acciones reconstruirán estas conversaciones desde
  la base en fase 3. El resultado estricto sustituye `repregunta` por `pregunta`.
- El núcleo `evaluar_respuesta` llama una vez al evaluador para todo texto actual
  no vacío, incluso si no alcanza el mínimo. Ante fallo, timeout o resultado
  inválido, solo un envío inicial corto produce VAGA, la pregunta genérica y
  todos los códigos de criterios del ítem. Un inicial que alcanza el mínimo o
  cualquier respuesta de seguimiento con fallo produce NO_EVALUADA, sin pregunta.
  No hay reintentos y se conservan modelo, prompt, latencia y un error saneado
  también en el respaldo del texto corto. Vacío sigue rechazándose sin evaluar.
- La comparación de longitud utiliza `strip()` y cuenta caracteres Unicode de
  Python; alcanzar exactamente el mínimo evita la pregunta genérica ante fallo.
  Un resultado que llega exactamente al timeout configurado es válido; uno
  posterior se descarta. El adaptador conserva su timeout de transporte.
- `EvaluadorFalso` decide por la respuesta más reciente: marcas en el inicial o
  en turnos anteriores no vuelven a activarse. `[vaga]` conserva los faltantes
  previos; `[falta:C2]` admite varios códigos separados por comas o marcas
  repetidas, conserva su orden y elimina repeticiones. `[falla]` tiene prioridad
  sobre otras marcas; `[atencion]` produce ADECUADA y ninguna pregunta, como antes.
- La validación exige códigos existentes y un subconjunto de los faltantes
  previos. Rechaza códigos duplicados en una salida externa, pues son una lista
  de criterios, no menciones repetidas. Mantiene ADECUADA sin faltantes y VAGA
  con pregunta y faltantes no vacíos, salvo la excepción de atención de §6.6.
  Los errores externos nunca se conservan literalmente en el resultado procesado.
- `texto_evaluado` del núcleo es JSON de la conversación completa, con las
  claves `texto_inicial` y `turnos` (pregunta/respuesta), en el orden recibido.
  Conserva espacios, saltos de línea y Unicode de los textos originales; es la
  misma conversación que se incluye en el contenido enviado al adaptador. Las
  consultas públicas todavía no cambian su contrato en esta fase.
- `VERSION_PROMPT_REGISTRO` pasa a v2 y
  `MAXIMO_SEGUIMIENTOS_POR_ITEM` a 2. Se alinea la instrucción de sistema con
  §6.6 y el adaptador existente recibe el nuevo contexto y esquema `pregunta`,
  para evitar etiquetar como v2 una instrucción v1. No se cambian dependencias,
  parámetros del SDK ni política de llamadas. El script recibe la adaptación
  mínima del constructor y resultado; sus 14 casos se conservan hasta agregar
  las conversaciones 15–16 y el reporte de turnos en fase 6.
- Se aísla una adaptación temporal explícita en
  `app/evaluacion_registro_anterior.py`: únicamente las acciones pendientes de
  reemplazo en fase 3 siguen usando el corte previo por longitud y el texto de
  auditoría de v1. Permite mantener sus escenarios de caracterización sin
  mezclar esa lógica con el núcleo v2. Se eliminará al conectar las acciones
  nuevas; esta fase no habilita aún «evaluador primero» en el recorrido HTTP.
  Se adaptan solamente los nombres del resultado, contexto, pregunta del falso
  y versión del prompt en esas pruebas; los escenarios de acciones no se
  presentan como aceptación de R4/R5/R5b/R5c/R11 v2 todavía.

Pendiente tras fase 2: conectar el núcleo a las acciones y persistir los turnos
con conversaciones completas, incluido aceptar el turno genérico sin otra
evaluación (fase 3); finalización, SQL, script de 16 casos, interfaz y cierre.
Se conservan las bases persistentes y no se ejecutan llamadas reales a Gemini.

Resultado de fase 2 de Registro v2: `uv run pytest -q` devuelve **836 passed,
2 warnings** en 552.67 segundos, frente a las 764 pruebas de fase 1. La comprobación
focalizada previa obtuvo 459 passed, 2 warnings; las comprobaciones adicionales
posteriores también pasan en la suite completa. Se conservan E1–E17, I1–I14,
el contrato anterior del motor y los presupuestos SQL vigentes. Los avisos siguen
siendo las deprecaciones conocidas de Starlette/httpx y Google en Python 3.14.
No se verifica visualmente una interfaz v2 todavía pendiente. Se termina únicamente
la fase 2.

### Fase 3: acciones y consultas de conversaciones

- Se elimina `evaluacion_registro_anterior.py` y se conecta directamente el
  núcleo v2 a los envíos iniciales y seguimientos del LLM. Todo envío inicial
  no vacío llega al evaluador; la longitud solo decide el respaldo ante fallo.
  Responder el turno genérico, continuar y editar un FINAL no llaman al evaluador.
- `enviar` acepta respuestas inexistentes, BORRADOR o edición de texto inicial
  en FINAL. En PENDIENTE_SEGUIMIENTO responde 409 y dirige a
  `responder-seguimiento`, evitando sobrescribir el texto inicial. El seguimiento
  responde el turno pendiente; si sigue VAGA puede crear el segundo, pero nunca
  un tercero. El contador de evaluaciones es 1 para el inicial y 2/3 para los
  turnos evaluados; el turno genérico no agrega evaluación.
- Se agregan `/acciones/registro/responder-seguimiento` y
  `/acciones/registro/continuar-sin-responder`. El endpoint de laboratorio
  `continuar-sin-ampliar` se sustituye por el contrato v2, sin alias. El contrato
  anterior `/acciones/responder-registro` del motor se conserva.
- En un FINAL, `responder-seguimiento` exige `orden` (1 o 2) de un turno ya
  respondido. Falta de orden, tipo no entero, límites inválidos u orden indicado
  mientras está pendiente reciben 422; un turno que no existe o no se respondió
  recibe 409. En ausencia de respuesta o en BORRADOR también recibe 409.
  Texto vacío recibe 422 sin escrituras ni evaluación en ambos endpoints.
- Los borradores iniciales reemplazan `texto_inicial`; con seguimiento pendiente
  solo reemplazan `turno_seguimiento.respuesta`, sin `respondido_en`. Ambos
  avanzan `actualizada_en`. El envío del turno reemplaza ese borrador y guarda
  la fecha simulada de respuesta. Las ediciones en FINAL conservan pregunta,
  criterios objetivo, fechas originales, clasificación inicial y evaluaciones;
  solo cambian el texto editado y la marca monotónica de concurrencia.
- Las acciones y consultas devuelven `conversacion`, nunca clasificación,
  criterios objetivo, origen o atención. El inicial es `{tipo: respuesta, texto}`;
  las preguntas llevan `orden`. Para identificar y retomar respuestas de turnos,
  esas respuestas también llevan `orden` y `borrador`: true si aún no se enviaron,
  false si están respondidas. El estado BORRADOR identifica el inicial sin añadir
  esa marca. Se conserva un borrador vacío como mensaje con texto vacío.
  La auditoría de demo expone ahora `numero` y `pregunta_generada`, sin ids internos.
- El contexto incluye todos los turnos de los otros ítems FINAL. Si se continuó
  sin contestar, se conserva esa pregunta con respuesta nula; no se inventa una
  respuesta ni se envían borradores. `TurnoEvaluacion.respuesta` admite nulo para
  representar ese caso. El texto actual de una evaluación siempre debe existir
  y no estar vacío. En un seguimiento enviado, el nuevo texto reemplaza el
  borrador en el contexto sin modificar aún la base.
- Continuar conserva la pregunta sin responder y descarta su borrador, pues no
  se envió. Conserva los turnos ya respondidos y `ampliada`; registra reflexión
  al finalizar si la clasificación inicial fue ADECUADA o hubo un turno enviado.
  Editar y repetir una finalización no agregan eventos. El rechazo y la escritura
  condicional de estado impiden duplicar la reflexión de una misma respuesta.
- Una lectura agrupada por actividad obtiene progreso, respuestas, turnos y
  origen de la evaluación inicial. No hay SQL dentro de bucles. Cada envío tiene
  lectura y validación, evaluación sin sesión/conexión y nueva transacción para
  revalidar disponibilidad y comparar id/estado/`actualizada_en`. La escritura
  vuelve a comprobar esa marca mediante UPDATE condicional. Un conflicto 409
  descarta la evaluación, y cualquier error SQL revierte respuesta, turnos,
  auditoría, eventos y desbloqueos. Cada transacción reconstruye su contexto de
  consultas para no reutilizar conteos anteriores a la evaluación.
- Se reemplazan los escenarios v1 autorizados por R1–R13, R13d y R14–R16 v2.
  Las comprobaciones existentes de completar, SQL y recursos adaptan solo los
  contratos de registro y sus preparaciones: para provocar respaldo corto se usa
  `[falla]`, para un seguimiento evaluado se usa `[vaga]`. No se cambian E1–E17,
  I1–I14 ni presupuestos SQL. Los casos adicionales de turnos, errores y
  concurrencia se agrupan en `tests/test_registro_v2.py`.

Pendiente tras fase 3: revisión de finalización e integración (fase 4), ampliar
la tabla de presupuestos para seguimiento y su cobertura de crecimiento (fase 5),
script de 16 casos (fase 6), conversación visual (fase 7) y cierre. La página
actual todavía usa contratos v1 y no representa el recorrido de conversaciones.
No se recrean bases persistentes, no se agregan dependencias ni se llama a Gemini real.

Resultado de fase 3 de Registro v2: `uv run pytest -q` devuelve **875 passed,
2 warnings** en 1155.83 segundos. La suite pasa de 836 a 875 pruebas, manteniendo
E1–E17, I1–I14 y los presupuestos SQL vigentes. Las comprobaciones focalizadas
previas obtuvieron 345 passed, 2 warnings (registro, consultas, recursos y
Gemini simulado) y 170 passed, 1 warning (casos adicionales v2 y núcleo puro).
No hubo fallos en estas ejecuciones. Los dos avisos de la suite completa son las
deprecaciones conocidas de Starlette/httpx y Google en Python 3.14. Las bases
persistentes conservan su tamaño y fecha de modificación. Se termina únicamente
la fase 3; no se considera validada una interfaz de conversaciones aún pendiente.

### Fase 4: finalización e integración con el motor

- Se conserva la implementación existente de `completar_actividad`: ya cumple
  la sección 6.8 de v2. Solo exige FINAL para los ítems obligatorios, devuelve
  los faltantes en orden y rechaza con 409 antes de escribir progreso o eventos.
  No exige ADECUADA ni vuelve a evaluar la conversación. Las actividades sin
  ítems de registro y los instrumentos conservan su comportamiento.
- Se conserva también la integración de las acciones v2 con el motor: una
  transición a FINAL genera RESPUESTA_REFLEXIVA si el inicial fue ADECUADO o
  se envió algún seguimiento. El evento usa referencia nula y la regla original
  R-LOG-PENSADOR, sin reglas nuevas. El seguimiento genérico cuenta como turno
  enviado aunque no tenga una segunda evaluación; un seguimiento todavía
  pendiente no genera la reflexión. Rehacer y editar no la duplican.
- Rehacer registra COMPLETA_ACTIVIDAD y conserva posición, textos iniciales,
  preguntas, respuestas enviadas, preguntas omitidas, clasificación inicial,
  `ampliada` y evaluaciones. COMPLETA_BLOQUE(REG) se registra una sola vez.
  Después se pueden editar el inicial y los turnos respondidos sin evaluar ni
  generar eventos nuevos; la auditoría original permanece intacta.
- Las pruebas de R13b y R13c existentes siguen válidas. Se amplían en
  `tests/test_registro_finalizacion_v2.py` con borrador inicial, pregunta genérica,
  primer y segundo seguimiento pendientes con borradores; todos rechazan
  completar sin escrituras y permiten completar al finalizar el ítem faltante.
  También cubren FINAL después del segundo turno VAGO, fallido o con atención,
  y continuar omitiendo ese turno después de haber respondido el primero.
- La integración comprueba LOG-PENSADOR mediante seguimientos genéricos y del
  LLM falso, incluyendo dos turnos. Verifica tres eventos de referencia nula,
  un único desbloqueo y las definiciones originales intactas. Rehacer conserva
  conversaciones con turnos respondidos y omitidos; la edición posterior del
  inicial y de ambos turnos conserva fechas, criterios y auditoría. Un fallo SQL
  después de insertar el lote de eventos revierte progreso y eventos y mantiene
  intactas todas las conversaciones; el intento siguiente completa normalmente.

No se modifica código de producción en esta fase: se conserva lo implementado
que sigue siendo válido en v2 y se comprueba su integración con los turnos.
No se agregan dependencias ni se ejecuta Gemini real, y las bases persistentes
del usuario se conservan. La siguiente fase es la ampliación de presupuestos SQL
y pruebas de crecimiento; después quedan el script, la interfaz y el cierre.

Resultado de fase 4 de Registro v2: `uv run pytest -q` devuelve **886 passed,
2 warnings** en 1135.36 segundos (18:55), frente a las 875 pruebas de fase 3.
La comprobación focalizada obtuvo 29 passed, 150 deselected, 1 warning en 62.02
segundos. Se conservan E1–E17, I1–I14 y los presupuestos SQL vigentes, incluido
completar registro con un máximo de 15 consultas. Los dos avisos de la suite
completa son las deprecaciones conocidas de Starlette/httpx y Google en Python
3.14. Se termina únicamente la fase 4; la siguiente es la fase 5 de SQL.

### Fase 5: presupuestos SQL y crecimiento de los seguimientos

- Se agrega `responder_seguimiento_registro: 12` a `LIMITES_SQL` y se retira la
  asignación provisional de los seguimientos al presupuesto `enviar_registro`.
  Todos los límites anteriores se conservan: posición 4, borrador 6, envío 12,
  continuar 8, ítems 1, estado 4 y completar REG-ACT08 15. La consulta de auditoría
  mantiene su límite anterior de 4.
- La medición rodea la petición HTTP completa: suma ambas transacciones y sus
  escrituras, también para responder un turno. Se extiende la comprobación del
  contador al inicial y a los turnos 1 y 2: dos lecturas de cuenta y dos lecturas
  agrupadas de respuestas. Dentro del evaluador no hay conexión tomada ni SQL.
  La preparación de datos y las verificaciones posteriores quedan fuera del contador.
- Los casos de límites incluyen respuesta breve ADECUADA por el falso, borrador
  de ambos turnos, seguimiento genérico sin reevaluación y edición de ambos turnos
  FINAL. Se miden los turnos 1 y 2 con respuestas adecuadas, vagas, atención, fallo,
  timeout y salida inválida, incluyendo otras dos conversaciones FINAL con dos
  turnos y un borrador que se reemplaza al enviar. Continuar tras responder el
  primer turno se mide descartando el borrador del segundo y registrando reflexión.
- El estado se mide también con el primer o segundo turno pendiente y borrador,
  y con los tres ítems FINAL (o la actividad COMPLETADA), dos turnos por ítem y
  sus evaluaciones. La lectura sigue agrupada y no depende de cuántos turnos haya.
  Se miden igualmente las nueve evaluaciones del recorrido completo, completar
  y rehacer después de dos turnos por ítem, y el 409 con el segundo turno pendiente.
- Se amplía la prueba de crecimiento de 8 a 19 recorridos. Compara dos bases
  SQLite temporales, una con 100 reglas adicionales activadas por
  RESPUESTA_REFLEXIVA y 500 eventos extra. Incluye nuevos turnos pendientes,
  finalización del segundo turno aunque siga VAGA, fallos/timeout/salida inválida,
  atención, turno genérico y edición de los turnos 1 y 2. Los recorridos nuevos
  incluyen otras dos conversaciones FINAL con dos turnos cada una.
- Se exige igualdad exacta de cantidad y distribución por tipo SQL, tanto al
  enviar/responder como al consultar el estado antes y después. Las peticiones
  medidas no vuelven a consultar definiciones de reglas o condiciones. Cuando
  hay reflexión se evalúan las 100 reglas sintéticas una vez cada una y sus
  desbloqueos se insertan en un único lote; sin reflexión no se evalúan ni se
  desbloquean. Se comprueba además que el turno genérico y las ediciones no llaman
  al evaluador. Las reglas sintéticas solo existen en las bases temporales.

No hace falta modificar código de producción: las lecturas agrupadas, la caché
y las inserciones en lote ya satisfacen los presupuestos v2. No se cambian los
escenarios del motor/instrumentos, el contenido, las reglas de producción ni las
bases persistentes; se usa siempre el evaluador falso. Quedan el adaptador/script
de 16 casos (fase 6, con cliente simulado y sin ejecución real autorizada en esta
entrega), la interfaz de conversaciones y el cierre.

Resultado de fase 5 de Registro v2: `uv run pytest -q` devuelve **930 passed,
2 warnings** en 1303.33 segundos (21:43). Son 44 casos más que los 886 de fase 4.
Las comprobaciones focalizadas obtuvieron 80 passed, 73 deselected, 1 warning
en 203.06 segundos; 19 passed, 1 warning en 39.75 segundos; y 10 passed,
147 deselected, 1 warning en 23.82 segundos. Los máximos observados son 11
consultas para enviar/responder seguimiento, 2 para estado y auditoría, y 8
para completar; todos quedan dentro de sus presupuestos. Se conservan E1–E17,
I1–I14 y los contratos anteriores. Los avisos son las deprecaciones conocidas
de Starlette/httpx y Google en Python 3.14. Se termina únicamente la fase 5.

### Fase 6: adaptador y script de conversaciones

- Se conserva el adaptador ya compatible con v2: prompt v2, conversación completa,
  JSON estructurado estricto, temperatura 0.2, timeout, latencia por llamada y un
  solo intento. Los criterios faltantes no pueden volver a incluir un criterio
  satisfecho en una evaluación anterior. Los errores externos se traducen a
  mensajes fijos, sin clave ni detalles del proveedor. No cambian configuración,
  dependencias, modelos, contratos HTTP ni lógica de evaluación/respaldo.
- El script pasa de 14 a 16 casos. Conserva los textos de los primeros 14,
  incluido el caso 12 corregido, y la expectativa del caso 7 (solo C2 faltante).
  Agrega el inicial y respuesta al turno 1 del caso 15; el caso 16 inicia con
  «Voy a esforzarme más.», sin C1 ni C2, y responde «No sé, más seguido.».
  Las otras respuestas FINAL siguen siendo las de los casos 2 y 6.
- Los casos se preparan con mínimo de caracteres y `repregunta_generica` de la
  semilla oficial. Se retira el mínimo artificial de cero del script v1: siempre
  se evalúa primero el inicial, pero ante fallo/timeout se aplica el mismo respaldo
  por longitud de la aplicación. No se abre ninguna base persistente ni se guarda
  respuesta, turno, evaluación o evento. La base en memoria se cierra antes de la
  primera llamada, y no se emite SQL durante ninguna evaluación.
- En los casos 15 y 16 se usa la pregunta realmente recibida, la respuesta fija
  especificada y los criterios aún faltantes para evaluar la conversación completa.
  Si el inicial finaliza, el seguimiento se registra como no ejecutado. Si el
  respaldo deja una pregunta genérica, su respuesta se acepta sin nueva evaluación.
  El script no atribuye una clasificación ni una latencia a estos pasos sin llamada.
- El caso 16 termina al observar la segunda pregunta después de su turno 1 VAGO.
  La especificación no proporciona texto para responder ese turno 2, por lo que
  no se inventa uno. Esta elección permite revisar si ambas preguntas difieren,
  sin agregar otro caso ni una llamada fuera de los textos especificados.
- El reporte tiene 18 filas: 16 iniciales y los pasos de turno 1 de los casos 15
  y 16. Muestra texto, pregunta respondida, expectativa, clasificación, criterios,
  pregunta generada, atención, latencia, origen, error y observación. Las filas sin
  nueva evaluación explican la causa. Se escapan HTML, separadores y saltos de línea;
  se elimina además la clave literal o codificada en URL si apareciera en una salida.
- Puede haber hasta 18 llamadas. La pausa configurable se aplica entre todas,
  incluidos los seguimientos; no hay reintentos automáticos ni llamadas para
  pasos ya finales o genéricos. El comando manual fuerza Gemini sin cambiar el
  entorno del servidor y cierra su cliente al terminar.
- La revisión del contenido de las preguntas es semántica: la salida estructurada
  no garantiza que el caso 15 pregunte solo por C2 ni que el caso 16 trate C1/C2
  y produzca preguntas distintas. Los resultados simulados verifican el recorrido
  y el contrato; esas expectativas se revisarán en el reporte real cuando se pida.

Se amplían las pruebas con clientes simulados y `httpx.MockTransport`, que permite
comprobar la serialización y lectura del SDK instalado sin red. Cubren iniciales
cortos, ambos turnos, ausencia de reintentos, criterios satisfechos que reaparecen,
fallos/timeout/salidas inconsistentes, seguimiento omitido o genérico, pausas,
saneamiento del reporte, ejecución simulada del comando y liberación de conexiones.
El test del transporte acepta los nombres originales y lowerCamelCase que admite
[ProtoJSON](https://protobuf.dev/programming-guides/json/), verificando el mismo
valor de razonamiento solicitado.

No se ejecuta el script contra Gemini real ni se crea `docs/evaluacion_gemini.md`.
Los reportes de pruebas se escriben únicamente en directorios temporales. Las bases
del usuario y `.env` se conservan. La siguiente fase adapta la interfaz; después
queda el cierre documental y la evaluación real requiere una petición explícita.

Resultado de fase 6 de Registro v2: `uv run pytest -q` devuelve **947 passed,
2 warnings** en 1301.42 segundos (21:41), frente a los 930 tests de fase 5.
La ejecución focalizada del adaptador y evaluación pura devuelve **221 passed,
2 warnings** en 8.90 segundos. Se conservan E1–E17, I1–I14, los escenarios de
registro, los contratos anteriores y los presupuestos SQL. Los avisos son las
deprecaciones conocidas de Starlette/httpx y Google en Python 3.14. Se termina
únicamente la fase 6; la siguiente es la interfaz de conversaciones (fase 7).

### Fase 7: interfaz de conversaciones

- `/demo/registro` conserva HTML, CSS y JavaScript planos, la explicación de Lumi,
  tres íconos y el estilo anterior. Se reemplazan los campos de respuesta v1 por
  `conversacion`: el inicial, cada pregunta y cada turno respondido se presentan
  en orden como un hilo. Los textos se crean con `textContent`, sin interpretar
  HTML. Los borradores pendientes se muestran en su campo, sin duplicarlos como
  mensajes ya enviados.
- Mientras hay una pregunta pendiente, todo lo anterior se mantiene visible y
  sin controles de edición. El campo nuevo envía `responder-seguimiento` sin
  `orden`; **Responder** reemplaza **Ampliar mi respuesta** y **Prefiero seguir**
  usa `continuar-sin-responder`. Se retiran las lecturas de `texto`, `repregunta`
  e `intento` del contrato v1. El estado se presenta como **Pregunta pendiente**.
- En FINAL se conserva el campo de edición, inicialmente dirigido al texto
  inicial. Cada respuesta enviada tiene un botón para elegir su edición. Editar
  el inicial usa `enviar`; editar un turno usa `responder-seguimiento` con su
  `orden`. No hay edición de preguntas ni de turnos omitidos. Es una elección de
  interfaz que reutiliza exactamente los contratos v2 y no añade otra acción.
- Los buffers locales se identifican por ítem e inicial/orden de turno, evitando
  mezclar la respuesta anterior con el campo de la siguiente pregunta. Se conservan
  al cambiar de ítem, elegir otro mensaje final o actualizar; se limpian al cambiar
  de cuenta, reiniciar o recargar. La recarga reconstruye borradores y conversaciones
  desde el servidor. No se añade almacenamiento local persistente ni autoguardado.
- **Prefiero seguir** conserva la pregunta sin respuesta y muestra «Preferiste
  seguir.» en el hilo. Se descarta el borrador omitido. Puede usarse tanto en el
  primer turno como después de haber respondido uno. Completar sigue exigiendo
  todos los ítems obligatorios FINAL; sus criterios/clasificaciones no se muestran.
- Se conservan espera, bloqueo de controles, recuperación de errores y 409 sin
  reenvío automático, novedades y marcado como visto. El campo pendiente se
  vincula a la pregunta mediante `aria-describedby`. Se distingue **Borrador
  guardado**, **Respuesta guardada** y un campo todavía sin respuesta.
- El detalle técnico sigue separado y plegado; solo se consulta al abrirlo.
  Usa `numero` y agrega pregunta generada, atención y un desplegable para
  `texto_evaluado`. Las consultas tardías se descartan al cambiar de cuenta o
  cerrar el panel. La URL conserva cuenta, ítem y fecha, sin textos.
- Se mantiene el reinicio de toda la demo previamente solicitado por el usuario,
  mediante `/demo/reiniciar` y su confirmación existente. No se agregan APIs,
  reglas ni cambios a la semilla, motor, instrumentos o evaluador. El servidor de
  comprobación admite `--puerto` para abrir una base temporal en un puerto libre.

Se adapta `tests/validar_registro_ui.cjs` al contrato v2. Los cambios de expectativas
afectan exclusivamente al recorrido visual v1 (ampliación única y campos retirados),
sin modificar escenarios R, E o I. Se conservan las evidencias anteriores y se
guardan las nuevas en `docs/evidencias/registro-v2`. Las comprobaciones usan Edge
headless, evaluador falso, SQLite descartable y bloqueo de peticiones externas.
Cubren escritorio 1440×1000 y móvil táctil 390/360×844. No se agregan dependencias.
La ejecución y revisión semántica de Gemini real continúan pendientes.

Resultado de fase 7 de Registro v2: `uv run pytest -q` devuelve **947 passed,
2 warnings** en 1283.01 segundos (21:23). La comprobación focalizada de página,
recursos y reinicio devuelve **2 passed, 1 warning** en 4.33 segundos. La validación
del navegador registra **257 peticiones y 0 errores JavaScript**; se revisan las
capturas de escritorio y móvil. Se conservan E1–E17, I1–I14, los escenarios R,
los contratos anteriores y todos los presupuestos SQL. Los avisos son las
deprecaciones conocidas de Starlette/httpx y Google en Python 3.14. Las bases
persistentes mantienen tamaños y fechas y no existe un reporte de Gemini real.
Se termina únicamente la fase 7; la siguiente es el cierre documental (fase 8).

### Arranque local tras Registro v2

El usuario reporta el rechazo de `demo.db` al arrancar. La inspección de solo
lectura confirma esquema 4 con 44 tablas de Registro v1: falta `turno_seguimiento`
y `respuesta_registro` conserva `texto` y `texto_primer_envio`. La integridad SQLite
es correcta; el rechazo de estructura es el previsto, no un fallo del evaluador.

Para resolver este arranque se conserva el archivo completo mediante un traslado
manual dentro del proyecto a `demo.registro-v1.respaldo.20261001-175056.db`.
Se comprueba que no haya archivos auxiliares de SQLite y que la huella SHA-256
coincida antes y después. No se elimina ni migra el archivo anterior.

Se recrea `demo.db` mediante el ciclo de vida y la semilla habituales, con
`EVALUADOR=falso` impuesto solo al proceso de comprobación. El arranque confirma
esquema 4, 45 tablas, tres ítems y registro inicial sin respuestas; ambas consultas
HTTP responden 200. `.env` no cambia y no se llama a Gemini. No se modifica código
ni se avanza a fase 8. Los datos anteriores permanecen en el respaldo; la base
nueva empieza desde cero. El usuario puede volver a ejecutar el comando habitual.

### Puerto 8000 bloqueado por una instancia antigua

Tras reiniciar, el usuario reporta que `/demo/registro` no carga. Las peticiones
GET expiran y `netstat` muestra dos procesos escuchando en 127.0.0.1:8000.
Se identifican sus procesos padres: ambos pertenecen al Uvicorn del proyecto con
`--reload`; la instancia antigua comenzó a las 11:44 y la nueva a las 17:59.
Se detienen solo los procesos verificados de la antigua (18828, 38320 y 24500),
conservando la nueva y los otros servidores de demo.

El puerto queda con un único proceso (39912). `/demo/registro` responde 200,
igual que sus tres recursos, JSON de contenido, cuentas, ítems y registro inicial.
La configuración local selecciona `gemini`, tiene clave configurada y timeout de
10 segundos; no se muestra ni cambia la clave. Solo se realizan lecturas HTTP,
sin enviar respuestas ni llamar a la API real. No se modifica código, base o
`.env` ni se avanza a la fase 8. Se vuelve a abrir el enlace del puerto 8000.

### Fase 8: cierre y evaluación real autorizada

- El usuario solicita terminar los casos y el cierre. La revisión automática
  rechaza la primera ejecución real por considerar insuficiente esa autorización.
  Se pide permiso concreto para 16 iniciales y hasta dos seguimientos, pausa de
  5 segundos, envío de textos ficticios y posible coste. El usuario responde
  «Sí, autorizo las llamadas reales a Gemini» y se ejecuta una única vez el script.
- El reporte `docs/evaluacion_gemini.md` usa el modelo configurado
  `gemini-3.1-flash-lite`, prompt v2, temperatura 0.2 y timeout de 10 segundos.
  Contiene 18 filas y 17 llamadas: los 16 iniciales y el turno 1 del caso 16.
  El caso 15 no obtiene salida válida al inicial, finaliza por respaldo y no
  ejecuta su turno. No se inventa pregunta ni clasificación para ese paso.
- Se obtienen 12 salidas LLM válidas y 5 respaldos: timeout en 2, 6 y 8; otros
  fallos en 5 y 15. Los textos suficientes finalizan NO_EVALUADA según §6.3.
  No se repiten casos fallidos ni se modifica `.env` para elegir un resultado
  favorable. La latencia tiene mediana 2967 ms y rango 1643–10122 ms.
- Las 12 clasificaciones válidas concuerdan con las expectativas, incluida la
  atención de 14. Se confirma ADECUADA en 12 y, en 16, C1/C2 faltantes y una
  segunda pregunta distinta. Las ocho preguntas tienen entre 21 y 28 palabras.
  La aceptación semántica es parcial: 7 y 11 agregan C1 cuando debe faltar solo
  C2; 1 elogia la elección; 15 no permite comprobar su conversación. Se registra
  la revisión por caso sin declarar que los 16 casos pasaron.
- Se conservan literalmente los criterios, escenarios, prompt v2 y expectativas
  autorizadas. Estas discrepancias de calidad no justifican cambiar tests,
  incorporar heurísticas que decidan criterios ni hacer reintentos automáticos.
  Un ajuste de instrucciones y otra medición requieren una iteración acordada.
- Se consolida la cobertura v2, presupuestos y crecimiento SQL, concurrencia,
  reversión, privacidad y validación visual en `docs/validacion.md`. Se actualiza
  README para usar contratos y recorrido actuales, señalar el reporte real y
  distinguirlo de pytest sin red. Las fases y evidencias v1 quedan como historial.
- Se conservan las evidencias de fase 7: 257 peticiones de navegador, cero errores
  JavaScript, escritorio 1440×1000 y móvil 390/360×844 con falso. La ejecución real
  comprueba el evaluador y sus casos; no es una prueba visual real ni escribe
  respuestas, eventos o evaluaciones en la demo del usuario. No se agregan
  dependencias ni se modifica código de producción. `uv lock --check` pasa.

El cierre documental y la ejecución/revisión real quedan realizados. Se conservan
como observaciones de aceptación parcial los resultados semánticos pendientes,
sin presentar la integración como un evaluador perfecto ni garantizar la misma
respuesta en futuras ejecuciones.

Resultado del cierre de fase 8: `uv run pytest -q`, **947 passed, 2 warnings**
en 1038.05 segundos (17:18), y `uv lock --check` correcto (43 paquetes).
Se conservan los 947 tests, E1–E17, I1–I14, R1–R17 y sus ampliaciones, los contratos
anteriores y presupuestos SQL. Los avisos son las deprecaciones conocidas de
Starlette/httpx y Google en Python 3.14. Las ocho fases de implementación quedan
cerradas y las pruebas reales ejecutadas/revisadas; su aceptación semántica
permanece parcial con los hallazgos explícitos del reporte. No se declara que
Gemini haya aprobado todos los casos ni se hace una segunda ejecución real.
