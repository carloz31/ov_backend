# Demo de actividad de registro con preguntas de seguimiento (Gemini): especificación para FastAPI

> Los datos y escenarios de esta spec se retiraron; sus reglas de comportamiento siguen vigentes.

> **Versión 2.** Reemplaza a la versión 1. Cambio principal: el estudiante ya no reescribe su respuesta cuando es vaga. Lumi le hace una **pregunta de seguimiento** sobre los criterios que faltan, el estudiante la responde como un turno nuevo, y el registro final es la respuesta inicial más sus turnos. También cambia el papel del mínimo de caracteres: ya no decide si se llama a Gemini, sino que es el respaldo cuando Gemini falla o no responde a tiempo. Si la implementación de la versión 1 ya avanzó, se conservan la semilla, la validación del JSON, la caché, el evaluador falso y la lógica de evaluación, y se ajustan la tabla de respuestas, las acciones y los escenarios según esta versión. Las diferencias se anotan en `docs/decisiones.md`, bajo "Registro v2".

## 1. Objetivo

Extender el backend existente para verificar que el modelo de datos soporta una actividad de registro completa:

1. Una plantilla de dos momentos definida en un JSON del front: primero alguien explica algo, luego el estudiante responde varios ítems de registro.
2. Guardar la posición del estudiante dentro de la actividad y retomar donde quedó.
3. Guardar borradores de una respuesta sin enviarla.
4. Al enviar una respuesta, evaluar su completitud con Gemini; si Gemini falla o no responde a tiempo, usar como respaldo un mínimo de caracteres. Si le faltan criterios, hacer una pregunta de seguimiento solo sobre lo que falta, que el estudiante responde sin reescribir lo anterior, hasta un máximo de dos preguntas por ítem.
5. Registrar cada evaluación para poder analizar después cómo se comporta el LLM.
6. Completar la actividad solo cuando todas las respuestas obligatorias están finalizadas, y que eso dispare los eventos y desbloqueos existentes.

La actividad de prueba es el cierre de ACT-08 del proceso base: "Mi plan para fortalecer una habilidad".

## 2. Punto de partida y reglas de convivencia

El backend ya implementa `docs/spec-demo-motor-desbloqueos.md` y `docs/spec-demo-instrumentos.md`, con las decisiones de `docs/decisiones.md`, la optimización de consultas y la auditoría de constantes. Este documento se agrega sin cambiar lo anterior:

- **No se modifican** la semántica del motor, los instrumentos, la semilla existente, los contratos HTTP existentes ni los resultados esperados de E1–E17 e I1–I14. La acción existente `/acciones/responder-registro` se conserva tal cual.
- **Adaptaciones de tests autorizadas por adelantado**, que deben anotarse en `docs/decisiones.md`, bajo "Registro":
  - conteos y listas exactas de tablas, columnas, bloques, actividades y reglas, para incluir lo nuevo;
  - la versión de esquema vigente pasa de 3 a 4, y la versión usada como inválida pasa de 4 a 5. Los rechazos de las versiones 1, 2 y 3 se conservan.
- Cualquier otra adaptación requiere detenerse y preguntar.
- **Base local:** `esquema_version` sube a 4. Se aplica la regla vigente: la `demo.db` anterior se borra y el arranque la recrea.
- **Consultas:** las peticiones nuevas entran en `LIMITES_SQL` (sección 8) y en las pruebas de crecimiento. Se aplican las técnicas ya adoptadas: definiciones en caché, lecturas agrupadas por cuenta, escrituras en lote y ninguna consulta dentro de bucles.
- **Constantes:** los parámetros del método (mínimos, tiempo máximo, versión del prompt, modelo) van en `app/configuracion_metodos.py` o en variables de entorno, nunca dispersos. Los datos de los ítems viven en la base.
- **Dependencias nuevas permitidas:** `google-genai` (SDK oficial de Gemini) y `python-dotenv`, si el proyecto aún no lee archivos `.env`. Se agregan con `uv add`.

## 3. Configuración

Variables de entorno, leídas desde `.env` (que nunca se versiona):

| Variable | Valor por defecto | Uso |
|---|---|---|
| `GEMINI_API_KEY` | ninguno | Clave de la API. Obligatoria solo si `EVALUADOR=gemini`. |
| `EVALUADOR` | `falso` | `gemini` usa la API real; `falso` usa el evaluador determinista de la sección 6.4. |
| `GEMINI_MODELO` | `gemini-3.1-flash-lite` | Modelo a usar. |
| `GEMINI_TIMEOUT_SEGUNDOS` | `8` | Tiempo máximo de espera por evaluación. |

Si `EVALUADOR=gemini` y falta la clave, la aplicación no arranca y lo indica con un mensaje claro. La clave nunca se escribe en logs, respuestas ni errores.

En `app/configuracion_metodos.py`: `VERSION_PROMPT_REGISTRO = "v2"` y `MAXIMO_SEGUIMIENTOS_POR_ITEM = 2`.

Los tests siempre usan el evaluador falso, sin red.

## 4. Modelo de datos

### 4.1 Enumerados nuevos o ampliados

| Enumerado | Valores |
|---|---|
| `ClasificacionRespuesta` | ADECUADA, VAGA, se agrega **NO_EVALUADA** |
| `EstadoRespuestaRegistro` (nuevo) | BORRADOR, PENDIENTE_SEGUIMIENTO, FINAL |
| `OrigenEvaluacion` (nuevo) | LLM, RESPALDO_LONGITUD |

### 4.2 Columna nueva en una tabla existente

| Tabla | Columna | Uso |
|---|---|---|
| `progreso_actividad` | `posicion` (texto, nullable) | Identificador del momento del JSON donde quedó el estudiante. Ya existe en el diagrama de clases. |

### 4.3 Tablas nuevas

**Definición** (se carga con la semilla y entra en la caché de definiciones)

| Tabla | Columnas | Restricción |
|---|---|---|
| `item_registro` | id, codigo (único), nombre, consigna, min_caracteres, obligatorio (bool), repregunta_generica | |
| `criterio_completitud` | id, item_registro_id, codigo, descripcion, orden | único (item_registro_id, codigo) |
| `actividad_item_registro` | actividad_id, item_registro_id, orden | clave compuesta |

`min_caracteres` y `repregunta_generica` son el respaldo para cuando Gemini falla: si el texto inicial no alcanza el mínimo, se le hace al estudiante esa pregunta genérica, y lo que responda se acepta sin otra revisión. Los criterios son la `descripcionCompletitud` del diagrama, separada en filas para que el LLM devuelva qué criterios faltan por su código.

**Respuestas, turnos y evaluaciones**

| Tabla | Columnas | Restricción |
|---|---|---|
| `respuesta_registro` | id, progreso_id → progreso_actividad, item_registro_id, texto_inicial, estado, clasificacion_inicial (nullable), ampliada (bool, default false), creada_en, actualizada_en | único (progreso_id, item_registro_id) |
| `turno_seguimiento` | id, respuesta_id, orden (1 o 2), pregunta, criterios_objetivo (JSON, lista de códigos), respuesta (nullable), respondido_en (nullable), creado_en | único (respuesta_id, orden) |
| `evaluacion_respuesta` | id, respuesta_id, numero (1, 2, 3…), origen, clasificacion, criterios_faltantes (JSON), pregunta_generada (nullable), requiere_atencion (bool), modelo (nullable), version_prompt (nullable), latencia_ms (nullable), error (nullable), texto_evaluado, fecha_hora | |

- `texto_inicial` es la respuesta a la consigna. No se reescribe al recibir preguntas de seguimiento; solo cambia si el estudiante la edita después de finalizar (6.2).
- Cada `turno_seguimiento` es una pregunta de Lumi y la respuesta del estudiante. `criterios_objetivo` indica qué criterios faltantes busca completar. Mientras `respondido_en` es nulo, `respuesta` puede contener un borrador.
- `clasificacion_inicial` se fija con la evaluación del texto inicial y no cambia nunca; alimenta la métrica de la Meta 2.
- `ampliada` es verdadero si el estudiante respondió al menos una pregunta de seguimiento.
- `texto_evaluado` guarda exactamente lo que se envió al evaluador en cada evaluación. Las evaluaciones se agregan, nunca se modifican.

## 5. Semilla

### 5.1 Bloque y actividad

| Bloque | Nombre | Espacio | Audiencia | Regla de bloque |
|---|---|---|---|---|
| REG | Laboratorio de registros (solo demo) | MISIONES_CAMPO | ESTUDIANTE | ninguna |

| Actividad | Título | Tipo | Plantilla | Ítems (orden) |
|---|---|---|---|---|
| REG-ACT08 | Mi plan para fortalecer una habilidad | REGISTRO | `registro-guiado` | REG-HAB-1, REG-HAB-2, REG-HAB-3 |

No se agregan reglas. La actividad está disponible desde el inicio para estudiantes.

### 5.2 Ítems

**REG-HAB-1, "Habilidad a fortalecer"**
- Consigna: ¿Qué habilidad social quieres fortalecer y por qué?
- Mínimo: 40 caracteres. Obligatorio.
- Repregunta genérica: Cuéntame un poco más: ¿qué habilidad elegiste y en qué momento de tu vida sientes que te haría falta?
- Criterios:
  - `C1`: Nombra una habilidad social concreta, por ejemplo asertividad, empatía, comunicación o trabajo en equipo.
  - `C2`: La relaciona con una situación de su propia vida en la que la necesita o le cuesta.

**REG-HAB-2, "Mi acción"**
- Consigna: ¿Qué harás para practicarla?
- Mínimo: 40 caracteres. Obligatorio.
- Repregunta genérica: Cuéntame un poco más: ¿qué harás exactamente y en qué momento?
- Criterios:
  - `C1`: Describe una acción que puede realizar, no solo una intención general como "esforzarme" o "mejorar".
  - `C2`: Indica dónde, cuándo o con quién la realizará.

**REG-HAB-3, "Cómo sabré que mejoro"**
- Consigna: ¿Cómo sabrás que estás mejorando?
- Mínimo: 30 caracteres. Obligatorio.
- Repregunta genérica: Cuéntame un poco más: ¿qué notarías tú que cambia cuando mejores?
- Criterios:
  - `C1`: Describe algo que él mismo puede observar o notar, no solo un sentimiento general como "me sentiré mejor".
  - `C2`: Se relaciona con la habilidad y la acción que eligió.

### 5.3 Contenido JSON de la plantilla

Archivo `app/static/contenido/REG-ACT08.json`. Es la única fuente del contenido de la actividad; el back no lo interpreta, salvo para validarlo.

```json
{
  "actividad": "REG-ACT08",
  "plantilla": "registro-guiado",
  "momentos": [
    {
      "id": "explicacion",
      "tipo": "dialogo",
      "personaje": "Lumi",
      "lineas": [
        "En casi todos los avisos de trabajo se piden habilidades como comunicarse bien, trabajar en equipo o resolver conflictos.",
        "No se aprenden en un curso: se fortalecen practicando en situaciones del día a día.",
        "Ahora vas a armar tu propio plan para fortalecer una de tus habilidades."
      ]
    },
    {
      "id": "plan",
      "tipo": "registro",
      "presentacion": "iconos",
      "items": ["REG-HAB-1", "REG-HAB-2", "REG-HAB-3"]
    }
  ]
}
```

Al arrancar, y en un test, se valida que la actividad del JSON exista, que los ítems existan y coincidan con los asignados a la actividad en la base, y que los `id` de los momentos sean únicos. Si algo no coincide, la aplicación no arranca y lo indica.

## 6. Lógica

### 6.1 Estados de una respuesta

```
(sin respuesta) --guardar borrador--> BORRADOR
BORRADOR o sin respuesta --enviar--> FINAL                  (completa, no evaluada o requiere atención)
BORRADOR o sin respuesta --enviar--> PENDIENTE_SEGUIMIENTO  (faltan criterios: se crea el turno 1)
PENDIENTE_SEGUIMIENTO --guardar borrador--> PENDIENTE_SEGUIMIENTO (borrador de la respuesta al turno)
PENDIENTE_SEGUIMIENTO --responder seguimiento--> FINAL      (completa, máximo alcanzado, fallo o atención)
PENDIENTE_SEGUIMIENTO --responder seguimiento--> PENDIENTE_SEGUIMIENTO (aún faltan criterios: se crea el turno 2)
PENDIENTE_SEGUIMIENTO --continuar sin responder--> FINAL
FINAL --editar--> FINAL                                     (sin evaluar de nuevo)
```

### 6.2 Acciones

| Acción | Efecto |
|---|---|
| **Guardar posición** | Crea el progreso en EN_CURSO si no existe y guarda `posicion`. La posición debe ser un `id` de momento del JSON. |
| **Guardar borrador** | Sin evaluar. Si la respuesta no existe o está en BORRADOR, guarda `texto_inicial` en BORRADOR. Si está en PENDIENTE_SEGUIMIENTO, guarda el texto como borrador de la respuesta del turno pendiente. En FINAL responde 409. |
| **Enviar** (respuesta inexistente o en BORRADOR) | Guarda `texto_inicial` y lo evalúa (6.3). Fija `clasificacion_inicial`. |
| **Responder seguimiento** (respuesta en PENDIENTE_SEGUIMIENTO) | Guarda la respuesta del turno pendiente, marca `respondido_en` y `ampliada = true`, y evalúa el conjunto (6.3). Si el turno era la pregunta genérica del respaldo, no evalúa: la respuesta pasa a FINAL. |
| **Continuar sin responder** (respuesta en PENDIENTE_SEGUIMIENTO) | Pasa a FINAL. El turno pendiente queda sin respuesta, como registro de que se preguntó. No evalúa. |
| **Editar** (respuesta en FINAL) | Con la acción de enviar, reemplaza `texto_inicial`; con la de responder seguimiento e indicando el `orden`, reemplaza la respuesta de un turno ya respondido. No evalúa, no crea turnos y no cambia `clasificacion_inicial`. |

Todas las acciones exigen que la actividad esté disponible, que la cuenta sea estudiante y que el ítem pertenezca a la actividad. Aceptan `fecha_hora` opcional.

**Evento RESPUESTA_REFLEXIVA.** Se registra una sola vez por respuesta, cuando pasa a FINAL y se cumple alguna de estas condiciones: `clasificacion_inicial` es ADECUADA, o `ampliada` es verdadero. No se registra al continuar sin haber respondido ningún turno, ni cuando el texto inicial quedó NO_EVALUADA sin turnos. Va con `id_referencia` nulo, como en la acción existente, así que la regla de LOG-PENSADOR funciona sin cambios.

### 6.3 Evaluación

Se evalúa al enviar el texto inicial y al responder cada pregunta de seguimiento generada por el LLM.

1. **Texto vacío** (solo espacios): 422.
2. **Siempre se llama primero al evaluador,** con el contexto de 6.5, sea cual sea la longitud del texto. Al responder un turno, el evaluador recibe la conversación completa del ítem y evalúa si el conjunto ya cumple todos los criterios.
3. **Resultado del evaluador:**
   - **ADECUADA:** la respuesta pasa a FINAL.
   - **VAGA y quedan turnos disponibles** (menos de `MAXIMO_SEGUIMIENTOS_POR_ITEM` turnos creados): se crea el siguiente turno, con la pregunta generada y `criterios_objetivo` igual a los criterios que siguen faltando. La respuesta queda en PENDIENTE_SEGUIMIENTO.
   - **VAGA y ya no quedan turnos:** la respuesta pasa a FINAL. No se hace una tercera pregunta.
   - **Requiere atención:** la respuesta pasa a FINAL sin más preguntas, se guarda la marca y el estudiante no ve nada distinto. En la plataforma real alimentará una alerta para la orientadora; en la demo solo se guarda.
4. **Respaldo por longitud.** Si el evaluador falla, supera el tiempo máximo o devuelve algo que no cumple el esquema, se registra una evaluación con origen RESPALDO_LONGITUD y el error, y:
   - **Si era el texto inicial y tiene menos de `min_caracteres`:** la clasificación es VAGA, se crea un turno con `repregunta_generica` y `criterios_objetivo` con todos los criterios, y la respuesta queda en PENDIENTE_SEGUIMIENTO. Cuando el estudiante responde ese turno, la respuesta pasa a FINAL **sin evaluarla de nuevo**.
   - **Si era el texto inicial y alcanza el mínimo:** la clasificación es NO_EVALUADA y la respuesta pasa a FINAL.
   - **Si era la respuesta a un turno:** la respuesta pasa a FINAL, sin otra pregunta.

   El estudiante nunca queda bloqueado por un problema de la API.
5. Toda evaluación se registra en `evaluacion_respuesta`, con su origen. Así, en el análisis se pueden separar las clasificaciones del LLM de las decididas por longitud.

Las preguntas de seguimiento **solo** buscan completar criterios faltantes. Si el texto inicial ya cumple todos los criterios, no hay pregunta: lo que se quería obtener ya está, y otra pregunta repetiría información. Para obtener respuestas más ricas, se agregan criterios al ítem, no preguntas extra.

### 6.4 Evaluadores

Una interfaz común en `app/evaluador_respuestas.py`:

```python
class EvaluadorRespuestas(Protocol):
    def evaluar(self, contexto: ContextoEvaluacion) -> ResultadoEvaluacion: ...
```

`ResultadoEvaluacion` tiene `clasificacion` (ADECUADA o VAGA), `criterios_faltantes` (lista de códigos), `pregunta` (texto o nulo) y `requiere_atencion` (bool). La interfaz no conoce SQLAlchemy ni FastAPI.

- **`EvaluadorGemini`** usa `google-genai` con salida estructurada en JSON según el esquema de 6.6, temperatura 0.2, el tiempo máximo configurado y, si el modelo lo permite, el nivel mínimo de razonamiento. Mide la latencia. Valida el esquema, que los códigos de criterios existan y que `criterios_faltantes` sea un subconjunto de los criterios que faltaban antes de este turno; si no, lanza un error, que activa el respaldo por longitud (6.3).
- **`EvaluadorFalso`** es determinista y decide solo por el texto más reciente (el inicial o la última respuesta a un turno):
  - sin marcas: ADECUADA;
  - `[vaga]`: VAGA, siguen faltando todos los criterios que faltaban;
  - `[falta:C2]` (uno o varios códigos): VAGA, faltan exactamente esos;
  - `[atencion]`: marca `requiere_atencion`;
  - `[falla]`: lanza un error.

  La pregunta que genera es `"¿Podrías contarme más sobre {códigos faltantes}?"`. Guarda los contextos recibidos, para que los tests puedan revisarlos.

### 6.5 Contexto que recibe el evaluador

- Título de la actividad.
- Consigna del ítem y sus criterios, con código y descripción, en orden.
- Los criterios que faltaban antes de esta evaluación (en el texto inicial, todos).
- La conversación del ítem: el texto inicial y, si los hay, cada pregunta de seguimiento con su respuesta.
- Las respuestas FINAL de los demás ítems de la misma actividad y cuenta, como conversación completa y con su consigna.

Nunca se envían nombres, códigos de cuenta ni otros datos que identifiquen al estudiante.

### 6.6 Prompt y esquema de salida

Instrucción de sistema (versión `v2`):

```
Eres el asistente de una plataforma de orientación vocacional para estudiantes de último año de secundaria en Perú.
Tu única tarea es revisar si la respuesta del estudiante está COMPLETA según los criterios indicados.

Reglas:
1. Evalúa solo la completitud. Nunca juzgues si la opinión, el gusto o la decisión del estudiante es correcta o conveniente.
2. Si recibes una conversación (respuesta inicial y respuestas a preguntas de seguimiento), evalúa todo el conjunto: un criterio está cumplido si se cumple en cualquier parte de la conversación.
3. La respuesta es ADECUADA si cumple todos los criterios, aunque sea breve o informal. Es VAGA si le falta al menos uno. Solo pueden faltar criterios de la lista de criterios que faltaban.
4. Si es VAGA, escribe UNA sola pregunta de seguimiento:
   - solo sobre los criterios que faltan; nunca preguntes por algo que el estudiante ya respondió;
   - de máximo 30 palabras, en español, tratando al estudiante de "tú";
   - que retome sus propias palabras;
   - cálida y sin reproche; no digas que la respuesta está mal ni menciones criterios, evaluaciones o inteligencia artificial.
5. Usa las respuestas de otras preguntas de la actividad solo como contexto.
6. Marca requiere_atencion = true si la respuesta sugiere una situación de riesgo o malestar serio (por ejemplo autolesión, violencia o abuso). En ese caso, clasifica como ADECUADA y deja la pregunta vacía.
7. Responde solo con el JSON pedido.
```

Esquema de salida:

```json
{
  "type": "object",
  "properties": {
    "clasificacion": {"type": "string", "enum": ["ADECUADA", "VAGA"]},
    "criterios_faltantes": {"type": "array", "items": {"type": "string"}},
    "pregunta": {"type": "string", "nullable": true},
    "requiere_atencion": {"type": "boolean"}
  },
  "required": ["clasificacion", "criterios_faltantes", "pregunta", "requiere_atencion"]
}
```

Reglas de consistencia que valida el back: si la clasificación es VAGA, la pregunta debe existir y `criterios_faltantes` no puede estar vacío, salvo que `requiere_atencion` sea verdadero; si es ADECUADA, `criterios_faltantes` debe estar vacío. Si no se cumplen, se trata como un fallo y se aplica el respaldo por longitud (6.3).

### 6.7 Transacciones y la llamada al LLM

La llamada a Gemini **nunca** ocurre dentro de una transacción de base de datos ni con una conexión tomada:

Esto aplica tanto a enviar como a responder seguimiento:

1. **Fase 1 (transacción corta):** validar cuenta, actividad, disponibilidad e ítem; leer la respuesta actual con sus turnos y las respuestas FINAL de la actividad. Se toma nota de `actualizada_en` y del estado. Se cierra la transacción.
2. **Fase 2 (sin transacción):** llamar al evaluador. Si falla, no responde a tiempo o devuelve un resultado inválido, decidir con el respaldo por longitud (6.3).
3. **Fase 3 (transacción corta):** volver a leer la respuesta y comprobar que su estado y `actualizada_en` no cambiaron desde la fase 1. Si cambiaron (otro envío o borrador simultáneo), responder 409 sin escribir nada; la evaluación hecha se descarta. Si no, guardar la respuesta, la evaluación y los eventos, y evaluar reglas como en cualquier acción.

### 6.8 Completar la actividad

La acción existente `/acciones/completar-actividad` agrega una validación, igual que con los instrumentos: si la actividad tiene ítems de registro obligatorios, todos deben estar en FINAL. Si no, responde 409 con `items_faltantes` (los códigos que no están en FINAL, en orden) y sin registrar eventos. Las actividades sin ítems de registro no cambian.

Rehacer la actividad conserva las respuestas, que se pueden editar.

## 7. Endpoints

### 7.1 Acciones (POST)

| Endpoint | Cuerpo | Respuesta |
|---|---|---|
| `/acciones/guardar-posicion` | cuenta, actividad, posicion | posición guardada y estado del progreso |
| `/acciones/registro/guardar-borrador` | cuenta, actividad, item, texto | estado de la respuesta |
| `/acciones/registro/enviar` | cuenta, actividad, item, texto | ver ejemplo abajo |
| `/acciones/registro/responder-seguimiento` | cuenta, actividad, item, texto, orden (solo para editar un turno en FINAL) | igual que enviar |
| `/acciones/registro/continuar-sin-responder` | cuenta, actividad, item | estado de la respuesta y eventos |

Respuesta de `enviar` o `responder-seguimiento` cuando queda una pregunta pendiente:

```json
{
  "item": "REG-HAB-1",
  "estado": "PENDIENTE_SEGUIMIENTO",
  "conversacion": [
    {"tipo": "respuesta", "texto": "Me gustaría mejorar mi comunicación, porque siento que es un punto débil mío."},
    {"tipo": "pregunta", "orden": 1, "texto": "¿En qué situaciones notas que te cuesta comunicarte?"}
  ],
  "eventos_registrados": [],
  "nuevos_desbloqueos": []
}
```

La respuesta al estudiante nunca incluye la clasificación, los criterios ni `requiere_atencion`.

### 7.2 Consultas (GET)

| Endpoint | Devuelve |
|---|---|
| `/actividades/{actividad}/items-registro` | ítems en orden, con código, nombre, consigna, mínimo y obligatoriedad. Sin criterios. Sale de la caché. |
| `/cuentas/{cuenta}/actividades/{actividad}/registro` | posición, estado del progreso y, por ítem: estado y conversación (texto inicial, preguntas de seguimiento y respuestas, incluidos los borradores pendientes) |
| `/demo/registro/{cuenta}/{actividad}/evaluaciones` | **solo demo y análisis:** todas las evaluaciones, con número, origen, clasificación, criterios faltantes, pregunta generada, requiere atención, modelo, versión del prompt, latencia, error y texto evaluado |

Como en las consultas existentes, los apoderados y las cuentas o actividades inexistentes reciben 404.

## 8. Límites de consultas SQL

Se agregan a `LIMITES_SQL`. En `enviar` se cuentan las dos transacciones juntas, y la llamada al evaluador no consulta la base.

| Petición | Límite |
|---|---|
| Guardar posición | 4 |
| Guardar borrador | 6 |
| Enviar, con cualquier origen de evaluación | 12 |
| Responder seguimiento | 12 |
| Continuar sin responder | 8 |
| Ítems de registro de una actividad | 1 |
| Estado del registro de una actividad | 4 |
| Completar REG-ACT08 | 15 (el límite existente de completar) |

La prueba de crecimiento se extiende a `enviar`, `responder-seguimiento` y al estado del registro: con 100 reglas y 500 eventos extra, deben mantener la misma cantidad de consultas.

## 9. Escenarios

En `tests/test_registro.py`, con el evaluador falso y SQLite temporal. Cada escenario parte de `/demo/reiniciar`.

**R1. Estado inicial.** REG-ACT08 DISPONIBLE para Ana; tres ítems en orden; registro sin posición ni respuestas. Rosa recibe 404.

**R2. Posición.** Ana guarda la posición `plan`. El progreso queda EN_CURSO con esa posición, y el estado del mapa muestra REG-ACT08 EN_CURSO. Una posición inexistente en el JSON responde 422.

**R3. Borrador.** Ana guarda un borrador de REG-HAB-1 y luego lo reemplaza. Queda una sola fila en BORRADOR, sin evaluaciones ni eventos, y el evaluador falso no fue llamado.

**R4. Respaldo por longitud con texto corto.** Ana envía "Asertividad [falla]" en REG-HAB-1, con menos de 40 caracteres.
Esperado: el evaluador falso fue llamado y falló. Queda PENDIENTE_SEGUIMIENTO, con el turno 1 que contiene la repregunta genérica del ítem y `criterios_objetivo = [C1, C2]`; una evaluación con origen RESPALDO_LONGITUD y el error registrado; `clasificacion_inicial = VAGA`.

**R5. Responder la pregunta genérica.** Desde R4, Ana responde el turno 1.
Esperado: FINAL **sin una nueva evaluación**; el evaluador falso no fue llamado otra vez. `texto_inicial` no cambia, el turno 1 tiene su respuesta y `respondido_en`, `ampliada = true`, y se registra un evento RESPUESTA_REFLEXIVA.

**R5b. Responder un seguimiento del LLM.** Ana envía en REG-HAB-2 un texto con `[vaga]` y luego responde el turno 1 sin marcas.
Esperado: FINAL tras una segunda evaluación con origen LLM. El contexto de esa evaluación incluye el texto inicial, la pregunta del turno 1 y su respuesta.

**R5c. Texto corto evaluado por el LLM.** Ana envía "Asertividad" (menos de 40 caracteres, sin marcas) en REG-HAB-1.
Esperado: el evaluador falso fue llamado, aunque el texto no alcanza el mínimo, y la respuesta queda en FINAL. El mínimo de caracteres no se aplica mientras el LLM responda.

**R6. Solo se pregunta por lo que falta.** Ana envía en REG-HAB-1 un texto de más de 40 caracteres con `[falta:C2]`.
Esperado: turno 1 con `criterios_objetivo = [C2]`, no [C1, C2]. El contexto del evaluador indicaba que faltaban C1 y C2.

**R7. Dos seguimientos y máximo alcanzado.** Desde R6, Ana responde el turno 1 con `[vaga]`.
Esperado: turno 2 con `criterios_objetivo = [C2]`. Ana responde el turno 2 con `[vaga]` otra vez: la respuesta pasa a FINAL sin crear un turno 3, con `ampliada = true` y un evento RESPUESTA_REFLEXIVA. Hay tres evaluaciones (números 1, 2 y 3).

**R8. Continuar sin responder.** Ana envía en REG-HAB-2 un texto con `[vaga]` y luego continúa sin responder.
Esperado: FINAL; el turno 1 queda sin respuesta; `ampliada = false`; ningún evento.

**R9. Completa al primer intento.** Ana envía una respuesta sin marcas en REG-HAB-3.
Esperado: FINAL sin turnos, `clasificacion_inicial = ADECUADA`, un evento RESPUESTA_REFLEXIVA y una sola evaluación con origen LLM.

**R10. Contexto entre ítems.** Con REG-HAB-1 en FINAL tras un seguimiento, Ana envía REG-HAB-2. El contexto del evaluador incluye la conversación completa de REG-HAB-1, y no incluye el nombre ni el código de Ana.

**R11. Fallo del LLM con texto suficiente.** Ana envía un texto inicial de más de 40 caracteres con `[falla]`.
Esperado: FINAL, `clasificacion_inicial = NO_EVALUADA`, evaluación con origen RESPALDO_LONGITUD y el error registrado, sin evento, y la petición responde 200. En otro ítem, un fallo al responder un turno del LLM deja la respuesta en FINAL sin otra pregunta, con `ampliada = true` y un evento RESPUESTA_REFLEXIVA.

**R12. Requiere atención.** Ana envía un texto con `[atencion]`: FINAL sin turnos y con la marca en la evaluación. La respuesta HTTP no contiene la marca ni la clasificación.

**R13. Borradores durante el seguimiento.** Con un turno pendiente, Ana guarda un borrador de su respuesta. El estado sigue en PENDIENTE_SEGUIMIENTO, el turno tiene el borrador sin `respondido_en`, y al consultar el registro aparece para retomarlo.

**R13b. Completar.** Con REG-HAB-3 en BORRADOR o en PENDIENTE_SEGUIMIENTO, completar responde 409 con `items_faltantes = ["REG-HAB-3"]` y sin eventos. Con los tres ítems en FINAL, la actividad queda COMPLETADA y registra COMPLETA_ACTIVIDAD y COMPLETA_BLOQUE(REG).

**R13c. Logro por respuestas reflexivas.** Ana completa los tres ítems sin marcas: tres eventos RESPUESTA_REFLEXIVA, y con el tercero se desbloquea LOG-PENSADOR, sin cambiar la regla existente.

**R13d. Edición después de finalizar.** Ana edita el texto inicial y la respuesta del turno 1 de un ítem FINAL: los textos cambian, no hay evaluaciones nuevas, turnos nuevos ni eventos, y `clasificacion_inicial` no cambia.

**R14. Envío concurrente.** Mientras el evaluador falso procesa una respuesta a un turno, se guarda un borrador para el mismo ítem (simulado desde el propio evaluador falso).
Esperado: el envío original responde 409, no se guarda su evaluación ni se crea un turno, y queda el borrador guardado en paralelo.

**R15. Sin transacción durante la evaluación.** Durante la llamada al evaluador falso no hay ninguna transacción abierta ni conexión tomada del pool. El test lo verifica desde el propio evaluador.

**R16. Aislamiento.** Las respuestas, evaluaciones y posiciones de Ana no aparecen en las consultas de Luis.

**R17. Validación del contenido JSON.** Un JSON con un ítem que no existe, o que no coincide con los ítems de la actividad, impide arrancar con un mensaje claro.

## 10. Prueba con Gemini real

Un script separado, `scripts/evaluar_gemini.py`, que **no** forma parte de `pytest`. Envía estos casos al evaluador real, con una pausa entre llamadas para respetar los límites del nivel gratuito, y genera `docs/evaluacion_gemini.md` con una tabla: ítem, texto, clasificación esperada, clasificación obtenida, criterios faltantes, pregunta generada, requiere atención y latencia.

| # | Ítem | Texto | Esperada |
|---|---|---|---|
| 1 | REG-HAB-1 | Asertividad, porque es importante para el futuro. | VAGA (falta C2) |
| 2 | REG-HAB-1 | La asertividad, porque en los trabajos grupales me quedo callado aunque no esté de acuerdo. | ADECUADA |
| 3 | REG-HAB-1 | Quiero mejorar en todo, la verdad no sé bien qué elegir. | VAGA |
| 4 | REG-HAB-1 | Trabajo en equipo, porque cuando hacemos proyectos en el colegio siempre termino haciendo todo yo solo. | ADECUADA |
| 5 | REG-HAB-2 | Voy a esforzarme más y ser mejor persona con los demás. | VAGA |
| 6 | REG-HAB-2 | En el próximo trabajo de Comunicación voy a decir mi opinión al menos una vez antes de que decidamos. | ADECUADA |
| 7 | REG-HAB-2 | Voy a practicar hablando más. | VAGA (falta C2) |
| 8 | REG-HAB-2 | Los sábados, cuando juego fútbol con mi barrio, voy a pedir el balón y organizar al equipo. | ADECUADA |
| 9 | REG-HAB-3 | Me sentiré mejor conmigo mismo y más feliz. | VAGA |
| 10 | REG-HAB-3 | Cuando en una reunión diga que no estoy de acuerdo sin quedarme pensando en eso después. | ADECUADA |
| 11 | REG-HAB-3 | Mis notas van a subir. | VAGA (falta C2) |
| 12 | REG-HAB-1 | Empatía, aunque creo que está sobrevalorada; igual me serviría, porque cuando mis amigos me cuentan sus problemas no sé qué decirles. | ADECUADA (opinión discutible, pero cumple C1 y C2) |
| 13 | REG-HAB-2 | jajaja no sé, lo que sea | VAGA |
| 14 | REG-HAB-1 | Ninguna, porque en mi casa me dicen que no sirvo para nada y ya no me importa. | requiere atención |

Para REG-HAB-2 y REG-HAB-3, el script envía como contexto respuestas adecuadas de los ítems anteriores, por ejemplo las de los casos 2 y 6.

El caso 12 comprueba que el LLM no juzga opiniones. El caso 14, que detecta una situación de malestar en lugar de preguntar.

Además, el script ejecuta dos conversaciones completas, con turnos simulados:

| # | Ítem | Texto inicial | Respuesta al turno 1 | Qué se revisa |
|---|---|---|---|---|
| 15 | REG-HAB-1 | Me gustaría mejorar mi comunicación, porque siento que es un punto débil mío. | En los trabajos grupales, cuando no estoy de acuerdo, me quedo callado. | La pregunta del turno 1 trata solo C2 (la situación), no vuelve a preguntar por la habilidad. Tras la respuesta, ADECUADA. |
| 16 | REG-HAB-2 | Voy a esforzarme más. | No sé, más seguido. | El texto inicial no cumple C1 (es una intención general) ni C2, así que la pregunta del turno 1 trata ambos. Tras la respuesta, sigue VAGA y genera una segunda pregunta distinta de la primera. |

El reporte incluye las preguntas generadas en cada turno, para revisar a mano que no repitan lo ya respondido.

## 11. Interfaz mínima: `/demo/registro`

En HTML, CSS y JavaScript planos, con el estilo de `/demo` y un enlace desde ella. Lee `REG-ACT08.json` y usa los endpoints de la sección 7, más estos endpoints existentes, sin modificarlos:

- `GET /cuentas`, para el selector de cuenta;
- `GET /cuentas/{cuenta}/estado`, para saber si la actividad está disponible o completada;
- `POST /acciones/completar-actividad`, para completar la actividad;
- `GET /cuentas/{cuenta}/desbloqueos?solo_no_vistos=true` y `POST /cuentas/{cuenta}/desbloqueos/marcar-vistos`, para mostrar lo que se desbloqueó, por ejemplo LOG-PENSADOR.

No se agregan endpoints auxiliares para la interfaz.

1. **Selector de cuenta y fecha simulada,** como en `/demo`.
2. **Momento `explicacion`:** muestra a Lumi con sus líneas y un botón "Continuar", que guarda la posición `plan`.
3. **Momento `plan`:** tres íconos, uno por ítem, con su estado (vacío, borrador, pregunta pendiente, listo). Al pulsar un ícono se abre su consigna con un campo de texto y dos botones: "Guardar borrador" y "Enviar".
4. **Conversación:** la respuesta se muestra como un hilo. Si queda una pregunta pendiente, Lumi la muestra debajo, con un campo nuevo para responderla, el botón "Responder" y un enlace discreto "Prefiero seguir" (continuar sin responder). El texto anterior queda visible y no se edita mientras haya una pregunta pendiente.
5. **Indicador de espera** mientras se evalúa: "Lumi está leyendo tu respuesta…".
6. **Botón "Completar actividad",** habilitado cuando los tres ítems están listos.
7. **Al recargar,** la página retoma la posición, los borradores y las preguntas pendientes desde el servidor.
8. **Panel "Detalle técnico",** separado y plegado, que muestra el registro de evaluaciones del endpoint de demo: origen, clasificación, criterios faltantes, latencia y modelo. Sirve para validar; en la plataforma real no se mostraría al estudiante.

## 12. Fuera de alcance

- Precarga entre ítems (`precarga desde`).
- Alertas a la orientadora por `requiere_atencion`; solo se guarda la marca.
- Recomendación del día y etiquetado de temáticas con el LLM.
- Reintentos automáticos ante fallos de la API.
- Edición del contenido JSON desde la plataforma.

## 13. Orden de implementación sugerido

1. Columna `posicion`, tablas nuevas, enumerados, semilla de REG y su caché, y validación del JSON. Esquema versión 4. Verificar que los tests existentes siguen pasando con las adaptaciones autorizadas.
2. Interfaz `EvaluadorRespuestas`, `EvaluadorFalso` y lógica pura de la evaluación (consistencia del resultado y respaldo por longitud), con sus tests.
3. Acciones de posición, borrador, envío y respuesta de seguimiento en tres fases, y continuar sin responder (R1 a R13, R13d y R14 a R16).
4. Validación en completar actividad (R13b y R13c).
5. Límites de consultas y pruebas de crecimiento.
6. `EvaluadorGemini` y el script de la sección 10. Ejecutarlo con la clave real y revisar el reporte.
7. Interfaz de la sección 11.
8. Actualizar `docs/decisiones.md` y `docs/validacion.md`.
