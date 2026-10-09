# Inventario para el retiro de la demo · P1

Estado: **propuesta pendiente de aprobación**. Fecha: 9 de octubre de 2026.
Fuente: `docs/spec-pruebas-y-retiro-demo.md`, especialmente §§4, 5, 10 y 11.
Base revisada: `iteracion-1`, backend `5beec8c` (P0), frontend `7df1b17`.
P1 no cambia aplicación, datos, pruebas, configuración ni contrato.

## Criterio y unidad de conteo

Se cuentan **casos recolectados por pytest**, incluidos todos los parámetros,
no solamente funciones Python. La recolección actual da **1099**, igual que P0.
La revisión combina cuerpos, decoradores, ayudantes, fixtures locales y autouse,
importaciones y llamadas directas a `preparar_base`. No se infiere la categoría
por el nombre del archivo: `test_evaluador_gemini.py`, `test_semilla_plataforma.py`
y `test_piloto.py` contienen dependencias que una clasificación por fixture omitiría.

- **A:** independiente de los datos de demo; conservar aserciones. En los tres
  archivos con parametrización por conjunto se retira únicamente el parámetro
  `demo`, como autoriza §5. Los cambios mecánicos de importación o reinicio
  siguen §11 y se detallan más abajo.
- **B:** la demo proporciona la base, pero sus aserciones sobreviven al cambio
  a plataforma. Conservar aserciones y parámetros. Las cuentas `est-ana`,
  `est-luis`, `apo-rosa` y el vínculo `VIN-ANA` también existen en plataforma;
  usarlos como entrada no convierte por sí solo una prueba en C. Si el cuerpo
  necesita una actividad o un catálogo exclusivos de demo, se clasifica C.
- **C:** depende de catálogo, reglas, cuentas/conteos específicos, ayudantes o
  comportamiento que se retira expresamente (§4). Incluye pruebas sobre
  `posiciones_registro`, aunque preparen plataforma o una base vacía. Por ello
  C no significa siempre «usa el fixture global demo».

Una prueba cuyo único objetivo es un elemento eliminado por §4 se retira sin
port: no se conserva una aserción sobre ese elemento solo porque no use base.
Los 163 + 28 + 11 casos de `test_registro*.py` y los 2 de `test_demo_registro.py`
son C completos, sin port, por instrucción expresa de §5.

En B, los nombres antiguos que solo son entradas inválidas pueden permanecer:
por ejemplo, un cuerpo rechazado por Pydantic no consulta `LAB-RIA1`. No se
pretende convertir una referencia inexistente en una prueba de disponibilidad.
Cuando el resultado dependía de esa disponibilidad, se ha clasificado C.
En B también se cambian llamadas directas a preparar_base/CONJUNTOS o al CLI
que usaban demo como base genérica: cli_sin_esquema_y_carga_tras_migracion
conserva todas sus aserciones y carga plataforma también en el --vaciar final.

## Conteo por archivo

Todos los nombres de esta tabla son relativos a `tests/`.

| Archivo | A | B | C | Total |
|---|---:|---:|---:|---:|
| `test_acciones.py` | 0 | 25 | 13 | 38 |
| `test_calculo_instrumentos.py` | 69 | 0 | 0 | 69 |
| `test_carga_datos.py` | 5 | 4 | 5 | 14 |
| `test_configuracion.py` | 15 | 0 | 2 | 17 |
| `test_configuracion_base.py` | 0 | 0 | 3 | 3 |
| `test_configuracion_metodos.py` | 0 | 0 | 8 | 8 |
| `test_consultas.py` | 3 | 4 | 151 | 158 |
| `test_consultas_dominio.py` | 42 | 0 | 0 | 42 |
| `test_contenido_actividades.py` | 2 | 0 | 6 | 8 |
| `test_demo.py` | 0 | 0 | 2 | 2 |
| `test_demo_registro.py` | 0 | 0 | 2 | 2 |
| `test_descripciones_dimensiones.py` | 1 | 0 | 3 | 4 |
| `test_escenarios.py` | 0 | 0 | 17 | 17 |
| `test_evaluador_gemini.py` | 56 | 0 | 23 | 79 |
| `test_evaluador_respuestas.py` | 142 | 0 | 0 | 142 |
| `test_exportar_fixtures_front.py` | 3 | 0 | 0 | 3 |
| `test_fase1.py` | 0 | 11 | 12 | 23 |
| `test_fixtures_dominio.py` | 3 | 0 | 0 | 3 |
| `test_instrumentos.py` | 0 | 6 | 75 | 81 |
| `test_invariantes.py` | 0 | 1 | 10 | 11 |
| `test_migraciones.py` | 24 | 0 | 0 | 24 |
| `test_motor.py` | 0 | 14 | 47 | 61 |
| `test_piloto.py` | 8 | 1 | 0 | 9 |
| `test_plataforma.py` | 15 | 0 | 0 | 15 |
| `test_postgres.py` | 4 | 0 | 0 | 4 |
| `test_registro.py` | 0 | 0 | 163 | 163 |
| `test_registro_finalizacion_v2.py` | 0 | 0 | 11 | 11 |
| `test_registro_v2.py` | 0 | 0 | 28 | 28 |
| `test_semilla_instrumentos.py` | 10 | 8 | 25 | 43 |
| `test_semilla_plataforma.py` | 16 | 0 | 1 | 17 |
| **Total** | **418** | **74** | **607** | **1099** |

## Propuesta de ports de C

Se proponen **40 casos recolectados** en total. Cada identificador R01–R40
corresponde a un caso, no a una función con una parametrización oculta. Cuando
se indican variantes relacionadas, el caso recorre esas variantes con estado
aislado. Si P2 necesita más casos, se actualiza el inventario antes de ampliar
el alcance aprobado.

Las pruebas actuales de plataforma/piloto se usan como evidencia de cobertura,
no se modifican para hacer sitio a los ports. Los orígenes de cada fila son
pruebas C; las A/B del mismo comportamiento se conservan por separado. Un port
puede agrupar varios orígenes y un origen amplio puede aportar a varias filas.

Los destinos de la tabla son los **destinos finales de P3**. En P2 las pruebas
nuevas quedan directamente en `tests/`, con el mismo nombre de archivo y nombres
de función únicos; P3 las mueve sin cambiar aserciones.

Para comportamientos que plataforma todavía no define (casos, conversaciones,
DESTACADAS, COMPARACION), preparar **solo en la base temporal de la prueba** las
filas mínimas necesarias, marcadas `DATO DE PRUEBA`, mediante ayudas de
`tests/soporte/`. No modificar `datos/plataforma.py`, importar `datos/demo/`,
recrear su catálogo ni implementar HUs futuras. Esto conserva pruebas de lógica
que ya existe. El plan de iteraciones solo justifica su vigencia.

En los presupuestos SQL, la preparación y la reconstrucción de caché quedan
fuera del contador; se cuenta la petición completa, incluidas escrituras en
lote. Conservar los límites existentes aplicables (lecturas 10; progreso 8;
completar 15; responder 10; calcular 20; historial 10; entrevista 10; marcar
vistos 2; reiniciar instrumento 12), sin incrementarlos para aprobar el port.

| ID | Comportamiento agrupado y orígenes C | Por qué cumple §5 / qué falta en plataforma y piloto | Destino final |
|---|---|---|---|
| R01 | Conteos EVENTOS, REFERENCIAS_DISTINTAS y DIAS_DISTINTOS con filtro, repetición, cuentas y fechas; `test_motor.test_conteos_filtran_cuenta_tipo_y_referencia` (6 casos), E6. | Núcleo vigente y diario/check-in de it. 3. El evaluador de camino y los invariantes actuales no contrastan los tres conteos generales. | `integration/motor/test_conteos_motor.py` |
| R02 | AND, umbral y progreso sin tope, evaluador especial, aislamiento y evaluación una vez por lote; `test_motor.test_regla_compuesta_exige_todas_las_condiciones`, `test_eventos_de_otras_cuentas_no_completan_regla_compuesta`, `test_progreso_umbral_y_avance_sin_limitar`, `test_regla_relacionada_con_dos_eventos_se_evaluan_una_sola_vez`; E8. | P6 tiene varios desbloqueos; no verifica una regla sintética con dos condiciones, su progreso ni la deduplicación de evaluación por lote. | `integration/motor/test_reglas_motor.py` |
| R03 | Despacho por tipos relacionados, lista vacía y rollback por evaluador desconocido; `test_motor.test_solo_se_evaluan_tipos_relacionados_y_lista_vacia_no_hace_nada`, `test_evaluador_desconocido_revierte_lote_completo`. | Motor vigente; los rechazos por disponibilidad de P3 no fuerzan un fallo de configuración durante la evaluación. La regla sin condiciones ya queda en B. | `integration/motor/test_reglas_motor.py` |
| R04 | Condición cumplida sin desbloqueo persistido y regla cumplida antes de abrir el bloque; `test_motor.test_condiciones_cumplidas_sin_desbloqueo_no_dan_disponibilidad`, `test_regla_de_actividad_puede_cumplirse_antes_que_bloque_contenedor`, `test_consultas.test_progreso_regla_cumplida_con_bloque_contenedor_pendiente`, `test_gets_no_generan_eventos_ni_desbloqueos`. | El bloqueo sobre progreso en consultas_dominio no distingue condición cumplida, concesión persistida y bloqueo del contenedor. | `integration/motor/test_reglas_motor.py` |
| R05 | Diversidad de familias y parámetro independiente por regla; `test_motor.test_evaluador_de_carreras_cuenta_familias_no_visitas_ni_carreras`, `test_configuracion_metodos.test_evaluador_lee_parametro_de_cada_regla_sin_compartir_resultados`, E13. | Exploración de it. 3; plataforma solo cubre `misiones_camino_sin_inicio`. Crear reglas de prueba con umbrales distintos y referencias nulas/ajenas. | `integration/motor/test_evaluadores_motor.py` |
| R06 | Reglas alternativas para CONVERSACIONES, audiencia tras un evento compartido y cuentas independientes; `test_motor.test_reglas_alternativas_mismo_objetivo_no_exigen_ambas` (2), `test_evento_compartido_filtro_audiencia_y_aislamiento`, E10–E11. | Familia de it. 4; P7 abre conversaciones del estudiante, pero no contrasta alternativas ni concesiones de dos cuentas con audiencia distinta. | `integration/motor/test_reglas_motor.py` |
| R07 | Progreso de insignia oculta: 403 sin revelar código; tras obtenerla devuelve explicación; `test_consultas.test_progreso_oculto_responde_403_sin_explicacion` (4), `test_logro_oculto_obtenido_revela_estado_y_progreso`. | consultas_dominio verifica el listado revelado, no `/progreso` antes/después. Usar I10. | `integration/logros/test_progreso_logros.py` |
| R08 | Explicación HTTP de condiciones compuestas, alternativas, objetivo sin reglas y evaluador especial separado; `test_consultas.test_progreso_compuesto_muestra_lo_que_falta`, `test_progreso_conversaciones_muestra_alternativas_y_cuentas_independientes`, `test_progreso_objetivo_sin_reglas` (2), `test_progreso_evaluador_especial_se_muestra_separado`. | P13 solo revisa una condición del bloque; falta el contrato de explicación genérica. | `integration/motor/test_progreso_motor.py` |
| R09 | `respondida` por pregunta y cuenta, sin confundir entradas libres; `test_consultas.test_pregunta_respondida_solo_depende_de_entradas_de_la_cuenta`, `test_preguntas_respondidas_no_se_mezclan_entre_cuentas`. | It. 3; semilla_plataforma verifica unicidad de escritura, pero no el valor del listado con dos preguntas distintas. | `integration/cuentas/test_consultas_cuenta.py` |
| R10 | GET sin efectos ni ids internos, historial de eventos por fecha/desempate/cuenta; `test_consultas.test_linea_de_tiempo_por_fecha_y_cuenta_con_codigos`, `test_respuestas_no_exponen_ids_internos`, `test_instrumentos.test_todas_las_consultas_son_de_lectura_y_exponen_solo_codigos_publicos`. | El contrato actual comprueba valores; falta una fotografía de tablas antes/después y la inspección recursiva, también para instrumentos. | `integration/cuentas/test_consultas_cuenta.py` |
| R11 | Presupuestos de las siete consultas y progreso; 100 reglas, 500 eventos y completar con evaluación única; `test_consultas.test_consultas_no_crecen_con_100_reglas_y_500_eventos` (2), `test_medicion_base_estado_progreso_y_actividades`. | No hay ContadorConsultas en P1–P16, consultas_dominio ni piloto. Comparar ambas bases y exigir límites también tras repetir. El caso B de 100 fichas se conserva. | `integration/motor/test_presupuestos_motor.py` |
| R12 | SQL constante al insertar/reemplazar uno o todos los ítems, con identidad y fechas conservadas; `test_consultas.test_responder_un_item_o_24_cuesta_lo_mismo` (2), `test_instrumentos.test_i3_validacion_de_item_opcion_y_disponibilidad_y_reemplazo`. | Retoma vigente: P9 guarda los restantes, pero no compara tamaño de lote, reemplazo, timestamps ni coste. Usar los 5 ítems de act-tip-01. | `integration/instrumentos/test_presupuestos_instrumentos.py` |
| R13 | Validar el lote completo antes de crear/reemplazar; `test_consultas.test_lote_mixto_valida_antes_de_escribir_y_respeta_limite`, `test_instrumentos.test_lote_se_valida_completo_antes_de_crear_o_reemplazar` (4). | P8 rechaza completar sin respuestas; no verifica un lote de respuestas mixto con item ajeno/opción inválida y estado previo. | `integration/instrumentos/test_validacion_instrumentos.py` |
| R14 | Caché aislada entre motores, commit la reemplaza y rollback la conserva; `test_consultas.test_cache_aislada_detecta_commit_y_conserva_rollback`. | semilla_plataforma prueba rollback de carga; no prueba dos instancias con una regla nueva confirmada y lectura posterior. | `integration/motor/test_cache_motor.py` |
| R15 | Reinicio de desarrollo vacía las 16 tablas, conserva catálogo/cartas/caché, es idempotente y revierte por fallo; `test_carga_datos.test_reinicio_vacia_las_dieciseis_tablas_con_datos`, `test_reinicio_preserva_catalogo_cache_posiciones_y_no_usa_cargadores` (2), `test_consultas.test_reinicio_conserva_cache_tras_exito_y_fallo`, `test_fase1.test_reinicio_conserva_catalogo_y_vacia_todo_el_estado`. | Requisito explícito §4.2. El reinicio de piloto solo llena progreso y eventos. Sembrar datos sintéticos de registro para comprobar borrado, sin probar evaluación Gemini; no conservar posiciones_registro. El rollback B también se conserva. | `integration/desarrollo/test_reinicio_desarrollo.py` |
| R16 | Reinicio solo en desarrollo; ninguna ruta /demo; arranque vacío sin siembra ni lecturas de datos; `test_configuracion.test_demo_solo_en_desarrollo_sin_contaminar_instancias`, `test_arranque_con_esquema_y_catalogo_vacio_no_siembra`, `test_semilla_plataforma.test_cargador_independiente_en_arranque_y_reinicio`. | Sustitución obligatoria §§4.2–4.4 y §11.5. Eliminar únicamente verificaciones de recursos/posiciones retirados; conservar separación de instancias y catálogo vacío. | `integration/desarrollo/test_entorno_desarrollo.py` |
| R17 | Respuesta editable mientras falta completar la aplicación; congelada con resultado; rehacer no recalcula; `test_instrumentos.test_se_puede_editar_una_actividad_completada_si_la_aplicacion_sigue_incompleta`, `test_i7_respuestas_fijas_y_rehacer_sin_recalcular`. | P5 repite informativas; no verifica congelación de respuestas ni conservación de resultado/fecha. | `integration/instrumentos/test_ciclo_instrumentos.py` |
| R18 | Fallo después de generar resultado revierte resultado/dimensiones/coincidencias/progreso/eventos/desbloqueos; `test_instrumentos.test_fallo_del_calculo_revierte_resultados_progreso_eventos_y_desbloqueos`, `test_i14_fallo_del_calculo_riasec_revierte_ultima_actividad`. | RIASEC vigente. P10 cubre éxito, P8 validación previa; ninguno falla después de persistir el cálculo. | `integration/instrumentos/test_atomicidad_instrumentos.py` |
| R19 | Una actividad genera varias aplicaciones, selección explícita y SQL constante al aumentar aplicaciones; `test_instrumentos.test_una_actividad_genera_resultados_para_cada_aplicacion`, `test_consultas.test_completar_no_crece_con_mas_aplicaciones`. | Instrumentos existentes y autoconocimiento de it. 3; plataforma solo tiene una aplicación. Añadir aplicaciones sintéticas asociadas al recorrido completo. | `integration/instrumentos/test_aplicaciones_instrumentos.py` |
| R20 | Reiniciar y recalcular conserva historial, vigentes únicos, desbloqueos y otra cuenta; varios ciclos planos; `test_instrumentos.test_i11_reinicio_riasec_conserva_historia_y_permite_nuevo_resultado`, `test_i13_cuentas_intercaladas_con_resultados_y_reinicio_aislados`, `test_ciclos_planos_mantienen_un_solo_vigente_y_todo_el_historial` (2). | Reinicio vigente sin cobertura en plataforma/piloto. Evitar volver a verificar el ranking del notebook que ya cubren P10 y cálculo puro. | `integration/instrumentos/test_ciclo_instrumentos.py` |
| R21 | Historial conserva detalles, ordena por fecha/id y coste constante con 20 resultados extra; `test_instrumentos.test_historial_conserva_dimensiones_coincidencias_y_ordena_fecha_y_desempate`, `test_consultas.test_historial_no_crece_con_20_resultados_extra`. | P10 solo consulta resultado vigente; falta historial real y su presupuesto SQL. | `integration/instrumentos/test_historial_instrumentos.py` |
| R22 | Reinicio parcial solo borra sus respuestas y no crea progresos ni abre actividades; `test_instrumentos.test_reinicio_parcial_no_crea_progresos_y_no_abre_actividades`, `test_reinicio_borra_solo_respuestas_del_instrumento_en_los_progresos_elegidos`. | Reinicio vigente; ni P9 ni piloto reinician instrumentos. Agregar ítem ajeno sintético y comprobar que sobrevive. | `integration/instrumentos/test_ciclo_instrumentos.py` |
| R23 | Reinicio inválido o sin datos rechaza sin escribir; cuenta, audiencia, instrumento/aplicación, fecha y selección; `test_instrumentos.test_reinicio_invalido_no_modifica_estado` (9), `test_reinicio_sin_respuestas_ni_resultado_devuelve_409` (5). | Falta validación del endpoint de reinicio en plataforma. Un caso recorre entradas con fotografía y estado aislado. | `integration/instrumentos/test_validacion_instrumentos.py` |
| R24 | Fallo al registrar reinicio revierte anulación, respuestas y progresos, parcial y completo; `test_instrumentos.test_fallo_al_registrar_reinicio_revierte_anulacion_respuestas_y_progresos` (2). | Atomicidad del reinicio; los invariantes de semilla no fuerzan esa transacción. | `integration/instrumentos/test_atomicidad_instrumentos.py` |
| R25 | COINCIDENCIAS y código de interés siguen tipo/orden persistido, incluso plano, al renombrar instrumento; `test_configuracion_metodos.test_coincidencias_y_codigo_siguen_tipo_y_orden_de_la_base` (2). | P10/P11 usan metadatos originales. Probar tipo/orden, sin asumir códigos de demo ni ranking del Excel completo. | `integration/instrumentos/test_metadatos_instrumentos.py` |
| R26 | DESTACADAS por metadatos, ganador, empates y cero; ítems inversos; `test_configuracion_metodos.test_destacadas_no_dependen_del_codigo`, I8/I8b/I9 y `test_inteligencias_en_cero_destaca_todas_las_dimensiones`. | Autoconocimiento de it. 3. Cálculo puro ya verifica aritmética, pero falta persistencia/consulta genérica. Crear instrumento pequeño, no replicar los tests de demo. | `integration/instrumentos/test_metadatos_instrumentos.py` |
| R27 | COMPARACION por momentos, sin generar resultado, con códigos renombrados; tipo/momentos faltantes rechazan; `test_configuracion_metodos.test_comparacion_generica_conserva_test_auto_y_usa_momentos`, `test_comparacion_requiere_tipo_y_ambos_momentos`, I10. | Autoconocimiento de it. 3; ninguna base actual tiene dos momentos. Sembrar entrada/salida mínimos con ítems compartidos. | `integration/instrumentos/test_comparacion_instrumentos.py` |
| R28 | Reinicio selectivo de salida conserva entrada y hace pendiente la comparación; `test_instrumentos.test_i12_reinicio_solo_de_salida_conserva_entrada_y_exige_seleccion`. | Mismo comportamiento futuro vigente; no lo cubre reinicio RIASEC. | `integration/instrumentos/test_comparacion_instrumentos.py` |
| R29 | Código legible nullable en coincidencia, vía e historial/anulación; `test_configuracion_base.test_codigo_ocupacion_en_resultado_historial_y_via` (2). | P10 siempre recibe códigos no nulos; el esquema admite nulos. Anular temporalmente el código de una ocupación recomendada, sin catálogo demo. | `integration/instrumentos/test_resultados_instrumentos.py` |
| R30 | Cálculo SQL constante con 100 ocupaciones extra y una lectura agrupada de puntajes; `test_consultas.test_calculo_riasec_no_crece_con_100_ocupaciones`. | No hay presupuesto de cálculo en P10. | `integration/instrumentos/test_presupuestos_instrumentos.py` |
| R31 | Presupuestos de catálogo, ítems, avance, respuestas, resultado pendiente/vigente y reinicio; `test_consultas.test_medicion_base_respuestas_calculo_y_resultado_riasec`, parte instrumental de `test_medicion_base_otras_vistas_y_acciones`. | Las consultas funcionales no comprueban consultas agrupadas ni presupuestos de petición. | `integration/instrumentos/test_presupuestos_instrumentos.py` |
| R32 | Fallo posterior a evaluar completar revierte progreso/eventos/desbloqueos; `test_acciones.test_fallo_despues_de_evaluar_revierte_completar_actividad`, `test_motor.test_reversion_de_accion_incluye_estado_eventos_y_desbloqueos`. | P3 rechaza antes de escribir; no prueba rollback tras una concesión real. | `integration/actividades/test_atomicidad_acciones.py` |
| R33 | Conversación compartida: disponibilidad del actor, primera vez para ambos, repetición idempotente y rollback de segunda cuenta; `test_acciones.test_conversacion_solo_exige_disponibilidad_de_quien_marca`, `test_fallo_segunda_cuenta_revierte_conversacion_y_novedades`, E10–E11 e invariantes compartidos. | Familia it. 4; no hay conversaciones sembradas en plataforma. Solo filas sintéticas. | `integration/actividades/test_acciones_compartidas.py` |
| R34 | Coautoría independiente con desbloqueos y coste constante de 2 a 20 autores; `test_motor.test_coautores_se_evaluan_independientemente`, E12, `test_consultas.test_publicar_entrevista_no_crece_con_20_autores`. | Entrevistas it. 4. El fallo del segundo autor queda en B, pero falta éxito/desbloqueos por autor y SQL agrupado. | `integration/actividades/test_acciones_compartidas.py` |
| R35 | Casos: intento fallido, umbral inclusivo, extremos y superación una sola vez; completar por la ruta general rechaza; `test_acciones.test_puntaje_minimo_inclusivo_y_extremos_validos`, `test_completar_caso_mediante_actividad_no_crea_intento`, E9. | Casos it. 4. No hay casos en plataforma/piloto; preparar actividad mínima de prueba y comprobar intentos/progreso/eventos. | `integration/actividades/test_resolver_casos.py` |
| R36 | Eventos crudos evalúan reglas sin crear estado de dominio; `test_acciones.test_eventos_crudos_omiten_dominio_sin_modificar_progresos`. | P16 emite eventos nuevos; no contrasta completar por `/eventos` con ausencia de progreso ni PUBLICA_ENTREVISTA sin entrevista. | `integration/motor/test_eventos_motor.py` |
| R37 | Distribución de ítems rechaza faltantes, repetidos y ajenos con atomicidad; `test_semilla_instrumentos.test_distribucion_rechaza_items_faltantes_repetidos_y_ajenos` (3), `test_contenido_actividades.test_clave_invalida_revierte_toda_la_carga` (6), `test_configuracion_metodos.test_excel_asocia_dimension_por_codigo_aunque_cambie_orden`. | Carga vigente: semilla_plataforma valida datos buenos y errores de Excel, pero no estas corrupciones ni la asociación tras invertir orden. Un caso comprueba variantes de carga sobre bases temporales independientes, conservando rollback total y código en el error. | `integration/datos/test_validacion_catalogos.py` |
| R38 | Integridad SQL no cubierta: unicidad de catálogos/relaciones y respuestas/opciones/ítems, defaults y código de ocupación nullable; `test_fase1.test_codigos_y_numeros_unicos_en_catalogos`, `test_defaults_falsos`, C de `test_estado_no_admite_duplicados` (2), `test_semilla_instrumentos.test_respuestas_opciones_e_items_unicos`, `test_configuracion_base.test_columnas_y_restricciones_nuevas_con_demo_intacta`. | Migraciones compara DDL y algunas restricciones; no intenta todas estas escrituras. Las restricciones B se mantienen. Añadir filas sintéticas para catálogos vacíos y comprobar IntegrityError en savepoints. | `integration/migraciones/test_integridad_catalogos.py` |
| R39 | Textos aprobados de dimensiones y propagación a destacadas/historial; `test_descripciones_dimensiones.test_descripciones_coinciden_con_los_textos_aprobados_del_anexo`, `test_inteligencias_expone_descripciones_tambien_en_destacadas_y_conserva_habilidades`. | El caso A solo cubre RIASEC. Conservar textos de inteligencias en datos de prueba de soporte y contrastarlos con el anexo, sin mover catálogo demo a app ni reproducir la aserción del texto de demostración de habilidades. | `integration/instrumentos/test_descripciones_resultados.py` |
| R40 | Rechazos por tipo de actividad, audiencia y ausencia de vínculo sin efectos; consultas instrumentales inválidas/ajenas; `test_acciones.test_accion_no_permitida_responde_409_sin_efectos` (7), `test_instrumentos.test_cuentas_actividades_y_audiencia_se_validan` (4), `test_apoderado_no_puede_completar_actividades_de_instrumentos`, `test_consultas_de_instrumentos_rechazan_apoderados_y_cuentas_inexistentes` (10), `test_consultas_rechazan_referencias_y_aplicaciones_ajenas` (8). | P14 cubre completar con apoderado y P3 un salto; faltan métodos de instrumentos y reglas de otros dominios planificados. Recorre entradas inválidas preservando diferencias 404/409/422 y ausencia de escrituras; no simular indisponibilidad mediante ids inexistentes. | `integration/actividades/test_validacion_acciones.py` |

R37 reúne validaciones de carga; si se prefiere separarlas por fallo, se debe
redistribuir el presupuesto de 40 casos en el inventario antes de implementar.
Lo mismo vale para R38 y R40: la aprobación cubre los comportamientos descritos,
no solamente comprobar que «alguna entrada falla».

## C que no se propone portar

| Grupo | Decisión y evidencia |
|---|---|
| Registro y UI | Eliminar 204 casos de los cuatro archivos indicados; además, los 103 casos SQL de registro de `test_consultas.py` (desde `test_limite_sql_guardar_posicion_registro` hasta `test_registro_sql_no_crece_con_100_reglas_reflexivas_y_500_eventos`). §3 y §5 autorizan dejar ese registro sin cobertura de integración hasta it. 2. Las 142 pruebas puras de evaluación y las 56 A de Gemini permanecen. |
| Script Gemini e integración demo del adaptador | Eliminar los 23 C de `test_evaluador_gemini.py`: 21 de script/CLI/casos y 2 de HTTP REG-ACT08. Retirar importación de `scripts.evaluar_gemini` y `ClienteConversacionesSimulado`; conservar `ClienteSimulado`, transporte HTTP simulado, prompt y todas las A sin cambiar aserciones. No llamar a Gemini real. |
| Páginas y catálogo /demo | Los 2 de `test_demo.py`, los auxiliares UI, lectura JSON de registro y auxiliar de registro en memoria se retiran por §4. No reproducir sus recursos ni catálogo HTTP. |
| Catálogo demo literal | Retirar verificaciones de bloques LAB/REG, conteos de 30 actividades/137 ítems/47 reglas/58 condiciones, títulos, rejillas y textos de demostración. Ya existe catálogo exacto de plataforma en `test_semilla_plataforma.py`; no copiar el catálogo antiguo como fixture alternativo. |
| Relaciones O*NET de demo | Retirar los 10 parámetros de `test_relaciones_exigen_todas_las_ocupaciones`, fallback de medicina y relaciones exactas de 923 ocupaciones. Son reglas del cargador demo, no de `datos.ocupaciones`. Conservar las 10 A del lector Excel; plataforma ya prueba sus 36 ocupaciones, 23 relaciones y errores de catálogo. La asociación por dimensión se conserva en R37. |
| Recorridos E1–E17 | Retirar el archivo como escenarios. E1–E5/E7/E17 ya tienen cobertura en P1–P9/P12 y semilla_plataforma. E6/E8–E13 aportan a R01/R02/R05/R06/R33–R35. E14 coincide con el invariante de diario existente; R09 conserva la consulta. E15 es registro autorizado a retirarse. E16 es la progresión literal de demo, sin implementar una ruta futura para llegar a nivel 5. |
| Disponibilidad, progreso y monotonía repetidos | Retirar las variantes de disponibilidad inicial, bloqueo sobre progreso, herencia de ciudad, progreso en curso, primeros desbloqueos y permanencia ya cubiertas por P1/P2/P3/P5/P6/P7/P8/P14, consultas_dominio y los invariantes de semilla_plataforma. Las diferencias genéricas de concesión/condición, AND/OR y audiencia compartida están en R02/R04/R06/R08. |
| Resultado demo / notebook | P10 y cálculo puro ya comprueban ranking, Pearson, ajuste, código, recomendaciones y vías; P11 el perfil plano; P8/P9 la finalización y retoma. Retirar duplicados de I1–I6 y partes equivalentes de I8–I10. Persistencia, metadatos, reinicio, aislamiento y fallos distintos se agrupan en R17–R31. |
| Otras pruebas C de carga, arranque y reinicio | No portar el orden exacto de flush de la semilla demo ni conservar `posiciones_registro`. La carga fallida B y semilla_plataforma ya comprueban atomicidad; R15/R16 conservan reinicio y arranque del sistema que permanece. |

El anexo de clasificación identifica cada función y sus parámetros; dentro de C,
solo los comportamientos nombrados en R01–R40 se reescriben. El resto se elimina.
No se considera aprobada ninguna eliminación o reescritura hasta aprobar P1.

## Ajustes mecánicos y utilidades compartidas para P2/P3

| Dependencia actual | Tratamiento propuesto |
|---|---|
| `test_configuracion_base.py` importa `CADENA_B`, `REQUIERE_OCUPACIONES`, `aplicar_cadena` de `test_instrumentos.py` | Esos consumidores son C. No mover `aplicar_cadena` con sus cuatro LAB-RIA. Reutilizar `MARA`, `responder` y `avanzar_camino` desde `soporte_plataforma`; añadir solo las ayudas genéricas de ciclo, fotografía y consulta a `tests/soporte/soporte_instrumentos.py`. Los nuevos tests no importan un test. |
| `test_configuracion_metodos.py` importa `CADENA_MEDICION`, `buscar`, `datos_medicion`, `preparar_peticion` de `test_consultas.py` | Consumidores C. Mover solo ayudas vigentes: búsqueda y preparación de datos/peticiones a soporte; usar recorrido de plataforma. No mover RUTA_HASTA_CIUDAD, límites de registro ni pasos de LAB. Las mediciones R11/R12/R30/R31 usan `ContadorConsultas`/`MedidorPeticiones` de `soporte_consultas.py`, que ya está en soporte. |
| `test_postgres.py` importa `test_plataforma` y llama a cuatro funciones test mediante getattr | Extraer los cuerpos verificadores P01/P02/P07/P10 a `tests/soporte/soporte_escenarios_plataforma.py`, manteniendo sus aserciones exactas; los cuatro tests SQLite llaman al verificador, al igual que los cuatro casos PostgreSQL. Conservar 15 escenarios SQLite y 4 PostgreSQL recolectados, sin duplicar tests ni importar `test_*.py`. |
| `test_registro_v2.py` y `test_registro_finalizacion_v2.py` importan ayudas/fixture de `test_registro.py` | Los tres archivos se retiran completos. No trasladar utilidades muertas a soporte. |
| Constantes descriptivas de `datos.demo.instrumentos` en `test_descripciones_dimensiones.py` | Conservar la prueba A RIASEC; sacar el import demo. R39 usa textos aprobados de inteligencias en soporte como dato de prueba. No convertirlos en un nuevo catálogo de producción. |
| `conftest.py` importa `datos.demo.instrumentos` para catálogo opcional y siembra demo | Al retirar demo, cambiar fixture base a plataforma en P2. Retirar parche opcional exclusivo de demo; los tests del lector usan Excel sintético y plataforma conserva su validación real. En P4 se trasladan fixtures con base a integration y se aplica plantilla; no adelantarlo en P2. |
| `tests/soporte/soporte_plataforma.py` redefine aplicacion/cliente/sesion | Conservar ayudas y eliminar solo el puente que deja de hacer falta al cambiar la base global. Reorganización/plantilla conforme P3/P4, sin introducir nuevas bases globales en P1. |
| Reinicio en A/B y piloto | Cambiar `/demo/reiniciar` y servicio/esquema a desarrollo, además del mensaje esperado, según §§4.2 y 11.4. No cambiar otras aserciones A/B. Afecta migraciones, piloto y carga; algunos C se sustituyen en R15/R16. |
| Tres parametrizaciones A por conjunto | Quitar `demo` de carga_conteos, carga_vaciado_y_reinicio_conservan_revision y claves_y_visibilidad_de_los_conjuntos; conservar plataforma y sus aserciones. En contenido retirar también la rama ya inalcanzable de demo. **3 casos A menos**, sin port. |
| C con posiciones de registro o parches del cargador eliminado | R15/R16 reemplazan la cobertura de estado/catalogo/aislamiento; no conservar referencias a app.state.posiciones_registro, contenido JSON ni monkeypatch de funciones eliminadas. Este ajuste se registra expresamente, no se oculta como cambio de fixture B. |

Los destinos de soporte son propuestas dentro de la estructura existente. No se
crea ninguno en P1. Auditar después con búsqueda y AST que no quede importación
entre tests, ni importaciones directas/indirectas de datos.demo o evaluar_gemini.
El análisis de `app/**/*.py` no encuentra lectura de Excel ni importación de
O*NET; la lectura de datos que sí existe está en registro/contenido y las rutas
estáticas, ambas previstas para retirarse por §4.

## Impacto esperado y límites de la aprobación

Si se aprueba esta propuesta completa, el cálculo orientativo de P2 es:
**1099 − 607 C − 3 parámetros demo de A + 40 ports + 1 prueba arquitectónica
obligatoria = 530 casos**. Es una previsión, no un conteo ejecutado ni una
autorización para ajustar pruebas con el fin de alcanzarlo. P2 medirá el conteo
real, justificará diferencias y P3 debe conservar exactamente ese conteo.

Los 418 A y 74 B no autorizan cambiar resultados esperados, salvo el reinicio
expresamente autorizado. Los 40 ports sí se reescriben porque su catálogo cambia;
conservan el comportamiento descrito, no resultados literales de demo. Los
escenarios y resultados de plataforma/piloto siguen siendo la referencia.

Frontend: P1 no toca archivos ni requiere regenerar fixtures. P2 tiene únicamente
los cambios de contrato de §4.3; sus 14 fallas previas permanecen como línea base.
No agregar interfaces, endpoints, migraciones, dependencias ni datos de producción.

Al aprobar P1 se aprueban el retiro de los C no portados y los comportamientos
R01–R40, más las adaptaciones mecánicas enumeradas. La implementación sigue
siendo P2. **Detenerse aquí y esperar aprobación**, como exige §10.

## Validación de P1

- Recolección mediante `uv run python -m pytest --collect-only -qq` con un
  observador externo, sin modificar tests: **1099 casos**. El observador registra
  función, nodeid y cierre de fixtures; las categorías se asignan tras revisar
  cuerpos, ayudantes y referencias, no por coincidencia automática de palabras.
- Auditoría del inventario: las 30 filas por archivo y el anexo por función
  coinciden con la recolección; **418 A + 74 B + 607 C = 1099**. Se verifican
  los 40 identificadores R01–R40 y las cinco importaciones entre tests.
- Suite completa del backend, requerida por AGENTS.md para cerrar fase:
  `uv run python -m pytest -q -p no:cacheprovider --basetemp=<temporal externo>/ov-p1-validacion`:
  **1095 aprobadas, 4 omitidas, cero fallas y 2 advertencias en 937,52 s
  (15 min 37,52 s)**, código 0. Se ejecuta fuera del sandbox por la incidencia
  de permisos documentada en P0. Mismas omisiones de PostgreSQL sin
  TEST_POSTGRES_URL y advertencias Starlette/httpx y google-genai/Python.
- Frontend sin cambios; no se repite su suite en esta fase solo del backend.
  Su línea base P0 sigue siendo 449 aprobadas y 14 fallas previas de 463.
- Solo se agrega este documento; no se adapta ninguna prueba, no se retira
  dato/código, no se llama a Gemini y no se hace push. P2 queda pendiente de
  la aprobación expresa del inventario.


## Anexo · Clasificación trazable por función

Cada número incluye parámetros recolectados. A/B/C mezcladas en una fila
se desglosan por categoría. Los archivos enteramente A/C aparecen también
para que el inventario sea reproducible; no se han contado funciones auxiliares.

### test_acciones.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_ingresar_repite_eventos_y_usa_hora_actual_de_lima` | 0 | 1 | 0 |
| `test_entradas_invalidas_no_generan_estado` | 0 | 12 | 0 |
| `test_accion_no_permitida_responde_409_sin_efectos` | 0 | 0 | 7 |
| `test_referencias_inexistentes_responden_404` | 0 | 4 | 0 |
| `test_completar_caso_mediante_actividad_no_crea_intento` | 0 | 0 | 1 |
| `test_puntaje_minimo_inclusivo_y_extremos_validos` | 0 | 0 | 1 |
| `test_carta_se_actualiza_sin_repetir_evento` | 0 | 1 | 0 |
| `test_conversacion_solo_exige_disponibilidad_de_quien_marca` | 0 | 0 | 1 |
| `test_fecha_con_zona_conserva_calendario_simulado` | 0 | 1 | 0 |
| `test_eventos_crudos_omiten_dominio_sin_modificar_progresos` | 0 | 0 | 1 |
| `test_referencias_de_eventos_invalidas_no_se_registran` | 0 | 5 | 0 |
| `test_fallo_despues_de_evaluar_revierte_completar_actividad` | 0 | 0 | 1 |
| `test_fallo_segundo_autor_revierte_entrevista_completa` | 0 | 1 | 0 |
| `test_fallo_segunda_cuenta_revierte_conversacion_y_novedades` | 0 | 0 | 1 |

### test_calculo_instrumentos.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_pearson_y_ajuste_con_vectores_de_la_especificacion` | 4 | 0 | 0 |
| `test_correlacion_negativa_del_notebook_se_descarta` | 1 | 0 | 0 |
| `test_umbrales_de_ajuste_inclusivos_sin_redondear` | 8 | 0 | 0 |
| `test_puntuacion_e_inversion_segun_limites_de_la_escala` | 8 | 0 | 0 |
| `test_porcentaje_redondeado_a_dos_decimales` | 5 | 0 | 0 |
| `test_dimension_suma_puntajes_y_maximos_con_escalas_distintas` | 1 | 0 | 0 |
| `test_dimensiones_destacadas_compara_proporciones_exactas_y_conserva_empates` | 5 | 0 | 0 |
| `test_calculo_de_inteligencias_con_si_en_impares` | 7 | 0 | 0 |
| `test_calculo_de_habilidades_con_items_inversos` | 6 | 0 | 0 |
| `test_puntuacion_de_las_cadenas_riasec_completas` | 2 | 0 | 0 |
| `test_codigo_de_interes_y_empate_solo_en_el_corte` | 5 | 0 | 0 |
| `test_top_diez_desempata_por_codigo_y_asigna_posiciones` | 1 | 0 | 0 |
| `test_top_ordena_por_pearson_y_conserva_precision_y_titulos` | 1 | 0 | 0 |
| `test_perfil_plano_no_evalua_ocupaciones` | 1 | 0 | 0 |
| `test_calculo_rechaza_datos_invalidos_en_lugar_de_generar_resultados` | 13 | 0 | 0 |
| `test_ocupacion_constante_provoca_error_identificando_su_codigo` | 1 | 0 | 0 |

### test_carga_datos.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_todas_las_tablas_clasificadas_sin_solapamientos` | 1 | 0 | 0 |
| `test_carga_conteos_recarga_rechazada_y_vaciado` | 2 | 0 | 0 |
| `test_carga_fallida_es_atomica` | 0 | 2 | 0 |
| `test_conjunto_invalido_no_abre_base` | 1 | 0 | 0 |
| `test_cli_rechaza_crear_tablas` | 1 | 0 | 0 |
| `test_cli_sin_esquema_y_carga_tras_migracion` | 0 | 1 | 0 |
| `test_reinicio_preserva_catalogo_cache_posiciones_y_no_usa_cargadores` | 0 | 0 | 2 |
| `test_reinicio_fallido_revierte_borrados` | 0 | 1 | 0 |
| `test_reinicio_vacia_las_dieciseis_tablas_con_datos` | 0 | 0 | 1 |
| `test_json_con_actividad_ausente_no_valida_momentos` | 0 | 0 | 1 |
| `test_auxiliar_registro_rechaza_base_persistente` | 0 | 0 | 1 |

### test_configuracion.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_valores_predeterminados_y_ruta_independiente_del_directorio` | 1 | 0 | 0 |
| `test_sqlite_relativa_desde_raiz_conserva_dialectos` | 2 | 0 | 0 |
| `test_urls_sin_ruta_relativa_se_conservan` | 3 | 0 | 0 |
| `test_ruta_absoluta_y_precedencia_env` | 1 | 0 | 0 |
| `test_configuracion_invalida_sin_filtrar_valores` | 5 | 0 | 0 |
| `test_fabrica_argumento_prevalece_incluso_sobre_url_invalida` | 1 | 0 | 0 |
| `test_arranque_sin_esquema_falla_sin_crear_tablas` | 2 | 0 | 0 |
| `test_arranque_con_esquema_y_catalogo_vacio_no_siembra` | 0 | 0 | 1 |
| `test_demo_solo_en_desarrollo_sin_contaminar_instancias` | 0 | 0 | 1 |

### test_configuracion_base.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_columnas_y_restricciones_nuevas_con_demo_intacta` | 0 | 0 | 1 |
| `test_codigo_ocupacion_en_resultado_historial_y_via` | 0 | 0 | 2 |

### test_configuracion_metodos.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_metadatos_semilla_catalogo_y_columnas` | 0 | 0 | 1 |
| `test_coincidencias_y_codigo_siguen_tipo_y_orden_de_la_base` | 0 | 0 | 2 |
| `test_destacadas_no_dependen_del_codigo` | 0 | 0 | 1 |
| `test_comparacion_generica_conserva_test_auto_y_usa_momentos` | 0 | 0 | 1 |
| `test_comparacion_requiere_tipo_y_ambos_momentos` | 0 | 0 | 1 |
| `test_evaluador_lee_parametro_de_cada_regla_sin_compartir_resultados` | 0 | 0 | 1 |
| `test_excel_asocia_dimension_por_codigo_aunque_cambie_orden` | 0 | 0 | 1 |

### test_consultas.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_lista_cuentas_con_codigos_publicos` | 0 | 1 | 0 |
| `test_estado_refleja_progreso_y_nivel` | 0 | 0 | 1 |
| `test_estado_ciudad_hereda_bloques_sin_perder_reglas` | 0 | 0 | 1 |
| `test_actividad_de_bloque_bloqueado_se_muestra_bloqueada_aunque_tenga_progreso` | 0 | 0 | 1 |
| `test_estado_expone_en_curso_con_progreso_parcial` | 0 | 0 | 1 |
| `test_pregunta_respondida_solo_depende_de_entradas_de_la_cuenta` | 0 | 0 | 1 |
| `test_progreso_oculto_responde_403_sin_explicacion` | 0 | 0 | 4 |
| `test_logro_oculto_obtenido_revela_estado_y_progreso` | 0 | 0 | 1 |
| `test_progreso_compuesto_muestra_lo_que_falta` | 0 | 0 | 1 |
| `test_progreso_objetivo_sin_reglas` | 0 | 0 | 2 |
| `test_progreso_regla_cumplida_con_bloque_contenedor_pendiente` | 0 | 0 | 1 |
| `test_progreso_conversaciones_muestra_alternativas_y_cuentas_independientes` | 0 | 0 | 1 |
| `test_progreso_evaluador_especial_se_muestra_separado` | 0 | 0 | 1 |
| `test_consultas_inexistentes_o_de_otra_audiencia_devuelven_404` | 0 | 0 | 13 |
| `test_validacion_de_tipo_y_filtro` | 0 | 1 | 0 |
| `test_linea_de_tiempo_por_fecha_y_cuenta_con_codigos` | 0 | 0 | 1 |
| `test_eventos_diario_y_check_in_no_exponen_ids` | 0 | 1 | 0 |
| `test_desbloqueos_no_vistos_marcado_idempotente_y_aislado` | 0 | 0 | 1 |
| `test_gets_no_generan_eventos_ni_desbloqueos` | 0 | 0 | 1 |
| `test_respuestas_no_exponen_ids_internos` | 0 | 0 | 1 |
| `test_contador_cuenta_lecturas_escrituras_y_lotes_sin_preparacion` | 1 | 0 | 0 |
| `test_contador_retira_listener_tras_error_y_se_puede_reutilizar` | 1 | 0 | 0 |
| `test_contadores_aislan_motores_y_permiten_contextos_independientes` | 1 | 0 | 0 |
| `test_medicion_base_estado_progreso_y_actividades` | 0 | 0 | 1 |
| `test_medicion_base_respuestas_calculo_y_resultado_riasec` | 0 | 0 | 1 |
| `test_medicion_base_otras_vistas_y_acciones` | 0 | 0 | 1 |
| `test_consultas_no_crecen_con_100_reglas_y_500_eventos` | 0 | 0 | 2 |
| `test_responder_un_item_o_24_cuesta_lo_mismo` | 0 | 0 | 2 |
| `test_lote_mixto_valida_antes_de_escribir_y_respeta_limite` | 0 | 0 | 1 |
| `test_estado_no_crece_con_100_objetos_adicionales` | 0 | 1 | 0 |
| `test_cache_aislada_detecta_commit_y_conserva_rollback` | 0 | 0 | 1 |
| `test_reinicio_conserva_cache_tras_exito_y_fallo` | 0 | 0 | 1 |
| `test_calculo_riasec_no_crece_con_100_ocupaciones` | 0 | 0 | 1 |
| `test_historial_no_crece_con_20_resultados_extra` | 0 | 0 | 1 |
| `test_publicar_entrevista_no_crece_con_20_autores` | 0 | 0 | 1 |
| `test_completar_no_crece_con_mas_aplicaciones` | 0 | 0 | 1 |
| `test_limite_sql_guardar_posicion_registro` | 0 | 0 | 3 |
| `test_limite_sql_guardar_borrador_registro` | 0 | 0 | 5 |
| `test_limite_sql_envio_registro_cualquier_origen` | 0 | 0 | 32 |
| `test_limite_sql_editar_final_registro` | 0 | 0 | 1 |
| `test_limite_sql_seguimiento_con_otras_conversaciones_finales` | 0 | 0 | 12 |
| `test_limite_sql_seguimiento_generico_sin_nueva_evaluacion` | 0 | 0 | 2 |
| `test_limite_sql_editar_turno_final_sin_nueva_evaluacion` | 0 | 0 | 2 |
| `test_contador_del_envio_incluye_ambas_transacciones_y_excluye_sql_al_evaluar` | 0 | 0 | 3 |
| `test_limite_sql_continuar_registro` | 0 | 0 | 3 |
| `test_limite_sql_items_registro_desde_cache` | 0 | 0 | 1 |
| `test_limite_sql_estado_registro` | 0 | 0 | 10 |
| `test_limite_sql_evaluaciones_registro` | 0 | 0 | 4 |
| `test_limite_sql_completar_registro` | 0 | 0 | 6 |
| `test_registro_sql_no_crece_con_100_reglas_reflexivas_y_500_eventos` | 0 | 0 | 19 |
| `test_preguntas_respondidas_no_se_mezclan_entre_cuentas` | 0 | 0 | 1 |

### test_consultas_dominio.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_contrato_y_valores_plataforma` | 14 | 0 | 0 |
| `test_cuenta_inexistente` | 7 | 0 | 0 |
| `test_apoderado_sin_listas_estudiantiles` | 7 | 0 | 0 |
| `test_visibilidad_no_oculta_filas_ni_titulos` | 8 | 0 | 0 |
| `test_actividad_al_desbloquear_cambia_de_visible_con_la_accion` | 1 | 0 | 0 |
| `test_bloqueo_prevalece_sobre_progreso` | 2 | 0 | 0 |
| `test_cuestionario_en_curso_y_lecturas_aisladas_por_cuenta` | 1 | 0 | 0 |
| `test_orden_por_numero_y_codigo_y_por_orden_y_codigo` | 1 | 0 | 0 |
| `test_insignia_oculta_solo_se_revela_al_obtenerse` | 1 | 0 | 0 |

### test_contenido_actividades.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_claves_y_visibilidad_de_los_conjuntos` | 2 | 0 | 0 |
| `test_clave_invalida_revierte_toda_la_carga` | 0 | 0 | 6 |

### test_demo.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_pagina_y_recursos_no_modifican_el_estado` | 0 | 0 | 1 |
| `test_catalogo_solo_expone_opciones_publicas_sin_logros_ocultos` | 0 | 0 | 1 |

### test_demo_registro.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_pagina_registro_recursos_y_enlace_sin_sql_ni_escrituras` | 0 | 0 | 1 |
| `test_reinicio_limpia_registros_de_ambas_cuentas_y_permite_primer_envio` | 0 | 0 | 1 |

### test_descripciones_dimensiones.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_resultado_riasec_incluye_las_seis_descripciones_reales` | 1 | 0 | 1 |
| `test_inteligencias_expone_descripciones_tambien_en_destacadas_y_conserva_habilidades` | 0 | 0 | 1 |
| `test_descripciones_coinciden_con_los_textos_aprobados_del_anexo` | 0 | 0 | 1 |

### test_escenarios.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_e1_estado_inicial` | 0 | 0 | 1 |
| `test_e2_primer_desbloqueo` | 0 | 0 | 1 |
| `test_e3_intento_de_saltarse_la_ruta` | 0 | 0 | 1 |
| `test_e4_un_evento_varios_desbloqueos` | 0 | 0 | 1 |
| `test_e5_rehacer_no_suma` | 0 | 0 | 1 |
| `test_e6_dias_distintos` | 0 | 0 | 1 |
| `test_e7_llegada_a_la_ciudad` | 0 | 0 | 1 |
| `test_e8_condicion_compuesta_con_varias_actividades` | 0 | 0 | 1 |
| `test_e9_casos_intento_fallido_reintento_y_repeticion` | 0 | 0 | 1 |
| `test_e10_cuentas_familia_avanzan_a_destiempo` | 0 | 0 | 1 |
| `test_e11_una_accion_desbloqueos_en_dos_cuentas` | 0 | 0 | 1 |
| `test_e12_coautoria` | 0 | 0 | 1 |
| `test_e13_evaluador_especial` | 0 | 0 | 1 |
| `test_e14_diario` | 0 | 0 | 1 |
| `test_e15_respuestas_reflexivas` | 0 | 0 | 1 |
| `test_e16_hasta_el_nivel_5` | 0 | 0 | 1 |
| `test_e17_novedades_no_vistas` | 0 | 0 | 1 |

### test_evaluador_gemini.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_configuracion_predeterminada_sin_clave` | 1 | 0 | 0 |
| `test_env_precedencia_sin_mutar_entorno_ni_interpolar` | 1 | 0 | 0 |
| `test_configuracion_invalida_saneada` | 12 | 0 | 0 |
| `test_clave_faltante_impide_arranque_sin_crear_bd` | 1 | 0 | 0 |
| `test_peticion_salida_estructurada_contexto_exclusivo_y_latencia` | 1 | 0 | 0 |
| `test_conversacion_enviada_y_auditada_coinciden_con_cliente_simulado` | 1 | 0 | 0 |
| `test_texto_corto_llega_a_gemini_simulado_antes_de_decidir_respaldo` | 2 | 0 | 0 |
| `test_razonamiento_minimo_compatible` | 7 | 0 | 0 |
| `test_modelo_desconocido_sin_supuestos_ni_descubrimiento` | 1 | 0 | 0 |
| `test_respuestas_validas_y_metadatos` | 3 | 0 | 0 |
| `test_resultados_invalidos_se_convierten_en_fallo` | 9 | 0 | 0 |
| `test_salida_ausente_bloqueada_o_malformada` | 4 | 0 | 0 |
| `test_fallos_timeout_sin_reintentar_ni_filtrar_secretos` | 6 | 0 | 0 |
| `test_error_directo_del_adaptador_sin_causa_externa` | 1 | 0 | 0 |
| `test_log_externo_con_clave_y_traceback_se_sanea` | 1 | 0 | 0 |
| `test_sdk_real_con_transporte_simulado_no_reintenta_429` | 1 | 0 | 0 |
| `test_cliente_propio_se_cierra_y_error_inicial_saneado` | 1 | 0 | 0 |
| `test_integracion_aplicacion_cliente_simulado_sin_conexion_y_con_metadatos` | 0 | 0 | 2 |
| `test_script_16_casos_contextos_y_reporte_simulado` | 0 | 0 | 1 |
| `test_script_fallo_no_interrumpe_casos_ni_expone_clave` | 0 | 0 | 1 |
| `test_script_rechaza_pausa_invalida_antes_de_llamar` | 0 | 0 | 3 |
| `test_cli_ayuda_no_inicializa_cliente` | 0 | 0 | 1 |
| `test_cli_fallo_externo_saneado_y_cliente_cerrado` | 0 | 0 | 1 |
| `test_prompt_y_casos_coinciden_con_la_especificacion_v2` | 0 | 0 | 1 |
| `test_script_no_inventa_turnos_si_el_inicial_finaliza` | 0 | 0 | 3 |
| `test_script_fallo_del_turno_sigue_con_los_demas_casos_y_no_reintenta` | 0 | 0 | 6 |
| `test_script_respaldo_corto_genera_turno_generico_sin_evaluar_ni_pausar_otra_vez` | 0 | 0 | 1 |
| `test_adaptador_rechaza_criterios_ya_cumplidos_en_el_seguimiento` | 2 | 0 | 0 |
| `test_sdk_con_transporte_simulado_envia_inicial_y_ambos_turnos_con_esquema_v2` | 1 | 0 | 0 |
| `test_script_reporte_escapa_html_y_omite_clave_literal_y_codificada` | 0 | 0 | 1 |
| `test_script_libera_conexiones_antes_del_evaluador_y_solo_prepara_definiciones_en_memoria` | 0 | 0 | 1 |
| `test_cli_exito_simulado_cierra_cliente_y_conserva_el_proveedor_del_entorno` | 0 | 0 | 1 |

### test_evaluador_respuestas.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_interfaz_no_importa_sqlalchemy_fastapi_ni_modelos` | 1 | 0 | 0 |
| `test_contexto_solo_contiene_campos_de_la_especificacion` | 1 | 0 | 0 |
| `test_constantes_de_registro_centralizadas` | 1 | 0 | 0 |
| `test_evaluador_falso_determinista_y_contextos` | 4 | 0 | 0 |
| `test_evaluador_falso_falla_y_conserva_contexto` | 2 | 0 | 0 |
| `test_texto_vacio_rechazado_sin_evaluar` | 4 | 0 | 0 |
| `test_texto_corto_llama_evaluador_primero_r4_y_r5c` | 4 | 0 | 0 |
| `test_limites_exactos_solo_deciden_respaldo_y_respetan_espacios` | 12 | 0 | 0 |
| `test_resultado_exige_esquema_estricto` | 11 | 0 | 0 |
| `test_resultado_exige_todos_los_campos` | 4 | 0 | 0 |
| `test_consistencia_y_criterios_del_item` | 7 | 0 | 0 |
| `test_vaga_con_atencion_admite_pregunta_nula_segun_consistencia` | 1 | 0 | 0 |
| `test_criterios_conservan_orden_del_evaluador` | 1 | 0 | 0 |
| `test_resultado_previamente_mutado_se_valida_otra_vez` | 1 | 0 | 0 |
| `test_resultado_construido_sin_validar_no_filtra_valores_ni_emite_avisos` | 1 | 0 | 0 |
| `test_llm_adecuada_conserva_contexto_y_metadatos` | 1 | 0 | 0 |
| `test_llm_vaga_registra_la_pregunta_del_falso` | 1 | 0 | 0 |
| `test_atencion_no_tiene_pregunta_en_el_falso` | 1 | 0 | 0 |
| `test_resultado_invalido_se_convierte_en_fallo` | 7 | 0 | 0 |
| `test_falso_faltantes_explicitos_y_pregunta_por_codigos` | 4 | 0 | 0 |
| `test_falso_solo_decide_por_ultimo_turno_y_faltantes_previos` | 8 | 0 | 0 |
| `test_ultimo_turno_vacio_rechazado_aunque_haya_respuestas_previas` | 8 | 0 | 0 |
| `test_no_admite_criterios_ya_cumplidos` | 2 | 0 | 0 |
| `test_marca_falso_invalida_aplica_respaldo_en_vez_de_aceptar` | 2 | 0 | 0 |
| `test_resultado_invalido_con_texto_corto_respalda_solo_el_inicial` | 12 | 0 | 0 |
| `test_serializacion_preserva_conversacion_completa_unicode_y_orden` | 1 | 0 | 0 |
| `test_fallos_guardan_error_seguro_y_no_reintentan` | 18 | 0 | 0 |
| `test_marcador_falla_procesado_no_propaga_excepcion` | 1 | 0 | 0 |
| `test_tiempo_maximo_exacto_sin_esperas_reales` | 12 | 0 | 0 |
| `test_minimo_invalido_es_error_de_configuracion` | 3 | 0 | 0 |
| `test_tiempo_maximo_invalido_no_llama_evaluador` | 5 | 0 | 0 |
| `test_pregunta_generica_vacia_es_error_solo_si_se_necesita_respaldo` | 1 | 0 | 0 |

### test_exportar_fixtures_front.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_exportador_exige_destino_incluso_desde_otro_directorio` | 1 | 0 | 0 |
| `test_fixtures_reproducen_el_contrato_y_se_regeneran_identicos` | 1 | 0 | 0 |
| `test_fallo_del_recorrido_no_escribe_fixtures_y_restaura_evaluador` | 1 | 0 | 0 |

### test_fase1.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_tablas_indices_y_claves_foraneas` | 0 | 1 | 0 |
| `test_cuentas_y_vinculo_segun_especificacion` | 0 | 0 | 1 |
| `test_bloques_y_actividades_segun_especificacion` | 0 | 0 | 1 |
| `test_contenido_familias_y_carreras_segun_especificacion` | 0 | 0 | 1 |
| `test_insignias_y_niveles_segun_especificacion` | 0 | 0 | 1 |
| `test_reglas_completas_segun_especificacion` | 0 | 0 | 1 |
| `test_arranque_no_repite_semilla_y_conserva_estado` | 0 | 0 | 1 |
| `test_reinicio_conserva_catalogo_y_vacia_todo_el_estado` | 0 | 0 | 1 |
| `test_estado_no_admite_duplicados` | 0 | 3 | 2 |
| `test_codigos_y_numeros_unicos_en_catalogos` | 0 | 0 | 1 |
| `test_entradas_libres_intentos_y_eventos_pueden_repetirse` | 0 | 1 | 0 |
| `test_restricciones_rechazan_datos_invalidos` | 0 | 6 | 0 |
| `test_defaults_falsos` | 0 | 0 | 1 |
| `test_preparar_base_se_revierte_completa_si_falla` | 0 | 0 | 1 |

### test_fixtures_dominio.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_exportacion_completa_reproducible_y_compatible` | 1 | 0 | 0 |
| `test_fallo_del_piloto_no_escribe_nada_y_restaura_evaluador` | 1 | 0 | 0 |
| `test_cli_exporta_los_dieciseis_fixtures` | 1 | 0 | 0 |

### test_instrumentos.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_i1_estado_inicial_del_laboratorio` | 0 | 0 | 1 |
| `test_i2_respuestas_parciales_impiden_completar_sin_eventos` | 0 | 0 | 1 |
| `test_i3_validacion_de_item_opcion_y_disponibilidad_y_reemplazo` | 0 | 0 | 1 |
| `test_i4_riasec_genera_resultado_solo_en_la_cuarta_actividad` | 0 | 0 | 1 |
| `test_i5_coincidencias_de_luis_contra_el_notebook` | 0 | 0 | 1 |
| `test_i6_perfil_plano_conserva_resultado_sin_coincidencias` | 0 | 0 | 1 |
| `test_i7_respuestas_fijas_y_rehacer_sin_recalcular` | 0 | 0 | 1 |
| `test_i8_inteligencias_genera_resultado_al_completar_la_segunda_actividad` | 0 | 0 | 1 |
| `test_i8b_inteligencias_destaca_espacial_y_musical_en_orden_y_conserva_historial` | 0 | 0 | 1 |
| `test_inteligencias_en_cero_destaca_todas_las_dimensiones` | 0 | 0 | 1 |
| `test_i9_habilidades_sociales_aplica_la_inversion` | 0 | 0 | 1 |
| `test_i10_autopercepcion_guarda_los_mismos_items_en_dos_progresos` | 0 | 0 | 1 |
| `test_entrada_invalida_no_crea_progreso_ni_respuestas` | 0 | 6 | 0 |
| `test_lote_se_valida_completo_antes_de_crear_o_reemplazar` | 0 | 0 | 4 |
| `test_cuentas_actividades_y_audiencia_se_validan` | 0 | 0 | 4 |
| `test_apoderado_no_puede_completar_actividades_de_instrumentos` | 0 | 0 | 1 |
| `test_completar_sin_respuestas_devuelve_todos_los_faltantes` | 0 | 0 | 1 |
| `test_actividad_sin_items_conserva_eventos_y_anuncia_lista_vacia` | 0 | 0 | 1 |
| `test_se_puede_editar_una_actividad_completada_si_la_aplicacion_sigue_incompleta` | 0 | 0 | 1 |
| `test_respuestas_de_otra_cuenta_no_completan_la_actividad` | 0 | 0 | 1 |
| `test_actividad_con_progreso_en_curso_sigue_bloqueada_si_su_bloque_lo_esta` | 0 | 0 | 1 |
| `test_una_actividad_genera_resultados_para_cada_aplicacion` | 0 | 0 | 1 |
| `test_fallo_del_calculo_revierte_resultados_progreso_eventos_y_desbloqueos` | 0 | 0 | 1 |
| `test_catalogo_e_items_publicos_conservan_definiciones_orden_y_opciones` | 0 | 0 | 1 |
| `test_consultas_de_instrumentos_rechazan_apoderados_y_cuentas_inexistentes` | 0 | 0 | 10 |
| `test_consultas_rechazan_referencias_y_aplicaciones_ajenas` | 0 | 0 | 8 |
| `test_resultado_exige_aplicacion_y_devuelve_avance_sin_resultado` | 0 | 0 | 1 |
| `test_respuestas_publicas_se_aislan_por_cuenta_y_aplicacion` | 0 | 0 | 1 |
| `test_historial_conserva_dimensiones_coincidencias_y_ordena_fecha_y_desempate` | 0 | 0 | 1 |
| `test_todas_las_consultas_son_de_lectura_y_exponen_solo_codigos_publicos` | 0 | 0 | 1 |
| `test_i11_reinicio_riasec_conserva_historia_y_permite_nuevo_resultado` | 0 | 0 | 1 |
| `test_i12_reinicio_solo_de_salida_conserva_entrada_y_exige_seleccion` | 0 | 0 | 1 |
| `test_i13_cuentas_intercaladas_con_resultados_y_reinicio_aislados` | 0 | 0 | 1 |
| `test_i14_fallo_del_calculo_riasec_revierte_ultima_actividad` | 0 | 0 | 1 |
| `test_reinicio_invalido_no_modifica_estado` | 0 | 0 | 9 |
| `test_reinicio_sin_respuestas_ni_resultado_devuelve_409` | 0 | 0 | 5 |
| `test_reinicio_parcial_no_crea_progresos_y_no_abre_actividades` | 0 | 0 | 1 |
| `test_ciclos_planos_mantienen_un_solo_vigente_y_todo_el_historial` | 0 | 0 | 2 |
| `test_reinicio_borra_solo_respuestas_del_instrumento_en_los_progresos_elegidos` | 0 | 0 | 1 |
| `test_fallo_al_registrar_reinicio_revierte_anulacion_respuestas_y_progresos` | 0 | 0 | 2 |

### test_invariantes.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_desbloqueos_unicos_permanentes_y_nivel_monotono_en_recorrido` | 0 | 0 | 1 |
| `test_actividad_bloqueada_no_altera_estado_ni_historial` | 0 | 0 | 6 |
| `test_audiencias_se_conservan_tras_eventos_compartidos` | 0 | 0 | 1 |
| `test_eventos_de_primera_vez_y_repeticiones_por_cuenta_y_referencia` | 0 | 0 | 1 |
| `test_check_in_unico_por_dia_con_aislamiento_entre_estudiantes` | 0 | 1 | 0 |
| `test_diario_guiado_unico_por_cuenta_y_pregunta_y_libre_repetible` | 0 | 0 | 1 |

### test_migraciones.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_migracion_inicial_coincide_completamente_con_modelos` | 1 | 0 | 0 |
| `test_upgrade_repetible_downgrade_y_nuevo_upgrade` | 1 | 0 | 0 |
| `test_carga_vaciado_y_reinicio_conservan_revision` | 2 | 0 | 0 |
| `test_esquema_migrado_vacio_arranca_y_rechaza_enumerado_invalido` | 1 | 0 | 0 |
| `test_migracion_y_modelos_compilan_para_postgresql` | 1 | 0 | 0 |
| `test_migracion_0002_conserva_filas_y_referencias_de_0001` | 1 | 0 | 0 |
| `test_columnas_de_actividad_rechazan_nulos_y_visibilidad_invalida` | 3 | 0 | 0 |
| `test_visibilidad_predeterminada_y_al_desbloquear_en_base_migrada` | 1 | 0 | 0 |
| `test_motor_configura_solo_su_dialecto` | 2 | 0 | 0 |
| `test_clasificacion_de_bloqueos` | 11 | 0 | 0 |

### test_motor.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_conteos_filtran_cuenta_tipo_y_referencia` | 0 | 0 | 6 |
| `test_conteo_inicial_es_cero` | 0 | 3 | 0 |
| `test_referencias_nulas_no_son_objetos_distintos` | 0 | 1 | 0 |
| `test_progreso_umbral_y_avance_sin_limitar` | 0 | 0 | 1 |
| `test_regla_compuesta_exige_todas_las_condiciones` | 0 | 0 | 1 |
| `test_eventos_de_otras_cuentas_no_completan_regla_compuesta` | 0 | 0 | 1 |
| `test_evaluador_de_carreras_cuenta_familias_no_visitas_ni_carreras` | 0 | 0 | 1 |
| `test_evaluador_verdadero_no_reemplaza_condiciones` | 0 | 1 | 0 |
| `test_primer_desbloqueo_explicado_sin_ids_internos` | 0 | 0 | 1 |
| `test_varios_eventos_se_evaluan_juntos_y_sin_cascadas` | 0 | 0 | 1 |
| `test_regla_relacionada_con_dos_eventos_se_evaluan_una_sola_vez` | 0 | 0 | 1 |
| `test_repeticiones_no_duplican_ni_revocan_desbloqueos` | 0 | 0 | 1 |
| `test_solo_se_evaluan_tipos_relacionados_y_lista_vacia_no_hace_nada` | 0 | 0 | 1 |
| `test_reglas_alternativas_mismo_objetivo_no_exigen_ambas` | 0 | 0 | 2 |
| `test_evento_compartido_filtro_audiencia_y_aislamiento` | 0 | 0 | 1 |
| `test_disponibilidad_inicial` | 0 | 0 | 16 |
| `test_desbloqueo_no_elimina_filtro_de_audiencia` | 0 | 0 | 6 |
| `test_ciudad_hereda_bloque_y_conserva_reglas_propias` | 0 | 0 | 1 |
| `test_regla_de_actividad_puede_cumplirse_antes_que_bloque_contenedor` | 0 | 0 | 1 |
| `test_condiciones_cumplidas_sin_desbloqueo_no_dan_disponibilidad` | 0 | 0 | 1 |
| `test_objetivos_inexistentes_no_estan_disponibles` | 0 | 8 | 0 |
| `test_niveles_requieren_condiciones_previas_y_nunca_bajan` | 0 | 0 | 1 |
| `test_coautores_se_evaluan_independientemente` | 0 | 0 | 1 |
| `test_reversion_de_accion_incluye_estado_eventos_y_desbloqueos` | 0 | 0 | 1 |
| `test_evaluador_desconocido_revierte_lote_completo` | 0 | 0 | 1 |
| `test_regla_sin_condiciones_es_configuracion_invalida` | 0 | 1 | 0 |

### test_piloto.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_inicio_cinco_actividades_y_ciudad_bloqueada` | 1 | 0 | 0 |
| `test_segundo_paso_abre_ciudad_sin_completar_camino` | 1 | 0 | 0 |
| `test_camino_reducido_conserva_insignias_y_niveles` | 1 | 0 | 0 |
| `test_elena_se_revela_despues_de_interaccion_catorce` | 1 | 0 | 0 |
| `test_actividad_sin_contenido_se_envia_visible_y_hereda_ciudad` | 1 | 0 | 0 |
| `test_rechaza_salto_en_el_camino_sin_registrar_estado` | 1 | 0 | 0 |
| `test_reinicio_conserva_catalogo_piloto` | 1 | 0 | 0 |
| `test_catalogos_ajenos_camino_son_identicos_a_plataforma` | 1 | 0 | 0 |
| `test_cargador_cli_admite_piloto_y_vaciado` | 0 | 1 | 0 |

### test_plataforma.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_p01_estado_inicial` | 1 | 0 | 0 |
| `test_p02_primer_paso` | 1 | 0 | 0 |
| `test_p03_saltarse_la_ruta` | 1 | 0 | 0 |
| `test_p04_informativa_con_fichas` | 1 | 0 | 0 |
| `test_p05_repetir_no_suma` | 1 | 0 | 0 |
| `test_p06_un_evento_varios_desbloqueos` | 1 | 0 | 0 |
| `test_p07_llegada_a_la_ciudad` | 1 | 0 | 0 |
| `test_p08_cuestionario_incompleto` | 1 | 0 | 0 |
| `test_p09_retomar` | 1 | 0 | 0 |
| `test_p10_resultado` | 1 | 0 | 0 |
| `test_p11_perfil_plano` | 1 | 0 | 0 |
| `test_p12_avisos` | 1 | 0 | 0 |
| `test_p13_progreso_de_lo_bloqueado` | 1 | 0 | 0 |
| `test_p14_audiencia` | 1 | 0 | 0 |
| `test_p16_eventos_nuevos` | 1 | 0 | 0 |

### test_postgres.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_postgresql_por_http` | 4 | 0 | 0 |

### test_registro.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_esquema_registro_columnas_y_enumerados` | 0 | 0 | 1 |
| `test_semilla_registro_coincide_con_especificacion` | 0 | 0 | 1 |
| `test_reg_disponible_solo_para_estudiantes` | 0 | 0 | 1 |
| `test_respuestas_y_evaluaciones_guardan_json_y_campos_opcionales` | 0 | 0 | 1 |
| `test_unicidad_de_definiciones_y_respuestas` | 0 | 0 | 4 |
| `test_restricciones_sql_registro` | 0 | 0 | 15 |
| `test_mismo_item_admite_respuestas_de_cuentas_distintas` | 0 | 0 | 1 |
| `test_turnos_persisten_pregunta_borrador_respuesta_y_texto_inicial` | 0 | 0 | 1 |
| `test_turno_unico_por_respuesta_y_orden` | 0 | 0 | 1 |
| `test_restricciones_sql_turno_seguimiento` | 0 | 0 | 7 |
| `test_reinicio_borra_turnos_y_conserva_cache` | 0 | 0 | 1 |
| `test_contenido_json_valido_y_publico_sin_escrituras` | 0 | 0 | 1 |
| `test_r17_contenido_invalido_impide_arranque_sin_modificar_datos` | 0 | 0 | 10 |
| `test_arranque_valida_json_tambien_con_base_existente` | 0 | 0 | 1 |
| `test_reinicio_no_relee_json_y_conserva_cache` | 0 | 0 | 1 |
| `test_cache_registro_orden_criterios_por_item_y_reinicio` | 0 | 0 | 1 |
| `test_cache_registro_reconstruye_tras_commit_y_conserva_tras_rollback` | 0 | 0 | 1 |
| `test_accion_registro_anterior_sigue_rechazando_no_evaluada` | 0 | 0 | 1 |
| `test_r1_consultas_iniciales_ordenadas_sin_escrituras` | 0 | 0 | 1 |
| `test_r2_posicion_valida_crea_progreso_y_se_retoma` | 0 | 0 | 1 |
| `test_r3_borrador_reemplaza_sin_evaluacion_ni_eventos` | 0 | 0 | 1 |
| `test_r4_respaldo_corto_y_r5_turno_generico_sin_reevaluar` | 0 | 0 | 1 |
| `test_r5b_seguimiento_llm_evalua_conversacion_completa` | 0 | 0 | 1 |
| `test_r5c_corto_se_evalua_antes_del_minimo` | 0 | 0 | 1 |
| `test_r6_solo_faltantes_y_r7_dos_turnos_con_maximo` | 0 | 0 | 1 |
| `test_r8_continuar_conserva_pregunta_sin_respuesta` | 0 | 0 | 1 |
| `test_r9_adecuada_y_r12_atencion_solo_en_auditoria` | 0 | 0 | 1 |
| `test_r10_contexto_solo_finales_con_turnos_de_otros_items_y_misma_cuenta` | 0 | 0 | 1 |
| `test_r11_fallo_inicial_y_fallo_seguimiento_no_bloquean` | 0 | 0 | 1 |
| `test_r13d_edicion_final_sin_cambiar_auditoria_ni_metricas` | 0 | 0 | 3 |
| `test_r14_concurrencia_descarta_toda_evaluacion_incluso_fecha_igual` | 0 | 0 | 6 |
| `test_r15_sin_sesiones_transacciones_ni_conexiones_en_evaluacion` | 0 | 0 | 2 |
| `test_r16_aislamiento_posiciones_respuestas_y_evaluaciones` | 0 | 0 | 1 |
| `test_envio_limites_exactos_y_preserva_espacios` | 0 | 0 | 6 |
| `test_envio_vacio_422_sin_escrituras` | 0 | 0 | 6 |
| `test_borrador_vacio_es_valido_sin_evaluar` | 0 | 0 | 1 |
| `test_r13_borrador_de_turno_conserva_texto_inicial_pregunta_e_historial` | 0 | 0 | 2 |
| `test_segundo_turno_siempre_final_sin_tercera_pregunta` | 0 | 0 | 4 |
| `test_continuar_rechaza_estados_sin_repregunta` | 0 | 0 | 3 |
| `test_acciones_registro_validan_cuenta_y_disponibilidad_sin_escrituras` | 0 | 0 | 20 |
| `test_acciones_registro_rechazan_items_ajenos` | 0 | 0 | 8 |
| `test_consultas_registro_404_y_lectura_de_actividades_sin_items` | 0 | 0 | 1 |
| `test_evaluacion_invalida_o_timeout_finaliza_con_error_saneado` | 0 | 0 | 4 |
| `test_marca_concurrencia_monotonica_con_reloj_y_fecha_simulada_iguales` | 0 | 0 | 1 |
| `test_comparacion_condicional_protege_relectura_hasta_escritura` | 0 | 0 | 1 |
| `test_error_sql_revierte_respuesta_evaluacion_eventos_y_desbloqueos` | 0 | 0 | 9 |
| `test_envio_reconstruye_contexto_entre_transacciones` | 0 | 0 | 1 |
| `test_posiciones_permanecen_tras_reinicio` | 0 | 0 | 1 |
| `test_orden_de_respuestas_por_item_y_evaluaciones_por_insercion` | 0 | 0 | 1 |
| `test_registro_se_recupera_despues_de_reabrir_aplicacion` | 0 | 0 | 1 |
| `test_guardar_posicion_y_editar_preservan_progreso_completado` | 0 | 0 | 1 |
| `test_r11_borrador_impide_completar_y_finales_completan_actividad_y_bloque` | 0 | 0 | 1 |
| `test_r12_tres_reflexivas_desbloquean_pensador_sin_cambiar_reglas` | 0 | 0 | 1 |
| `test_completar_registro_rechaza_respuestas_no_finales_sin_escrituras` | 0 | 0 | 3 |
| `test_completar_admite_finales_sin_exigir_clasificacion_adecuada` | 0 | 0 | 4 |
| `test_completar_ignora_items_opcionales_no_finales` | 0 | 0 | 3 |
| `test_completar_con_todos_los_items_opcionales_no_exige_respuestas` | 0 | 0 | 1 |
| `test_faltantes_siguen_el_orden_de_presentacion_y_excluyen_opcionales` | 0 | 0 | 1 |
| `test_completar_registro_rechaza_cuenta_no_estudiante_sin_escrituras` | 0 | 0 | 2 |
| `test_completar_registro_no_usa_finales_de_otra_cuenta` | 0 | 0 | 1 |
| `test_completar_registro_no_usa_finales_de_otra_actividad` | 0 | 0 | 1 |
| `test_rehacer_conserva_respuestas_posicion_evaluaciones_y_permite_edicion` | 0 | 0 | 1 |

### test_registro_finalizacion_v2.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_r13b_pendiente_impide_completar_sin_escrituras_y_luego_finaliza` | 0 | 0 | 4 |
| `test_completar_acepta_finalizacion_del_segundo_turno_y_conserva_la_conversacion` | 0 | 0 | 4 |
| `test_r13c_seguimientos_generan_tres_reflexivas_y_un_solo_logro` | 0 | 0 | 1 |
| `test_rehacer_conserva_turnos_respondidos_y_omitidos_y_permite_editar_sin_reevaluar` | 0 | 0 | 1 |
| `test_error_sql_al_completar_revierte_progreso_y_eventos_conservando_conversaciones` | 0 | 0 | 1 |

### test_registro_v2.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_seguimiento_rechaza_sin_turno_respondible_y_no_escribe` | 0 | 0 | 4 |
| `test_edicion_exige_orden_valido_sin_coercion` | 0 | 0 | 7 |
| `test_pendiente_rechaza_reescritura_inicial_y_orden_de_edicion` | 0 | 0 | 1 |
| `test_turno_vacio_no_evalua_ni_sobrescribe_borrador` | 0 | 0 | 6 |
| `test_borrador_vacio_en_turno_se_retoma_sin_modificar_el_inicial` | 0 | 0 | 1 |
| `test_continuar_descarta_borrador_y_reflexiva_depende_de_turno_enviado` | 0 | 0 | 2 |
| `test_criterio_cumplido_no_puede_reaparecer_en_seguimiento` | 0 | 0 | 1 |
| `test_borrador_del_segundo_turno_no_entra_en_contexto_hasta_el_envio` | 0 | 0 | 1 |
| `test_editar_segundo_turno_preserva_preguntas_y_toda_la_auditoria` | 0 | 0 | 1 |
| `test_otro_final_conserva_pregunta_sin_responder_en_contexto` | 0 | 0 | 1 |
| `test_r14_seguimiento_con_reloj_y_fecha_fijos_descarta_evaluacion` | 0 | 0 | 1 |
| `test_error_al_crear_turno_revierte_respuesta_y_auditoria` | 0 | 0 | 2 |

### test_semilla_instrumentos.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_catalogos_y_estado_inicial_de_instrumentos` | 0 | 0 | 1 |
| `test_escalas_y_puntajes_exactos` | 0 | 0 | 1 |
| `test_rejillas_dimensiones_y_enunciados` | 0 | 0 | 1 |
| `test_items_por_actividad_y_aplicacion` | 0 | 0 | 1 |
| `test_distribucion_rechaza_items_faltantes_repetidos_y_ajenos` | 0 | 0 | 3 |
| `test_excel_valido_conserva_orden_y_valores` | 1 | 0 | 0 |
| `test_excel_rechaza_datos_invalidos` | 8 | 0 | 0 |
| `test_excel_ausente_o_ilegible` | 1 | 0 | 0 |
| `test_relaciones_exigen_todas_las_ocupaciones` | 0 | 0 | 10 |
| `test_medicina_utiliza_el_primero_del_archivo_si_falta_codigo` | 0 | 0 | 1 |
| `test_catalogo_real_y_relaciones_exactas` | 0 | 0 | 1 |
| `test_dos_resultados_vigentes_prohibidos` | 0 | 1 | 0 |
| `test_respuestas_opciones_e_items_unicos` | 0 | 0 | 1 |
| `test_coincidencias_rechazan_ajustes_y_posiciones_invalidas` | 0 | 7 | 0 |
| `test_reinicio_conserva_catalogo_completo` | 0 | 0 | 1 |
| `test_error_de_catalogo_revierte_preparar_base` | 0 | 0 | 3 |
| `test_reinicio_no_depende_del_excel` | 0 | 0 | 1 |

### test_semilla_plataforma.py

| Función | A | B | C |
|---|---:|---:|---:|
| `test_catalogo_estructura_y_estado_vacio` | 1 | 0 | 0 |
| `test_riasec_enunciados_y_distribucion_exactos` | 1 | 0 | 0 |
| `test_cargador_independiente_en_arranque_y_reinicio` | 0 | 0 | 1 |
| `test_excel_erroneo_revierte_carga_explicita` | 3 | 0 | 0 |
| `test_fallo_tardio_revierte_carga_y_conserva_cache` | 1 | 0 | 0 |
| `test_evaluador_rechaza_parametros_invalidos` | 5 | 0 | 0 |
| `test_evaluador_exige_regla_y_sin_camino_es_falso` | 1 | 0 | 0 |
| `test_evaluador_filtra_repeticiones_cuentas_ciudad_y_memoiza_por_umbral` | 1 | 0 | 0 |
| `test_invariantes_desbloqueos_nivel_audiencia_y_eventos` | 1 | 0 | 0 |
| `test_check_in_y_diario_aislados_por_cuenta` | 1 | 0 | 0 |
| `test_carta_se_registra_solo_la_primera_vez_por_cuenta` | 1 | 0 | 0 |

Notas sobre las dos filas con clasificación mixta:

- `test_estado_no_admite_duplicados`: B = ProgresoActividad, CheckIn y
  Desbloqueo. C = EntradaDiario GUIADA y ConversacionVinculo, cuyas filas de
  catálogo referenciadas no existen en plataforma; R38 aporta datos sintéticos.
- `test_resultado_riasec_incluye_las_seis_descripciones_reales`: A =
  aplicacion_plataforma; C = aplicacion (cuatro actividades LAB). Se conserva
  el primer parámetro y se elimina el segundo, ya cubierto por el primero.
