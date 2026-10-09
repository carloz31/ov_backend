"""R25–R26: cálculo y presentación siguen metadatos persistidos."""

from soporte_datos_ports import renombrar_e_invertir_dimensiones
from soporte_retiro import ciclo, contestar_minimo, instrumento_minimo, resultado


def test_r25_coincidencias_tipo_y_orden_independientes_del_codigo(tmp_path, base_aislada):
    for plano in (False, True):
        with base_aislada(tmp_path, f'metadatos-{plano}') as (aplicacion, cliente):
            with aplicacion.state.fabrica_sesiones.begin() as sesion:
                renombrar_e_invertir_dimensiones(sesion)
            ciclo(cliente, opcion=3 if plano else None)
            obtenido = resultado(cliente, instrumento='TEST-RENOMBRADO')
            assert [d['codigo'] for d in obtenido['dimensiones']] == list('CESAIR')
            assert obtenido['codigo_interes'] == {'codigo': 'CES' if plano else 'IRA', 'hay_empate': plano}
            assert obtenido['perfil_plano'] == plano
            assert (obtenido['coincidencias'] == []) == plano


def test_r26_destacadas_genericas_inversos_empates_y_cero(tmp_path, base_aislada):
    variantes = [([5, 5, 1], ['DIM-A'], [100, 0, 0]),
                ([5, 1, 1], ['DIM-A', 'DIM-B'], [100, 100, 0]),
                ([1, 5, 1], ['DIM-A', 'DIM-B', 'DIM-C'], [0, 0, 0])]
    for n, (opciones, destacadas, porcentajes) in enumerate(variantes):
        with base_aislada(tmp_path, f'destacadas-{n}') as (aplicacion, cliente):
            with aplicacion.state.fabrica_sesiones.begin() as sesion:
                actividad, = instrumento_minimo(sesion)
            salida = contestar_minimo(cliente, actividad, opciones)
            assert salida['resultados_generados'] == [{'instrumento': 'TEST-PRUEBA', 'aplicacion': 'APL-PRUEBA-UNICA'}]
            obtenido = resultado(cliente, instrumento='TEST-PRUEBA')
            assert [d['porcentaje'] for d in obtenido['dimensiones']] == porcentajes
            assert [d['codigo'] for d in obtenido['dimensiones_destacadas']] == destacadas
            assert 'codigo_interes' not in obtenido and 'coincidencias' not in obtenido
