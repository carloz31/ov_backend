# Decisiones de la iteración 1

Registro de decisiones que afectan a ambos repos. Las internas de cada repo van en `ov_backend/docs/decisiones.md` y `ov_frontend/docs/student-experience/plan.md`.

Formato de cada entrada: fecha, fase, decisión, motivo y archivos afectados.

## Decisiones tomadas antes de implementar

Ver la sección 8 de `spec-iteracion-1.md`.

## F0. Línea base

### 2026-10-07 · Verificación inicial, sin cambios de código

**Decisión y motivo.** Ejecutar únicamente F0 y registrar las fallas previas, sin
corregir la implementación ni adaptar pruebas. La sección 9 de la especificación
permite cerrar esta fase con fallas previas documentadas. Se leyeron completos,
en este orden, los `AGENTS.md` de ambos repos, el plan de iteraciones y la
especificación de la iteración 1.

**Archivos afectados.** Solo este documento. Se conservan los cambios previos en
los dos `AGENTS.md` y los demás documentos de iteraciones que ya estaban sin
versionar. No se modifican código, pruebas, manifiestos ni archivos de bloqueo.
No se agregan dependencias, no se ejecuta Gemini y no se hace push.

**Preparación.** `uv sync` terminó correctamente: 43 paquetes resueltos y 42
verificados. `npm install` terminó correctamente, con las dependencias al día.
Herramientas: Python 3.14.7, uv 0.11.16, Node.js 24.19.0 y npm 12.0.2.

**Reglas compartidas.** Las secciones que comienzan con
`## Reglas compartidas entre ov_backend y ov_frontend` son idénticas mediante
comparación exacta, incluidos espacios y saltos de línea: 3191 caracteres cada
una. No fue necesario editarlas.

**Ramas y commits.** El backend ya estaba en `iteracion-1`. En el frontend se
creó `iteracion-1` desde la rama existente `iteration-1`, conservando el estado
de trabajo. El commit del backend incluye únicamente este registro; el del
frontend es vacío para dejar constancia de F0 sin agregar archivos ni incluir
los cambios previos del usuario.

| Repo | Comando | Resultado |
|---|---|---|
| Backend | `uv run pytest -q`, con `EVALUADOR=falso` y `SEMILLA=demo` | 947 pruebas pasan, 0 fallas, 2 advertencias; 889,05 segundos (14 min 49 s), con temporales propios. |
| Frontend | `npm run build` | Correcto; 2820 módulos transformados. |
| Frontend | `npm run lint` | Correcto, salida 0; sin diagnósticos emitidos. |
| Frontend | `npm test` | 292 pruebas: 276 pasan, 16 fallan; 0 canceladas, omitidas o pendientes. 12 archivos de pruebas; 0 suites declaradas. |

**Incidencias del entorno del backend.** El primer intento dentro del sandbox
falló antes de ejecutar pytest con `uv trampoline failed to canonicalize script
path`. Fuera del sandbox, pytest encontró `PermissionError: [WinError 5]` al
acceder a `C:\Users\mauri\AppData\Local\Temp\pytest-of-mauri`, además de avisos
de permisos de la caché existente. Se diagnosticó el primer error con
`uv run pytest -q -x --tb=short` y se interrumpió la ejecución completa afectada.
La repetición usa un directorio temporal propio y otra caché, solo mediante
variables de entorno del proceso; no cambia la configuración del proyecto:

```powershell
$env:EVALUADOR = 'falso'
$env:SEMILLA = 'demo'
$env:TEMP = Join-Path $env:LOCALAPPDATA 'Temp\ov-f0-20261007'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$env:PYTEST_ADDOPTS = '-o cache_dir=' + ($env:TEMP -replace '\\','/') + '/cache'
uv run pytest -q
```

La suite completa terminó con salida 0. Sus dos advertencias son de
deprecación: `httpx` en `starlette.testclient` y `_UnionGenericAlias` en
`google.genai.types`. No se cambian dependencias para resolverlas en F0.

**Advertencia previa del build.** Vite avisa que el JavaScript principal supera
500 kB: 1628,19 kB, o 477,00 kB con gzip. El aviso no impide compilar y no se
aplican cambios para resolverlo en F0.

**Fallas previas del frontend.** Dos ejecuciones de `npm test` terminaron con
las mismas 16 fallas. Todas pertenecen a `tests/adventure-rendering.test.mjs`:

| Línea del test | Nombre reportado |
|---|---|
| 731 | real access conditions lock successive missions and expose the city gate without changing review mode |
| 1504 | immersive submission preserves validation, drafts, versions and the keep action |
| 1571 | immersive questions preserve attempts, hints, revelation, retry and fresh revision behavior |
| 1699 | immersive finish shows saved sheets, narrative rewards and the prompted journal action |
| 1776 | follow-up service waits 700ms, respects both text thresholds and never asks a third turn |
| 1855 | first text submission saves version one before follow-up; edits and matrices use the normal form |
| 1881 | follow-up accepts two replies, caps the field at available space and saves one condensed version |
| 1915 | omitting all turns preserves version one, while a long reply ends follow-up after one turn |
| 1932 | no question, failure, timeout or fewer than 40 free characters advances silently with the original |
| 1951 | interrupted follow-up recovers only answered turns and loads the condensed form without duplicate versions |
| 2000 | follow-up requires 40 free characters and stops before a second question that cannot fit |
| 2033 | leaving during evaluation never stores a late question and recovery preserves the replied turn |
| 2326 | every supplied mission node renders, including matrices, slides, questions and instrument items |
| 2621 | phase 8 path sequence respects both completion records without changing catalog or real thresholds |
| 2658 | phase 8 direct links open blocked details instead of starting unavailable players |
| 3229 | discovery atlas covers existing IDs, symmetric relations and gated affinity |

Entre los diagnósticos observados están diferencias entre `locked` y
`completed`, el texto esperado «Salir de la actividad» frente a «Salir de la
misión», expectativas de preguntas de seguimiento y la relación
`psychology:psychologist`. Son síntomas reportados por las pruebas, no un
diagnóstico de causa raíz. No se abrieron ni modificaron las carpetas de los
portales ni `tests/counselor-portal.test.mjs`; sus suites se ejecutaron como
permite el `AGENTS.md` del frontend.

**Cierre y pendientes.** F0 completa, con las fallas previas documentadas según
el criterio de la especificación. F1–F7 quedan sin ejecutar. Las 16 fallas
previas del frontend requieren una tarea posterior de diagnóstico; no se
corrigen ni se cambian sus resultados esperados en F0.
