# Decisiones de la spec en curso

Una viñeta por decisión: qué se decidió y por qué, en una o dos líneas, con el repo afectado si no es obvio. Incluye las pruebas adaptadas con autorización de la spec. No incluye conteos de pruebas, tiempos, líneas base ni el relato de las fases.

Al cerrar la spec, lo que siga vigente pasa al `AGENTS.md` o a `docs/sistema/` (o a `ov_frontend/docs/`), y este archivo se mueve junto con la spec a `docs/historico/<nombre-de-la-spec>/`, dejando aquí solo este encabezado.

<!-- Spec en curso: spec-actividades-apoderado. -->

- Alembic generó `0003` sin operaciones porque no detecta el cambio del `CHECK` no nativo; se reemplaza a mano con `batch_alter_table`. El downgrade comprueba antes si existen bloques `PORTAL_FAMILIA` y falla sin modificar la base, evitando dejar una tabla temporal en SQLite (§4.1).
- Se adaptan según §4.4 `test_catalogo_estructura_y_estado_vacio`, `test_cargador_cli_admite_piloto_y_vaciado`, `test_claves_y_visibilidad_de_los_conjuntos`, `test_apoderado_sin_listas_estudiantiles`, `test_invariantes_desbloqueos_nivel_audiencia_y_eventos`, `test_p14_audiencia` y `test_migracion_0002_conserva_filas_y_referencias_de_0001`: solo se incorpora el catálogo familiar y se actualiza la cabeza de Alembic; se mantienen las expectativas del estudiante.
- Los fixtures del apoderado se exportan desde la misma base temporal de `plataforma`, tras el recorrido del estudiante; `cuentas.json` se consulta al inicio. Se conserva así el recorrido y las respuestas existentes (§4.5).
- Se amplían `test_fixtures_reproducen_el_contrato_y_se_regeneran_identicos`, `test_exportacion_completa_reproducible_y_compatible` y la prueba CLI (renombrada `test_cli_exporta_los_veintidos_fixtures`) para incluir los archivos del apoderado; ninguna expectativa del estudiante cambia (§4.5).
- En el front se actualizan solo las rutas de `parentJourneyStore` en `parent-missions.test.mjs` y `adventure-rendering.test.mjs`, según §8.2; sus aserciones permanecen idénticas.
- Los selectores de disponibilidad y completitud del apoderado excluyen actividades invisibles o sin contenido, igual que su lista, para que no cuenten en el progreso (DA12).
- El almacén del apoderado permite un envío a la vez: reutiliza la promesa del mismo código y devuelve 409 para otro código mientras está pendiente, conservando un único `enviando` (§5.2).
