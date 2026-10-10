# Instrumentos, resultados y recomendación

Cuestionarios repartidos en actividades, cálculo de resultados y recomendación de ocupaciones y carreras. Código: `app/services/instrumentos/` (`calculo.py` es puro, sin base), `app/services/actividades.py` (responder, completar, reiniciar). Parámetros: `app/core/parametros.py`. Datos: `datos/plataforma.py` y `datos/ocupaciones.py`.

## Modelo

| Tabla | Qué guarda |
|---|---|
| `instrumento` | `tipo_resultado`: COINCIDENCIAS (RIASEC), DESTACADAS (inteligencias, habilidades sociales) o COMPARACION (autopercepción). |
| `dimension` | Dimensiones con `orden` y `descripcion` (la que ve el estudiante). Un instrumento de COMPARACION no tiene dimensiones. |
| `escala_respuesta`, `opcion_escala` | Opciones con `orden`, `etiqueta` y `puntaje`. |
| `item_instrumento` | `numero`, `enunciado`, dimensión, escala e `inverso`. |
| `actividad_item` | Qué ítems presenta cada actividad y en qué orden. |
| `aplicacion`, `aplicacion_actividad` | Una aplicación del instrumento (`momento` UNICA, ENTRADA o SALIDA) y sus actividades. |
| `ocupacion`, `puntaje_ocupacion` | Catálogo O*NET (código, título, `codigo` del front y seis puntajes RIASEC). |
| `carrera_ocupacion` | Ocupaciones a las que conduce cada carrera. |
| `respuesta_item` | Respuesta por progreso de actividad e ítem (única). |
| `resultado_instrumento`, `resultado_dimension`, `coincidencia` | Resultado calculado, con `anulado_en` y `perfil_plano`. A lo sumo uno vigente por cuenta y aplicación; los anulados quedan como historial. |

Dentro de una aplicación, cada ítem del instrumento se presenta en exactamente una actividad; la carga lo valida (`validar_distribucion_items`).

**Catálogo O*NET.** `datos/ocupaciones.py` lee `datos/archivos/Career_Interest_RIASEC_Clean.xlsx` (columnas `code, title, R, I, A, S, E, C`) solo al cargar la base. Encabezado distinto, valores no numéricos o códigos repetidos detienen la carga. La aplicación nunca lee el Excel.

**Escala RIASEC.** `ESC-LIKERT5`: la opción 1–5 que marca el estudiante vale 0–4 (transformación O*NET, aplicada solo al sembrar). El cálculo usa siempre los puntajes guardados en `opcion_escala`.

## Responder ítems — `POST /acciones/responder-items`

- Cuerpo: `cuenta`, `actividad`, `respuestas: [{item, opcion}]` (opción por su `orden`).
- Lote no vacío, sin ítems repetidos, opciones enteras de la escala del ítem: si no, 422. Un ítem que la actividad no presenta: 409. Actividad no disponible: 409 con su progreso. Apoderado: 404.
- Se valida todo el lote antes de escribir. La primera respuesta crea el progreso en EN_CURSO; reemplazar una respuesta conserva su fila y `creada_en`.
- Las respuestas quedan **fijas** (409) si alguna aplicación de la actividad tiene resultado vigente; en COMPARACION, cuando la actividad está COMPLETADA.
- No registra eventos.

## Completar y calcular

`completar-actividad` exige todos los ítems de la actividad respondidos (si no, 409 con `items_faltantes`). Después de los eventos y desbloqueos, en la misma transacción: para cada aplicación de la actividad, si todas sus actividades están COMPLETADA, el instrumento tiene dimensiones y no hay resultado vigente, se calcula el resultado y se informa en `resultados_generados`. Si el cálculo falla, se revierte toda la acción. Repetir una actividad con respuestas fijas registra COMPLETA_ACTIVIDAD pero no recalcula.

**Cálculo** (`calculo.py`):

- Puntaje del ítem: el de la opción; si es inverso, `máximo + mínimo − puntaje` de su escala.
- Dimensión: suma de sus ítems; máximo = suma de los máximos; porcentaje = `100 × puntaje / máximo`, redondeado a 2 decimales.
- Entradas inválidas (puntaje fuera de escala, vectores incompletos, máximo no positivo): `ValueError`, nunca un valor inventado.

**Coincidencias (COINCIDENCIAS):**

1. Vector del estudiante en el orden de `dimension.orden` (R, I, A, S, E, C).
2. Si los seis puntajes son iguales: `perfil_plano`, sin coincidencias.
3. Si no, Pearson (`statistics.correlation`) con cada ocupación. Se descartan las negativas. BEST_FIT si r ≥ 0.729; GREAT_FIT si 0.608 ≤ r < 0.729; GOOD_FIT si 0 ≤ r < 0.608.
4. Se guardan las 10 primeras por r descendente, con `codigo_onet` ascendente como desempate. La correlación se guarda sin redondear y se expone con 6 decimales.

**Derivados al consultar** (no se guardan):

- Código de interés: las 3 dimensiones de mayor puntaje, con el orden de las dimensiones como desempate. `hay_empate` si la tercera y la cuarta empatan.
- Carreras recomendadas: las vinculadas a alguna de las 10 ocupaciones, ordenadas por su mejor posición (y código); cada una con `via`, las ocupaciones que la vinculan.
- Dimensiones destacadas (DESTACADAS): las de mayor proporción exacta `puntaje / máximo` (no el porcentaje redondeado); si empatan, todas, en el orden del instrumento.

**Comparación (COMPARACION):** con las aplicaciones ENTRADA y SALIDA completas (elegidas por `momento`, nunca por código), devuelve por ítem la opción y el puntaje de cada una y la diferencia salida − entrada. No genera resultado.

## Reiniciar — `POST /acciones/reiniciar-instrumento`

Recibe `cuenta`, `instrumento` y `aplicacion` (obligatoria si hay más de una: si falta, 422). En una transacción: anula el resultado vigente, borra las respuestas del instrumento en los progresos de la aplicación, pasa esos progresos a EN_CURSO y registra REINICIA_INSTRUMENTO. No revoca desbloqueos ni borra eventos ni resultados anteriores. Sin respuestas ni resultado vigente: 409 «Nada que reiniciar».

## Consultas (GET)

| Ruta | Devuelve |
|---|---|
| `/instrumentos` | Instrumentos con dimensiones (con descripción), escalas, aplicaciones y actividades. |
| `/actividades/{a}/items` | Ítems de la actividad en orden, con las opciones de su escala. No exige cuenta ni disponibilidad. |
| `/cuentas/{c}/actividades/{a}/respuestas` | Respuestas actuales de la cuenta en esa actividad. |
| `/cuentas/{c}/instrumentos` | Por instrumento y aplicación: NO_INICIADO, EN_PROGRESO o COMPLETADO; actividades e ítems respondidos sobre el total; si hay resultado vigente. |
| `/cuentas/{c}/instrumentos/{i}/resultado?aplicacion=` | Resultado vigente: dimensiones (con `descripcion`), y según el tipo, `codigo_interes`, `coincidencias`, `carreras_recomendadas` o `dimensiones_destacadas`. Sin vigente: 409 con el avance. |
| `/cuentas/{c}/instrumentos/{i}/historial` | Todos los resultados, incluidos los anulados, del más reciente al más antiguo. |
| `/cuentas/{c}/instrumentos/{i}/comparacion` | Comparación de entrada y salida. Instrumento de otro tipo: 404. Sin las dos aplicaciones completas: 409. |

Las consultas con cuenta responden 404 a un apoderado. El resultado se arma con lo guardado, sin recalcular.

## Invariantes

1. A lo sumo un resultado vigente por cuenta y aplicación, y solo con todas sus actividades COMPLETADA.
2. Mientras hay resultado vigente, sus respuestas no cambian.
3. Reiniciar solo anula; nunca borra resultados, eventos ni desbloqueos.
4. Las respuestas de una cuenta nunca afectan a otra.
5. Toda coincidencia guardada tiene r ≥ 0 y el ajuste que corresponde a los umbrales.
