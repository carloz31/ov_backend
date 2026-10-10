# Plan de iteraciones de la plataforma de orientación vocacional

Contexto para cualquier agente que trabaje en `ov_backend` u `ov_frontend`. Vive en `ov_backend/docs/iteraciones/`. **Solo se implementa la iteración vigente**, que tiene su propia especificación (`spec-iteracion-N.md`). Las demás filas sirven para no cerrar caminos que vendrán después, no para adelantarlas.

Catálogo de referencia: catálogo de requisitos vigente, 93 HUs.

## Las cinco iteraciones

| It. | Tema | HUs | N.º | Estado del backend al empezar |
|---|---|---|---|---|
| **1** (vigente) | Integración base: desbloqueos, informativas, test de intereses y recomendaciones | 002, 004, 011, 013, 014, 015, 021, 022, 025, 026 (sin favoritos), 027, 073, 074, 075 (solo nivel) | 14 | Motor, instrumentos y recomendación existen; falta la semilla alineada al front. |
| 2 | Registro con LLM, comprobaciones, acceso y ayuda | 001, 005, 006, 007, 008, 009, 010, 012, 016, 017, 018, 019, 020 | 13 | El registro con Gemini existe. Faltan login, retoma de ítems de otras actividades (009), misiones adicionales y batalla. |
| 3 | Autoconocimiento y exploración: diario, check-in, perfil, catálogos y planes | 023, 024, 028–036, 037–042, 043–050 | 25 | Diario y check-in existen. Catálogos, favoritos y planes son nuevos. |
| 4 | Ciudad y comunidad: casos, entrevistas y familia | 003, 051–056, 057–065, 066–072 | 23 | Casos, entrevistas, coautoría, cartas y conversaciones existen. Reacciones y Leyendas son nuevas. |
| 5 | Apoderado, orientadora y perfil social, con holgura para el material | 076–080, 081–093 | 18 | Casi todo es consulta de datos que ya existen. |

## Holgura para cargar el material

- Cada iteración carga el material de sus propias actividades. El contenido narrativo vive en los JSON del front, así que cargar material no requiere tocar el backend salvo para agregar actividades, ítems o reglas.
- Los datos de prueba se marcan como `DATO DE PRUEBA` para encontrarlos y reemplazarlos al cargar el material definitivo.
- El último 15–20 % del calendario se reserva para revisar y completar el material, no para producirlo desde cero.

## Cómo arrancar la iteración 1 en Codex

Agrega las dos carpetas, `ov_backend` y `ov_frontend`, al proyecto de Codex. Un prompt por fase; espera el resumen de cada fase antes de pasar a la siguiente.

1. «Lee los `AGENTS.md` de `ov_backend` y `ov_frontend`, y `ov_backend/docs/iteraciones/plan-iteraciones.md` y `ov_backend/docs/iteraciones/spec-iteracion-1.md` completos. Ejecuta la fase F0 y detente.»
2. «Ejecuta la fase F1 de la spec de la iteración 1.»
3. «Ejecuta la fase F2.»
4. «Ejecuta la fase F3.»
5. «Ejecuta la fase F4.» Con esto ya se puede probar el camino completo contra la BD.
6. «Ejecuta la fase F5.»
7. «Ejecuta la fase F6.»
8. «Ejecuta la fase F7 y entrégame el informe por HU.»

Si Codex se detiene por una contradicción entre documentos, resuélvela en la spec de la iteración (no en el código) y pídele que continúe.

## Levantar ambos proyectos para probar

Backend (PowerShell, desde la carpeta `ov_backend`):

```powershell
uv sync
$env:EVALUADOR = "falso"
uv run alembic upgrade head
uv run python -m datos.cargar plataforma
uv run uvicorn app.main:app --reload
```

Frontend (otra terminal, desde la carpeta `ov_frontend`), con un `.env.local` que contenga `VITE_DATOS=api`:

```powershell
npm run dev
```

En bash se usan los mismos comandos, con `export EVALUADOR=falso` en lugar
de la asignación PowerShell. La preparación se ejecuta una vez; después basta
con arrancar Uvicorn. Para otra base, definir `DATABASE_URL` antes de migrar,
cargar y arrancar. La configuración está en el README de `ov_backend`.
