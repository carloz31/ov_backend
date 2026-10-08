# Evaluación Gemini de registro

Modelo: gemini-3.1-flash-lite. Prompt: v2.

Los 16 textos iniciales llegan al LLM, incluidos los cortos. Las respuestas previas usan los casos 2 y 6; no se persisten respuestas ni eventos.

Casos 15 y 16: se responde el turno 1 solo si fue generado. Se usa la pregunta recibida y se evalúa la conversación completa. El caso 16 termina al observar la segunda pregunta: no se inventa una respuesta al turno 2. Si falla el LLM, se aplica el mismo respaldo por longitud que en la aplicación.

Revisión manual: en el caso 15 la primera pregunta debe tratar solo C2; en el caso 16 debe tratar C1 y C2, y la segunda debe ser distinta de la primera. La salida estructurada no acredita por sí sola esos resultados semánticos.

| # | Ítem | Envío | Texto | Pregunta respondida | Esperada | Obtenida | Criterios faltantes | Pregunta generada | Requiere atención | Latencia ms | Origen | Error | Observación |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | REG-HAB-1 | Inicial | Asertividad, porque es importante para el futuro. |  | VAGA (falta C2) | ADECUADA |  |  | False | 2 | LLM |  |  |
| 2 | REG-HAB-1 | Inicial | La asertividad, porque en los trabajos grupales me quedo callado aunque no esté de acuerdo. |  | ADECUADA | ADECUADA |  |  | False | 1 | LLM |  |  |
| 3 | REG-HAB-1 | Inicial | Quiero mejorar en todo, la verdad no sé bien qué elegir. |  | VAGA | ADECUADA |  |  | False | 1 | LLM |  |  |
| 4 | REG-HAB-1 | Inicial | Trabajo en equipo, porque cuando hacemos proyectos en el colegio siempre termino haciendo todo yo solo. |  | ADECUADA | ADECUADA |  |  | False | 1 | LLM |  |  |
| 5 | REG-HAB-2 | Inicial | Voy a esforzarme más y ser mejor persona con los demás. |  | VAGA | ADECUADA |  |  | False | 1 | LLM |  |  |
| 6 | REG-HAB-2 | Inicial | En el próximo trabajo de Comunicación voy a decir mi opinión al menos una vez antes de que decidamos. |  | ADECUADA | ADECUADA |  |  | False | 1 | LLM |  |  |
| 7 | REG-HAB-2 | Inicial | Voy a practicar hablando más. |  | VAGA (falta C2) | ADECUADA |  |  | False | 1 | LLM |  |  |
| 8 | REG-HAB-2 | Inicial | Los sábados, cuando juego fútbol con mi barrio, voy a pedir el balón y organizar al equipo. |  | ADECUADA | ADECUADA |  |  | False | 1 | LLM |  |  |
| 9 | REG-HAB-3 | Inicial | Me sentiré mejor conmigo mismo y más feliz. |  | VAGA | ADECUADA |  |  | False | 1 | LLM |  |  |
| 10 | REG-HAB-3 | Inicial | Cuando en una reunión diga que no estoy de acuerdo sin quedarme pensando en eso después. |  | ADECUADA | ADECUADA |  |  | False | 1 | LLM |  |  |
| 11 | REG-HAB-3 | Inicial | Mis notas van a subir. |  | VAGA (falta C2) | ADECUADA |  |  | False | 1 | LLM |  |  |
| 12 | REG-HAB-1 | Inicial | Empatía, aunque creo que está sobrevalorada; igual me serviría, porque cuando mis amigos me cuentan sus problemas no sé qué decirles. |  | ADECUADA (opinión discutible, pero cumple C1 y C2) | ADECUADA |  |  | False | 1 | LLM |  |  |
| 13 | REG-HAB-2 | Inicial | jajaja no sé, lo que sea |  | VAGA | ADECUADA |  |  | False | 1 | LLM |  |  |
| 14 | REG-HAB-1 | Inicial | Ninguna, porque en mi casa me dicen que no sirvo para nada y ya no me importa. |  | requiere atención | ADECUADA |  |  | True | 1 | LLM |  |  |
| 15 | REG-HAB-1 | Inicial | Me gustaría mejorar mi comunicación, porque siento que es un punto débil mío. |  | VAGA (falta C2) | VAGA | C2 | ¿En qué situaciones notas que te cuesta comunicarte? | False | 1 | LLM |  |  |
| 15 | REG-HAB-1 | Turno 1 | En los trabajos grupales, cuando no estoy de acuerdo, me quedo callado. | ¿En qué situaciones notas que te cuesta comunicarte? | ADECUADA | ADECUADA |  |  | False | 1 | LLM |  |  |
| 16 | REG-HAB-2 | Inicial | Voy a esforzarme más. |  | VAGA (faltan C1 y C2) | VAGA | C1, C2 | ¿Qué harás exactamente y en qué momento? | False | 2 | LLM |  |  |
| 16 | REG-HAB-2 | Turno 1 | No sé, más seguido. | ¿Qué harás exactamente y en qué momento? | VAGA (segunda pregunta distinta de la primera) | NO_EVALUADA |  |  | False | 1 | RESPALDO_LONGITUD | El resultado del evaluador no cumple el esquema o las reglas de consistencia |  |
