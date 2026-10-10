# Spec: compactación de la documentación

Afecta a `ov_backend` y `ov_frontend` (rama `iteracion-1`). Solo cambia documentación y dos pruebas que leían specs como fuente de datos. No cambia código de `app/` ni de `src/`, contratos, datos ni dependencias.

## 1. Objetivo

Que un agente lea poco y lea lo vigente. Hoy los `AGENTS.md` remiten a unas 200.000 palabras de specs encadenadas, bitácoras de decisiones e informes. Después del cambio quedan unas 14.000 palabras vigentes:

| Repo | Vigente | Pasa a `docs/historico/` |
|---|---|---|
| back | `AGENTS.md`, `README.md`, `docs/sistema/{motor,instrumentos,registro,integracion}.md`, `docs/plan-iteraciones.md`, `docs/decisiones.md` (vacío), `docs/specs/` | specs de demo, refactor, iteración 1 y pruebas; `decisiones.md` anterior; `validacion.md`; evaluación de Gemini; inventario del retiro |
| front | `AGENTS.md`, `README.md`, `docs/origen-de-datos.md`, `docs/contenidos-actividades.md`, `docs/pendientes-interfaz.md`, `docs/evidencias/` | `student-experience/`, `staff-experience/`, `parent-experience/`, `occupation-exploration/`, `refactor/` y los documentos sueltos de actividades |

Los documentos vigentes ya están redactados y verificados contra el código. Vienen en dos parches, uno por repo, que hacen todo el cambio: movimientos con `git mv` (historial conservado), archivos nuevos, `AGENTS.md` y `README.md` reescritos, el comentario de cabecera de `scripts/verificar-estructura.mjs` y las dos pruebas.

**Pruebas adaptadas con autorización de esta spec:**

- `tests/integration/datos/test_semilla_plataforma.py` leía las tablas de ocupaciones y enunciados RIASEC de `spec-iteracion-1.md`. Ahora las lee de `tests/soporte/soporte_datos_aprobados.py`, que contiene esos mismos valores copiados literalmente. Las aserciones contra la base no cambian.
- `tests/integration/instrumentos/test_descripciones_resultados.py` comprobaba que la spec del anexo contuviera las descripciones de inteligencias. Se quita solo esa comprobación sobre el documento; las que verifican la API no cambian.

## 2. Archivos de entrada

El usuario deja en `ov_backend/docs/specs/compactacion-docs/`:

- `spec-compactacion-docs.md` (este documento)
- `docs-backend.patch`
- `docs-frontend.patch`

Los parches se generaron sobre `ov_backend@70bcffa` y `ov_frontend@10cb654`.

## 3. Fases

### D0 · Comprobación (los dos repos)

1. Lee este documento completo. No leas los documentos que se van a archivar.
2. En cada repo: rama `iteracion-1`, árbol limpio (salvo la carpeta de entrada) y `git log -1` en el commit indicado. Si el commit no coincide, ejecuta igual `git apply --check` en D1 y D2; si falla, detente y avisa.
3. Detente y resume.

### D1 · Backend

1. `git apply --check docs/specs/compactacion-docs/docs-backend.patch`; luego `git apply` con el mismo archivo. Si `--check` falla, prueba con `--ignore-whitespace` (finales de línea en Windows). Si sigue fallando, detente y muestra el error. **No edites los archivos a mano para que el parche entre.**
2. Comprueba:
   - `docs/` contiene solo `decisiones.md`, `plan-iteraciones.md`, `sistema/`, `specs/` e `historico/`.
   - Ninguna referencia a documentos movidos fuera de `docs/historico/`: `git grep -nE "spec-demo|spec-refactor|spec-iteracion|decisiones-iteracion|validacion\.md|evaluacion_gemini|inventario-retiro|spec-pruebas|docs/iteraciones" -- . ':!docs/historico' ':!docs/specs'` vacío.
   - `uv run pytest tests/integration/datos tests/integration/instrumentos -q` en verde.
3. Commit: `Documentación · D1: compactar documentación del backend`.
4. Detente y resume.

### D2 · Frontend

1. Desde `ov_frontend`: `git apply --check` y `git apply` con la ruta del parche `docs-frontend.patch` (está en la carpeta de entrada de `ov_backend`), con el mismo criterio que en D1.
2. Comprueba:
   - `docs/` contiene solo `contenidos-actividades.md`, `origen-de-datos.md`, `pendientes-interfaz.md`, `evidencias/` e `historico/`.
   - `git grep -nE "docs/(student-experience|staff-experience|parent-experience|occupation-exploration|refactor)|mission-spec|actividades-comunes|spec-refactor" -- . ':!docs/historico'` vacío.
   - `npm run check:estructura` en verde.
3. Commit: `Documentación · D2: compactar documentación del frontend`.
4. Detente y resume.

### D3 · Verificación y cierre (los dos repos)

1. Suite completa: `uv run pytest -n auto -q` en el back; `npm test`, `npm run build`, `npm run lint` y `npm run check:estructura` en el front. Resultado esperado, igual que antes del cambio: back 526 aprobadas y 4 omitidas; front 463 pruebas con las 14 fallas previas de `tests/local/aventura/adventure-rendering.test.mjs`.
2. Lee los `AGENTS.md` nuevos y comprueba que la sección «Reglas compartidas» es idéntica en los dos (`diff` de esa sección).
3. Cierre de esta spec, según la regla nueva: mueve `docs/specs/compactacion-docs/spec-compactacion-docs.md` a `docs/historico/compactacion-docs/` y borra los dos `.patch`. `docs/specs/` queda solo con `.gitkeep`.
4. Commit en el back: `Documentación · D3: cerrar compactación`. Sin push.
5. Resumen final: resultado de las suites, archivos movidos por repo y cualquier diferencia que hayas notado entre un documento vigente y el código (anótala; no la corrijas).

## 4. Fuera de alcance

- No se corrigen enlaces internos de los documentos históricos.
- No se modifica ningún documento vigente fuera de lo que traen los parches. Si al leerlos encuentras una contradicción con el código, anótala en el resumen.
- `docs/pendientes-interfaz.md` no cambia.
