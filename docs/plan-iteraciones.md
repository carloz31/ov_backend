# Plan de iteraciones

Sirve para no cerrar caminos a lo que viene, no para adelantarlo: solo se implementa lo que pide la spec en curso (`docs/specs/`). Catálogo de referencia: catálogo de requisitos vigente, 93 HU.

| It. | Tema | HU | Estado |
|---|---|---|---|
| 1 | Integración base: desbloqueos, informativas, test de intereses y recomendaciones | 002, 004, 011, 013, 014, 015, 021, 022, 025, 026 (sin favoritos), 027, 073, 074, 075 (solo nivel) | Implementada; pendiente de aprobación del usuario. |
| 2 | Registro con LLM, comprobaciones, acceso y ayuda | 001, 005, 006, 007, 008, 009, 010, 012, 016, 017, 018, 019, 020 | El registro con evaluador existe en el backend (`docs/sistema/registro.md`), sin datos en `plataforma`. Faltan login, retoma de ítems de otras actividades (009), misiones adicionales y batalla. |
| 3 | Autoconocimiento y exploración: diario, check-in, perfil, catálogos y planes | 023, 024, 028–036, 037–042, 043–050 | Diario y check-in existen en el backend sin vista conectada. Catálogos, favoritos y planes son nuevos. |
| 4 | Ciudad y comunidad: casos, entrevistas y familia | 003, 051–056, 057–065, 066–072 | Casos, entrevistas, coautoría, cartas y conversaciones existen en el backend. Reacciones y Leyendas son nuevas. |
| 5 | Apoderado, orientadora y perfil social | 076–080, 081–093 | Casi todo es consulta de datos que ya existen. |

## Material

- Cada iteración carga el material de sus actividades. El contenido narrativo vive en los JSON del front (`ov_frontend/docs/contenidos-actividades.md`), así que cargar material solo toca el backend para agregar actividades, ítems o reglas.
- Los datos de prueba se marcan `DATO DE PRUEBA` para encontrarlos y reemplazarlos al cargar el material definitivo.
- El último 15–20 % del calendario se reserva para revisar y completar el material.
