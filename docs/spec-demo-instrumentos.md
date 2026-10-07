# Demo de instrumentos, resultados y recomendación de carreras: especificación para FastAPI

## 1. Objetivo

Extender el backend de la demo de desbloqueos para verificar que el modelo de datos permite:

1. Presentar un instrumento repartido en varias actividades (bloques de preguntas) y guardar sus respuestas.
2. Calcular sus resultados al completar la última actividad del instrumento.
3. Mostrar esos resultados: puntaje y porcentaje por dimensión, código de interés y, para el RIASEC, las ocupaciones afines con su correlación de Pearson y las carreras recomendadas.
4. Comparar un mismo instrumento aplicado dos veces (autopercepción de entrada y salida).
5. Reiniciar un instrumento, de modo que el estudiante deba rehacer las actividades que lo componen.

Al final se agrega una interfaz mínima para probar estos métodos de forma interactiva.

## 2. Punto de partida

El backend ya implementa `docs/spec-demo-motor-desbloqueos.md` (motor de desbloqueos, acciones, consultas, página `/demo`) con las decisiones de `docs/decisiones.md`. Este documento se agrega a ese proyecto:

- **No modifica** la semántica del motor, la semilla existente ni los resultados esperados de E1 a E17. Los 188 tests actuales deben seguir pasando.
- Solo se permite actualizar tests existentes en dos casos, y hay que anotarlo en `docs/decisiones.md`:
  - conteos del catálogo o de reglas (por ejemplo, 42 → 47 reglas y 53 → 58 condiciones);
  - listas exactas de bloques, actividades o carreras, para incluir los elementos nuevos de este documento;
  - tests que verifican que EN_CURSO no se muestra en el estado (por ejemplo, `test_estado_no_expone_en_curso`). Esa expectativa venía de la decisión de la fase 3, tomada porque la primera demo no tenía actividades a medias. La sección 5.9 la reemplaza: esos tests pasan a esperar EN_CURSO para una actividad disponible con progreso EN_CURSO, y la decisión de la fase 3 se marca como reemplazada en `docs/decisiones.md`.
- Las decisiones nuevas se agregan a `docs/decisiones.md` bajo el título "Instrumentos".
- **Base local existente:** no se implementan migraciones. Como el esquema cambia (tablas nuevas y el evento REINICIA_INSTRUMENTO), la `demo.db` anterior se descarta: se borra el archivo antes de levantar la aplicación, y el arranque la recrea con la semilla completa. Si al arrancar se detecta una `demo.db` con un esquema incompatible, la aplicación falla con un mensaje que indica borrarla, en lugar de intentar repararla. Los tests usan bases temporales y no dependen de `demo.db`.
- Nueva dependencia permitida: `openpyxl`, para leer el archivo de ocupaciones (`uv add openpyxl`). El coeficiente de Pearson se calcula con `statistics.correlation`, de la biblioteca estándar; no se agrega numpy.

## 3. Modelo de datos

### 3.1 Enumerados nuevos o ampliados

| Enumerado | Valores |
|---|---|
| `TipoEventoUso` | se agrega REINICIA_INSTRUMENTO (`id_referencia` = instrumento) |
| `NivelAjuste` | BEST_FIT, GREAT_FIT, GOOD_FIT |

### 3.2 Tablas nuevas

**Definición de instrumentos** (se cargan con la semilla)

| Tabla | Columnas | Restricción |
|---|---|---|
| `instrumento` | id, codigo (único), nombre, descripcion | |
| `dimension` | id, instrumento_id, codigo (único), nombre, descripcion, orden | |
| `escala_respuesta` | id, codigo (único), nombre | |
| `opcion_escala` | id, escala_id, orden, etiqueta, puntaje | único (escala_id, orden) |
| `item_instrumento` | id, instrumento_id, codigo (único), numero, enunciado, dimension_id (nullable), escala_id, inverso (bool) | único (instrumento_id, numero) |
| `actividad_item` | actividad_id, item_id, orden | clave compuesta (actividad_id, item_id) |
| `aplicacion` | id, instrumento_id, codigo (único), nombre | |
| `aplicacion_actividad` | aplicacion_id, actividad_id | clave compuesta |

`dimension_id` es nulo en los instrumentos sin dimensiones (autopercepción). Un mismo ítem puede presentarse en varias actividades (tabla `actividad_item`), pero dentro de una aplicación cada ítem del instrumento aparece en exactamente una actividad. La carga de la semilla debe validar esta regla.

**Catálogo O*NET**

| Tabla | Columnas | Restricción |
|---|---|---|
| `ocupacion` | id, codigo_onet (único), titulo | |
| `puntaje_ocupacion` | ocupacion_id, dimension_id, valor (float) | clave compuesta |
| `carrera_ocupacion` | carrera_id, ocupacion_id | clave compuesta; cada carrera tiene al menos una ocupación |

**Respuestas y resultados**

| Tabla | Columnas | Restricción |
|---|---|---|
| `respuesta_item` | id, progreso_id → progreso_actividad, item_id, opcion_id, creada_en, actualizada_en | único (progreso_id, item_id) |
| `resultado_instrumento` | id, cuenta_id, aplicacion_id, calculado_en, anulado_en (nullable), perfil_plano (bool) | a lo sumo uno vigente (`anulado_en` nulo) por (cuenta_id, aplicacion_id) |
| `resultado_dimension` | resultado_id, dimension_id, puntaje (float), puntaje_maximo (float), porcentaje (float) | clave compuesta |
| `coincidencia` | resultado_id, ocupacion_id, posicion (1 a 10), correlacion (float), ajuste | clave compuesta (resultado_id, ocupacion_id) |

Un resultado anulado no se borra: queda como historial, con sus dimensiones y coincidencias.

## 4. Datos semilla

### 4.1 Bloque de laboratorio

Para no alterar los escenarios de desbloqueo ya validados, los instrumentos se presentan en un bloque nuevo, exclusivo de la demo. En la plataforma real estas actividades son las misiones de Helena en la ciudad y los cuestionarios de entrada y salida.

| Bloque | Nombre | Espacio | Audiencia | Regla de bloque |
|---|---|---|---|---|
| LAB | Laboratorio de Helena (solo demo) | CIUDAD | ESTUDIANTE | ninguna: disponible desde el inicio |

| Actividad (orden) | Título | Tipo | Instrumento e ítems |
|---|---|---|---|
| LAB-AUT-E (1) | Autopercepción de entrada | CUESTIONARIO | TEST-AUTO, ítems 1 a 10 |
| LAB-AUT-S (2) | Autopercepción de salida | CUESTIONARIO | TEST-AUTO, ítems 1 a 10 (los mismos) |
| LAB-HAB (3) | Mi comportamiento con los demás | CUESTIONARIO | TEST-HAB, ítems 1 a 24 |
| LAB-INT1 (4) | Explorando mis inteligencias I | CUESTIONARIO | TEST-INT, ítems 1 a 22 |
| LAB-INT2 (5) | Explorando mis inteligencias II | CUESTIONARIO | TEST-INT, ítems 23 a 43 |
| LAB-RIA1 (6) | Mis intereses I | CUESTIONARIO | TEST-RIASEC, ítems 1 a 15 |
| LAB-RIA2 (7) | Mis intereses II | CUESTIONARIO | TEST-RIASEC, ítems 16 a 30 |
| LAB-RIA3 (8) | Mis intereses III | CUESTIONARIO | TEST-RIASEC, ítems 31 a 45 |
| LAB-RIA4 (9) | Mis intereses IV | CUESTIONARIO | TEST-RIASEC, ítems 46 a 60 |

Reglas nuevas (objetivo ACTIVIDAD):

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-LAB-AUT-S | LAB-AUT-S | COMPLETA_ACTIVIDAD(LAB-AUT-E) ≥ 1 |
| R-LAB-INT2 | LAB-INT2 | COMPLETA_ACTIVIDAD(LAB-INT1) ≥ 1 |
| R-LAB-RIA2 | LAB-RIA2 | COMPLETA_ACTIVIDAD(LAB-RIA1) ≥ 1 |
| R-LAB-RIA3 | LAB-RIA3 | COMPLETA_ACTIVIDAD(LAB-RIA2) ≥ 1 |
| R-LAB-RIA4 | LAB-RIA4 | COMPLETA_ACTIVIDAD(LAB-RIA3) ≥ 1 |

LAB-AUT-E, LAB-HAB, LAB-INT1 y LAB-RIA1 no tienen regla: están disponibles desde el inicio.

### 4.2 Escalas

| Escala | Opciones (orden: etiqueta = puntaje) |
|---|---|
| ESC-LIKERT5 | 1: Me disgusta mucho = 0; 2: Me disgusta = 1; 3: No estoy seguro = 2; 4: Me gusta = 3; 5: Me gusta mucho = 4 |
| ESC-SI-NO | 1: Sí = 1; 2: No = 0 |
| ESC-FRECUENCIA | 1: Casi siempre = 1; 2: Casi nunca = 0 |
| ESC-A-D | 1: A (Bastante) = 4; 2: B (Regular) = 3; 3: C (Poco) = 2; 4: D (Nada) = 1 |

En el RIASEC, el orden de la opción coincide con el valor 1 a 5 que marca el estudiante, y el puntaje aplica la transformación de O*NET a 0 a 4.

### 4.3 Instrumentos

Los enunciados no participan en ningún cálculo. Donde no se indican, se usa un texto de demostración: `Ítem {numero} de {nombre del instrumento}`.

**TEST-RIASEC: O*NET Interest Profiler (forma corta)**

- 60 ítems, escala ESC-LIKERT5, códigos `RIASEC-01` a `RIASEC-60`.
- Dimensiones, en este orden: R Realista, I Investigativa, A Artística, S Social, E Emprendedora, C Convencional. La descripción de cada una es un texto breve de demostración.
- Dimensión de cada ítem: patrón `R R I I A A S S E E C C` repetido 5 veces. El ítem `n` pertenece a `patron[(n - 1) % 12]`, así que cada dimensión tiene 10 ítems y un máximo de 40 puntos.
- Aplicación única: APL-RIASEC, con las actividades LAB-RIA1 a LAB-RIA4.

**TEST-INT: Explorando mis inteligencias**

- 43 ítems, escala ESC-SI-NO, códigos `INT-01` a `INT-43`.
- Aplicación única: APL-INT, con las actividades LAB-INT1 y LAB-INT2.

| Dimensión | Ítems |
|---|---|
| INT-LIN Lingüística | 1, 8, 11, 17, 21, 24, 27, 36, 41, 43 |
| INT-LOG Lógico-matemática | 3, 6, 13, 20, 25, 28, 37 |
| INT-ESP Espacial | 7, 18, 26, 29 |
| INT-CIN Cinestésico-corporal | 2, 14, 19, 30, 38 |
| INT-MUS Musical | 5, 10, 31, 39 |
| INT-INTER Interpersonal | 4, 9, 16, 22, 32, 34, 40, 42 |
| INT-INTRA Intrapersonal | 12, 15, 23, 33, 35 |

**TEST-HAB: Mi comportamiento con los demás**

- 24 ítems, escala ESC-FRECUENCIA, códigos `HAB-01` a `HAB-24`.
- Aplicación única: APL-HAB, con la actividad LAB-HAB.
- Solo la dimensión de asertividad proviene de la rejilla oficial. Las demás son **provisionales**, para probar el modelo, incluido el atributo `inverso`, y deben reemplazarse por la rejilla oficial antes de usarse con estudiantes.

| Dimensión | Ítems | Ítems inversos |
|---|---|---|
| HAB-ASE Asertividad (oficial) | 1, 10, 15, 19, 21 | ninguno |
| HAB-EMP Empatía (provisional) | 4, 7, 16, 22 | ninguno |
| HAB-LID Liderazgo (provisional) | 5, 14, 20 | 5, 20 |
| HAB-RES Resolución de problemas (provisional) | 6, 13, 17, 24 | ninguno |
| HAB-EXP Expresión de sentimientos (provisional) | 3, 8, 23 | 3, 8 |
| HAB-VAL Valores y participación (provisional) | 2, 9, 11, 12, 18 | ninguno |

**TEST-AUTO: Cuestionario de autopercepción**

- 10 ítems, escala ESC-A-D, códigos `AUT-01` a `AUT-10`, **sin dimensiones**.
- Dos aplicaciones: APL-AUTO-ENT (actividad LAB-AUT-E) y APL-AUTO-SAL (actividad LAB-AUT-S). Ambas presentan los mismos 10 ítems.
- Enunciados:
  1. Tengo información acerca de cómo se desempeña un profesional en la carrera que me gusta.
  2. Conozco las instituciones dónde estudiar la carrera que me gusta.
  3. La elección de mi futura profesión está influenciada por los consejos de mi grupo de amigos/as.
  4. Mis padres o algún otro pariente han contribuido mucho a la decisión de mi futura profesión.
  5. Tengo razones para decir que me gusta mi futura profesión porque goza de buena reputación y de reconocimiento social.
  6. La decisión de mi futura profesión está influenciada por el dinero que podré recibir de ella.
  7. Siendo consciente de los recursos económicos de mi familia, me siento obligado a elegir una profesión que no es de mi total satisfacción.
  8. Pienso que una carrera de mando intermedio no tiene la reputación social que deseo, por ello no la considero una posibilidad.
  9. En realidad estoy seguro(a) de lo que voy a estudiar.
  10. Los calificativos más altos que he obtenido están en los cursos que considero elementales para mi futura profesión.

### 4.4 Ocupaciones

Se cargan desde `data/Career_Interest_RIASEC_Clean.xlsx`, que el usuario copia al proyecto. Columnas: `code`, `title`, `R`, `I`, `A`, `S`, `E`, `C`. Cada fila crea una `ocupacion` y sus seis `puntaje_ocupacion` sobre las dimensiones del TEST-RIASEC.

La carga se hace dentro de la semilla y de `/demo/reiniciar`. Si el archivo falta, tiene columnas distintas, valores no numéricos o códigos repetidos, la carga falla con un mensaje claro. No se inventan datos.

### 4.5 Carreras y su relación con ocupaciones

Se agregan tres carreras a la familia existente FAM-INGENIERIA. Las cinco carreras existentes no cambian de familia.

| Carrera | Nombre | Ocupaciones O*NET |
|---|---|---|
| CAR-ENF | Enfermería | 29-1141.00 |
| CAR-MED | Medicina | 29-1216.00 |
| CAR-CIV | Ingeniería civil | 17-2051.00 |
| CAR-DIS | Diseño gráfico | 27-1024.00 |
| CAR-ADM | Administración | 11-1021.00 |
| CAR-AGR (nueva) | Ingeniería agrícola | 17-2021.00 |
| CAR-FOR (nueva) | Ingeniería forestal | 19-1031.02, 19-1032.00 |
| CAR-AMB (nueva) | Ingeniería ambiental | 17-2199.11, 19-2041.02 |

Si algún código no existe en el archivo, la carga falla indicando cuál. La única excepción es 29-1216.00: si falta, se usa el primer código del archivo que empiece con `29-12`, y se anota en `docs/decisiones.md`.

## 5. Lógica

### 5.1 Responder ítems

- Solo se responden ítems de una actividad disponible para la cuenta, y solo ítems presentados en esa actividad.
- La opción se indica por su `orden` y debe pertenecer a la escala del ítem.
- Responder crea el `progreso_actividad` en EN_CURSO si no existe, y crea o reemplaza la respuesta del ítem en ese progreso.
- Si la aplicación de esa actividad ya tiene un resultado vigente, las respuestas están **fijas**: la acción responde 409. Para instrumentos sin dimensiones (TEST-AUTO), las respuestas quedan fijas cuando la actividad está COMPLETADA.
- Responder no registra eventos.

### 5.2 Completar una actividad con ítems

La acción existente `/acciones/completar-actividad` agrega una validación: si la actividad presenta ítems de instrumento, todos deben estar respondidos en su progreso. Si falta alguno, responde 409 con la lista de códigos de ítems faltantes, sin registrar eventos. Las actividades sin ítems se comportan exactamente igual que antes.

Después de registrar los eventos y evaluar las reglas, en la misma transacción:

1. Para cada aplicación que incluye la actividad, si todas sus actividades están COMPLETADA para la cuenta, el instrumento tiene dimensiones y no hay un resultado vigente, se calcula el resultado (5.3).
2. La respuesta de la acción agrega `resultados_generados`: una lista de `{instrumento, aplicacion}`, vacía si no se generó ninguno.

Si el cálculo falla, se revierte toda la acción, incluidos los eventos y los desbloqueos.

Rehacer una actividad cuyas respuestas están fijas se permite, como cualquier actividad: registra COMPLETA_ACTIVIDAD, pero no modifica respuestas ni recalcula resultados.

### 5.3 Cálculo del resultado

Para cada ítem del instrumento se toma la respuesta de la actividad de la aplicación que lo presenta. Luego:

- **Puntaje del ítem:** el puntaje de la opción elegida. Si el ítem es inverso: `máximo de la escala + mínimo de la escala − puntaje`. En Sí/No esto es `1 − puntaje`.
- **Puntaje de la dimensión:** la suma de los puntajes de sus ítems.
- **Puntaje máximo de la dimensión:** la suma del máximo de la escala de cada uno de sus ítems.
- **Porcentaje:** `100 × puntaje / puntaje máximo`, redondeado a 2 decimales.

Se guarda un `resultado_instrumento` con un `resultado_dimension` por dimensión. Si el instrumento es TEST-RIASEC, se calculan además las coincidencias (5.4).

### 5.4 Coincidencias con ocupaciones (solo RIASEC)

1. El vector del estudiante son sus puntajes en el orden R, I, A, S, E, C.
2. Si los seis puntajes son iguales, `perfil_plano` es verdadero y no se calculan coincidencias: la correlación no está definida.
3. En otro caso, para cada ocupación se calcula `r = statistics.correlation(vector_estudiante, vector_ocupacion)`.
4. Se descartan las ocupaciones con `r < 0`. Las demás se clasifican:
   - BEST_FIT si `r ≥ 0.729`;
   - GREAT_FIT si `0.608 ≤ r < 0.729`;
   - GOOD_FIT si `0 ≤ r < 0.608`.
5. Se ordenan por `r` descendente, con `codigo_onet` ascendente como desempate, y se guardan las **10 primeras** con su posición.

### 5.5 Carreras recomendadas

Se derivan al consultar, sin guardarse: son las carreras vinculadas a alguna de las 10 ocupaciones del resultado vigente.

- Cada carrera se ordena por la mejor posición entre sus ocupaciones.
- Cada carrera incluye `via`: la lista de ocupaciones del top 10 que la vinculan, con posición, título, correlación y ajuste.

### 5.6 Código de interés del estudiante

Son las 3 dimensiones de mayor puntaje del RIASEC, de mayor a menor, con el orden R, I, A, S, E, C como desempate. Se agrega `hay_empate`, que es verdadero si la tercera y la cuarta dimensión tienen el mismo puntaje. El código se deriva del resultado y no se guarda.

### 5.6.1 Dimensiones destacadas (inteligencias y habilidades sociales)

Para TEST-INT y TEST-HAB, el resultado muestra la dimensión más destacada: la de mayor porcentaje. Si varias empatan en el porcentaje más alto, se muestran todas, en el orden de las dimensiones del instrumento.

- La comparación usa la proporción exacta `puntaje / puntaje máximo`, no el porcentaje redondeado. Así, dos dimensiones con 4 de 7 y 57.14% redondeado no empatan por error de redondeo con otra que no tenga exactamente la misma proporción.
- Si todas las dimensiones tienen 0%, todas quedan destacadas, por aplicación directa de la regla.
- Se deriva del resultado y no se guarda, igual que el código de interés.

### 5.7 Comparación de autopercepción

Requiere que ambas aplicaciones estén completas (LAB-AUT-E y LAB-AUT-S COMPLETADA). Para cada ítem devuelve la opción y el puntaje de entrada, la opción y el puntaje de salida, y la diferencia (salida − entrada). No genera `resultado_instrumento`.

### 5.8 Reinicio de un instrumento

`/acciones/reiniciar-instrumento` recibe la cuenta, el instrumento y, si el instrumento tiene más de una aplicación, la aplicación (si falta, responde 422). Si el instrumento tiene una sola aplicación, se usa esa.

En una sola transacción:

1. Si hay un resultado vigente de esa aplicación, se anula (`anulado_en` = fecha de la acción). No se borra.
2. Se borran las respuestas a ítems de ese instrumento en los progresos de las actividades de la aplicación.
3. Esos progresos pasan a EN_CURSO. Las actividades sin progreso no cambian.
4. Se registra REINICIA_INSTRUMENTO en la cuenta y se evalúan reglas, como con cualquier evento. Ninguna regla de la semilla lo usa.

El reinicio **no** revoca desbloqueos ni borra eventos. Por ejemplo, LAB-RIA2 a LAB-RIA4 siguen disponibles aunque se reinicie el RIASEC. Reiniciar una aplicación sin respuestas ni resultado responde 409 ("nada que reiniciar").

En la plataforma real solo la orientadora podrá reiniciar un instrumento. En la demo no hay autenticación.

### 5.9 Estado de las actividades

`/cuentas/{cuenta}/estado` ahora muestra EN_CURSO para una actividad disponible con progreso EN_CURSO: tras responder algún ítem o tras un reinicio. El resto de los estados no cambia.

## 6. Endpoints

### 6.1 Acciones (POST)

| Endpoint | Cuerpo | Respuesta |
|---|---|---|
| `/acciones/responder-items` | cuenta, actividad, respuestas: `[{item, opcion}]` | respuestas guardadas y progreso de la actividad (respondidos / total) |
| `/acciones/completar-actividad` | como antes | como antes, más `resultados_generados` |
| `/acciones/reiniciar-instrumento` | cuenta, instrumento, aplicacion (opcional) | resultado anulado (si había), actividades reiniciadas, eventos registrados |

Todas aceptan `fecha_hora` opcional, como las acciones existentes.

### 6.2 Consultas (GET)

| Endpoint | Devuelve |
|---|---|
| `/instrumentos` | instrumentos con sus dimensiones, escalas, aplicaciones y actividades |
| `/actividades/{actividad}/items` | ítems presentados en la actividad, en orden, con las opciones de su escala |
| `/cuentas/{cuenta}/actividades/{actividad}/respuestas` | respuestas actuales de la cuenta en esa actividad |
| `/cuentas/{cuenta}/instrumentos` | por instrumento y aplicación: estado (NO_INICIADO, EN_PROGRESO, COMPLETADO), actividades completadas / total, ítems respondidos / total y si hay resultado vigente |
| `/cuentas/{cuenta}/instrumentos/{instrumento}/resultado?aplicacion=` | resultado vigente (ver ejemplo) |
| `/cuentas/{cuenta}/instrumentos/{instrumento}/historial` | todos los resultados, incluidos los anulados, del más reciente al más antiguo |
| `/cuentas/{cuenta}/instrumentos/TEST-AUTO/comparacion` | comparación de entrada y salida (5.7) |

Si no hay resultado vigente, `resultado` responde 409 con el estado de la aplicación: qué actividades faltan y cuántos ítems están respondidos. Para una cuenta de apoderado, los endpoints de instrumentos responden 404, porque LAB es un bloque de estudiante.

Ejemplo de resultado del RIASEC:

```json
{
  "instrumento": "TEST-RIASEC",
  "aplicacion": "APL-RIASEC",
  "calculado_en": "2026-10-01T10:00:00",
  "perfil_plano": false,
  "dimensiones": [
    {"codigo": "R", "nombre": "Realista", "puntaje": 27, "puntaje_maximo": 40, "porcentaje": 67.5}
  ],
  "codigo_interes": {"codigo": "RIE", "hay_empate": false},
  "coincidencias": [
    {"posicion": 1, "codigo_onet": "19-1031.02", "titulo": "Range Managers", "correlacion": 0.897496, "ajuste": "BEST_FIT"}
  ],
  "carreras_recomendadas": [
    {"codigo": "CAR-FOR", "nombre": "Ingeniería forestal", "familia": "FAM-INGENIERIA",
     "via": [{"posicion": 1, "codigo_onet": "19-1031.02", "titulo": "Range Managers", "correlacion": 0.897496, "ajuste": "BEST_FIT"}]}
  ]
}
```

La correlación se expone redondeada a 6 decimales y se guarda sin redondear. Para los instrumentos sin coincidencias, `codigo_interes`, `coincidencias` y `carreras_recomendadas` se omiten.

Para TEST-INT y TEST-HAB, el resultado incluye además `dimensiones_destacadas`: la lista de dimensiones con el porcentaje más alto (5.6.1), con el mismo formato que `dimensiones`.

## 7. Invariantes

1. A lo sumo un resultado vigente por (cuenta, aplicación).
2. Un resultado solo existe si todas las actividades de su aplicación están COMPLETADA.
3. Mientras hay un resultado vigente, las respuestas de su aplicación no cambian.
4. Un reinicio nunca revoca desbloqueos ni borra eventos o resultados; solo anula.
5. Las respuestas de una cuenta nunca afectan los resultados de otra.
6. Dentro de una aplicación, cada ítem del instrumento se presenta en exactamente una actividad.
7. El coeficiente guardado en cada coincidencia es ≥ 0, y su ajuste corresponde a los umbrales de 5.4.

## 8. Cadenas de respuesta de prueba

Para el RIASEC, una cadena de 60 dígitos indica el orden de la opción elegida en cada ítem, del 1 al 60. Los caracteres 1 a 15 van en LAB-RIA1, del 16 al 30 en LAB-RIA2, y así sucesivamente. Los tests deben usar una función auxiliar que reparta la cadena entre las cuatro actividades.

| Nombre | Cadena | Puntajes R, I, A, S, E, C |
|---|---|---|
| Cadena A (notebook) | `511222115515411122551525542552114321231141335215514152553521` | 21, 9, 17, 20, 28, 15 |
| Cadena B | `333322223322343333233333443333333333444433333433444433334433` | 27, 24, 18, 17, 23, 18 |
| Perfil plano | sesenta veces `3` | 20, 20, 20, 20, 20, 20 |

La cadena A y su resultado vienen del notebook del usuario. La cadena B reproduce el perfil de ejemplo del notebook (27, 24, 18, 17, 23, 18), cuyas ocupaciones afines ya están verificadas.

## 9. Escenarios

Cada escenario es un test en `tests/test_instrumentos.py`, que parte de `/demo/reiniciar`. Los escenarios que usan ocupaciones requieren el archivo de 4.4. Si el archivo falta, esos tests se marcan como omitidos con un mensaje claro, y los demás se ejecutan igual.

**I1. Estado inicial.** Consultar `/cuentas/est-ana/instrumentos`.
Esperado: los cuatro instrumentos en NO_INICIADO (TEST-AUTO con sus dos aplicaciones). En el estado de Ana: LAB-AUT-E, LAB-HAB, LAB-INT1 y LAB-RIA1 DISPONIBLE; LAB-AUT-S, LAB-INT2 y LAB-RIA2 a LAB-RIA4 BLOQUEADA. En el estado de Rosa no aparece el bloque LAB.

**I2. Respuestas parciales.** Ana responde los ítems RIASEC-01 a RIASEC-10 en LAB-RIA1 e intenta completarla.
Esperado: 409 con los faltantes RIASEC-11 a RIASEC-15, sin eventos nuevos. LAB-RIA1 aparece EN_CURSO; el RIASEC aparece EN_PROGRESO con 10 de 60 ítems y 0 de 4 actividades.

**I3. Validaciones.** Ana intenta:
- responder RIASEC-20 en LAB-RIA1 (no se presenta ahí): 409;
- responder RIASEC-01 con la opción 6: 422;
- responder en LAB-RIA2 (bloqueada): 409 con el progreso de su regla.

Luego cambia su respuesta a RIASEC-01. Esperado: se reemplaza, sin crear una segunda fila.

**I4. RIASEC repartido en cuatro actividades.** Ana responde la cadena A y completa LAB-RIA1 a LAB-RIA3.
Esperado:
- Tras cada una se desbloquea la siguiente. `resultado` responde 409 indicando que falta LAB-RIA4.
- Al completar LAB-RIA4, `resultados_generados` incluye TEST-RIASEC.
- Puntajes 21, 9, 17, 20, 28, 15; porcentajes 52.5, 22.5, 42.5, 50.0, 70.0, 37.5; código `ERS` sin empate.
- 10 coincidencias con posiciones 1 a 10, correlación no creciente, todas ≥ 0 y con el ajuste que corresponde a su valor.

**I5. Coincidencias y carreras contra el notebook.** Luis responde la cadena B y completa las cuatro actividades.
Esperado: código `RIE` sin empate, y exactamente estas 10 coincidencias, todas BEST_FIT, con la correlación a 6 decimales:

| Pos. | Código O*NET | Título | Correlación |
|---|---|---|---|
| 1 | 19-1031.02 | Range Managers | 0.897496 |
| 2 | 17-2199.11 | Solar Energy Systems Engineers | 0.833365 |
| 3 | 17-2199.10 | Wind Energy Engineers | 0.813152 |
| 4 | 17-2021.00 | Agricultural Engineers | 0.789390 |
| 5 | 17-2121.00 | Marine Engineers and Naval Architects | 0.786206 |
| 6 | 19-2041.02 | Environmental Restoration Planners | 0.786097 |
| 7 | 49-9092.00 | Commercial Divers | 0.785974 |
| 8 | 53-7031.00 | Dredge Operators | 0.765276 |
| 9 | 11-9041.01 | Biofuels/Biodiesel Technology and Product Development Managers | 0.761303 |
| 10 | 17-2141.01 | Fuel Cell Engineers | 0.754871 |

Carreras recomendadas, en este orden:
1. CAR-FOR, vía 19-1031.02 (posición 1).
2. CAR-AMB, vía 17-2199.11 (posición 2) y 19-2041.02 (posición 6).
3. CAR-AGR, vía 17-2021.00 (posición 4).

CAR-CIV **no** aparece: Civil Engineers queda en la posición 17, fuera del top 10.

**I6. Perfil plano.** Ana responde sesenta veces `3` y completa el RIASEC.
Esperado: puntajes de 20 en todas las dimensiones, `perfil_plano` verdadero, 0 coincidencias, 0 carreras recomendadas y código `RIA` con `hay_empate` verdadero.

**I7. Respuestas fijas y rehacer.** Tras I4, Ana intenta cambiar una respuesta de LAB-RIA2 y luego rehace LAB-RIA2.
Esperado: el cambio responde 409. Rehacer registra COMPLETA_ACTIVIDAD, `resultados_generados` sale vacío y el resultado vigente no cambia (misma fecha de cálculo y mismos valores).

**I8. Inteligencias en dos actividades.** Ana responde Sí en los ítems impares y No en los pares de TEST-INT, completando LAB-INT1 y LAB-INT2.
Esperado: el resultado se genera al completar LAB-INT2, sin coincidencias ni código de interés:

| Dimensión | Puntaje | Máximo | Porcentaje |
|---|---|---|---|
| INT-LIN | 7 | 10 | 70.0 |
| INT-LOG | 4 | 7 | 57.14 |
| INT-ESP | 2 | 4 | 50.0 |
| INT-CIN | 1 | 5 | 20.0 |
| INT-MUS | 3 | 4 | 75.0 |
| INT-INTER | 1 | 8 | 12.5 |
| INT-INTRA | 4 | 5 | 80.0 |

Dimensión destacada: solo INT-INTRA (80.0%).

**I8b. Empate en la más destacada.** Ana responde Sí en los 4 ítems espaciales (7, 18, 26, 29) y en los 4 musicales (5, 10, 31, 39), y No en todos los demás.
Esperado: INT-ESP e INT-MUS con 100.0%, y ambas como dimensiones destacadas, en ese orden. Las demás tienen 0.0%.

**I9. Habilidades sociales con ítems inversos.** Ana responde Casi siempre en los ítems 1 a 12 y Casi nunca en los ítems 13 a 24, y completa LAB-HAB.
Esperado:

| Dimensión | Puntaje | Máximo | Porcentaje |
|---|---|---|---|
| HAB-ASE | 2 | 5 | 40.0 |
| HAB-EMP | 2 | 4 | 50.0 |
| HAB-LID | 1 | 3 | 33.33 |
| HAB-RES | 1 | 4 | 25.0 |
| HAB-EXP | 0 | 3 | 0.0 |
| HAB-VAL | 4 | 5 | 80.0 |

Dimensión destacada: solo HAB-VAL (80.0%).

HAB-LID y HAB-EXP comprueban la inversión: en ellas, los ítems 5 y 8, marcados Casi siempre, suman 0, y el ítem 20, marcado Casi nunca, suma 1.

**I10. Autopercepción: mismos ítems, dos aplicaciones.** Ana responde `B C C D B C A C D B` en LAB-AUT-E (letras en orden de los ítems 1 a 10) y la completa. `comparacion` responde 409. Luego responde `A A B C A A C B B A` en LAB-AUT-S y la completa.
Esperado: ningún `resultado_instrumento` para TEST-AUTO. Hay dos filas de respuesta por ítem, una en cada progreso. La comparación queda así:

| Ítem | Entrada | Salida | Diferencia |
|---|---|---|---|
| 1 | B (3) | A (4) | +1 |
| 2 | C (2) | A (4) | +2 |
| 3 | C (2) | B (3) | +1 |
| 4 | D (1) | C (2) | +1 |
| 5 | B (3) | A (4) | +1 |
| 6 | C (2) | A (4) | +2 |
| 7 | A (4) | C (2) | −2 |
| 8 | C (2) | B (3) | +1 |
| 9 | D (1) | B (3) | +2 |
| 10 | B (3) | A (4) | +1 |

**I11. Reinicio del RIASEC y nueva aplicación.** Tras I4, se reinicia TEST-RIASEC de Ana.
Esperado:
- El resultado de la cadena A queda anulado, y `resultado` responde 409.
- LAB-RIA1 a LAB-RIA4 aparecen EN_CURSO, sin respuestas, y siguen disponibles, porque sus desbloqueos no se revocan.
- Se registra REINICIA_INSTRUMENTO, y los COMPLETA_ACTIVIDAD anteriores siguen en la línea de tiempo.

Luego Ana responde la cadena B y completa las cuatro actividades. Esperado: un nuevo resultado vigente con los valores de I5, y un historial con 2 resultados, el más antiguo anulado.

**I12. Reinicio de una sola aplicación.** Tras I10, se reinicia TEST-AUTO sin indicar la aplicación.
Esperado: 422. Al reiniciarlo con APL-AUTO-SAL, las respuestas de entrada se conservan, LAB-AUT-S pasa a EN_CURSO y `comparacion` responde 409 hasta que se vuelva a completar. Reiniciar de nuevo APL-AUTO-SAL, ya sin respuestas, responde 409.

**I13. Aislamiento entre cuentas.** Ana responde la cadena A y Luis la cadena B, intercalando las actividades.
Esperado: cada uno obtiene su propio resultado, igual al de I4 y al de I5. Los endpoints de instrumentos para Rosa responden 404.

**I14. Transacción completa.** Con el cálculo del resultado forzado a fallar (monkeypatch), Ana completa LAB-RIA4.
Esperado: la acción falla; LAB-RIA4 no queda COMPLETADA, no hay evento COMPLETA_ACTIVIDAD de LAB-RIA4 y no hay resultado.

### 9.1 Pruebas unitarias del cálculo

En `tests/test_calculo_instrumentos.py`, sin base de datos ni archivo de ocupaciones:

- **Pearson y ajuste**, con el vector de la cadena A (21, 9, 17, 20, 28, 15):

  | Vector de ocupación | r esperado | Ajuste |
  |---|---|---|
  | 4.2, 1.8, 3.4, 4.0, 5.6, 3.0 | 1.000000 | BEST_FIT |
  | 5.0, 1.0, 2.0, 4.0, 6.0, 4.5 | 0.845946 | BEST_FIT |
  | 3.0, 2.5, 3.5, 5.0, 4.5, 2.0 | 0.681419 | GREAT_FIT |
  | 1.00, 1.69, 3.87, 3.14, 7.00, 4.43 (Advertising and Promotions Managers) | 0.584176 | GOOD_FIT |

- **Correlación negativa descartada:** el vector de la cadena B (27, 24, 18, 17, 23, 18) contra General and Operations Managers (2.20, 2.37, 1.29, 3.38, 7.00, 5.34) da r = −0.061193, y la ocupación se descarta.
- **Inversión:** en Sí/No, un ítem inverso con Sí suma 0; en Likert 0 a 4, un ítem inverso con puntaje 1 suma 3.
- **Código de interés:** 21, 9, 17, 20, 28, 15 da `ERS`; 20 en todas da `RIA` con empate; 10, 10, 30, 30, 20, 20 da `ASE` con empate entre E y C.
- **Dimensiones destacadas:** proporciones 3/4, 3/4 y 2/4 destacan las dos primeras; 4/7 y 1/2 destacan solo la primera; todas en 0 destacan todas.
- **Desempate del top 10:** dos ocupaciones con la misma correlación se ordenan por `codigo_onet` ascendente.

Comparar con tolerancia de 1e-6.

## 10. Fase final: interfaz mínima

Una página `/demo/instrumentos` en HTML, CSS y JavaScript planos, servida por FastAPI, con el mismo estilo técnico que `/demo` y un enlace desde ella. Solo usa los endpoints de la sección 6. Es la interfaz más simple que permita probar todo a mano:

1. **Selector de cuenta** y **fecha simulada**, como en `/demo`.
2. **Lista de instrumentos** con su estado por aplicación: actividades completadas, ítems respondidos y si hay resultado vigente.
3. **Panel de actividad.** Al elegir una actividad del bloque LAB, muestra sus ítems con sus opciones como botones de radio y dos botones: "Guardar respuestas" y "Completar actividad". Las actividades bloqueadas se muestran deshabilitadas, con sus requisitos.
4. **Relleno rápido.** Un campo para pegar una cadena de respuestas y botones para las cadenas A, B y Perfil plano. Para el RIASEC, la cadena se reparte entre las cuatro actividades y cada una se guarda con su propia llamada.
5. **Panel de resultado.** Muestra la tabla de dimensiones con una barra simple por porcentaje, las dimensiones destacadas (inteligencias y habilidades sociales), el código de interés, la tabla de coincidencias y las carreras recomendadas con su vía. Para TEST-AUTO muestra la tabla de comparación. Incluye el historial, con los resultados anulados marcados.
6. **Botón "Reiniciar instrumento"**, con selector de aplicación cuando corresponde y confirmación.
7. Cada acción muestra su respuesta del backend (eventos, desbloqueos, resultados generados o error) en un recuadro de registro.

## 11. Fuera de alcance

- High points de las ocupaciones y búsqueda de carreras por código de interés.
- Instrumentos prioritarios y la vista de la orientadora.
- Enunciados reales del RIASEC, de inteligencias y de habilidades sociales.
- Revelación narrativa de Helena y secciones del perfil.
- Clasificación de respuestas abiertas con LLM.

## 12. Orden de implementación sugerido

1. Tablas nuevas y semilla (escalas, instrumentos, bloque LAB, aplicaciones, carreras y relación con ocupaciones), con la validación de 4.1 y la carga del archivo de 4.4. Verificar que los tests existentes siguen pasando.
2. Funciones puras de cálculo (puntuación, porcentaje, Pearson, ajuste, top 10 y código de interés), con las pruebas de 9.1.
3. Acción de responder ítems, validación en `completar-actividad` y generación de resultados (I1 a I10).
4. Consultas de resultado, historial y comparación.
5. Reinicio (I11 y I12), aislamiento y transacción (I13 e I14).
6. Interfaz de la sección 10.
7. Actualizar `docs/decisiones.md` y `docs/validacion.md` con la cobertura de los escenarios I1 a I14 y de los invariantes de la sección 7.
