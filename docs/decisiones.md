# Decisiones de la spec en curso

Una viñeta por decisión: qué se decidió y por qué, en una o dos líneas, con el repo afectado si no es obvio. Incluye las pruebas adaptadas con autorización de la spec. No incluye conteos de pruebas, tiempos, líneas base ni el relato de las fases.

Al cerrar la spec, lo que siga vigente pasa al `AGENTS.md` o a `docs/sistema/` (o a `ov_frontend/docs/`), y este archivo se mueve junto con la spec a `docs/historico/<nombre-de-la-spec>/`, dejando aquí solo este encabezado.

<!-- Spec en curso: spec-actividades-apoderado. -->

- Alembic generó `0003` sin operaciones porque no detecta el cambio del `CHECK` no nativo; se reemplaza a mano con `batch_alter_table`. El downgrade comprueba antes si existen bloques `PORTAL_FAMILIA` y falla sin modificar la base, evitando dejar una tabla temporal en SQLite (§4.1).
- Se adaptan según §4.4 `test_catalogo_estructura_y_estado_vacio`, `test_cargador_cli_admite_piloto_y_vaciado`, `test_claves_y_visibilidad_de_los_conjuntos`, `test_apoderado_sin_listas_estudiantiles`, `test_invariantes_desbloqueos_nivel_audiencia_y_eventos`, `test_p14_audiencia` y `test_migracion_0002_conserva_filas_y_referencias_de_0001`: solo se incorpora el catálogo familiar y se actualiza la cabeza de Alembic; se mantienen las expectativas del estudiante.
