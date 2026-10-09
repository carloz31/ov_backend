# Demo del motor de desbloqueos: especificación para implementar en FastAPI

> Los datos y escenarios de esta spec se retiraron; sus reglas de comportamiento siguen vigentes.

## 1. Objetivo

Construir un backend de demostración que muestre cómo la plataforma de orientación vocacional desbloquea contenido a partir de las acciones de los usuarios. La demo debe permitir tres cosas:

1. Ver el estado de una cuenta: qué actividades, bloques, fichas, testimonios, preguntas de diario, insignias, niveles y conversaciones están bloqueados o disponibles.
2. Simular acciones (completar una actividad, escribir en el diario, superar un caso, etc.) que registran eventos.
3. Ver qué se desbloqueó con cada acción, por qué regla y cuánto falta para lo que sigue bloqueado.

Esta demo implementa **solo** el registro de eventos y el motor de desbloqueos, con las entidades mínimas necesarias para que las acciones tengan sentido. No es la plataforma completa.

## 2. Stack y convenciones

- Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (estilo declarativo con `Mapped`), SQLite en archivo local, pytest con `TestClient`.
- Sin Alembic: las tablas se crean con `Base.metadata.create_all()` al iniciar, y un endpoint de reinicio vuelve a cargar los datos semilla.
- Sin autenticación: las acciones reciben el código de la cuenta en el cuerpo de la petición.
- Nombres de tablas, columnas y funciones en español y `snake_case`. Valores de enumerados en MAYÚSCULAS, tal como aparecen en este documento.
- La API expone **códigos legibles** (`ACT-05`, `FIC-MERCADO`, `est-ana`), nunca ids internos. Internamente las tablas usan ids enteros y `id_referencia` guarda el id.
- Todo el trabajo de una acción (registrar eventos, actualizar estado, evaluar reglas, crear desbloqueos) ocurre en **una sola transacción**.

Estructura sugerida:

```
demo_desbloqueos/
  app/
    main.py            # crea la app, incluye routers, create_all al iniciar
    database.py        # engine, SessionLocal, Base, get_db
    models.py          # modelos SQLAlchemy
    schemas.py         # modelos Pydantic de entrada y salida
    motor.py           # evaluación de reglas (núcleo de la demo)
    evaluadores.py     # evaluadores especiales registrados por nombre
    acciones.py        # lógica de cada acción de dominio
    consultas.py       # armado del estado y del progreso
    seed.py            # datos semilla
    routers/
      acciones.py
      consultas.py
      demo.py
  tests/
    test_escenarios.py # un test por escenario de la sección 9
  README.md
```

## 3. Modelo de datos de la demo

Es un subconjunto simplificado del diagrama de clases de la plataforma. La simplificación principal es que `Cuenta` absorbe a `Persona`: tiene nombre y rol directamente.

### 3.1 Enumerados

| Enumerado | Valores |
|---|---|
| `Rol` | ESTUDIANTE, APODERADO |
| `Espacio` | MISIONES_CAMPO, CIUDAD |
| `Audiencia` | ESTUDIANTE, APODERADO |
| `TipoActividad` | INFORMATIVA, REGISTRO, CUESTIONARIO, CASO |
| `EstadoProgreso` | EN_CURSO, COMPLETADA |
| `TipoEventoUso` | INGRESO, COMPLETA_ACTIVIDAD, COMPLETA_BLOQUE, RESPUESTA_REFLEXIVA, ESCRIBE_ENTRADA_DIARIO, ESCRIBE_ENTRADA_LIBRE, REGISTRA_CHECK_IN, VISTA_CARRERA, SUPERA_CASO, PUBLICA_ENTREVISTA, ESCRIBE_CARTA, COMPLETA_CONVERSACION |
| `TipoObjetivo` | BLOQUE, ACTIVIDAD, FICHA, TESTIMONIO, PREGUNTA_DIARIO, CONVERSACIONES, INSIGNIA, NIVEL |
| `TipoConteo` | EVENTOS, REFERENCIAS_DISTINTAS, DIAS_DISTINTOS |
| `OrigenEntrada` | GUIADA, LIBRE |

En la plataforma real, `Caso` es una subclase de `Actividad`. En la demo basta con el tipo CASO y la columna `puntaje_minimo`.

### 3.2 Tablas

**Usuarios**

| Tabla | Columnas |
|---|---|
| `cuenta` | id, codigo (único), nombre, rol |
| `vinculo_familiar` | id, codigo (único), estudiante_id → cuenta, apoderado_id → cuenta, carta_estudiante (texto, nullable), carta_apoderado (texto, nullable) |

**Contenido** (se carga con la semilla; los usuarios no lo modifican)

| Tabla | Columnas |
|---|---|
| `bloque` | id, codigo (único), numero, nombre, espacio, audiencia |
| `actividad` | id, codigo (único), titulo, tipo, orden, bloque_id → bloque, puntaje_minimo (float, nullable; solo para CASO) |
| `ficha` | id, codigo (único), titulo, contenido |
| `testimonio` | id, codigo (único), titulo, descripcion, enlace |
| `pregunta_diario` | id, codigo (único), pregunta |
| `conversacion` | id, codigo (único), titulo, tema |
| `insignia` | id, codigo (único), nombre, descripcion, requisito, es_oculta (bool), audiencia |
| `nivel` | id, numero (único), titulo |
| `familia_carrera` | id, codigo (único), nombre |
| `carrera` | id, codigo (único), nombre, familia_id → familia_carrera |

**Estado del usuario**

| Tabla | Columnas | Restricción |
|---|---|---|
| `progreso_actividad` | id, cuenta_id, actividad_id, estado | único (cuenta_id, actividad_id) |
| `resultado_caso` | id, progreso_id → progreso_actividad, puntaje, fecha_hora | un registro por intento |
| `entrada_diario` | id, cuenta_id, origen, pregunta_id (nullable), texto, fecha_hora | una entrada GUIADA por (cuenta, pregunta) |
| `check_in` | id, cuenta_id, fecha (date), nivel_seguridad (1 a 5) | único (cuenta_id, fecha) |
| `entrevista` | id, codigo (único), resumen, fecha_hora | |
| `entrevista_autor` | entrevista_id, cuenta_id | clave compuesta |
| `conversacion_vinculo` | id, vinculo_id, conversacion_id, conversado (bool), conversado_en | único (vinculo_id, conversacion_id) |

**Motor**

| Tabla | Columnas | Restricción |
|---|---|---|
| `evento_uso` | id, cuenta_id, tipo, fecha_hora, id_referencia (int, nullable) | índice (cuenta_id, tipo) |
| `regla_desbloqueo` | id, codigo (único), nombre, tipo_objetivo, id_objetivo (int, nullable), evaluador_especial (texto, nullable) | |
| `condicion_desbloqueo` | id, regla_id, tipo_evento, id_referencia (int, nullable), tipo_conteo, cantidad_minima | cada regla tiene 1 o más condiciones |
| `desbloqueo` | id, cuenta_id, regla_id, fecha_hora, visto (bool, default false) | único (cuenta_id, regla_id) |

`id_objetivo` es nulo solo cuando el objetivo es CONVERSACIONES, que es la sección completa y no un objeto con id.

### 3.3 A qué apunta `id_referencia` en cada evento

| Evento | `id_referencia` |
|---|---|
| INGRESO | nulo |
| COMPLETA_ACTIVIDAD | actividad |
| COMPLETA_BLOQUE | bloque |
| RESPUESTA_REFLEXIVA | nulo |
| ESCRIBE_ENTRADA_DIARIO | entrada_diario |
| ESCRIBE_ENTRADA_LIBRE | entrada_diario |
| REGISTRA_CHECK_IN | check_in |
| VISTA_CARRERA | carrera |
| SUPERA_CASO | actividad (el caso) |
| PUBLICA_ENTREVISTA | entrevista |
| ESCRIBE_CARTA | vinculo_familiar |
| COMPLETA_CONVERSACION | conversacion |

## 4. El motor de desbloqueos

Esta es la parte central de la demo. Va en `motor.py` y debe ser independiente de los routers, para poder probarla directamente.

### 4.1 Cuándo se cumple una regla

Una regla se cumple para una cuenta cuando se cumplen **todas** sus condiciones y, si tiene `evaluador_especial`, además ese evaluador devuelve verdadero.

Para evaluar una condición, se cuentan los eventos de la cuenta con el `tipo_evento` de la condición. Si la condición tiene `id_referencia`, solo se cuentan los eventos con ese `id_referencia`. El conteo depende de `tipo_conteo`:

| `tipo_conteo` | Qué cuenta | Para qué sirve |
|---|---|---|
| EVENTOS | cantidad de eventos | "completó esta actividad", "3 respuestas reflexivas" |
| REFERENCIAS_DISTINTAS | cantidad de `id_referencia` distintos | "completó 8 actividades distintas": rehacer la misma no suma |
| DIAS_DISTINTOS | cantidad de fechas distintas de `fecha_hora` | "hizo check-in en 3 días distintos" |

La condición se cumple si el conteo es mayor o igual que `cantidad_minima`.

Una condición alternativa (A **o** B) no se expresa dentro de una regla: se crean dos reglas con el mismo objetivo.

### 4.2 Evaluadores especiales

Son para condiciones que no son conteos. Se registran en un diccionario en `evaluadores.py`:

```python
EVALUADORES: dict[str, Callable[[Session, Cuenta], bool]] = {
    "carreras_de_3_familias": carreras_de_3_familias,
}
```

`carreras_de_3_familias` devuelve verdadero si los eventos VISTA_CARRERA de la cuenta apuntan a carreras de al menos 3 familias distintas.

Una regla con evaluador especial también tiene condiciones normales. Estas cumplen una segunda función: definen con qué tipo de evento vale la pena reevaluarla. Por ejemplo, la regla de diversidad tiene la condición "VISTA_CARRERA, EVENTOS, 1".

### 4.3 Cuándo se evalúa

Cada vez que una acción registra uno o más eventos, el motor:

1. Busca las reglas que la cuenta todavía no tiene desbloqueadas, cuyo objetivo corresponde a la audiencia de la cuenta (ver 4.4) y que tienen al menos una condición con el tipo de alguno de los eventos recién registrados.
2. Evalúa cada una.
3. Crea un `desbloqueo` por cada regla que se cumple.
4. Devuelve la lista de desbloqueos nuevos con su explicación (ver 6.1).

Si una acción registra eventos en varias cuentas (entrevista con coautores, conversación familiar), el motor evalúa cada cuenta por separado con sus propios eventos.

Los desbloqueos **no generan eventos**, así que una sola pasada basta y no hay cascadas. Un desbloqueo es permanente: nunca se revoca.

Interfaz sugerida:

```python
def registrar_eventos(db, cuenta, eventos: list[tuple[TipoEventoUso, int | None]], fecha_hora) -> list[DesbloqueoNuevo]
def evaluar_regla(db, cuenta, regla) -> ResultadoRegla   # cumple + progreso por condición
def objetivo_disponible(db, cuenta, tipo_objetivo, id_objetivo) -> bool
```

### 4.4 Cuándo un objetivo está disponible

Un objetivo está disponible para una cuenta si se cumplen las tres condiciones siguientes:

1. **Audiencia.** El objetivo corresponde al rol de la cuenta (tabla abajo). Si no corresponde, no aparece en su estado.
2. **Bloque contenedor.** Si el objetivo es una actividad, su bloque debe estar disponible.
3. **Reglas.** No hay ninguna regla que apunte a él, **o** la cuenta tiene un `desbloqueo` de al menos una de esas reglas.

| Objetivo | Audiencia |
|---|---|
| BLOQUE | `bloque.audiencia` |
| ACTIVIDAD | la de su bloque |
| INSIGNIA | `insignia.audiencia` |
| FICHA, TESTIMONIO, PREGUNTA_DIARIO, NIVEL | solo ESTUDIANTE |
| CONVERSACIONES | ambos roles |

La regla del bloque contenedor evita escribir una regla por cada actividad de la ciudad. Al desbloquearse un bloque de la ciudad, todas sus actividades sin regla propia quedan disponibles. Las que tienen regla propia siguen bloqueadas hasta cumplirla.

### 4.5 Nivel actual

El nivel actual es el de mayor `numero` disponible para la cuenta. El nivel 1 no tiene reglas, así que todo estudiante empieza en él. Las reglas de cada nivel incluyen también las condiciones del nivel anterior, así que nadie puede saltarse un nivel.

## 5. Acciones de dominio

Cada acción valida lo que corresponde, actualiza el estado, registra eventos y devuelve los desbloqueos nuevos. Todas aceptan un campo opcional `fecha_hora` (ISO 8601) para simular el paso de los días. Si no viene, se usa la hora actual.

Si una acción no está permitida, se responde **409** con un mensaje y, cuando aplica, el progreso de las reglas del objetivo bloqueado (ver 6.3), para que se vea qué falta.

| Endpoint (POST) | Cuerpo | Validaciones | Efecto y eventos |
|---|---|---|---|
| `/acciones/ingresar` | cuenta | ninguna | INGRESO |
| `/acciones/completar-actividad` | cuenta, actividad | la actividad debe estar disponible y no ser de tipo CASO | Crea o actualiza el progreso a COMPLETADA. Registra COMPLETA_ACTIVIDAD en **cada** finalización, también al rehacerla. Si es la primera vez que se completan todas las actividades del bloque, registra COMPLETA_BLOQUE. |
| `/acciones/resolver-caso` | cuenta, actividad, puntaje (0 a 100) | la actividad debe estar disponible y ser de tipo CASO | Crea un `resultado_caso`. Completa la actividad igual que la acción anterior. Si puntaje ≥ `puntaje_minimo` y es la primera vez que lo supera, registra SUPERA_CASO. |
| `/acciones/responder-registro` | cuenta, clasificacion (ADECUADA o VAGA), ampliada (bool) | ninguna | Si la clasificación es ADECUADA o `ampliada` es verdadero, registra RESPUESTA_REFLEXIVA. En la plataforma real la clasificación la da el LLM; aquí llega en la petición. |
| `/acciones/escribir-entrada` | cuenta, origen, pregunta (solo si es GUIADA), texto | solo estudiantes; si es GUIADA, la pregunta debe estar disponible y no estar respondida ya | Crea la entrada. Registra ESCRIBE_ENTRADA_DIARIO y, si es LIBRE, también ESCRIBE_ENTRADA_LIBRE. |
| `/acciones/check-in` | cuenta, nivel_seguridad | solo estudiantes; uno por día | Crea el check-in. Registra REGISTRA_CHECK_IN. |
| `/acciones/ver-carrera` | cuenta, carrera | ninguna | VISTA_CARRERA |
| `/acciones/publicar-entrevista` | autores (lista de cuentas), resumen | todos estudiantes | Crea la entrevista. Registra PUBLICA_ENTREVISTA **en la cuenta de cada autor** y devuelve los desbloqueos agrupados por autor. |
| `/acciones/escribir-carta` | cuenta, texto | la cuenta debe pertenecer a un vínculo | Guarda la carta del rol que corresponde. Registra ESCRIBE_CARTA solo la primera vez. |
| `/acciones/completar-conversacion` | cuenta, conversacion | CONVERSACIONES debe estar disponible para la cuenta que marca | Marca la conversación del vínculo como conversada. Registra COMPLETA_CONVERSACION **en ambas cuentas del vínculo**, solo la primera vez, y devuelve los desbloqueos agrupados por cuenta. |

Además, un endpoint de depuración:

| Endpoint (POST) | Cuerpo | Efecto |
|---|---|---|
| `/eventos` | cuenta, tipo, referencia (código, opcional), fecha_hora (opcional) | Registra un evento crudo sin validaciones de dominio y evalúa reglas. Sirve para probar reglas aisladas. |

## 6. Consultas

### 6.1 Respuesta de toda acción

```json
{
  "eventos_registrados": [
    {"tipo": "COMPLETA_ACTIVIDAD", "referencia": "ACT-03", "fecha_hora": "2026-10-01T10:00:00"},
    {"tipo": "COMPLETA_BLOQUE", "referencia": "B0", "fecha_hora": "2026-10-01T10:00:00"}
  ],
  "nuevos_desbloqueos": [
    {
      "regla": "R-INS-PRIMER-PASO",
      "tipo_objetivo": "INSIGNIA",
      "objetivo": {"codigo": "INS-PRIMER-PASO", "nombre": "Primer paso"},
      "condiciones": [
        {"tipo_evento": "COMPLETA_BLOQUE", "referencia": "B0", "tipo_conteo": "EVENTOS", "actual": 1, "requerido": 1, "cumplida": true}
      ]
    },
    {
      "regla": "R-NIV-2",
      "tipo_objetivo": "NIVEL",
      "objetivo": {"codigo": "N2", "nombre": "Explorador de caminos"},
      "condiciones": [ "..." ]
    }
  ]
}
```

### 6.2 Estado de una cuenta

`GET /cuentas/{cuenta}/estado` devuelve, para la audiencia de la cuenta:

```json
{
  "cuenta": {"codigo": "est-ana", "nombre": "Ana", "rol": "ESTUDIANTE"},
  "nivel_actual": {"numero": 2, "titulo": "Explorador de caminos"},
  "bloques": [
    {
      "codigo": "B0", "nombre": "Inicio", "espacio": "MISIONES_CAMPO", "estado": "DISPONIBLE",
      "actividades": [
        {"codigo": "ACT-01", "titulo": "Bienvenida", "estado": "COMPLETADA"},
        {"codigo": "ACT-02", "titulo": "Mis expectativas", "estado": "DISPONIBLE"},
        {"codigo": "ACT-03", "titulo": "Mi diario", "estado": "BLOQUEADA"}
      ]
    }
  ],
  "fichas": [{"codigo": "FIC-PROFESIONES", "titulo": "...", "estado": "BLOQUEADA"}],
  "testimonios": [ "..." ],
  "preguntas_diario": [{"codigo": "PD-HISTORIA", "estado": "DISPONIBLE", "respondida": false}],
  "conversaciones": {"estado": "BLOQUEADA"},
  "insignias": [
    {"codigo": "INS-PRIMER-PASO", "nombre": "Primer paso", "requisito": "Completa el bloque de inicio", "estado": "OBTENIDA"},
    {"codigo": "???", "nombre": "Logro oculto", "requisito": null, "estado": "BLOQUEADA"}
  ],
  "niveles": [{"numero": 1, "titulo": "Viajero novato", "estado": "OBTENIDO"}]
}
```

Estados posibles de una actividad en la demo: BLOQUEADA, DISPONIBLE y COMPLETADA. EN_CURSO existe en la plataforma, pero la demo no simula actividades a medias. Las actividades de un bloque bloqueado aparecen como BLOQUEADA. Una insignia oculta y no obtenida se muestra sin nombre, descripción ni requisito; al obtenerla se muestra completa.

### 6.3 Progreso hacia un objetivo

`GET /cuentas/{cuenta}/progreso/{tipo_objetivo}/{codigo}` devuelve cada regla que apunta al objetivo, con el avance de cada condición. Es lo que en el diseño de gamificación se llama Dangling: muestra qué le espera al estudiante y qué debe hacer para acceder.

```json
{
  "objetivo": {"tipo": "ACTIVIDAD", "codigo": "ACT-17"},
  "disponible": false,
  "reglas": [
    {
      "regla": "R-ACT-17",
      "cumplida": false,
      "condiciones": [
        {"tipo_evento": "COMPLETA_ACTIVIDAD", "referencia": "ACT-13", "tipo_conteo": "EVENTOS", "actual": 1, "requerido": 1, "cumplida": true},
        {"tipo_evento": "COMPLETA_BLOQUE", "referencia": "C1", "tipo_conteo": "EVENTOS", "actual": 0, "requerido": 1, "cumplida": false}
      ]
    }
  ]
}
```

Si la regla tiene evaluador especial, se agrega el campo `"evaluador_especial": {"nombre": "carreras_de_3_familias", "cumplido": false}`, y `cumplida` solo es verdadero si también lo es el evaluador.

Para CONVERSACIONES el código es `-`. Si el objetivo es una insignia oculta, este endpoint responde 403 mientras no se obtenga.

### 6.4 Otras consultas

| Endpoint (GET) | Devuelve |
|---|---|
| `/cuentas` | cuentas de la demo |
| `/cuentas/{cuenta}/eventos` | línea de tiempo de eventos, del más reciente al más antiguo |
| `/cuentas/{cuenta}/desbloqueos?solo_no_vistos=true` | desbloqueos con fecha y objetivo |
| `/reglas` | todas las reglas en forma legible: objetivo, condiciones y evaluador especial |

| Endpoint (POST) | Efecto |
|---|---|
| `/cuentas/{cuenta}/desbloqueos/marcar-vistos` | marca como vistos todos los desbloqueos pendientes |
| `/demo/reiniciar` | borra todas las tablas y vuelve a cargar la semilla |

## 7. Datos semilla

Los códigos de actividad siguen el proceso base de orientación vocacional, reducido para la demo.

### 7.1 Cuentas y vínculos

| Código | Nombre | Rol |
|---|---|---|
| est-ana | Ana | ESTUDIANTE |
| est-luis | Luis | ESTUDIANTE |
| apo-rosa | Rosa | APODERADO |

Vínculo `VIN-ANA`: estudiante Ana, apoderado Rosa. Luis no tiene vínculo; solo sirve para la coautoría.

### 7.2 Bloques y actividades

| Bloque | Nombre | Espacio | Audiencia | Actividades (orden) |
|---|---|---|---|---|
| B0 | Inicio | MISIONES_CAMPO | ESTUDIANTE | ACT-01 Bienvenida (CUESTIONARIO), ACT-02 Mis expectativas (REGISTRO), ACT-03 Mi diario (INFORMATIVA) |
| B1 | Mi historia | MISIONES_CAMPO | ESTUDIANTE | ACT-04 Mi historia personal (REGISTRO), ACT-05 Mis aspiraciones (REGISTRO), ACT-06 Mi línea de tiempo (REGISTRO) |
| B3 | Exploro el mundo profesional | MISIONES_CAMPO | ESTUDIANTE | ACT-12 Exploro profesiones (INFORMATIVA), ACT-13 Mercado laboral y oferta educativa (INFORMATIVA) |
| B5 | Mi decisión | MISIONES_CAMPO | ESTUDIANTE | ACT-17 Mi perfil y carreras afines (REGISTRO), ACT-18 Mi proyecto vocacional (REGISTRO), ACT-19 Evaluación final (CUESTIONARIO) |
| C1 | Misiones de Helena | CIUDAD | ESTUDIANTE | HEL-01 Intereses I (CUESTIONARIO), HEL-02 Intereses II (CUESTIONARIO), HEL-03 Habilidades sociales (CUESTIONARIO) |
| C2 | Central de Casos | CIUDAD | ESTUDIANTE | CASO-01 El hospital (CASO, mínimo 70), CASO-02 La obra (CASO, mínimo 70) |
| C3 | Comprobaciones | CIUDAD | ESTUDIANTE | COMP-13 Comprobación de mercado laboral (INFORMATIVA) |
| C4 | Investigaciones | CIUDAD | ESTUDIANTE | INV-01 Mi investigación vocacional (REGISTRO) |
| P1 | Ruta del apoderado | MISIONES_CAMPO | APODERADO | ACT-P01 Mi rol en el proceso (INFORMATIVA), ACT-P02 Me fortalezco para acompañarte (INFORMATIVA) |

ACT-13 es la actividad de llegada a la ciudad. B5 queda después de la llegada, para que lo explorado en la ciudad llegue a tiempo al proyecto vocacional.

### 7.3 Contenido desbloqueable

| Tipo | Código | Título |
|---|---|---|
| Ficha | FIC-PROFESIONES | Profesiones y ocupaciones |
| Ficha | FIC-MERCADO | Mercado laboral en Lima |
| Ficha | FIC-INSTITUCIONES | Oferta educativa |
| Testimonio | TES-HOSPITAL | Testimonio de una enfermera |
| Testimonio | TES-OBRA | Testimonio de un maestro de obra |
| Pregunta de diario | PD-HISTORIA | ¿Qué descubriste de tu historia que no habías notado? |
| Pregunta de diario | PD-ASPIRACIONES | ¿Tus aspiraciones son tuyas o de tu entorno? |
| Pregunta de diario | PD-CONV-01 | ¿Qué aprendiste de la conversación con tu familia? |
| Conversación | CONV-01 | Lo que esperamos del futuro |
| Conversación | CONV-02 | Mis fortalezas vistas por mi familia |

Familias y carreras, para el evaluador especial:

| Familia | Carreras |
|---|---|
| FAM-SALUD | CAR-ENF Enfermería, CAR-MED Medicina |
| FAM-INGENIERIA | CAR-CIV Ingeniería civil |
| FAM-ARTE | CAR-DIS Diseño gráfico |
| FAM-NEGOCIOS | CAR-ADM Administración |

### 7.4 Insignias

| Código | Nombre | Oculta | Audiencia | Requisito visible |
|---|---|---|---|---|
| INS-PRIMER-PASO | Primer paso | no | ESTUDIANTE | Completa el bloque de inicio |
| INS-CIUDAD | Bienvenido a la ciudad | no | ESTUDIANTE | Llega a la ciudad |
| INS-PRIMER-CASO | Primer caso resuelto | no | ESTUDIANTE | Supera un caso de la Central de Casos |
| INS-INVESTIGADOR | Investigador | no | ESTUDIANTE | Publica tu primera entrevista |
| INS-EXPLORADOR | Explorador diverso | no | ESTUDIANTE | Revisa carreras de al menos 3 familias distintas |
| INS-CONOZCO-MI-ROL | Conozco mi rol | no | APODERADO | Completa tu ruta |
| LOG-PLUMA | Pluma libre | sí | ESTUDIANTE | (oculto) primera entrada libre |
| LOG-CONSTANCIA | Constancia | sí | ESTUDIANTE | (oculto) check-in en 3 días distintos |
| LOG-PENSADOR | Pensador profundo | sí | ESTUDIANTE | (oculto) 3 respuestas reflexivas |
| LOG-INCANSABLE | Incansable | sí | ESTUDIANTE | (oculto) 8 actividades distintas completadas |

### 7.5 Niveles

| Número | Título |
|---|---|
| 1 | Viajero novato |
| 2 | Explorador de caminos |
| 3 | Habitante de la ciudad |
| 4 | Mago del autoconocimiento |
| 5 | Arquitecto de su futuro |

### 7.6 Reglas

Notación de cada condición: `EVENTO(referencia) conteo ≥ n`. Si no se indica el conteo, es EVENTOS. Si no se indica la referencia, cuenta todos los eventos de ese tipo.

**Ruta secuencial (objetivo ACTIVIDAD)**

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-ACT-02 | ACT-02 | COMPLETA_ACTIVIDAD(ACT-01) ≥ 1 |
| R-ACT-03 | ACT-03 | COMPLETA_ACTIVIDAD(ACT-02) ≥ 1 |
| R-ACT-04 | ACT-04 | COMPLETA_ACTIVIDAD(ACT-03) ≥ 1 |
| R-ACT-05 | ACT-05 | COMPLETA_ACTIVIDAD(ACT-04) ≥ 1 |
| R-ACT-06 | ACT-06 | COMPLETA_ACTIVIDAD(ACT-05) ≥ 1 |
| R-ACT-12 | ACT-12 | COMPLETA_ACTIVIDAD(ACT-06) ≥ 1 |
| R-ACT-13 | ACT-13 | COMPLETA_ACTIVIDAD(ACT-12) ≥ 1 |
| R-ACT-17 | ACT-17 | COMPLETA_ACTIVIDAD(ACT-13) ≥ 1 y COMPLETA_BLOQUE(C1) ≥ 1 |
| R-ACT-18 | ACT-18 | COMPLETA_ACTIVIDAD(ACT-17) ≥ 1 |
| R-ACT-19 | ACT-19 | COMPLETA_ACTIVIDAD(ACT-18) ≥ 1 |
| R-ACT-P02 | ACT-P02 | COMPLETA_ACTIVIDAD(ACT-P01) ≥ 1 |

Las primeras actividades de B0 (ACT-01) y de P1 (ACT-P01) no tienen regla: están disponibles desde el inicio para su audiencia. El bloque B5 tampoco tiene regla propia: lo controlan las reglas de sus actividades.

**La ciudad (objetivo BLOQUE)**

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-CIUDAD-C1 | C1 | COMPLETA_ACTIVIDAD(ACT-13) ≥ 1 |
| R-CIUDAD-C2 | C2 | COMPLETA_ACTIVIDAD(ACT-13) ≥ 1 |
| R-CIUDAD-C3 | C3 | COMPLETA_ACTIVIDAD(ACT-13) ≥ 1 |
| R-CIUDAD-C4 | C4 | COMPLETA_ACTIVIDAD(ACT-13) ≥ 1 |

B1 y B3 no tienen regla de bloque: sus actividades ya están encadenadas.

**Dentro de la ciudad (objetivo ACTIVIDAD)**

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-HEL-02 | HEL-02 | COMPLETA_ACTIVIDAD(HEL-01) ≥ 1 |
| R-CASO-02 | CASO-02 | COMPLETA_ACTIVIDAD(CASO-01) ≥ 1 |
| R-INV-01 | INV-01 | SUPERA_CASO ≥ 1 |

HEL-01, HEL-03, CASO-01 y COMP-13 no tienen regla propia: quedan disponibles al desbloquearse su bloque. CASO-02 se abre al intentar CASO-01, aunque no lo supere.

**Fichas, testimonios y preguntas de diario**

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-FIC-PROFESIONES | FIC-PROFESIONES | COMPLETA_ACTIVIDAD(ACT-12) ≥ 1 |
| R-FIC-MERCADO | FIC-MERCADO | COMPLETA_ACTIVIDAD(ACT-13) ≥ 1 |
| R-FIC-INSTITUCIONES | FIC-INSTITUCIONES | COMPLETA_ACTIVIDAD(COMP-13) ≥ 1 |
| R-TES-HOSPITAL | TES-HOSPITAL | SUPERA_CASO(CASO-01) ≥ 1 |
| R-TES-OBRA | TES-OBRA | SUPERA_CASO(CASO-02) ≥ 1 |
| R-PD-HISTORIA | PD-HISTORIA | COMPLETA_ACTIVIDAD(ACT-04) ≥ 1 |
| R-PD-ASPIRACIONES | PD-ASPIRACIONES | COMPLETA_ACTIVIDAD(ACT-05) ≥ 1 |
| R-PD-CONV-01 | PD-CONV-01 | COMPLETA_CONVERSACION(CONV-01) ≥ 1 |

**Módulo de familia (objetivo CONVERSACIONES)**

Son dos reglas independientes con el mismo objetivo. Cada cuenta solo puede cumplir la de su rol, porque la otra exige una actividad de otra audiencia.

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-FAM-ESTUDIANTE | CONVERSACIONES | ESCRIBE_CARTA ≥ 1 y COMPLETA_ACTIVIDAD(ACT-13) ≥ 1 |
| R-FAM-APODERADO | CONVERSACIONES | ESCRIBE_CARTA ≥ 1 y COMPLETA_ACTIVIDAD(ACT-P02) ≥ 1 |

**Insignias**

| Regla | Objetivo | Condiciones | Evaluador especial |
|---|---|---|---|
| R-INS-PRIMER-PASO | INS-PRIMER-PASO | COMPLETA_BLOQUE(B0) ≥ 1 | |
| R-INS-CIUDAD | INS-CIUDAD | COMPLETA_ACTIVIDAD(ACT-13) ≥ 1 | |
| R-INS-PRIMER-CASO | INS-PRIMER-CASO | SUPERA_CASO ≥ 1 | |
| R-INS-INVESTIGADOR | INS-INVESTIGADOR | PUBLICA_ENTREVISTA ≥ 1 | |
| R-INS-EXPLORADOR | INS-EXPLORADOR | VISTA_CARRERA ≥ 1 | carreras_de_3_familias |
| R-INS-CONOZCO-MI-ROL | INS-CONOZCO-MI-ROL | COMPLETA_BLOQUE(P1) ≥ 1 | |
| R-LOG-PLUMA | LOG-PLUMA | ESCRIBE_ENTRADA_LIBRE ≥ 1 | |
| R-LOG-CONSTANCIA | LOG-CONSTANCIA | REGISTRA_CHECK_IN DIAS_DISTINTOS ≥ 3 | |
| R-LOG-PENSADOR | LOG-PENSADOR | RESPUESTA_REFLEXIVA ≥ 3 | |
| R-LOG-INCANSABLE | LOG-INCANSABLE | COMPLETA_ACTIVIDAD REFERENCIAS_DISTINTAS ≥ 8 | |

**Niveles (objetivo NIVEL)**

Cada nivel repite las condiciones del anterior y agrega las suyas.

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-NIV-2 | nivel 2 | COMPLETA_BLOQUE(B0) ≥ 1 |
| R-NIV-3 | nivel 3 | lo de R-NIV-2 y COMPLETA_ACTIVIDAD(ACT-13) ≥ 1 |
| R-NIV-4 | nivel 4 | lo de R-NIV-3, COMPLETA_BLOQUE(C1) ≥ 1 y SUPERA_CASO ≥ 1 |
| R-NIV-5 | nivel 5 | lo de R-NIV-4 y COMPLETA_ACTIVIDAD(ACT-18) ≥ 1 |

## 8. Invariantes que los tests deben verificar

1. Nunca hay dos `desbloqueo` para la misma (cuenta, regla).
2. Un desbloqueo nunca se elimina, aunque la cuenta siga registrando eventos.
3. Una actividad bloqueada no se puede completar: la acción responde 409 y no registra eventos.
4. Una cuenta nunca ve en su estado objetivos de otra audiencia.
5. COMPLETA_BLOQUE, SUPERA_CASO, ESCRIBE_CARTA y COMPLETA_CONVERSACION se registran solo la primera vez para cada referencia y cuenta.
6. COMPLETA_ACTIVIDAD se registra en cada finalización, incluso al rehacer.
7. Rehacer una actividad no cambia su estado COMPLETADA.
8. Un estudiante no puede tener dos check-in el mismo día ni dos entradas GUIADA para la misma pregunta.
9. El nivel actual nunca baja.

## 9. Escenarios de demostración

Cada escenario es un test en `tests/test_escenarios.py` y, a la vez, el guion para mostrar la demo. Todos parten de `/demo/reiniciar`. Cuando un escenario indica un prerrequisito, el test ejecuta antes esos pasos con funciones auxiliares, por ejemplo `llevar_a_ana_a_la_ciudad(client)`. Donde se indica una fecha, se envía en `fecha_hora`.

**E1. Estado inicial.** Consultar el estado de Ana.
Esperado: ACT-01 DISPONIBLE; ACT-02 en adelante BLOQUEADA; bloques C1 a C4 BLOQUEADA; nivel actual 1; fichas, testimonios y preguntas de diario BLOQUEADA; conversaciones BLOQUEADA. Las insignias visibles muestran su requisito, y los 4 logros ocultos aparecen como `???`. ACT-P01 e INS-CONOZCO-MI-ROL no aparecen. En el estado de Rosa aparecen ACT-P01 DISPONIBLE, ACT-P02 BLOQUEADA, INS-CONOZCO-MI-ROL y CONVERSACIONES, y no aparece ninguna actividad de estudiante.

**E2. Primer desbloqueo.** Ana completa ACT-01.
Esperado: un desbloqueo nuevo, R-ACT-02, con su condición cumplida (1 de 1). ACT-01 COMPLETADA y ACT-02 DISPONIBLE.

**E3. Intento de saltarse la ruta.** Ana intenta completar ACT-04 sin haber hecho ACT-03.
Esperado: 409 con el progreso de R-ACT-04: COMPLETA_ACTIVIDAD(ACT-03), 0 de 1. No se registra ningún evento.

**E4. Un evento, varios desbloqueos.** Ana completa ACT-02 y luego ACT-03.
Esperado: al completar ACT-03 se registran COMPLETA_ACTIVIDAD y COMPLETA_BLOQUE(B0), y la respuesta trae tres desbloqueos: R-ACT-04, R-INS-PRIMER-PASO y R-NIV-2. El nivel actual pasa a 2.

**E5. Rehacer no suma.** Ana rehace ACT-01 cinco veces.
Esperado: se registran 5 eventos COMPLETA_ACTIVIDAD más, pero el progreso de LOG-INCANSABLE sigue en 3 de 8 (REFERENCIAS_DISTINTAS). No se registra otro COMPLETA_BLOQUE(B0). Ningún desbloqueo nuevo.

**E6. Días distintos.** Ana hace check-in el 1 de octubre, intenta otro el mismo día y luego lo hace el 2 y el 3 de octubre.
Esperado: el segundo check-in del 1 de octubre responde 409. Tras el del 3 de octubre, se desbloquea LOG-CONSTANCIA, y en el estado ya aparece con su nombre y descripción.

**E7. Llegada a la ciudad.** Ana completa ACT-04, ACT-05, ACT-06, ACT-12 y ACT-13.
Esperado:
- Por el camino se desbloquean PD-HISTORIA (con ACT-04), PD-ASPIRACIONES (con ACT-05) y FIC-PROFESIONES (con ACT-12).
- Al completar ACT-13 se desbloquean en una sola respuesta los bloques C1 a C4, INS-CIUDAD, FIC-MERCADO, R-NIV-3 y el logro oculto LOG-INCANSABLE, porque ACT-13 es la octava actividad distinta completada.
- En el estado: HEL-01, HEL-03, CASO-01, COMP-13 DISPONIBLE (heredan su bloque); HEL-02, CASO-02 e INV-01 BLOQUEADA (tienen regla propia).
- CONVERSACIONES sigue BLOQUEADA, y su progreso muestra la regla R-FAM-ESTUDIANTE con ACT-13 cumplida y ESCRIBE_CARTA en 0 de 1.

**E8. Condición compuesta con varias actividades.** Prerrequisito: E7. Consultar el progreso de ACT-17.
Esperado: COMPLETA_ACTIVIDAD(ACT-13) cumplida y COMPLETA_BLOQUE(C1) en 0 de 1. Ana completa HEL-01, HEL-02 y HEL-03: al completar HEL-03 se registra COMPLETA_BLOQUE(C1) y se desbloquea ACT-17.

**E9. Casos: intento fallido, reintento y repetición.** Prerrequisito: E8. Ana resuelve CASO-01 con 50, luego con 85 y luego con 95.
Esperado:
- Con 50: CASO-01 COMPLETADA y se desbloquea CASO-02 (basta con intentarlo). No hay SUPERA_CASO, TES-HOSPITAL sigue BLOQUEADA y existe un `resultado_caso`.
- Con 85: se registra SUPERA_CASO(CASO-01) y se desbloquean TES-HOSPITAL, INS-PRIMER-CASO e INV-01. Como Ana ya completó C1 en E8, también se desbloquea R-NIV-4.
- Con 95: un tercer `resultado_caso` y otro COMPLETA_ACTIVIDAD, pero ningún SUPERA_CASO ni desbloqueo nuevo.

**E10. Cuentas que avanzan a destiempo en la familia.** Prerrequisito: E7. Ana escribe su carta.
Esperado:
- Para Ana se desbloquea CONVERSACIONES. En el estado de Rosa sigue BLOQUEADA.
- Rosa escribe su carta: sigue BLOQUEADA, y su progreso muestra ESCRIBE_CARTA cumplida y ACT-P02 en 0 de 1.
- Rosa completa ACT-P01 y ACT-P02: al completar ACT-P02 se desbloquean, en la misma respuesta, CONVERSACIONES (R-FAM-APODERADO) e INS-CONOZCO-MI-ROL.

**E11. Una acción, desbloqueos en dos cuentas.** Prerrequisito: E10. Rosa marca CONV-01 como conversada.
Esperado: se registra COMPLETA_CONVERSACION(CONV-01) en Rosa y en Ana. La respuesta agrupa por cuenta, y para Ana trae el desbloqueo de PD-CONV-01, aunque ella no hizo la acción. Rosa no recibe PD-CONV-01, aunque tiene el mismo evento, porque las preguntas de diario son solo para estudiantes (filtro de audiencia de 4.3). Si Ana marca CONV-01 después, no se registran eventos nuevos.

**E12. Coautoría.** Ana y Luis publican una entrevista juntos.
Esperado: PUBLICA_ENTREVISTA en ambas cuentas e INS-INVESTIGADOR desbloqueada para los dos, agrupada por autor en la respuesta.

**E13. Evaluador especial.** Ana ve CAR-ENF, CAR-MED y CAR-CIV.
Esperado: son dos familias, así que INS-EXPLORADOR sigue BLOQUEADA, aunque su condición de conteo está cumplida. Al ver CAR-DIS (tercera familia), se desbloquea. El progreso de la regla muestra la condición de conteo y el resultado del evaluador por separado.

**E14. Diario.** Prerrequisito: E7. Ana escribe una entrada GUIADA para PD-HISTORIA, intenta escribir otra para la misma pregunta y escribe una entrada LIBRE.
Esperado: la segunda entrada guiada responde 409. La entrada libre registra ESCRIBE_ENTRADA_DIARIO y ESCRIBE_ENTRADA_LIBRE, y desbloquea LOG-PLUMA. Escribir una entrada GUIADA para PD-CONV-01 antes de E11 responde 409, porque la pregunta está bloqueada.

**E15. Respuestas reflexivas.** Ana envía cuatro respuestas de registro, en este orden: VAGA sin ampliar, VAGA ampliada, ADECUADA y ADECUADA.
Esperado: la primera no registra evento. Las otras tres registran RESPUESTA_REFLEXIVA, y con la cuarta respuesta se desbloquea LOG-PENSADOR.

**E16. Hasta el nivel 5.** Prerrequisito: E9. Ana completa ACT-17 y ACT-18.
Esperado: al completar ACT-18 se desbloquean R-ACT-19 y R-NIV-5, y el nivel actual es 5. La lista de niveles muestra los cinco como OBTENIDO.

**E17. Novedades no vistas.** Tras cualquiera de los escenarios anteriores, consultar los desbloqueos no vistos de Ana, marcarlos como vistos y volver a consultar.
Esperado: la segunda consulta devuelve una lista vacía.

## 10. Fuera de alcance

Estas partes existen en el diseño de la plataforma, pero no van en esta demo:

- Autenticación, salones, orientadoras y panel.
- Contenido de las actividades (el JSON por plantilla), instrumentos, cálculo de resultados y clasificación con LLM.
- Ocupaciones desbloqueadas por un caso: dependen de qué ocupaciones usó bien el estudiante en ese intento, no de un conteo de eventos.
- Lectura de la carta del otro (`cartas_disponibles()`) y Leyendas: dependen de acciones de otras personas, no de los eventos de la propia cuenta.
- Tarjetas de carrera, favoritos, catálogos completos y datos salariales.

## 11. Orden de implementación sugerido

1. Modelos, base de datos y semilla. Verificar con `/reglas` que las reglas se cargan como en la sección 7.6.
2. `motor.py` con sus pruebas unitarias: conteo por cada `tipo_conteo`, regla con varias condiciones, evaluador especial y disponibilidad con audiencia y bloque contenedor.
3. Consultas de estado y progreso.
4. Acciones, una por una, con el escenario que las prueba.
5. Tests de los 17 escenarios y de los invariantes.
6. README con instrucciones para levantar la demo (`uvicorn app.main:app --reload`) y recorrer los escenarios desde `/docs`.

Opcional, después de lo anterior: una página `/demo` en HTML plano, servida por FastAPI, que muestre el estado de una cuenta como tablero (bloques con sus actividades, fichas, insignias y nivel) y tenga botones para las acciones principales. Tras cada acción, la página resalta lo recién desbloqueado. Sirve para presentar la demo sin usar Swagger.
