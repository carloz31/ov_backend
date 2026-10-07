# Evaluación Gemini de registro

Modelo: gemini-3.1-flash-lite. Prompt: v2.

Los 16 textos iniciales llegan al LLM, incluidos los cortos. Las respuestas previas usan los casos 2 y 6; no se persisten respuestas ni eventos.

Casos 15 y 16: se responde el turno 1 solo si fue generado. Se usa la pregunta recibida y se evalúa la conversación completa. El caso 16 termina al observar la segunda pregunta: no se inventa una respuesta al turno 2. Si falla el LLM, se aplica el mismo respaldo por longitud que en la aplicación.

Revisión manual: en el caso 15 la primera pregunta debe tratar solo C2; en el caso 16 debe tratar C1 y C2, y la segunda debe ser distinta de la primera. La salida estructurada no acredita por sí sola esos resultados semánticos.

| # | Ítem | Envío | Texto | Pregunta respondida | Esperada | Obtenida | Criterios faltantes | Pregunta generada | Requiere atención | Latencia ms | Origen | Error | Observación |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | REG-HAB-1 | Inicial | Asertividad, porque es importante para el futuro. |  | VAGA (falta C2) | VAGA | C2 | ¡Qué buena elección! Para conocerte mejor, ¿podrías contarme en qué situación específica de tu vida sientes que te cuesta ser asertivo? | False | 3300 | LLM |  |  |
| 2 | REG-HAB-1 | Inicial | La asertividad, porque en los trabajos grupales me quedo callado aunque no esté de acuerdo. |  | ADECUADA | NO_EVALUADA |  |  | False | 10122 | RESPALDO_LONGITUD | Se agotó el tiempo máximo de evaluación |  |
| 3 | REG-HAB-1 | Inicial | Quiero mejorar en todo, la verdad no sé bien qué elegir. |  | VAGA | VAGA | C1, C2 | ¿Qué habilidad social, como la comunicación o el trabajo en equipo, te gustaría fortalecer y en qué momento de tu día a día sientes que te hace falta? | False | 3660 | LLM |  |  |
| 4 | REG-HAB-1 | Inicial | Trabajo en equipo, porque cuando hacemos proyectos en el colegio siempre termino haciendo todo yo solo. |  | ADECUADA | ADECUADA |  |  | False | 2582 | LLM |  |  |
| 5 | REG-HAB-2 | Inicial | Voy a esforzarme más y ser mejor persona con los demás. |  | VAGA | NO_EVALUADA |  |  | False | 8347 | RESPALDO_LONGITUD | Falló el evaluador de respuestas |  |
| 6 | REG-HAB-2 | Inicial | En el próximo trabajo de Comunicación voy a decir mi opinión al menos una vez antes de que decidamos. |  | ADECUADA | NO_EVALUADA |  |  | False | 10108 | RESPALDO_LONGITUD | Se agotó el tiempo máximo de evaluación |  |
| 7 | REG-HAB-2 | Inicial | Voy a practicar hablando más. |  | VAGA (falta C2) | VAGA | C1, C2 | ¿Cómo planeas practicar el hablar más en tus trabajos grupales y en qué momentos específicos lo harás para sentirte más cómodo expresando tu opinión? | False | 2158 | LLM |  |  |
| 8 | REG-HAB-2 | Inicial | Los sábados, cuando juego fútbol con mi barrio, voy a pedir el balón y organizar al equipo. |  | ADECUADA | NO_EVALUADA |  |  | False | 10089 | RESPALDO_LONGITUD | Se agotó el tiempo máximo de evaluación |  |
| 9 | REG-HAB-3 | Inicial | Me sentiré mejor conmigo mismo y más feliz. |  | VAGA | VAGA | C1, C2 | ¿Qué cambios notarías en tu forma de participar durante el trabajo de Comunicación que te indiquen que estás logrando expresar tu opinión antes de que decidan? | False | 6844 | LLM |  |  |
| 10 | REG-HAB-3 | Inicial | Cuando en una reunión diga que no estoy de acuerdo sin quedarme pensando en eso después. |  | ADECUADA | ADECUADA |  |  | False | 2633 | LLM |  |  |
| 11 | REG-HAB-3 | Inicial | Mis notas van a subir. |  | VAGA (falta C2) | VAGA | C1, C2 | ¿Cómo notarás que estás siendo más asertivo al dar tu opinión en el trabajo de Comunicación, más allá de si tus notas suben? | False | 2967 | LLM |  |  |
| 12 | REG-HAB-1 | Inicial | Empatía, aunque creo que está sobrevalorada; igual me serviría, porque cuando mis amigos me cuentan sus problemas no sé qué decirles. |  | ADECUADA (opinión discutible, pero cumple C1 y C2) | ADECUADA |  |  | False | 2784 | LLM |  |  |
| 13 | REG-HAB-2 | Inicial | jajaja no sé, lo que sea |  | VAGA | VAGA | C1, C2 | ¿Qué acción específica podrías realizar para practicar tu asertividad en los trabajos grupales y cuándo o con quién te gustaría empezar a ponerlo en práctica? | False | 9068 | LLM |  |  |
| 14 | REG-HAB-1 | Inicial | Ninguna, porque en mi casa me dicen que no sirvo para nada y ya no me importa. |  | requiere atención | ADECUADA |  |  | True | 2799 | LLM |  |  |
| 15 | REG-HAB-1 | Inicial | Me gustaría mejorar mi comunicación, porque siento que es un punto débil mío. |  | VAGA (falta C2) | NO_EVALUADA |  |  | False | 1643 | RESPALDO_LONGITUD | Falló el evaluador de respuestas |  |
| 15 | REG-HAB-1 | Turno 1 | En los trabajos grupales, cuando no estoy de acuerdo, me quedo callado. |  | ADECUADA | Sin nueva evaluación |  |  |  |  |  |  | No ejecutado: el inicial finalizó sin seguimiento. |
| 16 | REG-HAB-2 | Inicial | Voy a esforzarme más. |  | VAGA (faltan C1 y C2) | VAGA | C1, C2 | ¿Qué acciones concretas realizarás para ser más asertivo en tus trabajos grupales y en qué momentos o con quiénes podrías empezar a practicarlo? | False | 2584 | LLM |  |  |
| 16 | REG-HAB-2 | Turno 1 | No sé, más seguido. | ¿Qué acciones concretas realizarás para ser más asertivo en tus trabajos grupales y en qué momentos o con quiénes podrías empezar a practicarlo? | VAGA (segunda pregunta distinta de la primera) | VAGA | C1, C2 | ¿Qué actividad específica podrías hacer en tu próximo trabajo grupal para expresar tu opinión y con qué compañero te sentirías más cómodo empezando a practicarlo? | False | 2484 | LLM |  |  |

## Revisión de esta ejecución real

Ejecutada el 2026-10-01 tras la autorización explícita del usuario, con
`uv run python -m scripts.evaluar_gemini --pausa 5`. Modelo
`gemini-3.1-flash-lite`, prompt v2, temperatura 0.2, timeout configurado de
10 segundos y un intento por evaluación. No se cambió `.env`, la semilla ni
ninguna base persistente. Esta tabla recoge una ejecución, sin repetir los
casos fallidos para seleccionar un resultado favorable.

Hay **18 filas y 17 llamadas reales**: 16 iniciales y el turno 1 del caso 16.
El caso 15 finalizó mediante respaldo y no se inventó una pregunta ni se evaluó
su turno. Hubo **12 resultados LLM válidos y 5 respaldos**, de los cuales 3
corresponden a timeout y 2 a otro fallo del evaluador. Los mensajes seguros no
permiten atribuir esos dos fallos a cuota, clave o disponibilidad concreta.

La latencia de las 17 evaluaciones estuvo entre **1643 y 10122 ms**, con mediana
de **2967 ms** y media de **4951 ms**. La media de los 12 resultados válidos fue
**3655 ms**. Las ocho preguntas del LLM tienen entre 21 y 28 palabras, dentro
del máximo de 30. Se verificó que los campos de auditoría y la clave no se
incluyen en los textos de prueba enviados al modelo.

Las clasificaciones de las 12 salidas válidas coinciden con lo esperado,
incluida la marca de atención del caso 14. Eso **no equivale a aprobar todos
los criterios ni los 16 casos**:

| Caso | Revisión manual | Resultado |
|---|---|---|
| 1 | VAGA, solo C2, pregunta por situación propia. La frase «¡Qué buena elección!» elogia la elección, aunque la instrucción pide no juzgarla. | Clasificación/criterios correctos; observación de tono. |
| 2, 6, 8 | Timeout; los textos alcanzan el mínimo y pasan a NO_EVALUADA sin pregunta. | Respaldo correcto; expectativa semántica no verificada. |
| 3, 4, 9, 10, 13 | Clasificación y preguntas, cuando corresponden, coherentes con los criterios y contexto. | Conforme en esta ejecución. |
| 5 | Fallo del evaluador; texto suficiente pasa a NO_EVALUADA. | Respaldo correcto; no se obtuvo el VAGA esperado del LLM. |
| 7 | Se esperaba solo C2. Gemini devuelve C1 y C2 y pregunta también cómo practicar el hablar. | Discrepancia de criterios; no se cambia la expectativa autorizada. |
| 11 | «Mis notas van a subir.» cumple el indicador observable C1 según el escenario; debía faltar solo C2. Gemini marca C1 y C2. | Discrepancia de criterios; pregunta por un indicador que se considera ya aportado. |
| 12 | ADECUADA pese a la opinión discutible sobre empatía, sin pregunta ni juicio. | Conforme con el texto corregido. |
| 14 | ADECUADA y requiere_atencion verdadero, sin pregunta. | Conforme; no se confunde malestar con falta de completitud. |
| 15 | Fallo del evaluador al inicial; texto suficiente pasa a NO_EVALUADA. Su turno aparece como no ejecutado. | Respaldo correcto; conversación y pregunta solo C2 no verificadas con Gemini. |
| 16 | Inicial y turno VAGA, C1/C2 faltantes. La segunda pregunta propone actividad y compañero específicos y difiere de la primera. | Conforme; ambas preguntas buscan los dos criterios y no se inventa respuesta al turno 2. |

La integración, el esquema de resultados, la evaluación de conversación y el
respaldo funcionan. **La aceptación semántica de Gemini es parcial**: quedan
las discrepancias de 7 y 11, el tono de 1 y los casos sin respuesta válida.
No se modifican criterios, prompt v2, timeout o tests para ocultar estos resultados.
Otra evaluación real o un ajuste de las instrucciones debe acordarse por separado;
no hay reintentos automáticos ni garantía de repetir estas salidas.
