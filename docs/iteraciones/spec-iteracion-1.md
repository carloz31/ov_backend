# Iteración 1: integración base de `ov_backend` y `ov_frontend`

> Especificación para implementar con Codex en un proyecto que usa ambos repositorios, cada uno en su propia carpeta.
> Vive en `ov_backend/docs/iteraciones/`, junto con el plan y el registro de decisiones de la iteración.
> Fuente de verdad de la iteración 1. Extiende las especificaciones existentes del backend
> (`ov_backend/docs/spec-demo-*.md`) y del frontend (`ov_frontend/docs/`) sin reemplazarlas.
> Si este documento contradice a otro, detente y explica la contradicción antes de cambiar nada.

## 0. Cómo usar este documento

- Implementa por fases, en el orden de la sección 9. Al terminar cada fase, detente y resume qué hiciste, qué pruebas pasan y qué queda pendiente.
- Lee la sección completa de una fase antes de escribir código.
- Si algo no está definido aquí, elige la opción más simple, anótala en `ov_backend/docs/iteraciones/decisiones-iteracion-1.md` y sigue.
- Todos los datos de esta iteración son **de prueba**. Si existen en el front, se usan adaptándolos. Si no existen, se crean y se marcan con el comentario `DATO DE PRUEBA` en el código o con `"_dato_de_prueba": true` en los JSON.
- No implementes nada de la sección 2.2 (fuera de alcance), aunque parezca fácil.

## 1. Objetivo

Que el estudiante recorra la plataforma en el navegador con **una sola base de datos** (la del backend) como fuente de la disponibilidad, el progreso, las respuestas de cuestionario, los resultados y los logros. El frontend deja de calcular desbloqueos por su cuenta cuando trabaja en modo servidor.

Al terminar, debe poder hacerse este recorrido sin tocar `localStorage` a mano:

1. Ingresar como `est-ana`.
2. Ver el camino con su primera actividad disponible y el resto bloqueado.
3. Completar las informativas y los registros del camino, en orden, viendo qué se desbloquea en cada paso.
4. Repetir una informativa sin que eso sume logros.
5. Abrir la ciudad al completar el camino.
6. Responder las 14 interacciones de Mara (test de intereses), dejarlas a medias y retomarlas.
7. Revelar el resultado con Elena y ver ocupaciones afines y carreras recomendadas.
8. Revisar fichas, insignias, nivel y qué falta para lo que sigue bloqueado.
9. Reiniciar los datos de prueba y volver a empezar.

### 1.1 Historias de usuario de la iteración 1 (14)

IDs según la versión vigente del catálogo de requisitos (93 HUs).

| HU | Historia (resumida) | Criterio de aceptación en esta iteración |
|---|---|---|
| HU-002 | Consultar mis actividades con su estado | El mapa del camino y de la ciudad muestra BLOQUEADA, DISPONIBLE, EN_CURSO o COMPLETADA según `GET /cuentas/{cuenta}/estado`. Ningún estado se calcula en el front. |
| HU-004 | Realizar una actividad informativa | `mission-welcome` y `enc-mitos` se reproducen con su contenido del front y, al terminar, se registran en el servidor con `completar-actividad`. |
| HU-011 | Ver, al ingresar, la siguiente actividad | El panel del mapa recomienda la primera actividad DISPONIBLE o EN_CURSO del camino según el servidor; si el camino está completo, la ciudad. |
| HU-013 | Mensaje de retroalimentación al completar | La pantalla de cierre lista lo que devolvió `nuevos_desbloqueos` (actividades, fichas, insignias, nivel, ciudad). |
| HU-014 | Repetir una informativa completada | Repetirla registra otro `COMPLETA_ACTIVIDAD` en el servidor, no cambia su estado COMPLETADA y no suma en los conteos de actividades distintas. |
| HU-015 | Consultar las fichas desbloqueadas | La mochila muestra como disponibles solo las fichas DISPONIBLE en el servidor. El cuerpo de la ficha sigue saliendo del front. |
| HU-021 | Responder los ítems de un cuestionario | Las interacciones de Mara muestran los ítems del servidor y guardan cada respuesta con `responder-items`. Se puede salir y retomar. |
| HU-022 | Vista resumida del resultado | Al revelar el resultado se ven las tres dimensiones principales y sus porcentajes, tomados del resultado vigente del servidor. |
| HU-025 | Qué habilita cada sección bloqueada del perfil | Las páginas bloqueadas del libro de Helena y los puntos bloqueados del mapa muestran el requisito pendiente según `GET /cuentas/{cuenta}/progreso/...` o el avance del instrumento. |
| HU-026 | Ocupaciones afines y carreras que conducen a ellas | Se muestran las coincidencias y las carreras recomendadas del resultado vigente. **Sin** la indicación de favoritos (iteración 3). |
| HU-027 | Revelar el resultado al completar todas las misiones | El sello de la página de intereses solo queda listo para romperse cuando existe un resultado vigente en el servidor. |
| HU-073 | Aviso al desbloquear un contenido o logro | Los desbloqueos nuevos y los no vistos del servidor se muestran en la cola de avisos; al mostrarlos se marcan como vistos en el servidor. |
| HU-074 | Logros obtenidos y condición de los no ocultos | El pasaporte muestra las insignias del servidor: obtenidas, bloqueadas con su requisito y ocultas como `???`. |
| HU-075 | Consultar mi nivel (**solo el nivel**) | El nivel actual y la lista de niveles salen del servidor. Avance por temática y afinidad quedan para la iteración 3. |

## 2. Alcance

### 2.1 Dentro

- Una semilla nueva del backend, `plataforma`, alineada con los identificadores y el contenido del front.
- Un modo de datos `api` en el front, activable por variable de entorno, que conserva el modo `local` actual.
- Las actividades del camino (9), las 14 interacciones de Mara y el cierre de Elena.
- El test de intereses RIASEC con cálculo de coincidencias y carreras recomendadas.
- Fichas, insignias, niveles, avisos de desbloqueo y progreso hacia objetivos bloqueados.
- Una cuenta de prueba elegida desde el login de demostración.
- Reinicio de los datos de prueba desde el front, solo en desarrollo.

### 2.2 Fuera (no implementar)

| Funcionalidad | Iteración | Comportamiento en modo `api` durante la iteración 1 |
|---|---|---|
| Evaluación de registros con LLM, preguntas de seguimiento, misiones adicionales, batalla El Rumor, comprobaciones guardadas en el servidor, login real, ayuda | 2 | Los registros se responden con la lógica local actual; solo su **finalización** va al servidor. Las misiones adicionales no se muestran y el desafío aparece bloqueado. Su insignia I10 ya existe en la BD como logro oculto. |
| Diario, check-in, catálogos desde la BD, favoritos, planes de carrera, vista explicada del resultado, perfil completo | 3 | Siguen con su lógica y sus datos locales. |
| Central de casos, entrevistas, Crew, conversaciones familiares, testimonios | 4 | Sus puntos y accesos se muestran bloqueados con el texto «Disponible en una próxima iteración». No se pueden iniciar. |
| Portales de apoderado y orientadora, perfil social | 5 | Sin cambios. No se tocan sus carpetas. |

El cuestionario «Mi brújula personal» (`mission-compass`) se completa en el servidor como actividad, pero **sus respuestas siguen locales** en esta iteración: no se siembran sus ítems.

## 3. Principios de la integración

### 3.1 Propiedad de los datos

| Dato | Dueño en la iteración 1 | Notas |
|---|---|---|
| Cuentas, bloques, actividades (código, tipo, orden), reglas y condiciones | BD | Se siembran con los ids del front. |
| Fichas, insignias y niveles (código, nombre, requisito, oculta) | BD | La presentación (íconos, metáforas, imágenes, cuerpo de la ficha) sigue en el front, buscada por código. |
| Instrumento RIASEC: ítems, enunciados, escala, dimensiones, aplicación | BD | El front ya no usa el TIP de muestra en modo `api`. |
| Ocupaciones y carreras del universo de recomendación, con sus puntajes O*NET | BD | Adaptadas del catálogo del front (sección 4.3.7). |
| Estado del estudiante: progreso, eventos, desbloqueos, respuestas a ítems, resultados | BD | El front solo guarda una copia de presentación. |
| Contenido narrativo de cada actividad (nodos: diálogos, diapositivas, preguntas, consignas) | Front | Igual que en `spec-demo-registro-gemini.md`: el back no interpreta el contenido. |
| Textos escritos en registros, borradores, respuestas de la brújula, intentos de comprobaciones | Front (local) | Pasan al servidor en las iteraciones 2 y 3. |
| Detalle del catálogo (descripciones, ingresos, instituciones) | Front (local) | Pasa a la BD en la iteración 3. |

Regla que no se negocia: **en modo `api`, el front nunca decide si algo está disponible, completado u obtenido.** Lo lee del servidor. Si el servidor no responde, el front lo dice y no inventa un estado.

### 3.2 Códigos

- Los códigos del backend son **exactamente** los ids del front: `mission-welcome`, `enc-mitos`, `act-tip-01`, `ficha-mitos`, `I1`, `nursing`, `psychologist`. No hay tabla de traducción.
- Los códigos que no existen en el front se crean con el mismo estilo (minúsculas y guiones), salvo los del backend que ya existen y se reutilizan (`TEST-RIASEC`, `APL-RIASEC`, `ESC-LIKERT5`, dimensiones `R`…`C`).
- La API sigue exponiendo solo códigos legibles, nunca ids internos.

### 3.3 Modo de datos del front

- `VITE_DATOS=local` (por defecto): el front se comporta exactamente como hoy. Ninguna prueba existente debe cambiar.
- `VITE_DATOS=api`: el front usa el servidor según esta especificación. `prototypeAllUnlocked`, `studentDemoEnabled` y `pendingContent` **no** afectan la disponibilidad en este modo.

## 4. Backend

### 4.1 Selección de semilla y archivo de base

> Sustituido por `docs/spec-refactor-estructura.md`. Esta sección conserva la
> configuración histórica; la preparación vigente usa Alembic y `datos.cargar`.

| Variable | Valores | Por defecto | Efecto |
|---|---|---|---|
| `SEMILLA` | `demo`, `plataforma` | `demo` | Qué semilla se carga al crear la base y al llamar a `/demo/reiniciar`. |
| `RUTA_BD` | ruta a un archivo `.db` | `demo.db` si `SEMILLA=demo`; `plataforma.db` si `SEMILLA=plataforma` | Archivo SQLite en la raíz del repo. Ambos ya están ignorados por `*.db`. |

- `crear_aplicacion(url_bd=..., semilla=...)` recibe la semilla de forma explícita. Si no se pasa, la lee de `SEMILLA`. Las pruebas existentes no cambian: siguen usando `demo`.
- `cargar_semilla_si_vacia` y `/demo/reiniciar` cargan la semilla configurada.
- La validación del JSON de registro (`cargar_posiciones_registro`, `REG-ACT08.json`) se ejecuta solo con la semilla `demo`. Con `plataforma`, `posiciones_registro` queda vacío.
- La semilla `demo` **no cambia**: mismos datos, mismas reglas, mismos escenarios E1–E17, I1–I14 y los de registro.

### 4.2 Esquema 5

> Sustituido por `docs/spec-refactor-estructura.md`. Esta sección conserva el
> esquema histórico; las migraciones actuales gestionan la revisión de la base.

`VERSION_ESQUEMA` pasa de 4 a 5. Cambios:

| Tabla | Cambio | Uso |
|---|---|---|
| `esquema_version` | columna `semilla` (texto, no nula) | Guarda con qué semilla se creó la base. |
| `ocupacion` | columna `codigo` (texto, único, nullable) | Código legible del front (`psychologist`). Nulo en la semilla `demo`. |

Al arrancar, si la base existe y su `semilla` no coincide con la configurada, la aplicación no arranca y dice: «La base `<archivo>` fue creada con la semilla `<x>`; la aplicación está configurada con `<y>`. Usa otra `RUTA_BD` o borra el archivo.» El mensaje de esquema anterior nombra el archivo real, no siempre `demo.db`.

Contrato: `CoincidenciaPublica` agrega `codigo: str | None` (el `codigo` de la ocupación).

**Adaptaciones de pruebas existentes autorizadas por adelantado** (anótalas en `ov_backend/docs/decisiones.md`, bajo «Iteración 1»):

- versión de esquema vigente 4 → 5 y versión usada como inválida 5 → 6, conservando los rechazos de versiones anteriores;
- conteos y listas exactas de tablas y columnas;
- aserciones exactas de coincidencias, para incluir `"codigo": null` en la semilla `demo`;
- nuevos valores de `TipoEventoUso` (4.3.4) en listas exactas de enumerados.
- mensajes de esquema incompatible: las pruebas que esperan la constante fija con `demo.db` pasan a esperar el mensaje con el nombre real del archivo, conservando la comprobación de que la base se rechaza y no se modifica.

Cualquier otra adaptación de una prueba existente requiere detenerse y preguntar.

### 4.3 Semilla `plataforma`

El cargador está en `datos/plataforma.py`: definiciones en tablas de datos,
sin consultas dentro de bucles y con la transacción del llamador. Reutiliza
`leer_ocupaciones` de `datos/ocupaciones.py`. La ubicación sigue
`docs/spec-refactor-estructura.md`; el contenido de esta sección se conserva.

#### 4.3.1 Cuentas

| Código | Nombre | Rol |
|---|---|---|
| est-ana | Ana | ESTUDIANTE |
| est-luis | Luis | ESTUDIANTE |
| apo-rosa | Rosa | APODERADO |

Vínculo `VIN-ANA` (Ana y Rosa), igual que en la demo. Se conserva aunque las conversaciones sean de la iteración 4.

#### 4.3.2 Bloques y actividades

| Bloque | Número | Nombre | Espacio | Audiencia |
|---|---|---|---|---|
| CAMINO | 1 | El camino | MISIONES_CAMPO | ESTUDIANTE |
| CIUDAD | 2 | La ciudad | CIUDAD | ESTUDIANTE |

Actividades del CAMINO, en el orden de `baseRoute` (`src/features/student-experience/reflection/config.ts`):

| Orden | Código | Título | Tipo |
|---|---|---|---|
| 1 | mission-welcome | El inicio del viaje | INFORMATIVA |
| 2 | enc-mitos | La plaza de los rumores | INFORMATIVA |
| 3 | act-07 | Mis propios pregones | REGISTRO |
| 4 | mission-story | Las huellas que traigo | REGISTRO |
| 5 | mission-future | Mi horizonte | REGISTRO |
| 6 | mission-compass | Mi brújula personal | CUESTIONARIO (sin ítems en esta iteración) |
| 7 | act-06 | Mi mapa de ruta | REGISTRO |
| 8 | mission-expectations | Preparar la mochila | REGISTRO |
| 9 | mission-next-step | Elegir mi siguiente paso | REGISTRO |

Correspondencia de tipos del front: `encuentro` → INFORMATIVA, `registro` → REGISTRO, `instrumento` → CUESTIONARIO.

Actividades de la CIUDAD:

| Orden | Código | Título | Tipo |
|---|---|---|---|
| 1 | act-tip-01 | Una vuelta por el molino | CUESTIONARIO |
| 2–14 | act-tip-02 … act-tip-14 | Mara: interacción N de 14 (DATO DE PRUEBA) | CUESTIONARIO |
| 15 | act-tip-final | Las pistas que hablan de ti | INFORMATIVA |

#### 4.3.3 Contenido desbloqueable

Fichas (el `contenido` en la BD es el resumen; el cuerpo lo muestra el front):

| Código | Título | Se desbloquea con |
|---|---|---|
| first-steps | Tres pistas para comenzar el viaje | completar `mission-welcome` |
| ficha-mitos | Ficha: Mitos y realidades del futuro profesional | completar `enc-mitos` |
| rec-ponteencarrera | Ponte en Carrera: compara carreras e instituciones | completar `enc-mitos` |
| rec-unesco-stem | Ciencia sin etiquetas | completar `enc-mitos` |

No se siembran testimonios, preguntas de diario ni conversaciones en esta iteración. `estado.testimonios` y `estado.preguntas_diario` vuelven vacíos.

Niveles (títulos de `travelerTitles` en `profile/passport.ts`):

| Número | Título |
|---|---|
| 1 | Observador del horizonte |
| 2 | Recolector de pistas |
| 3 | Cartógrafo de posibilidades |
| 4 | Explorador de la ciudad |
| 5 | Autor de su rumbo |

Insignias (de `AdventureAchievements.ts`; `requisito` = su `description`, `descripcion` = su `message`):

| Código | Nombre | Oculta | Requisito visible |
|---|---|---|---|
| I1 | La primera chispa | no | Completa la introducción de tu viaje. |
| I2 | Coleccionista de pistas | no | Completa tres Misiones de Campo. |
| I3 | La llave de la ciudad | no | Completa todas las Misiones de Campo. |
| I4 | Una invitación abre caminos | no | Invita a un compañero a tu Crew. |
| I5 | Nadie viaja solo | no | Forma un Crew con un compañero que acepte tu invitación. |
| I6 | Una mesa para conversar | no | Completen la primera conversación en familia. |
| I7 | Aquí para ayudar | no | Resuelve tu primer caso. |
| I8 | Historias que inspiran | no | Publica una misión de investigación. |
| I9 | Una ciudad que sonríe | no | Resuelve todos los llamados de la Central de casos. |
| I10 | Luz sin fisuras | sí | (oculto) Vence al enemigo sin perder destellos en tu primera victoria. |

I10 se siembra ya para poder probar cómo se muestra un logro oculto; el desafío que lo otorga llega en la iteración 2. Las insignias de misiones adicionales entran en la iteración 2 con sus actividades.

#### 4.3.4 Eventos nuevos

Se agregan a `TipoEventoUso`, con `id_referencia` nulo: `INVITA_A_CREW`, `FORMA_CREW` y `VENCE_DESAFIO_INTACTO`. Ninguna acción los registra en esta iteración; solo sirven para que I4, I5 e I10 tengan regla y no aparezcan como obtenidas (un objetivo sin reglas está disponible desde el inicio, según 4.4 de la spec del motor). Se pueden probar con `POST /eventos`.

#### 4.3.5 Evaluador especial nuevo

`misiones_camino_sin_inicio`, registrado en `EVALUADORES`. Usa `parametro_evaluador` como mínimo. Devuelve verdadero si la cuenta completó al menos ese número de actividades **distintas** del bloque `CAMINO`, sin contar la de orden 1 (`mission-welcome`). Equivale a `completedMissionIds.filter(id => id !== 'welcome').length >= n` del front. Sigue la técnica de `carreras_de_3_familias`: contexto de consultas, definiciones en caché y sin consultas dentro de bucles.

#### 4.3.6 Reglas

Notación de la spec del motor: `EVENTO(referencia) conteo ≥ n`. Sin conteo es EVENTOS; sin referencia, todos los eventos de ese tipo.

**Camino (objetivo ACTIVIDAD)**

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-enc-mitos | enc-mitos | COMPLETA_ACTIVIDAD(mission-welcome) ≥ 1 |
| R-act-07 | act-07 | COMPLETA_ACTIVIDAD(enc-mitos) ≥ 1 |
| R-mission-story | mission-story | COMPLETA_ACTIVIDAD(act-07) ≥ 1 |
| R-mission-future | mission-future | COMPLETA_ACTIVIDAD(mission-story) ≥ 1 |
| R-mission-compass | mission-compass | COMPLETA_ACTIVIDAD(mission-future) ≥ 1 |
| R-act-06 | act-06 | COMPLETA_ACTIVIDAD(mission-compass) ≥ 1 |
| R-mission-expectations | mission-expectations | COMPLETA_ACTIVIDAD(act-06) ≥ 1 |
| R-mission-next-step | mission-next-step | COMPLETA_ACTIVIDAD(mission-expectations) ≥ 1 |

`mission-welcome` no tiene regla.

**Ciudad**

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-ciudad | BLOQUE CIUDAD | COMPLETA_BLOQUE(CAMINO) ≥ 1 |
| R-act-tip-NN (NN = 02…14) | act-tip-NN | COMPLETA_ACTIVIDAD(act-tip-(NN−1)) ≥ 1 |
| R-act-tip-final | act-tip-final | COMPLETA_ACTIVIDAD(act-tip-14) ≥ 1 |

`act-tip-01` no tiene regla: hereda la disponibilidad de la ciudad.

**Fichas**

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-first-steps | first-steps | COMPLETA_ACTIVIDAD(mission-welcome) ≥ 1 |
| R-ficha-mitos | ficha-mitos | COMPLETA_ACTIVIDAD(enc-mitos) ≥ 1 |
| R-rec-ponteencarrera | rec-ponteencarrera | COMPLETA_ACTIVIDAD(enc-mitos) ≥ 1 |
| R-rec-unesco-stem | rec-unesco-stem | COMPLETA_ACTIVIDAD(enc-mitos) ≥ 1 |

**Insignias**

| Regla | Objetivo | Condiciones | Evaluador |
|---|---|---|---|
| R-I1 | I1 | COMPLETA_ACTIVIDAD(mission-welcome) ≥ 1 | |
| R-I2 | I2 | COMPLETA_ACTIVIDAD ≥ 1 | misiones_camino_sin_inicio, parámetro 3 |
| R-I3 | I3 | COMPLETA_BLOQUE(CAMINO) ≥ 1 | |
| R-I4 | I4 | INVITA_A_CREW ≥ 1 | |
| R-I5 | I5 | FORMA_CREW ≥ 1 | |
| R-I6 | I6 | COMPLETA_CONVERSACION ≥ 1 | |
| R-I7 | I7 | SUPERA_CASO ≥ 1 | |
| R-I8 | I8 | PUBLICA_ENTREVISTA ≥ 1 | |
| R-I9 | I9 | SUPERA_CASO REFERENCIAS_DISTINTAS ≥ 6 | |
| R-I10 | I10 | VENCE_DESAFIO_INTACTO ≥ 1 | |

El 6 de R-I9 es el número de casos de `cityCases` del front. Los casos se siembran en la iteración 4.

**Conversaciones** (para que la sección no aparezca disponible sin regla; se ajustan en la iteración 4)

| Regla | Objetivo | Condiciones |
|---|---|---|
| R-FAM-ESTUDIANTE | CONVERSACIONES | COMPLETA_BLOQUE(CAMINO) ≥ 1 (igual que `isFamilyUnlocked` del front) |
| R-FAM-APODERADO | CONVERSACIONES | ESCRIBE_CARTA ≥ 1 (provisional) |

**Niveles** (cada nivel incluye las condiciones del anterior; el nivel 4 tiene dos reglas alternativas, como en `getTravelerLevel`)

| Regla | Objetivo | Condiciones | Evaluador |
|---|---|---|---|
| R-NIV-2 | nivel 2 | COMPLETA_ACTIVIDAD ≥ 1 | misiones_camino_sin_inicio, parámetro 3 |
| R-NIV-3 | nivel 3 | lo de R-NIV-2 y COMPLETA_BLOQUE(CAMINO) ≥ 1 | ídem |
| R-NIV-4-CASO | nivel 4 | lo de R-NIV-3 y SUPERA_CASO ≥ 1 | ídem |
| R-NIV-4-INV | nivel 4 | lo de R-NIV-3 y PUBLICA_ENTREVISTA ≥ 1 | ídem |
| R-NIV-5 | nivel 5 | lo de R-NIV-3, SUPERA_CASO REFERENCIAS_DISTINTAS ≥ 6, PUBLICA_ENTREVISTA ≥ 1 y COMPLETA_CONVERSACION ≥ 1 | ídem |

En esta iteración solo se alcanzan los niveles 1 a 3.

#### 4.3.7 Instrumento RIASEC

Se crean con los mismos valores que en `datos/demo/instrumentos.py`: instrumento `TEST-RIASEC` (`tipo_resultado` COINCIDENCIAS), escala `ESC-LIKERT5` con la transformación O*NET, dimensiones `R I A S E C` y patrón de ítems `R R I I A A S S E E C C` repetido 5 veces. No se llama a `cargar_definiciones_instrumentos`, porque crea el bloque LAB y los otros instrumentos. Si conviene extraer funciones compartidas, la semilla `demo` debe producir exactamente los mismos datos. Cambian solo el nombre visible, los enunciados y las actividades de la aplicación.

- Nombre del instrumento: «Test de intereses (RIASEC)». Descripción: «Versión de prueba para la iteración 1.»
- Aplicación `APL-RIASEC`, momento UNICA, con las actividades `act-tip-01` a `act-tip-14`.
- Reparto de los 60 ítems (orden dentro de la actividad = orden del número):

| Actividades | Ítems |
|---|---|
| act-tip-01 | 1–5 |
| act-tip-02 | 6–10 |
| act-tip-03 | 11–15 |
| act-tip-04 | 16–20 |
| act-tip-05 … act-tip-14 | 4 ítems cada una: 21–24, 25–28, …, 57–60 |

- `validar_distribucion_items` debe pasar con la semilla `plataforma`.

**Enunciados (DATO DE PRUEBA).** El ítem `n` pertenece a la dimensión `patron[(n − 1) % 12]` y toma el enunciado `k = 2·⌊(n − 1) / 12⌋ + ((n − 1) % 12) % 2 + 1` de su dimensión. Así, los ítems 1 y 2 son R1 y R2, los 3 y 4 son I1 e I2, y el 13 es R3.

| k | R Realista | I Investigativa | A Artística |
|---|---|---|---|
| 1 | Reparar una bicicleta o un electrodoméstico. | Hacer experimentos en un laboratorio. | Dibujar o pintar. |
| 2 | Armar muebles siguiendo un plano. | Investigar por qué ocurre un fenómeno natural. | Escribir cuentos, poemas o guiones. |
| 3 | Cultivar un huerto o cuidar plantas. | Resolver problemas de matemáticas o de lógica. | Tocar un instrumento o componer música. |
| 4 | Manejar maquinaria o herramientas eléctricas. | Analizar datos para encontrar patrones. | Actuar en una obra de teatro. |
| 5 | Instalar el cableado eléctrico de una casa. | Leer sobre descubrimientos científicos. | Diseñar un afiche o la portada de una revista. |
| 6 | Construir una maqueta o una estructura de madera. | Estudiar cómo funciona el cuerpo humano. | Tomar fotografías o grabar videos creativos. |
| 7 | Cuidar animales en una granja o un refugio. | Observar el cielo y aprender sobre los planetas. | Decorar un espacio con un estilo propio. |
| 8 | Trabajar al aire libre, en el campo o en una obra. | Investigar las causas de una enfermedad. | Bailar o crear una coreografía. |
| 9 | Pintar o reparar paredes y techos. | Programar una solución para un problema. | Diseñar ropa o accesorios. |
| 10 | Ensamblar las piezas de una computadora. | Comparar información de distintas fuentes antes de concluir. | Inventar personajes para una historia o un videojuego. |

| k | S Social | E Emprendedora | C Convencional |
|---|---|---|---|
| 1 | Enseñar algo a un niño o a un compañero. | Vender un producto o una idea. | Ordenar y clasificar documentos. |
| 2 | Escuchar y aconsejar a alguien que tiene un problema. | Liderar un equipo para cumplir una meta. | Llevar las cuentas de ingresos y gastos. |
| 3 | Cuidar a personas enfermas o mayores. | Iniciar un negocio propio. | Registrar datos en una hoja de cálculo. |
| 4 | Organizar actividades para ayudar a la comunidad. | Convencer a otros en un debate. | Revisar un texto para corregir errores. |
| 5 | Trabajar como voluntario en una campaña. | Organizar un evento y conseguir auspiciadores. | Seguir un procedimiento paso a paso. |
| 6 | Explicar un tema difícil a un grupo. | Negociar un acuerdo o un precio. | Organizar un inventario de materiales. |
| 7 | Mediar en una discusión entre amigos. | Representar a tu salón ante la dirección. | Preparar un horario o un calendario de actividades. |
| 8 | Acompañar a alguien en su primer día en un lugar nuevo. | Planificar cómo hacer crecer un emprendimiento. | Archivar información para encontrarla rápido. |
| 9 | Orientar a otros estudiantes sobre sus estudios. | Dirigir una reunión y tomar decisiones. | Verificar que una factura esté correcta. |
| 10 | Atender a personas que llegan buscando ayuda. | Promocionar una actividad en redes sociales. | Mantener al día una base de datos. |

No se siembran TEST-INT, TEST-HAB ni TEST-AUTO en la semilla `plataforma`.

#### 4.3.8 Familias, carreras y ocupaciones

Universo de recomendación de esta iteración: las ocupaciones del catálogo del front que tienen código O*NET, más una creada. Cada `ocupacion` toma `codigo` = id del front, `titulo` = nombre en español del front y sus seis puntajes del Excel `data/Career_Interest_RIASEC_Clean.xlsx` por `codigo_onet`. **Solo se cargan estas 36 filas**, no las 923. Si falta un código en el Excel, la carga falla indicando cuál.

| codigo | titulo | codigo_onet |
|---|---|---|
| sound-technician | Técnico/a de sonido | 27-4014.00 |
| electrician | Electricista | 47-2111.00 |
| event-coordinator | Coordinador/a de eventos | 13-1121.00 |
| translator | Traductor/a | 27-3091.00 |
| community-manager | Community manager | 27-3031.00 |
| graphic-designer | Diseñador/a gráfico/a | 27-1024.00 |
| event-assistant | Asistente de eventos | 39-3031.00 |
| security-guard | Guardia de seguridad | 33-9032.00 |
| paramedic | Paramédico/a | 29-2043.00 |
| photographer | Fotógrafo/a | 27-4021.00 |
| lawyer | Abogado/a | 23-1011.00 |
| cook | Cocinero/a | 35-2014.00 |
| illustrator | Ilustrador/a | 27-1013.00 |
| firefighter | Bombero/a | 33-2011.00 |
| meteorologist | Meteorólogo/a | 19-2021.00 |
| municipal-police | Policía municipal | 33-3051.00 |
| medical-specialist | Médico/a especialista | 29-1216.00 |
| veterinarian | Veterinario/a | 29-1131.00 |
| biologist | Biólogo/a | 19-1029.04 |
| environmental-engineer | Ingeniero/a medioambiental | 17-2081.00 |
| civil-engineer | Ingeniero/a civil | 17-2051.00 |
| machinery-operator | Operador/a de maquinaria | 47-2073.00 |
| social-worker | Trabajador/a social | 21-1021.00 |
| psychologist | Psicólogo/a | 19-3033.00 |
| logistics-coordinator | Coordinador/a logístico/a | 13-1081.00 |
| journalist | Periodista | 27-3023.00 |
| teacher | Docente | 25-2031.00 |
| architect | Arquitecto/a | 17-1011.00 |
| geologist | Geólogo/a | 19-2042.00 |
| agricultural-engineer | Ingeniero/a agrónomo/a | 17-2021.00 |
| public-administrator | Gestor/a público/a | 11-3012.00 (por validar) |
| sociologist | Sociólogo/a | 19-3041.00 |
| data-analyst | Analista de datos | 15-2051.00 |
| urban-planner | Urbanista | 19-3051.00 |
| documentary-filmmaker | Documentalista | 27-2012.00 |
| nurse | Enfermero/a (DATO DE PRUEBA: no existe en el front) | 29-1141.00 |

`drone-operator` no entra: no tiene un código O*NET equivalente en el archivo.

Familias y carreras (de `ExplorationCatalogData.ts` y `catalogDetails.ts`; código de familia = `family-<id de carrera>`, nombre = `area`):

| Carrera | Nombre | Familia (nombre) | Ocupaciones (adaptadas de `careerOccupationIds`) |
|---|---|---|---|
| environmental-engineering | Ingeniería Ambiental | Ingeniería y ambiente | environmental-engineer, agricultural-engineer, geologist, data-analyst |
| journalism | Periodismo | Comunicación | journalist, documentary-filmmaker, photographer, community-manager, translator |
| nursing | Enfermería | Salud | nurse, paramedic |
| civil-engineering | Ingeniería Civil | Ingeniería e infraestructura | civil-engineer, architect, urban-planner, geologist, machinery-operator |
| veterinary-medicine | Medicina Veterinaria | Salud y ciencias naturales | veterinarian, agricultural-engineer, biologist |
| psychology | Psicología | Ciencias sociales y salud | psychologist, teacher, sociologist, social-worker |

Las adaptaciones respecto del front (agregar la ocupación propia de cada carrera y quitar `drone-operator`) se anotan como decisión. El catálogo local del front no se modifica en esta iteración.

### 4.4 Endpoints que usa el front

No se crean endpoints nuevos salvo los indicados. Todos aceptan y devuelven lo que ya definen las especificaciones del backend.

| Método y ruta | Uso en el front |
|---|---|
| `GET /cuentas` | Elegir la cuenta al ingresar. |
| `POST /acciones/ingresar` | Al iniciar la sesión del estudiante. |
| `GET /cuentas/{c}/estado` | Fuente de todo el mapa, fichas, insignias y nivel. |
| `GET /cuentas/{c}/progreso/{tipo}/{codigo}` | Requisitos de lo bloqueado (HU-025). |
| `POST /acciones/completar-actividad` | Al terminar o repetir una actividad. |
| `GET /actividades/{a}/items` | Ítems de una interacción de Mara. |
| `GET /cuentas/{c}/actividades/{a}/respuestas` | Retomar una interacción. |
| `POST /acciones/responder-items` | Guardar cada respuesta. |
| `GET /cuentas/{c}/instrumentos` | Avance del test: actividades completadas y faltantes. |
| `GET /cuentas/{c}/instrumentos/TEST-RIASEC/resultado` | Resultado, coincidencias y carreras recomendadas. |
| `GET /cuentas/{c}/desbloqueos?solo_no_vistos=true` | Avisos pendientes al ingresar. |
| `POST /cuentas/{c}/desbloqueos/marcar-vistos` | Al cerrar los avisos. |
| `POST /demo/reiniciar` | Reinicio de datos de prueba (solo desarrollo). |

### 4.5 Fixtures de contrato para el front

Script `scripts/exportar_fixtures_front.py`: prepara explícitamente una base temporal con `preparar_base(url, 'plataforma', crear_tablas=True)` y crea la aplicación sobre ella, según `docs/spec-refactor-estructura.md`. Ejecuta el recorrido de los escenarios P1, P2, P7, P10 y P12 y guarda las respuestas JSON en la carpeta que recibe el argumento obligatorio `--destino`, que debe ser `tests/fixtures/servidor/` dentro de `ov_frontend`. Como los repos están en carpetas independientes, el script no asume ninguna ruta relativa entre ellos; si el destino no existe, lo crea, y si no se pasa, falla con un mensaje que lo explica. Nombres: `estado-inicial.json`, `completar-mission-welcome.json`, `completar-mission-next-step.json`, `estado-ciudad.json`, `items-act-tip-01.json`, `completar-act-tip-14.json`, `resultado-riasec.json`, `desbloqueos-no-vistos.json`. Las pruebas del front usan estos archivos; si el contrato cambia, se regeneran en la misma tarea.

### 4.6 Escenarios de la semilla `plataforma`

En `tests/test_plataforma.py`. Todos parten de una base nueva con la semilla `plataforma` y fechas explícitas en `fecha_hora`. Cadena de respuestas de prueba para el RIASEC: opción 5 para los ítems de I, 4 para R, 3 para A y 1 para S, E y C.

| Escenario | Pasos | Esperado |
|---|---|---|
| P1. Estado inicial | Consultar el estado de Ana. | `mission-welcome` DISPONIBLE; el resto del camino BLOQUEADA; bloque CIUDAD BLOQUEADA y todas sus actividades BLOQUEADA; 4 fichas BLOQUEADA; I1–I9 BLOQUEADA con su requisito; un logro oculto como `???`; conversaciones BLOQUEADA; nivel actual 1; testimonios y preguntas de diario vacíos. |
| P2. Primer paso | Ana completa `mission-welcome`. | En una respuesta: R-enc-mitos, R-first-steps y R-I1. |
| P3. Saltarse la ruta | Ana intenta completar `act-07`. | 409 con el progreso de R-act-07 en 0 de 1; ningún evento. |
| P4. Informativa con fichas | Ana completa `enc-mitos`. | R-act-07, R-ficha-mitos, R-rec-ponteencarrera y R-rec-unesco-stem. |
| P5. Repetir no suma | Ana repite `enc-mitos` tres veces. | Tres eventos COMPLETA_ACTIVIDAD más; ningún desbloqueo; el progreso de I2 muestra el evaluador no cumplido. |
| P6. Un evento, varios desbloqueos | Ana completa `act-07` y `mission-story`. | Con `mission-story`: R-mission-future, R-I2 y R-NIV-2. Nivel actual 2. |
| P7. Llegada a la ciudad | Ana completa el resto del camino en orden. | Con `mission-next-step`: COMPLETA_BLOQUE(CAMINO), R-ciudad, R-I3, R-NIV-3 y R-FAM-ESTUDIANTE en una respuesta. En el estado: `act-tip-01` DISPONIBLE; `act-tip-02` a `act-tip-final` BLOQUEADA. |
| P8. Cuestionario incompleto | Ana responde 3 de los 5 ítems de `act-tip-01` e intenta completarla. | La actividad queda EN_CURSO; completar responde 409 con los 2 ítems faltantes y no registra eventos. |
| P9. Retomar | Consultar las respuestas de `act-tip-01`; responder los 2 faltantes; completar. | Se devuelven las 3 respuestas guardadas; al completar se desbloquea R-act-tip-02; `resultados_generados` vacío. |
| P10. Resultado | Ana responde y completa `act-tip-02` a `act-tip-14` con la cadena de prueba. | Con `act-tip-14`: `resultados_generados` = TEST-RIASEC/APL-RIASEC y R-act-tip-final. El resultado tiene I 100 %, R 75 %, A 50 %, S, E y C 0 %; `codigo_interes` = IRA sin empate; 10 coincidencias ordenadas por correlación, todas con `codigo` no nulo, la primera `geologist` con BEST_FIT; carreras recomendadas, como conjunto, `environmental-engineering`, `civil-engineering` y `veterinary-medicine`, cada una con un `via` que solo contiene ocupaciones del top 10. (Valores calculados con el Excel actual del repo.) |
| P11. Perfil plano | Luis completa el camino (función auxiliar), responde los 60 ítems con la opción 3 y completa las 14 interacciones. | `perfil_plano` verdadero, sin coincidencias ni carreras recomendadas. |
| P12. Avisos | Tras P7, consultar los desbloqueos no vistos de Ana, marcarlos y volver a consultar. | La segunda consulta devuelve una lista vacía. |
| P13. Progreso de lo bloqueado | Tras P2, consultar el progreso de BLOQUE CIUDAD, INSIGNIA I2 y ACTIVIDAD act-tip-final. | CIUDAD: COMPLETA_BLOQUE(CAMINO) en 0 de 1. I2: condición cumplida y evaluador `misiones_camino_sin_inicio` no cumplido. act-tip-final: COMPLETA_ACTIVIDAD(act-tip-14) en 0 de 1. |
| P14. Audiencia | Consultar el estado de Rosa. | Sin bloques, fichas ni insignias de estudiante. |
| P15. Semillas separadas | **Sustituido por `docs/spec-refactor-estructura.md`.** Escenario histórico: arrancar con `SEMILLA=plataforma` sobre una base creada con `demo`. Luego llamar a `/demo/reiniciar` en una app `plataforma`. | Resultado histórico: el arranque falla con el mensaje de 4.2. El reinicio vuelve a cargar `plataforma`, no `demo`. |
| P16. Eventos nuevos | Registrar `INVITA_A_CREW`, `FORMA_CREW` y `VENCE_DESAFIO_INTACTO` con `POST /eventos`. | Se desbloquean I4, I5 e I10; en el estado, I10 aparece con su nombre y requisito. |

Los invariantes de la sección 8 de la spec del motor se verifican también sobre esta semilla, reutilizando las pruebas parametrizables cuando se pueda.

## 5. Frontend

### 5.1 Configuración

- Variables en `.env.example` (nuevo): `VITE_DATOS=local`, `VITE_API_URL=/api`.
- `vite.config.ts` agrega un proxy de desarrollo: `/api` → `http://127.0.0.1:8000`, quitando el prefijo `/api`. Así no hace falta CORS en el backend.
- Sin dependencias nuevas: `fetch` nativo y `useSyncExternalStore`, como el resto del proyecto.

### 5.2 Módulo de servidor

Todo el acceso al backend vive en `src/features/servidor/`. Ningún componente llama a `fetch` directamente.

| Archivo | Responsabilidad |
|---|---|
| `config.ts` | Lee `VITE_DATOS` y `VITE_API_URL`; exporta `modoApi`. |
| `tipos.ts` | Tipos TypeScript que copian los esquemas Pydantic usados (nombres de campos en español, tal como llegan). |
| `cliente.ts` | `pedir<T>()`: JSON, errores tipados. Un 409 se devuelve como `{ tipo: 'bloqueado', detalle }` con el progreso o los ítems faltantes; un error de red como `{ tipo: 'sin_conexion' }`. |
| `cuenta.ts` | Cuenta activa en `sessionStorage` (`ov.cuenta-servidor.v1`). |
| `estadoServidor.ts` | Almacén con el último `EstadoCuenta`, el resultado RIASEC y los desbloqueos no vistos. `refrescar()` tras cada acción. |
| `acciones.ts` | `ingresar`, `completarActividad`, `responderItems`, `marcarVistos`, `reiniciarDatosDePrueba`. |
| `adaptadores.ts` | Funciones puras que convierten las respuestas del servidor a lo que consume la UI (estados del mapa, fichas, insignias, nivel, avisos, requisitos). Son lo que prueban los tests del front. Solo importa tipos (`import type`), para poder probarse con el mismo patrón de `tests/mission-logic.test.mjs`: transpilar con `typescript` e importar el resultado. |

### 5.3 Cuenta y sesión

- El login de demostración sigue aceptando cualquier usuario. En modo `api`, si el usuario escrito coincide con un código de `GET /cuentas` de rol ESTUDIANTE, se usa esa cuenta; si no, `est-ana`.
- Al entrar al portal del estudiante: `POST /acciones/ingresar`, luego `refrescar()` y la consulta de no vistos.
- Los portales de apoderado y orientadora no cambian.

### 5.4 Almacenes locales en modo `api`

- `ov.missions.v2` y `ov.student-adventure.v1` usan las claves `ov.missions.v2.api` y `ov.student-adventure.v1.api` en modo `api`, para no mezclar datos con el modo local.
- **Hidratación** tras cada `refrescar()`: el estado del servidor se proyecta sobre `journey.progress[codigo].estado` (COMPLETADA → `completada`, EN_CURSO → `en_curso`) y sobre `adventure.completedMissionIds` (misiones de campo cuya actividad está COMPLETADA). Se conservan `nodoActualId`, borradores y respuestas locales. Nunca se proyecta del front al servidor.
- La disponibilidad, las fichas obtenidas, las insignias y el nivel **no** se leen de esas proyecciones, sino del almacén del servidor a través de los adaptadores.

### 5.5 Mapa y siguiente actividad (HU-002, HU-011)

En `src/features/student-experience/map/mapPoints.ts`:

- En modo `api`, el `status` de cada punto del camino sale del estado de su `specActivityId` en el servidor (BLOQUEADA → `locked`, DISPONIBLE y EN_CURSO → `available`, COMPLETADA → `completed`). El badge «En progreso» usa EN_CURSO del servidor.
- El punto `city` está disponible si el bloque CIUDAD está DISPONIBLE.
- El punto `mara-test` refleja la primera interacción no completada (`act-tip-NN`), su número de 1 a 14 y la cantidad de ítems que devuelve el servidor, en lugar del texto fijo «siete preguntas».
- Los casos y el desafío se muestran bloqueados con «Disponible en una próxima iteración». Las misiones adicionales no se muestran.
- El requisito de un punto bloqueado sale de `GET /progreso/ACTIVIDAD/{codigo}` (5.10).
- `getRecommendedPoint` y `getNextCaminoActivity` usan esos estados, de modo que el panel recomienda lo mismo que dice el servidor.

### 5.6 Completar y repetir actividades (HU-004, HU-013, HU-014)

- Hay **un solo punto** donde se informa la finalización: cuando el reproductor (`StudentActivityPlayer.tsx`, función `move`) llega al cierre (`$fin`), tanto la primera vez como al repetir. Se llama a `completarActividad` antes de mostrar `FinishScreen`.
- Si el servidor responde con desbloqueos, `FinishScreen` los lista con textos del front por tipo: actividad («Se abrió: …»), ficha («Nueva ficha en tu mochila: …»), insignia, nivel («Subiste a …») y bloque CIUDAD («La ciudad te espera»).
- Si responde 409, se muestra el requisito pendiente y la actividad no se marca como completada localmente.
- Si no hay conexión, se avisa «No se pudo guardar en el servidor» con un botón para reintentar. No se avanza como si se hubiera guardado.
- Los registros (`act-07`, `mission-story`, etc.) siguen validando y guardando sus textos de forma local. Solo su finalización va al servidor.
- En modo `api`, `mission-expectations` y `mission-next-step` se pueden realizar con su contenido genérico actual (`createRegistration`); `pendingContent` no las bloquea.
- Las comprobaciones de las informativas siguen siendo locales y deben superarse antes de llegar a `$fin`, como hoy.

### 5.7 Fichas (HU-015)

- La mochila (`TravelerResources.ts` y la vista de recursos) muestra como obtenida una ficha solo si está DISPONIBLE en el servidor. El contenido, ícono y resumen siguen saliendo de `sheetDetails` y `catalog.recursos`.
- En modo `api`, abrir una diapositiva ya no agrega la ficha a `journey.resources`. `readResourceIds` (fichas leídas) sigue local.
- Las fichas bloqueadas muestran su requisito desde el progreso del servidor.

### 5.8 Test de intereses con Mara (HU-021, HU-022, HU-026, HU-027)

**Interacciones.** En modo `api`, cada `act-tip-NN` se construye en tiempo de ejecución con:

1. un diálogo de apertura de Mara (el de `instrumento_mara.json` para la 01; para 02–14, una plantilla con 3 variantes de saludo marcada como DATO DE PRUEBA);
2. un nodo `item` por cada ítem de `GET /actividades/act-tip-NN/items`, con formato `likert` de 5 puntos y las etiquetas de `ESC-LIKERT5`;
3. un diálogo de cierre.

`ItemNode` recibe el `enunciado` como texto y las opciones de la escala. Los ítems TIP de muestra (`tip-001`…`tip-007`) no se usan en modo `api`.

**Respuestas.**

- Cada selección llama a `responderItems` con `{item, opcion}` (orden 1–5).
- Al abrir una interacción se cargan sus respuestas guardadas y se continúa en el primer ítem sin responder.
- Si una respuesta ya no se puede cambiar (409 por resultado vigente), los ítems se muestran en solo lectura.

**Resultado.**

- Al completar `act-tip-14`, si `resultados_generados` incluye TEST-RIASEC, se refresca el resultado y se avisa que Elena tiene algo que mostrar.
- `act-tip-final` (`ResultNode`) y la página «intereses» del libro de Helena (`helenaPages.ts`, `HelenaBookView.tsx`) usan el resultado del servidor: áreas = las tres dimensiones de `codigo_interes`, en ese orden, con su nombre y porcentaje.
- El sello está listo para romperse (HU-027) solo si hay resultado vigente. El gesto de romperlo sigue guardándose en `discovery.revealedPages`.
- Con `perfil_plano`, se muestra que las respuestas no distinguen un interés y se ofrece revisar las interacciones. No se muestran ocupaciones afines.

**Afines (HU-026).**

- En el catálogo con `?afines=1`, `isAffine` usa las coincidencias del servidor por `codigo`: posición, correlación y ajuste (BEST_FIT, GREAT_FIT, GOOD_FIT).
- Una coincidencia cuyo `codigo` no exista en el catálogo del front (por ejemplo `nurse`) se muestra con el `titulo` del servidor y sin enlace a detalle.
- La página de intereses agrega «Carreras que conducen a ellas», con `carreras_recomendadas` y su `via`. Cada carrera enlaza a su detalle del front por `codigo`.

Las páginas de inteligencias y habilidades siguen con su contenido de demostración y la etiqueta «Disponible en una próxima iteración».

### 5.9 Avisos, insignias y nivel (HU-073, HU-074, HU-075)

- **Avisos.** La cola de avisos (`overlays/unlocks.ts`, `OverlayQueue.tsx`, `BadgeToast.tsx`, `NoveltiesMenu.tsx`) se alimenta de:
  - los `nuevos_desbloqueos` de cada acción;
  - los no vistos del servidor al ingresar.

  Se mapean así: INSIGNIA → `badge`, FICHA → `ficha`, BLOQUE CIUDAD → `ciudad`, NIVEL → `nivel` (nuevo tipo, con el estilo del aviso de insignia). Los desbloqueos de ACTIVIDAD y los demás tipos quedan fuera de la cola y de su contador. La cola automática se muestra solo en Camino y Ciudad, después de cerrar el reproductor y respetando los overlays prioritarios; la campana abre el mismo lote por solicitud en los demás módulos. Elena permanece únicamente en `FinishScreen`, con su enlace al libro.

  Se llama a `marcarVistos` **al terminar de mostrar todos los avisos del lote**. Antes del POST se vuelven a consultar los no vistos; cualquier aviso nuevo se incorpora y se muestra antes de marcar. Se utiliza el marcado global existente, incluidos los tipos sin presentación propia. Recargar antes del marcado conserva los pendientes en el servidor. Los errores mantienen el lote y permiten reintentar; si el POST quedó confirmado, se repiten solo las consultas pendientes. En modo `api`, `seenUnlockIds` y `announcedBadgeCodes` no deciden qué mostrar, contar o marcar.
- **Pasaporte.** `getStudentAchievementGroups` en modo `api` toma `done` del servidor (OBTENIDA). Conserva la agrupación, íconos y textos del front por código. Las ocultas no obtenidas (`???`) no se listan una por una: se muestra cuántas quedan por descubrir. Las insignias de misiones adicionales, que aún no existen en el servidor, no se muestran.
- **Nivel.** `getTravelerLevel` en modo `api` usa `nivel_actual` del servidor. La descripción y el «siguiente paso» siguen siendo los textos del front para ese número.

### 5.10 Requisitos de lo bloqueado (HU-025)

| Elemento bloqueado | Consulta | Texto |
|---|---|---|
| Punto del camino o de la ciudad | `GET /progreso/ACTIVIDAD/{codigo}` | La primera condición no cumplida, con el título de la actividad referida: «Requisito: completa “…”». |
| Punto de la ciudad desde el camino | `GET /progreso/BLOQUE/CIUDAD` | «Completa todas las misiones del camino (N de 9).» N se calcula con el estado del camino. |
| Ficha bloqueada | `GET /progreso/FICHA/{codigo}` | Igual que para una actividad. |
| Insignia bloqueada | `GET /progreso/INSIGNIA/{codigo}` | El `requisito` del estado; si tiene evaluador, «N de 3 misiones» con el conteo del camino. |
| Página «intereses» del libro de Helena | estado del bloque CIUDAD y `GET /cuentas/{c}/instrumentos` | Si la ciudad está bloqueada, su requisito. Si no, «Conversa con Mara: interacción N de 14» con la primera actividad faltante. |

Los adaptadores construyen estos textos. Las consultas se hacen al abrir el detalle, no al pintar todo el mapa.

### 5.11 Reinicio de datos de prueba

Solo si `import.meta.env.DEV` y `modoApi`: el menú del estudiante (`StudentUserMenu.tsx`) ofrece «Reiniciar datos de prueba». Confirma, llama a `POST /demo/reiniciar`, borra las claves `.api` del almacenamiento local y recarga.

### 5.12 Pruebas del front

- Pruebas nuevas en `tests/servidor-*.test.mjs` para los adaptadores, con los fixtures de 4.5: estados del mapa, siguiente actividad, fichas, insignias, nivel, avisos, requisitos, resultado y afines.
- Una prueba comprueba que en modo `local` los adaptadores no se usan y el comportamiento no cambia.
- Se ejecutan las suites que indica `ov_frontend/AGENTS.md`, más build y lint.

## 6. Recorrido de aceptación

Con una base preparada con Alembic y cargada mediante
`uv run python -m datos.cargar plataforma`, y el front en `VITE_DATOS=api`.
Cada paso indica qué HU verifica.

1. Reiniciar datos de prueba. Ingresar con el usuario `est-ana`. → Camino con «El inicio del viaje» recomendado y el resto bloqueado (HU-002, HU-011).
2. Abrir «La plaza de los rumores» bloqueada. → Requisito «completa “El inicio del viaje”» (HU-025).
3. Completar «El inicio del viaje». → El cierre lista la nueva actividad, la ficha «Tres pistas…» e I1; llegan los avisos (HU-004, HU-013, HU-073).
4. Completar «La plaza de los rumores». → Tres fichas nuevas en la mochila (HU-015).
5. Repetirla. → Sin desbloqueos nuevos; sigue completada (HU-014).
6. Completar `act-07` y «Las huellas que traigo». → I2 y nivel 2 (HU-074, HU-075).
7. Completar el resto del camino. → Ciudad abierta, I3 y nivel 3.
8. En la ciudad, responder 3 ítems de la primera interacción con Mara, salir y volver. → Retoma en el cuarto ítem (HU-021).
9. Completar las 14 interacciones. → Aviso de Elena; el sello de intereses está listo (HU-027).
10. Revelar el resultado. → Tres dimensiones con porcentaje, ocupaciones afines y carreras recomendadas (HU-022, HU-026).
11. Abrir el pasaporte. → Insignias obtenidas, bloqueadas con requisito y ocultas sin nombre (HU-074).
12. Recargar el navegador. → Todo el estado se mantiene porque sale del servidor.

## 7. Invariantes de la integración

1. En modo `api`, ningún estado de disponibilidad, finalización, ficha, insignia o nivel se decide en el front.
2. Una actividad solo se ve COMPLETADA si el servidor la tiene COMPLETADA.
3. Repetir una actividad siempre llega al servidor.
4. Ningún componente llama a `fetch` fuera de `src/features/servidor/`.
5. En modo `local`, el comportamiento y las pruebas existentes del front no cambian.
6. La semilla `demo` y todos sus escenarios siguen pasando sin cambios fuera de las adaptaciones autorizadas en 4.2.

## 8. Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Test de intereses | RIASEC O*NET de 60 ítems repartido en las 14 interacciones de Mara, en lugar del TIP de muestra. |
| Semillas | **Sustituido por `docs/spec-refactor-estructura.md`.** Decisión histórica: `plataforma` nueva y separada; `demo` intacta para conservar sus pruebas. |
| Códigos | Los ids del front son los códigos del backend. |
| Universo de recomendación | Solo las ocupaciones del catálogo del front con código O*NET, para que la recomendación siempre muestre opciones conocidas. |
| Comunicación | Proxy de Vite en desarrollo, sin CORS. |
| Contenido narrativo | Se queda en el front; el backend guarda estructura y estado. |

## 9. Fases de implementación

| Fase | Repo | Contenido | Para terminar |
|---|---|---|---|
| F0 | ambos | Línea base: instalar, correr pruebas del back, build, lint y suites del front. Comprobar que la sección «Reglas compartidas» es idéntica en los dos `AGENTS.md`. Registrar los conteos en `decisiones-iteracion-1.md`. | Todo en verde o fallas previas documentadas. |
| F1 | back | 4.1 y 4.2: selección de semilla, esquema 5, contrato de coincidencias, adaptaciones autorizadas, README. | `uv run pytest -q` en verde con la semilla `demo`. |
| F2 | back | 4.3 y 4.6: semilla `plataforma`, eventos, evaluador, reglas, instrumento, catálogo y escenarios P1–P16. | P1–P16 y las pruebas anteriores en verde. |
| F3 | back → front | 4.5: script de fixtures y su ejecución. | Fixtures generados en el front. |
| F4 | front | 5.1–5.7 y 5.11: configuración, módulo de servidor, cuenta, hidratación, mapa, finalización, fichas y reinicio. | Recorrido de aceptación pasos 1–7 a mano; build, lint y pruebas nuevas en verde. |
| F5 | front | 5.8: Mara, respuestas, resultado, libro de Helena y afines. | Pasos 8–10. |
| F6 | front | 5.9, 5.10 y 5.12: avisos, pasaporte, nivel y requisitos. | Pasos 11–12 y todas las pruebas. |
| F7 | ambos | Verificación final: recorrido completo, revisión de invariantes, actualización de decisiones y README de ambos repos. | Informe con resultado por HU. |

Atajo para un primer intento rápido: F1 → F2 → F3 → F4 permite ya probar el camino completo contra la BD. F5 y F6 completan el test y los logros.
