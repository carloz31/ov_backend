# Registro con preguntas de seguimiento

Actividades de registro cuyas respuestas evalúa un LLM (Gemini) para pedir, como máximo, dos preguntas de seguimiento. Código: `app/services/registro/` y `app/api/registro.py`. Parámetros: `VERSION_PROMPT_REGISTRO`, `MAXIMO_SEGUIMIENTOS_POR_ITEM` (2), modelo, temperatura y tiempo máximo en `app/core/parametros.py`.

Estado actual: el backend implementa todo lo de este documento, pero el conjunto `plataforma` todavía no tiene ítems de registro; el front responde los registros con su lógica local y solo informa la finalización. La integración llega con la iteración 2.

## Configuración

| Variable | Por defecto | Uso |
|---|---|---|
| `EVALUADOR` | `falso` | `gemini` usa la API real; `falso`, el evaluador determinista. |
| `GEMINI_API_KEY` | — | Obligatoria si `EVALUADOR=gemini`; sin ella la aplicación no arranca. |
| `GEMINI_MODELO` | `gemini-3.1-flash-lite` | Modelo. |
| `GEMINI_TIMEOUT_SEGUNDOS` | `8` | Tiempo máximo por evaluación. |

## Modelo

| Tabla | Qué guarda |
|---|---|
| `item_registro` | `codigo`, `nombre`, `consigna`, `min_caracteres`, `obligatorio`, `repregunta_generica` (catálogo, en caché). |
| `criterio_completitud` | Criterios del ítem con `codigo` (C1, C2…), `descripcion` y `orden`. |
| `actividad_item_registro` | Ítems de cada actividad y su orden. |
| `respuesta_registro` | Por progreso e ítem: `texto_inicial`, `estado` (BORRADOR, PENDIENTE_SEGUIMIENTO o FINAL), `clasificacion_inicial` (inmutable), `ampliada`. |
| `turno_seguimiento` | Hasta dos por respuesta: pregunta, `criterios_objetivo`, respuesta o borrador, `respondido_en`. |
| `evaluacion_respuesta` | Cada evaluación, sin modificarse nunca: origen (LLM o RESPALDO_LONGITUD), clasificación, criterios faltantes, pregunta, `requiere_atencion`, modelo, versión del prompt, latencia, error y `texto_evaluado`. |

## Estados de una respuesta

```
(sin respuesta) --guardar borrador--> BORRADOR
BORRADOR o sin respuesta --enviar--> FINAL o PENDIENTE_SEGUIMIENTO (se crea el turno 1)
PENDIENTE_SEGUIMIENTO --guardar borrador--> igual (borrador de la respuesta al turno)
PENDIENTE_SEGUIMIENTO --responder seguimiento--> FINAL o PENDIENTE_SEGUIMIENTO (turno 2)
PENDIENTE_SEGUIMIENTO --continuar sin responder--> FINAL
FINAL --editar--> FINAL (sin evaluar)
```

## Acciones (POST)

Todas exigen actividad disponible, cuenta de estudiante e ítem de la actividad. Aceptan `fecha_hora`.

| Ruta | Efecto |
|---|---|
| `/acciones/registro/guardar-borrador` | Sin evaluar. En BORRADOR o sin respuesta, guarda `texto_inicial`; en PENDIENTE_SEGUIMIENTO, el borrador del turno; en FINAL, 409. |
| `/acciones/registro/enviar` | Guarda `texto_inicial`, lo evalúa y fija `clasificacion_inicial`. En FINAL, reemplaza el texto sin evaluar (edición). |
| `/acciones/registro/responder-seguimiento` | Guarda la respuesta del turno, marca `ampliada` y evalúa la conversación. Si el turno era la repregunta genérica, no evalúa: pasa a FINAL. En FINAL y con `orden`, edita ese turno sin evaluar. |
| `/acciones/registro/continuar-sin-responder` | Pasa a FINAL; el turno queda sin respuesta. |

**RESPUESTA_REFLEXIVA** se registra una sola vez por respuesta, al pasar a FINAL, si `clasificacion_inicial` es ADECUADA o `ampliada` es verdadero.

La respuesta al estudiante (`item`, `estado`, `conversacion`, eventos y desbloqueos) nunca incluye la clasificación, los criterios ni `requiere_atencion`.

## Evaluación

1. Texto vacío: 422.
2. Siempre se llama primero al evaluador, sea cual sea la longitud. Al responder un turno, evalúa la conversación completa del ítem.
3. ADECUADA → FINAL. VAGA con turnos disponibles → nuevo turno con la pregunta generada y los criterios que faltan. VAGA sin turnos → FINAL. `requiere_atencion` → FINAL, sin más preguntas; se guarda la marca y el estudiante no ve nada distinto.
4. **Respaldo por longitud**, si el evaluador falla, tarda demasiado o devuelve algo inválido (se registra con origen RESPALDO_LONGITUD y el error):
   - texto inicial con menos de `min_caracteres`: VAGA y un turno con `repregunta_generica`; su respuesta pasa a FINAL sin evaluar;
   - texto inicial que alcanza el mínimo: NO_EVALUADA y FINAL;
   - respuesta a un turno: FINAL.

   El estudiante nunca queda bloqueado por un fallo de la API.
5. Las preguntas solo buscan completar criterios faltantes. Si la respuesta ya cumple todos, no hay pregunta. Para pedir más profundidad, se agregan criterios al ítem, no preguntas.

**Evaluadores** (`evaluacion.py`, protocolo `EvaluadorRespuestas`, sin SQLAlchemy ni FastAPI):

- `EvaluadorGemini` (`gemini.py`): salida JSON estructurada, temperatura 0.2, razonamiento mínimo, tiempo máximo configurado. Valida el esquema, que los códigos de criterio existan y que los faltantes sean un subconjunto de los que faltaban. VAGA exige pregunta y faltantes; ADECUADA, faltantes vacíos. Si no se cumple, se trata como fallo.
- `EvaluadorFalso`: determinista, por marcas en el texto más reciente: sin marca, ADECUADA; `[vaga]`; `[falta:C2]`; `[atencion]`; `[falla]` (lanza error). Lo usan todas las pruebas.

**Contexto que recibe:** título de la actividad, consigna y criterios del ítem, criterios que faltaban, la conversación del ítem y las respuestas FINAL de los demás ítems de la actividad. Nunca nombres, códigos de cuenta ni otros datos que identifiquen al estudiante.

**Prompt:** la instrucción de sistema vigente está en `app/services/registro/prompt.py`. Cambiarla exige subir `VERSION_PROMPT_REGISTRO`.

## Transacciones

La llamada al LLM nunca ocurre dentro de una transacción ni con una conexión tomada:

1. Transacción corta: validar y leer la respuesta, sus turnos y las respuestas FINAL; anotar `estado` y `actualizada_en`.
2. Sin transacción: llamar al evaluador (o aplicar el respaldo).
3. Transacción corta: releer; si el estado o `actualizada_en` cambiaron, 409 sin escribir. Si no, guardar respuesta, evaluación y eventos y evaluar reglas.

## Consultas (GET)

| Ruta | Devuelve |
|---|---|
| `/actividades/{a}/items-registro` | Ítems en orden, con consigna, mínimo y obligatoriedad. Sin criterios. |
| `/cuentas/{c}/actividades/{a}/registro` | Posición, estado del progreso y, por ítem, estado y conversación (incluidos los borradores). |

Apoderados y cuentas o actividades inexistentes: 404. Completar una actividad de registro exige todos sus ítems obligatorios en FINAL (`motor.md`).
