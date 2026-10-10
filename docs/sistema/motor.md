# Motor de desbloqueos

Cómo funciona hoy el núcleo de la plataforma: las acciones registran eventos, y las reglas convierten esos eventos en desbloqueos. Código: `app/services/motor/`, `app/services/actividades.py`, `app/services/cuentas.py` y servicios de cada dominio. Datos: `datos/plataforma.py`.

## Modelo

| Grupo | Tablas |
|---|---|
| Cuentas | `cuenta` (rol ESTUDIANTE o APODERADO), `vinculo_familiar` (estudiante, apoderado y sus cartas) |
| Catálogo | `bloque` (espacio MISIONES_CAMPO o CIUDAD, audiencia), `actividad` (tipo INFORMATIVA, REGISTRO, CUESTIONARIO o CASO; `orden`, `contenido`, `visibilidad`, `puntaje_minimo` solo en CASO), `ficha`, `testimonio`, `pregunta_diario`, `conversacion`, `insignia` (`es_oculta`, audiencia), `nivel`, `familia_carrera`, `carrera` |
| Estado de la cuenta | `progreso_actividad` (EN_CURSO o COMPLETADA, `posicion`), `resultado_caso`, `entrada_diario`, `check_in`, `entrevista`, `entrevista_autor`, `conversacion_vinculo` |
| Motor | `evento_uso`, `regla_desbloqueo`, `condicion_desbloqueo`, `desbloqueo` (único por cuenta y regla; `visto`) |

`id_objetivo` de una regla e `id_referencia` de un evento o condición son referencias polimórficas sin FK; los cargadores resuelven códigos a ids. `id_objetivo` es nulo solo para CONVERSACIONES, que es una sección y no un objeto.

### A qué apunta `id_referencia`

| Evento | Referencia |
|---|---|
| INGRESO, RESPUESTA_REFLEXIVA, INVITA_A_CREW, FORMA_CREW, VENCE_DESAFIO_INTACTO | nula |
| COMPLETA_ACTIVIDAD, SUPERA_CASO | actividad |
| COMPLETA_BLOQUE | bloque |
| ESCRIBE_ENTRADA_DIARIO, ESCRIBE_ENTRADA_LIBRE | entrada de diario (se expone como `null`: no tiene código público) |
| REGISTRA_CHECK_IN | check-in (se expone como `null`) |
| VISTA_CARRERA | carrera |
| PUBLICA_ENTREVISTA | entrevista |
| ESCRIBE_CARTA | vínculo familiar |
| COMPLETA_CONVERSACION | conversación |
| REINICIA_INSTRUMENTO | instrumento |

## Reglas

Una regla se cumple cuando se cumplen **todas** sus condiciones y, si tiene `evaluador_especial`, el evaluador devuelve verdadero. Una alternativa (A **o** B) se expresa con dos reglas que apuntan al mismo objetivo.

Cada condición cuenta los eventos de la cuenta con su `tipo_evento` (y su `id_referencia`, si la tiene) según `tipo_conteo`, y se cumple si el conteo es ≥ `cantidad_minima`:

| `tipo_conteo` | Cuenta | Ejemplo |
|---|---|---|
| EVENTOS | eventos | «completó esta actividad» |
| REFERENCIAS_DISTINTAS | referencias distintas, sin contar nulas | «8 actividades distintas»: repetir no suma |
| DIAS_DISTINTOS | fechas calendario distintas de `fecha_hora`, sin convertir a UTC | «check-in en 3 días distintos» |

**Evaluadores especiales** (`app/services/motor/evaluadores.py`, registro `EVALUADORES`). Reciben sesión y cuenta y leen su umbral de `regla_desbloqueo.parametro_evaluador`, no de `cantidad_minima`:

- `carreras_de_3_familias`: los eventos VISTA_CARRERA apuntan a carreras de al menos `parametro` familias distintas.
- `misiones_camino_sin_inicio`: la cuenta completó al menos `parametro` actividades distintas del bloque CAMINO, sin contar la de orden 1.

Una regla con evaluador también tiene condiciones normales: definen con qué eventos se reevalúa. Una regla sin condiciones o con un evaluador desconocido es un error de configuración (`ValueError`), nunca un desbloqueo.

## Evaluación

Cuando una acción registra eventos (`registrar_eventos`), el motor, en la misma transacción:

1. Inserta todos los eventos.
2. Toma las reglas que la cuenta aún no tiene, cuyo objetivo es de su audiencia y que tienen al menos una condición con el tipo de algún evento recién registrado.
3. Las evalúa en orden de código y crea un `desbloqueo` por cada una que se cumple.
4. Devuelve los desbloqueos nuevos, con el progreso de cada condición.

Si una acción registra eventos en varias cuentas (coautoría de entrevista, conversación familiar), cada cuenta se evalúa con sus propios eventos. Los desbloqueos no generan eventos: una pasada basta y no hay cascadas. Un desbloqueo es permanente.

## Disponibilidad

Un objetivo está disponible para una cuenta si:

1. **Audiencia:** corresponde a su rol. Si no, no aparece en sus consultas (y su progreso responde 404).
2. **Bloque contenedor:** si es una actividad, su bloque está disponible. Se comprueba al consultar, no al desbloquear.
3. **Reglas:** ninguna regla apunta a él, o la cuenta tiene el desbloqueo de al menos una.

| Objetivo | Audiencia |
|---|---|
| BLOQUE | `bloque.audiencia` |
| ACTIVIDAD | la de su bloque |
| INSIGNIA | `insignia.audiencia` |
| FICHA, TESTIMONIO, PREGUNTA_DIARIO, NIVEL | solo ESTUDIANTE |
| CONVERSACIONES | ambos roles |

Al desbloquearse un bloque, sus actividades sin regla propia quedan disponibles; las que tienen regla siguen bloqueadas hasta cumplirla. Un objetivo sin reglas está disponible desde el inicio: por eso todo logro que aún no se puede ganar necesita una regla.

**Estado de una actividad:** BLOQUEADA si ella o su bloque no están disponibles (prevalece sobre cualquier progreso); si no, COMPLETADA, EN_CURSO o DISPONIBLE según su progreso.

**Nivel actual:** el de mayor `numero` disponible. El nivel 1 no tiene reglas. Las reglas de cada nivel repiten las condiciones del anterior, así que el nivel nunca baja ni se salta. Para un apoderado es `null`.

**Insignia oculta no obtenida:** se muestra con código `???`, nombre «Logro oculto» y sin descripción ni requisito; al obtenerla se muestra completa.

## Acciones

Todas reciben `cuenta` y `fecha_hora` opcional, y devuelven `eventos_registrados` y `nuevos_desbloqueos`. Las que afectan a varias cuentas devuelven `{"por_cuenta": {codigo: {...}}}`.

| Acción (POST) | Valida | Efecto y eventos |
|---|---|---|
| `/acciones/ingresar` | — | INGRESO |
| `/acciones/completar-actividad` | Actividad disponible y no CASO. Si tiene ítems de instrumento, todos respondidos; si tiene ítems de registro obligatorios, todos en FINAL (si no, 409 con `items_faltantes`, sin eventos). | Progreso a COMPLETADA. COMPLETA_ACTIVIDAD en **cada** finalización, también al repetir. COMPLETA_BLOQUE la primera vez que se completan todas las actividades del bloque. Puede generar resultados de instrumentos (`resultados_generados`). |
| `/acciones/resolver-caso` | Actividad CASO disponible; puntaje 0–100 | Guarda el intento y completa la actividad. SUPERA_CASO la primera vez que el puntaje ≥ `puntaje_minimo`. |
| `/acciones/responder-registro` | Clasificación ADECUADA o VAGA | RESPUESTA_REFLEXIVA si es ADECUADA o `ampliada`. (Acción simple; el registro con evaluador está en `registro.md`.) |
| `/acciones/escribir-entrada` | Solo estudiante; GUIADA exige pregunta disponible y no respondida; LIBRE sin pregunta | ESCRIBE_ENTRADA_DIARIO y, si es LIBRE, ESCRIBE_ENTRADA_LIBRE. |
| `/acciones/check-in` | Solo estudiante; uno por día; nivel 1–5 | REGISTRA_CHECK_IN |
| `/acciones/ver-carrera` | — | VISTA_CARRERA |
| `/acciones/publicar-entrevista` | Autores: lista no vacía, sin repetidos, todos estudiantes | PUBLICA_ENTREVISTA en cada autor. Código `ENT-<uuid>`. |
| `/acciones/escribir-carta` | La cuenta pertenece a un vínculo | Guarda la carta de su rol; ESCRIBE_CARTA solo la primera vez. |
| `/acciones/completar-conversacion` | CONVERSACIONES disponible para quien marca | Marca la conversación del vínculo; COMPLETA_CONVERSACION en las dos cuentas, solo la primera vez. |
| `/eventos` (depuración) | Solo que existan cuenta y referencia | Registra un evento crudo y evalúa reglas, sin validaciones de dominio ni cambios de estado. |

Las acciones de instrumentos (`responder-items`, `reiniciar-instrumento`) están en `instrumentos.md`, y las de registro, en `registro.md`.

## Consultas del motor

| GET | Devuelve |
|---|---|
| `/reglas` | Todas las reglas, legibles, por código. No evalúa. |
| `/cuentas` | Cuentas. |
| `/cuentas/{c}/progreso/{tipo}/{codigo}` | Cada regla del objetivo con el avance de cada condición (`actual`, `requerido`, `cumplida`) y del evaluador. Niveles con código `N1`…`N5`; CONVERSACIONES con `-`. Insignia oculta no obtenida: 403. Tipo inválido: 422. |
| `/cuentas/{c}/eventos` | Línea de tiempo, del más reciente al más antiguo. |
| `/cuentas/{c}/desbloqueos?solo_no_vistos=true` | Desbloqueos con fecha y objetivo. |
| POST `/cuentas/{c}/desbloqueos/marcar-vistos` | Marca los pendientes; devuelve `{"marcados": n}`. |

Las consultas de lectura por dominio (`resumen`, `actividades`, `fichas`, `logros`…) están en `integracion.md`.

## Invariantes

1. Nunca hay dos desbloqueos para la misma cuenta y regla, y ninguno se elimina.
2. Una actividad bloqueada no se puede completar: 409 sin eventos.
3. Una cuenta nunca ve objetivos de otra audiencia.
4. COMPLETA_BLOQUE, SUPERA_CASO, ESCRIBE_CARTA y COMPLETA_CONVERSACION se registran solo la primera vez por referencia y cuenta; COMPLETA_ACTIVIDAD, en cada finalización.
5. Repetir una actividad no cambia su estado COMPLETADA.
6. Un check-in por día y una entrada GUIADA por pregunta.
7. El nivel actual nunca baja.
