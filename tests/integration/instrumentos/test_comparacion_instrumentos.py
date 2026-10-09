"""R27–R28: comparación por momentos y reinicio de salida."""

from app import models as m
from soporte_plataforma import filas_base, pedir
from soporte_retiro import buscar, contestar_minimo, instrumento_minimo, reiniciar


def test_r27_comparacion_generica_sin_resultado_y_momentos_requeridos(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        entrada, salida = instrumento_minimo(sesion, 'COMPARACION')
    ruta = '/cuentas/est-ana/instrumentos/TEST-PRUEBA/comparacion'
    pedir(cliente, 'GET', ruta, esperado=409)
    for actividad, opciones in [(entrada, [1, 2, 3]), (salida, [4, 3, 5])]:
        assert contestar_minimo(cliente, actividad, opciones)['resultados_generados'] == []
    comparacion = pedir(cliente, 'GET', ruta)
    assert comparacion['entrada'] == 'APL-PRUEBA-ENTRADA' and comparacion['salida'] == 'APL-PRUEBA-SALIDA'
    assert [i['diferencia'] for i in comparacion['items']] == [3, 1, 2]
    assert filas_base(aplicacion)['resultado_instrumento'] == []
    pedir(cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-RIASEC/comparacion', esperado=404)
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        buscar(sesion, m.Aplicacion, 'APL-PRUEBA-SALIDA').momento = 'UNICA'
    pedir(cliente, 'GET', ruta, esperado=422)


def test_r28_reiniciar_salida_conserva_entrada_y_exige_seleccion(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        entrada, salida = instrumento_minimo(sesion, 'COMPARACION')
    for actividad in (entrada, salida):
        contestar_minimo(cliente, actividad)
    antes = pedir(cliente, 'GET', f'/cuentas/est-ana/actividades/{entrada}/respuestas')
    reiniciar(cliente, instrumento='TEST-PRUEBA', esperado=422)
    reinicio = reiniciar(cliente, instrumento='TEST-PRUEBA', seleccion='APL-PRUEBA-SALIDA')
    assert reinicio['resultado_anulado'] is None and reinicio['actividades_reiniciadas'] == [salida]
    assert pedir(cliente, 'GET', f'/cuentas/est-ana/actividades/{entrada}/respuestas') == antes
    assert pedir(cliente, 'GET', f'/cuentas/est-ana/actividades/{salida}/respuestas')['respuestas'] == []
    pedir(cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-PRUEBA/comparacion', esperado=409)
