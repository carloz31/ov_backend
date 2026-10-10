# Iteración 1 · Anexo: tarjeta de cierre, perfil y vista de resultados

Vive en `ov_backend/docs/iteraciones/`. Es un anexo de `spec-iteracion-1.md`: no cambia su alcance de datos, solo agrega lo que aquí se describe. Afecta a `ov_backend` (rama `iteracion-1`) y `ov_frontend` (rama `iteracion-1`).

**Autorización de interfaz.** Este documento describe de forma expresa las vistas, los elementos y los textos que se agregan o cambian. Vale como la autorización que pide la sección «Datos del servidor sin vista» del `AGENTS.md` de `ov_frontend`. En el resumen de cada fase, cita la sección de este anexo que autoriza cada cambio de interfaz. Lo que no esté descrito aquí no se agrega: se anota en `docs/pendientes-interfaz.md` y se avisa.

**Precedencia.** Para la tarjeta de cierre de actividad, la vista de perfil y la vista de resultado completo, este anexo prevalece sobre las especificaciones de `docs/student-experience/`. En la fase F0 se agrega esa línea a la sección «Interfaz del estudiante» del `AGENTS.md` del front.

**Referencia visual.** El usuario diseñó las vistas en un lienzo; los textos, el orden de las secciones y las reglas de este anexo son la fuente de verdad. Si el usuario adjunta capturas en `ov_frontend/docs/student-experience/referencias/cierre-y-resultados/`, úsalas para la composición. El estilo se construye con los componentes y clases que ya existen (`Parchment`, `DiscoveryStage`, `LumiMedallion`, `sx-*`, `sx-d-*`); no se agregan librerías.

## Fases

| Fase | Repo | Qué |
|---|---|---|
| F0 | ambos | Lectura, precedencia y decisiones. |
| F1 | front | Restaurar la vista de perfil completa en modo API. |
| F2 | back + front | Descripciones reales de las dimensiones y campo `descripcion` en el resultado. |
| F3 | front | Tarjeta de cierre de actividad con todos los tipos de desbloqueo. |
| F4 | front | Vista de resultado completo por página del libro de Helena (COINCIDENCIAS y DESTACADAS). |
| F5 | ambos | Verificación final, documentos y resumen. |

Al terminar cada fase: `npm run build`, `npm run lint`, `npm test` y `npm run check:estructura` en el front; las pruebas del backend si la fase lo tocó. Un commit por fase y por repo (`Iteración 1 · A1: perfil completo en modo API`, `A2`, `A3`…). Sin push.

**Línea base de pruebas del front.** En `iteracion-1`, antes de este anexo, `npm test` da 398 pruebas que pasan y 15 que fallan. Esas 15 no son parte de este trabajo. Ninguna fase puede aumentar los fallos; reporta el número en cada resumen.

---

## F0 · Lectura y preparación

1. Lee los `AGENTS.md` de ambos repos, `plan-iteraciones.md`, `spec-iteracion-1.md`, `decisiones-iteracion-1.md` y este anexo.
2. Agrega a «Interfaz del estudiante» del `AGENTS.md` del front: «Para la tarjeta de cierre de actividad, la vista de perfil y la vista de resultado completo prevalece `ov_backend/docs/iteraciones/spec-iteracion-1-cierre-perfil-resultados.md`».
3. Registra en `decisiones-iteracion-1.md` una entrada «Anexo de cierre, perfil y resultados» con el resumen de las fases.
4. Detente y resume. Si algo de este anexo contradice otra fuente, explícalo aquí y no sigas.

---

## F1 · Vista de perfil completa en modo API (front)

**Problema.** En `iteracion-1`, `useStudentProfile` devuelve en modo API solo `ficha` (nombre, progreso, nivel, insignias, texto) y deja vacíos `pages`, `badges`, `visibleBadges` y `plans`. `StudentProfileView` hace un `return` temprano con un pergamino reducido. La vista completa de `main` (`src/features/student-experience/profile/StudentProfileView.tsx` en esa rama) sigue en el archivo, pero solo se usa en modo local.

**Cambio.** Una sola vista en ambos modos: la de `main`.

- `src/features/discovery/hooks/useStudentProfile.ts` devuelve la misma forma en ambos modos: `nombre`, `iniciales`, `level` (`TravelerLevel | null`), `recorrido`, `ciudad`, `afinidadCiudad`, `badges`, `visibleBadges`, `pages`, `plans` y `extraFavorites`, además de `adventure`, `journey` y `context`. Desaparece `ficha`.
  - Modo API:
    - `nombre` = `resumen.cuenta.nombre` (si falta, «Mi perfil») e `iniciales` sale de él.
    - `level` = `getTravelerLevel(adventure, resumen.nivel_actual ?? null)`.
    - `recorrido` = `progresoBloque(actividades).porcentaje`.
    - `ciudad` = `ciudadDisponible(actividades)` y `afinidadCiudad` = `progresoBloque(actividades, 'CIUDAD').porcentaje` (0 si no hay ciudad).
    - `badges` = `getStudentAchievementGroups(adventure, journey, gruposApi)` aplanado con su índice de grupo, donde `gruposApi = insigniasServidor(logros, getAchievementPresentations())`.
    - `visibleBadges` = `getProfileBadges(..., { grupos: gruposApi, cuenta })`.
    - `pages` = `getHelenaPagesApi(paginaInteresesServidor(...), paginasReveladasApi(...))`, igual que en `useHelenaPages`.
  - Modo local: como en `main` (nombre «Alex», iniciales «AL», `getZoneProgress`, `canAccessCity`).
  - Planes y favoritos se leen del estado local en ambos modos: no tienen equivalente en el servidor en esta iteración.
- `src/pages/student/StudentProfileView.tsx`: se elimina el bloque `if (ficha)`. El encabezado usa `iniciales` y `nombre`; las barras usan `recorrido` y `afinidadCiudad`. Si `level` es `null`, el medallón se reemplaza por el texto «No hay un nivel disponible en el servidor.» y se oculta el recuadro «Para el nivel N».
- `textoIntereses` desaparece: el capítulo II ya muestra el estado de cada página.

**Parche de referencia.** El usuario tiene `restaurar-perfil-iteracion-1.patch` con este cambio exacto. Si ya está aplicado (`git apply --check` falla porque los cambios están presentes), solo verifica y haz el commit. Si no lo está, aplica el parche o implementa lo descrito; el resultado debe ser el mismo.

**Pruebas.** Agrega `tests/servidor-perfil.test.mjs`. Debe comprobar, con los fixtures de `tests/fixtures/servidor/`, que en modo API `pages` tiene la página de intereses con el estado del servidor y que `badges` sale de los logros del servidor. Si el hook no se puede cargar aislado, prueba las funciones puras que usa y anótalo.

---

## F2 · Descripciones de las dimensiones (back + front)

Hoy todas las dimensiones tienen `descripcion = "Dimensión de demostración: …"` y `DimensionResultado` no la expone. El front inventa un texto («Te atraen actividades vinculadas con…»). Se llena el dato y se expone.

### Backend

1. `app/core/parametros.py`: agrega `DESCRIPCIONES_RIASEC: dict[str, str]` con los textos de la tabla de abajo. Úsalo en `datos/plataforma.py` y en `datos/demo/instrumentos.py` al crear las dimensiones RIASEC, en lugar del texto de demostración.
2. `datos/demo/instrumentos.py`: usa los textos de la tabla de inteligencias para las 7 dimensiones de `TEST-INT`. `TEST-HAB` conserva su texto de demostración.
3. `app/schemas/instrumentos.py`: `DimensionResultado` agrega `descripcion: str`, que se llena desde `Dimension.descripcion` donde se construye el resultado. Lo mismo para `dimensiones_destacadas`.
4. Si `datos.cargar` no actualiza filas existentes, documenta en el README que hay que recrear la BD local para ver los textos nuevos. No agregues una migración de datos.
5. Pruebas: el resultado de `TEST-RIASEC` trae `descripcion` no vacía y distinta del texto de demostración en las 6 dimensiones. Regenera los fixtures con `scripts/exportar_fixtures_front.py --destino <ov_frontend>/tests/fixtures/servidor/`.

**RIASEC** (los nombres son los de `DIMENSIONES_RIASEC`):

| Código | Nombre | `descripcion` |
|---|---|---|
| R | Realista | Te atraen las actividades prácticas: trabajar con las manos, usar herramientas o máquinas y estar al aire libre. |
| I | Investigativa | Te atrae observar, preguntar y analizar para entender cómo y por qué funcionan las cosas. |
| A | Artística | Te atrae crear, imaginar y expresarte con libertad, sin reglas rígidas. |
| S | Social | Te atrae ayudar, enseñar, cuidar o acompañar a otras personas. |
| E | Emprendedora | Te atrae liderar, convencer, organizar proyectos y tomar decisiones. |
| C | Convencional | Te atrae ordenar información, seguir procedimientos claros y trabajar con datos de forma precisa. |

**Inteligencias** (`TEST-INT`, 7 dimensiones; no hay Naturalista):

| Código | Nombre | `descripcion` |
|---|---|---|
| INT-LIN | Lingüística | Usar las palabras para expresarte, contar historias, explicar y convencer. |
| INT-LOG | Lógico-matemática | Razonar con números, patrones y relaciones de causa y efecto. |
| INT-ESP | Espacial | Imaginar, dibujar y orientarte en el espacio, viendo las cosas en tu mente. |
| INT-CIN | Cinestésico-corporal | Usar el cuerpo con precisión para moverte, crear o expresarte. |
| INT-MUS | Musical | Percibir ritmos, melodías y sonidos, y crear con ellos. |
| INT-INTER | Interpersonal | Entender a otras personas, ponerte en su lugar y trabajar en equipo. |
| INT-INTRA | Intrapersonal | Conocerte, reconocer lo que sientes y saber qué te motiva. |

### Frontend

1. `src/types/servidor.ts`: `DimensionResultado` agrega `descripcion: string`.
2. `src/lib/servidor/adaptadores.ts`: donde hoy se arma `description: \`Te atraen actividades vinculadas con …\``, usa `dimension.descripcion`.
3. Contenido del front (los ejemplos son contenido de presentación, no dato del servidor): crea `src/features/discovery/data/dimensionExamples.ts`, que exporta `ejemplosDimension: Record<string, string>` por código de dimensión, con los textos de la tabla de abajo. En modo local, la descripción de cada dimensión RIASEC sale de este mismo archivo (`descripcionesLocales`), con los textos de la tabla del backend.
4. Actualiza `docs/refactor/origen-de-datos.md`: la descripción de una dimensión viene del servidor; los ejemplos son contenido del front.

| Código | Ejemplos («Por ejemplo: …») |
|---|---|
| R | reparar o armar objetos, cultivar, construir, manejar equipos o trabajar al aire libre. |
| I | hacer experimentos, resolver acertijos, investigar un tema o entender cómo funciona algo. |
| A | dibujar, escribir, actuar, componer, diseñar o crear contenido. |
| S | enseñar a alguien, cuidar, escuchar, hacer voluntariado o trabajar en equipo. |
| E | dirigir un grupo, convencer, vender una idea u organizar un evento. |
| C | ordenar información, llevar registros, planificar con detalle o trabajar con números. |
| INT-LIN | leer, escribir, debatir o aprender idiomas. |
| INT-LOG | resolver problemas, programar, experimentar o encontrar patrones. |
| INT-ESP | dibujar, armar objetos, leer mapas o diseñar. |
| INT-CIN | practicar deportes, bailar, actuar o construir con las manos. |
| INT-MUS | tocar un instrumento, recordar canciones o notar sonidos que otros no notan. |
| INT-INTER | mediar en un conflicto, organizar un grupo o explicar algo a un amigo. |
| INT-INTRA | escribir sobre lo que vives, fijarte metas propias o reflexionar antes de decidir. |

---

## F3 · Tarjeta de cierre de actividad (front)

Reemplaza el contenido de `src/features/activities/components/FinishScreen.tsx` en ambos ramales: el de modo API (`registro`) y el de modo local.

### Archivos

- `src/features/activities/lib/finishSummary.ts` (lógica pura, solo importa tipos): `resumirCierre(entrada) → ResumenCierre`.
- `src/features/activities/hooks/useActivityFinish.ts`: arma la `entrada` desde el servidor o desde el estado local y devuelve el `ResumenCierre` y las acciones de navegación.
- `src/features/activities/components/FinishScreen.tsx`: compone las secciones. Las secciones son componentes del mismo dominio: `FinishBackpackSection.tsx`, `FinishJournalSection.tsx`, `FinishExtrasSection.tsx`. Ningún `.tsx` pasa de 300 líneas.
- CSS en `src/features/activities/styles/` (o en el archivo de estilos de la tarjeta que ya exista).

### Datos (`resumirCierre`)

Entrada: `desbloqueos: DesbloqueoNuevo[]`, `yaCompletada: boolean`, `completada: boolean` y `tienePreguntaDiario: boolean`. En modo local, la entrada se construye con los datos locales actuales: `sheets` → FICHA, `badge` → INSIGNIA y `piece` → extra «pieza».

Clasificación por `tipo_objetivo`:

| Tipo | Destino en la tarjeta | Texto |
|---|---|---|
| FICHA | Mochila · fichas | `objetivo.nombre` |
| TESTIMONIO | Mochila · testimonios | `objetivo.nombre`; si el recurso existe en `catalog.recursos`, se agregan la persona y una cita de una línea desde ese contenido. Si no existe, solo el nombre. No se inventa una cita. |
| PREGUNTA_DIARIO | Marca «Nueva» en el bloque del diario | — |
| NIVEL | Extras | «Subiste a {nombre}» |
| INSIGNIA | Extras | «Nueva insignia: {nombre}» |
| BLOQUE | Extras | «La ciudad te espera» si el código es `CIUDAD`; si no, «Nueva zona: {nombre}» |
| ACTIVIDAD | Extras | 1: «Se abrió: {nombre}». 2 o más: un solo chip «{n} actividades nuevas» |
| CONVERSACIONES | Extras | «Conversaciones disponibles» |
| pieza (solo local) | Extras | «Pieza de llave: {nombre} · {obtenidas} de {necesarias} para la ciudad» |

- Los extras van en este orden: NIVEL, INSIGNIA, BLOQUE, ACTIVIDAD, CONVERSACIONES y pieza.
- Se eliminan los duplicados por `tipo_objetivo` + `objetivo.codigo`.
- Reemplaza `textosDesbloqueos` por `resumirCierre`. Si otro archivo usa `textosDesbloqueos`, conserva esa función.

**Estado de la tarjeta (`modo`):**

- `consultando`: modo API y la actividad aún no figura como COMPLETADA. Es el estado actual («Consultando tu avance.»).
- `reintento`: `yaCompletada` y sin desbloqueos.
- `sinNovedades`: no `yaCompletada` y sin desbloqueos.
- `soloExtras`: hay desbloqueos, pero ninguno es FICHA ni TESTIMONIO.
- `recursos`: hay al menos una FICHA o un TESTIMONIO.

**`yaCompletada`.** Es el estado de la actividad en `store/servidor` en el momento de abrirla, antes de enviar la finalización; en modo local, el estado en `journey.progress`. Se guarda al montar el reproductor de la actividad (donde hoy se arma `cierreServidor` en `NodeRenderer`) y llega a `FinishScreen` como prop. Hoy el texto «No hay nuevos desbloqueos en esta repetición» aparece con cualquier cierre sin desbloqueos; eso se corrige con este estado.

### Textos

| Modo | Título (`h2`) | Subtítulo |
|---|---|---|
| recursos (1–4 recursos) | Este hallazgo viaja contigo. | Tu actividad quedó registrada. Guardamos {n} recurso nuevo / {n} recursos nuevos en tu mochila. |
| recursos (5 o más) | ¡Cuántos hallazgos juntos! | igual que arriba |
| soloExtras | Sigues avanzando. | Tu actividad quedó registrada. Esto es lo que desbloqueaste: |
| sinNovedades | Este hallazgo viaja contigo. | Tu actividad quedó registrada. |
| reintento | Repaso completado. | Tu actividad quedó registrada. Esta repetición no trae desbloqueos nuevos. |
| consultando | Consultando tu avance. | (sin cambios) |

En modo local, el título del modo `recursos` y del modo `sinNovedades` es «Tu avance queda guardado.» cuando la actividad no está completada, como hoy. Se conservan el texto de `recompensa.mensajeFin`, la nota de `act-tip-01` y el bloque «Elena tiene algo que mostrarte» de `act-tip-14`, en el mismo lugar relativo (después del subtítulo).

### Composición, de arriba abajo

1. **Lumi** (`LumiMedallion celebration`, rótulo «Lumi»). Va en versión compacta (unos 72 px) cuando hay 5 o más recursos o en escritorio. En `reintento`, el halo se ve atenuado.
2. **Título y subtítulo.**
3. **«Nuevo en tu mochila»** (solo en modo `recursos`):
   - Encabezado: ícono de mochila, el rótulo «Nuevo en tu mochila», un contador con el total de recursos y, a la derecha, el enlace «Abrir mochila», que lleva a `appPaths.student.resources`.
   - **Fichas:** van en una grilla de 2 columnas. Cada ficha es un enlace (`<a>`/`Link`, no un `div` con `onClick`) con un ícono de documento, el rótulo «Ficha», el título y un chevron a la derecha. Lleva a `${appPaths.student.resources}?ficha=${codigo}`.
     - Con más de 4 fichas, se muestran 3 y la cuarta celda es una tarjeta punteada «+{n} fichas más», que lleva a `${resources}?kind=sheet`.
     - Con 2 o más tipos de recurso, encima de la grilla va el rótulo «{n} fichas».
   - **Testimonios:** cada uno va en una tarjeta a ancho completo, con una inicial en un círculo, el rótulo «Testimonio», «{persona} · {rol}» (o el `nombre`), la cita en una línea (dos en escritorio) y un chevron. Lleva a `${resources}?kind=testimonial&ficha=${codigo}`.
     - Con más de 2 testimonios, se muestran 2 y debajo va el enlace «Ver {n} testimonio(s) más», que lleva a `${resources}?kind=testimonial`.
     - Con 2 o más tipos de recurso, el rótulo es «{n} testimonios».
   - Si `useBackpack` no selecciona un testimonio con `?kind=testimonial&ficha=`, amplíalo para que lo haga. Ese cambio está autorizado aquí.
4. **«Una pregunta para tu diario»:**
   - Se muestra siempre que `activity.promptDiario` exista, también en `reintento`.
   - Lleva la pregunta en cursiva y el botón «Escribir en mi diario» (`BookOpen`), con la misma navegación actual.
   - Si hay un desbloqueo PREGUNTA_DIARIO, junto al rótulo va la insignia «Nueva», con un círculo «!» y `aria-label="Pregunta nueva"`.
   - El rótulo «Nueva pregunta en tu diario» del ramal local pasa a ser «Una pregunta para tu diario».
5. **«También ocurrió»** (en modos `recursos` y `soloExtras`, cuando hay extras):
   - En modo `recursos`, son chips pequeños con ícono que pasan a otra fila cuando no caben.
   - En modo `soloExtras`, cada extra es una tarjeta pequeña (grilla de 2 columnas) con su rótulo en mayúsculas («Nivel», «Insignia», «Zona», «Actividad», «Conversaciones») y su texto. La insignia lleva a `appPaths.student.passport`.
   - Íconos (lucide): NIVEL `TrendingUp`, INSIGNIA `Award`, BLOQUE `Map`, ACTIVIDAD `Compass`, CONVERSACIONES `MessageCircle`.
6. **Separador y botón principal «Volver al mapa»** (ícono `Map`, antes del texto). Reemplaza a «Continuar» en todos los modos. Lleva a `appPaths.student.exploration`. Si `onClose` ya hace exactamente eso, úsalo; si no, navega y luego llama a `onClose`.

En modo `reintento` no hay sección de mochila ni de extras, y no se lista lo desbloqueado antes.

### Escritorio (ancho ≥ 900 px)

- La tarjeta mide hasta 960 px y se divide en dos columnas:
  - **Izquierda (340 px):** Lumi compacto, título, subtítulo, diario y extras.
  - **Derecha:** la mochila, separada por un borde a la izquierda. Los testimonios van en una grilla de 2 columnas con la cita en 2 líneas.
- El diario siempre va en la columna izquierda.
- «Volver al mapa» va alineado a la derecha, bajo un separador de ancho completo.
- Sin mochila (modos `soloExtras`, `sinNovedades` y `reintento`), la tarjeta usa una sola columna de hasta 560 px, centrada.
- Objetivo: el caso de 7 fichas, 3 testimonios y 5 extras cabe sin scroll en una pantalla de 1366 × 768.

### Pruebas

`tests/servidor-cierre.test.mjs`, sobre `finishSummary.ts`:

- La clasificación y el orden de los 8 tipos.
- Dos actividades se agrupan en un solo chip.
- Con 7 fichas, el resumen muestra 3 visibles y «+4».
- Con 3 testimonios, muestra 2 visibles y «1 más».
- Los modos `reintento` y `sinNovedades` según `yaCompletada`.
- El modo `soloExtras`.
- Con PREGUNTA_DIARIO, el diario lleva la marca «Nueva».
- Los duplicados se eliminan.
- El título cambia a «¡Cuántos hallazgos juntos!» con 5 recursos.

Usa desbloqueos de los fixtures del servidor cuando existan; si no, crea datos marcados `DATO DE PRUEBA`.

---

## F4 · Vista de resultado completo (front)

Hoy el resultado se ve resumido dentro del pergamino de cada página del libro de Helena (`HelenaBookPages.tsx`). Se agrega una vista de página completa por página descifrada, armada con una sola plantilla cuyas secciones dependen del **tipo de resultado** y no del código del instrumento.

### Ruta y entrada

- Nueva ruta: `profile/helena/:pagina` → `src/pages/student/HelenaResultView.tsx`. Agrega `discoveryPaths.helenaPage(id)` = `/student/profile/helena/${id}`.
- En `HelenaBookPages.tsx`, en cada página descifrada, se agrega como primer botón el enlace «Ver resultado completo» (`sx-d-action sx-d-action-gold`), que lleva a `discoveryPaths.helenaPage(p.id)`. Lo demás del pergamino no cambia.
- Si la página no existe o no está descifrada, la vista redirige al libro (`discoveryPaths.helena`).

### Tipo de resultado

- `src/features/discovery/data/resultPages.ts` exporta, por página: `instrumento` y `tipoResultado`. Los valores son `intereses` → `TEST-RIASEC` / `COINCIDENCIAS` e `inteligencias` → `TEST-INT` / `DESTACADAS`.
- Si `store/servidor` ya tiene la lista de `GET /instrumentos` (`InstrumentoPublico.tipo_resultado`), usa ese valor y deja el archivo como respaldo de modo local. Si no la tiene, usa el archivo y anótalo en `origen-de-datos.md`.
- `src/features/discovery/hooks/useResultPage.ts` arma el modelo de la vista según `tipoResultado`. La vista y sus componentes no preguntan por el código del instrumento.

### Secciones de la plantilla

La vista usa `DiscoveryStage` y un contenedor de hasta 1200 px.

| # | Sección | COINCIDENCIAS (intereses) | DESTACADAS (inteligencias) |
|---|---|---|---|
| 1 | Cabecera | Común | Común |
| 2 | Bloque protagonista | Código de interés | Dimensión o dimensiones destacadas |
| 3 | Perfil por dimensión | Común | Común |
| 4 | Guía «¿Qué significa…?» | Común | Común |
| 5 | Ocupaciones afines | Sí | No |
| 6 | Carreras que conducen | Sí | No |
| 7 | Qué hacer con esto | No | Sí |
| 8 | Caso límite | Perfil plano | Empate (dentro de la sección 2) |
| 9 | Avisos de cierre | Común | Común |

**1. Cabecera.**
- Enlace «El libro de Helena» (chevron izquierdo), que lleva a `discoveryPaths.helena`.
- Antetítulo «Página {numeral} · descifrada · {subtitle}».
- Título `h1` = `page.title`.
- Bajada:
  - Intereses: «Helena leyó tus respuestas y encontró los tipos de actividad que más te llaman. No es un veredicto: es una pista para explorar ocupaciones y carreras que podrías no haber considerado.»
  - Inteligencias: «No hay una sola forma de ser inteligente. Helena leyó tus respuestas y encontró las capacidades que más usas para aprender, crear y resolver. Todas se pueden desarrollar.»
- Si `page.demo`, debajo va el aviso que ya existe (`etiquetaDemo` + «Este ejemplo no es tu resultado personal.» / «Este instrumento aún no está disponible.»).

**2a. Código de interés (COINCIDENCIAS).**
- Rótulo «Tu código de interés».
- Las 3 dimensiones de `codigo_interes`, en orden: un círculo con la letra, el nombre y «Más fuerte», «Segundo» o «Tercero».
- Debajo, la frase: «Te atraen sobre todo las actividades en las que {desc1}, seguidas de las que te permiten {desc2} y de las que te invitan a {desc3}.» Si armarla con las descripciones del servidor no da un texto natural, muestra en su lugar las tres descripciones como lista y anótalo.
- Si `codigo_interes.hay_empate`, agrega: «Algunos de tus intereses quedaron empatados; el orden entre ellos no indica preferencia.»

**2b. Destacadas (DESTACADAS).**
- Rótulo «Tu inteligencia más desarrollada», o «Tus inteligencias más desarrolladas» si hay más de una en `dimensiones_destacadas` (o en las de mayor porcentaje, en modo local).
- Una tarjeta clara por cada destacada, con el porcentaje en un círculo, el nombre, la `descripcion` y «Suele notarse cuando {ejemplos}.».
- Si hay más de una, debajo va: «Dos inteligencias quedaron en el mismo nivel. No hace falta elegir entre ellas: juntas describen cómo te gusta aprender y resolver.» (con más de dos: «Varias inteligencias quedaron…»).

**3. Perfil por dimensión.**
- Rótulo «Cuánto resonó cada tipo de actividad» en intereses y «Cuánto se expresó cada inteligencia» en inteligencias.
- Una fila por dimensión, ordenada de mayor a menor `porcentaje`, con nombre, barra y porcentaje. Las del bloque protagonista van resaltadas (color de acento y negrita).
- Cada fila es un `<button aria-expanded>` que despliega debajo la `descripcion`.
- Nota final: «Toca un tipo para ver qué significa, o abre la guía completa. Ninguno es mejor que otro.» en intereses, y «Toca una inteligencia para ver qué significa. Un porcentaje bajo no es una carencia: es una capacidad que aún puedes ejercitar.» en inteligencias.
- Con `perfil_plano`, todas las filas se ven iguales y ninguna se resalta.

**4. Guía.**
- A la derecha del rótulo de la sección 3 va un botón con ícono de información, «¿Qué significa cada tipo?» en intereses y «¿Qué es cada una?» en inteligencias, con `aria-expanded`.
- El botón abre, debajo de la sección 2–3, un panel con el antetítulo «Guía rápida» y un título:
  - Intereses: «Los seis tipos de interés (RIASEC)», con la bajada «Tu código son las tres letras con más fuerza. Cada ocupación también tiene su código, y por eso podemos compararlas contigo.»
  - Inteligencias: «Las siete inteligencias de este cuestionario».
- El panel lleva un botón de cerrar con `aria-label="Cerrar guía"`.
- Contiene una tarjeta por dimensión, en el orden del instrumento, con nombre, `descripcion` y «Por ejemplo: {ejemplos}». Las del bloque protagonista llevan el borde de acento.

**5. Ocupaciones afines (COINCIDENCIAS, sin perfil plano).**
- Antetítulo «Paso 1 · Ocupaciones afines», título «Trabajos que se parecen a lo que te atrae» y bajada «Las ocupaciones cuyo perfil de intereses se parece más al tuyo. Elige una para ver abajo qué carreras conducen a ella.»
- Filtro de pestañas (`role="tablist"`): «Todas», «Mejor ajuste», «Gran ajuste» y «Buen ajuste».
- Datos:
  - Modo API: `coincidenciasRiasec(resultado)`; las etiquetas de ajuste salen de `textoAjuste`.
  - Modo local: las afinidades locales que ya usa `useCatalogAffinity`. Si no hay ninguna, la sección no se muestra.
- Cada ocupación es una tarjeta con:
  - la etiqueta de ajuste;
  - un botón corazón (`toggleOccupationInterest`, `aria-pressed`, «Guardar en favoritos» / «Quitar de favoritos»);
  - `titulo`;
  - la descripción corta del catálogo del front (`occupationDetails`), solo si la ocupación existe en él;
  - las letras RIASEC de la ocupación con «Comparte tus tres intereses» o «Comparte {n} de tus intereses», solo si el catálogo del front tiene su código;
  - el botón «Ver sus carreras» / «Mostrando sus carreras» (`aria-pressed`), que filtra la sección 6;
  - un enlace con chevron al detalle (`discoveryPaths.occupation`), solo si existe en el catálogo.
- Nota final: «Se muestran hasta 10 ocupaciones, de las que más se parecen a tu perfil a las que menos. Fuente: O*NET Interest Profiler.»
- No se muestra «Ícono obtenido en la Central de Casos» ni ningún dato que el servidor o el catálogo no tengan. Si se quiere mostrar, se anota en pendientes.

**6. Carreras que conducen (COINCIDENCIAS, sin perfil plano).**
- Antetítulo «Paso 2 · Carreras que conducen a ellas».
- Título «Carreras que conducen a tus ocupaciones afines», o «Carreras para ser {ocupación en minúscula}» si hay una ocupación elegida, con su botón «Ver todas las carreras».
- Bajada: «Ordenadas por cuántas de tus ocupaciones afines alcanzan. Guarda las que te interesen o conviértelas en un plan.», o con una ocupación elegida: «Estas carreras forman para la ocupación que elegiste arriba.»
- Datos: `carreras_recomendadas`, ordenadas por cantidad de `via` (de mayor a menor) y luego por el orden del servidor.
- Cada carrera muestra:
  - `nombre`;
  - la insignia «Ya es tu plan {A|B|C}» si existe un plan para ella;
  - `familia`;
  - «Conduce a {n} de tus ocupaciones afines:» o «Conduce a:», con un chip por cada `via` (su `titulo`).
- Acciones de cada carrera:
  - «Guardar» / «Favorita», con `toggleCareerInterest`;
  - «Hacer mi plan {siguiente letra}», con `createPlanFromCareer`, solo si no es plan y hay menos de 3 planes;
  - «Ver carrera», que lleva a `discoveryPaths.career(codigo)`.
- No se muestra la duración en años: el servidor no la entrega. Anótalo en pendientes.
- Nota final: «Carreras del Perú que forman para tus ocupaciones afines. Puedes tener hasta 3 planes: A, B y C.»

**7. Qué hacer con esto (DESTACADAS).**
- Antetítulo «Siguiente paso», título «Qué hacer con lo que descubriste» y bajada «Este resultado no recomienda carreras: te ayuda a conocer cómo aprendes y en qué contextos te desenvuelves mejor.»
- Tres tarjetas enlace:
  - «Conversa con tu familia»: «Compara lo que dice el cuestionario con lo que ellos ven de ti. Luego cuéntanos qué aprendiste.», con el enlace «Abrir guía de conversación», que lleva a `appPaths.student.conversations`.
  - «Escríbelo en tu diario»: «¿En qué momento reciente usaste tu inteligencia más fuerte sin darte cuenta?», con el enlace «Escribir en mi diario», que lleva al diario con esa pregunta como `prompt`, igual que la tarjeta de cierre.
  - «Míralo junto a tus intereses»: «Lo que te atrae hacer y la forma en que aprendes se complementan. La página I tiene ocupaciones y carreras.», con el enlace «Ir a la página I», que lleva a `discoveryPaths.helenaPage('intereses')`.

**8. Perfil plano (COINCIDENCIAS).**
- Con `perfil_plano`:
  - En lugar del código, en la sección 2 va un recuadro punteado con el título «Tus respuestas no marcaron un interés por encima de otro», el texto «Respondiste de forma muy parecida a todos los tipos de actividad, así que Helena no puede formar tu código de interés ni buscar ocupaciones afines. Puedes revisar tus encuentros con Mara y responder pensando en lo que de verdad disfrutas.» y el botón «Revisar mis encuentros con Mara» (`/student/exploration?punto=mara-test`, como hoy).
  - Se ocultan las secciones 5 y 6.

**9. Avisos de cierre.**
- Común: «Estas sugerencias exploran, no deciden. Pueden confirmar opciones que ya tenías o abrir otras que no habías considerado.»
- Solo intereses, además: «Tus intereses son una parte de ti. Contrástalos con tus otras páginas, con lo que investigas y con quienes te conocen.»
- En inteligencias, en lugar del común va: «Este perfil muestra cómo te ves hoy. Puede cambiar a medida que pruebas actividades nuevas.»

### Datos de la página de inteligencias en esta iteración

`TEST-INT` no está en la semilla `plataforma` y `spec-iteracion-1.md` lo deja como «Disponible en una próxima iteración». Por eso, en esta iteración la vista de inteligencias usa la demostración en ambos modos, con su aviso de demo:

- En `src/features/discovery/lib/helenaPages.ts`, `demoIntelligences` agrega `dimensiones`, todas marcadas `DATO DE PRUEBA`, con los códigos del backend:
  - INT-LIN Lingüística 75;
  - INT-INTER Interpersonal 75;
  - INT-INTRA Intrapersonal 63;
  - INT-MUS Musical 50;
  - INT-ESP Espacial 50;
  - INT-LOG Lógico-matemática 43;
  - INT-CIN Cinestésico-corporal 40.
- Las descripciones de la demostración son las de la tabla de F2.
- Las destacadas se calculan como las de mayor porcentaje, con empates: aquí, Lingüística e Interpersonal.
- `useResultPage` debe aceptar un `ResultadoPublico` real de tipo DESTACADAS (`dimensiones` + `dimensiones_destacadas`) sin cambios, para que la próxima iteración solo cambie el hook. Agrega una prueba con un `ResultadoPublico` de `TEST-INT` armado a mano (`DATO DE PRUEBA`).

### Archivos sugeridos

- Componentes en `src/features/discovery/components/`: `ResultHeader.tsx`, `InterestCode.tsx`, `HighlightedDimensions.tsx`, `DimensionProfile.tsx`, `DimensionGuide.tsx`, `AffineOccupations.tsx`, `RecommendedCareers.tsx`, `ResultNextSteps.tsx`, `FlatProfileNotice.tsx` y `ResultNotes.tsx`.
- Lógica pura en `src/features/discovery/lib/resultPage.ts`: ordenar dimensiones, calcular destacadas con empates, ordenar carreras por `via` y filtrar por ajuste.
- La vista de ruta (`HelenaResultView.tsx`) solo lee `:pagina`, llama a `useResultPage` y compone. Idealmente, 150 líneas o menos.
- Mantén `sx-d-*` y agrega los estilos nuevos en `src/features/discovery/styles/`.
- Debe funcionar en anchos de teléfono: secciones apiladas y grillas de una columna.

### Pruebas

`tests/servidor-resultado.test.mjs`, sobre `resultPage.ts` y los adaptadores:

- La plantilla elige secciones por `tipoResultado`.
- Destacadas con una y con dos dimensiones.
- Con perfil plano no hay ocupaciones ni carreras.
- La `descripcion` llega desde el resultado del servidor.
- Las carreras se ordenan por cantidad de `via`.
- El filtro por ajuste.

Usa el fixture de resultado RIASEC del servidor.

---

## F5 · Verificación y documentos

1. Corre todas las verificaciones de ambos repos y reporta el número de pruebas que pasan y fallan, comparado con la línea base.
2. Actualiza `docs/refactor/origen-de-datos.md` (F2, F4) y `docs/student-experience/plan.md` con una entrada por fase que cite este anexo.
3. En `docs/pendientes-interfaz.md` quedan, como mínimo:
   - la duración de las carreras;
   - la cita o persona de un testimonio sin contenido en el front;
   - que la tarjeta de cierre se conserve al volver desde una ficha;
   - cualquier dato que hayas necesitado y no exista.
4. Prueba manual contra la BD (`VITE_DATOS=api`):
   - completar una actividad con desbloqueos y repetirla;
   - abrir una ficha desde la tarjeta;
   - ver el perfil completo;
   - abrir el resultado completo de intereses y el de inteligencias (demo);
   - la guía;
   - el filtro de ajuste;
   - favorito y plan.

   Repite lo mismo en modo local.
5. Resume por fase qué se hizo, en qué archivos y qué queda pendiente.
