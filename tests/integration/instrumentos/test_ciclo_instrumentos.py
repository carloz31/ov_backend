"""R17, R20 y R22: edición, historia y reinicio selectivo."""

from soporte_datos_ports import preparar_respuesta_ajena
from soporte_plataforma import MARA, actividades, avanzar_camino, completar, filas_base, pedir, responder
from soporte_retiro import ciclo, reiniciar, resultado


def test_r17_editar_hasta_resultado_y_repetir_sin_recalcular(cliente, aplicacion):
    avanzar_camino(cliente)
    responder(cliente, MARA[0])
    completar(cliente, MARA[0])
    responder(cliente, MARA[0], opcion=1)
    assert actividades(cliente)[MARA[0]] == 'COMPLETADA'
    assert all(r['opcion']['orden'] == 1 for r in pedir(cliente, 'GET', f'/cuentas/est-ana/actividades/{MARA[0]}/respuestas')['respuestas'])
    for actividad in MARA[1:]:
        responder(cliente, actividad)
        completar(cliente, actividad)
    obtenido = resultado(cliente)
    antes = filas_base(aplicacion)
    datos = {'cuenta': 'est-ana', 'actividad': MARA[0], 'respuestas': [{'item': 'RIASEC-01', 'opcion': 5}]}
    pedir(cliente, 'POST', '/acciones/responder-items', datos, 409)
    assert filas_base(aplicacion) == antes
    assert completar(cliente, MARA[-1])['resultados_generados'] == []
    assert resultado(cliente) == obtenido
    assert filas_base(aplicacion)['resultado_instrumento'] == antes['resultado_instrumento']


def test_r20_ciclos_planos_historial_vigentes_y_otra_cuenta(cliente, aplicacion):
    ciclo(cliente, cuenta='est-luis')
    ajeno = resultado(cliente, cuenta='est-luis')
    ciclo(cliente, opcion=3)
    grants = filas_base(aplicacion)['desbloqueo']
    for n in range(3):
        historial = pedir(cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-RIASEC/historial')
        assert len(historial) == n+1 and sum(r['anulado_en'] is None for r in historial) == 1
        assert all(r['perfil_plano'] and r['coincidencias'] == [] for r in historial)
        assert resultado(cliente, cuenta='est-luis') == ajeno
        assert filas_base(aplicacion)['desbloqueo'] == grants
        if n < 2:
            reinicio = reiniciar(cliente)
            assert reinicio['resultado_anulado'] is not None
            assert reinicio['actividades_reiniciadas'] == list(MARA)
            pedir(cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado', esperado=409)
            ciclo(cliente, opcion=3, abrir=False)


def test_r22_reinicio_parcial_conserva_respuesta_ajena_y_no_abre(cliente, aplicacion):
    avanzar_camino(cliente)
    responder(cliente, MARA[0], fin=2)
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        preparar_respuesta_ajena(sesion)
    antes = filas_base(aplicacion)
    estados = actividades(cliente)
    reinicio = reiniciar(cliente)
    assert reinicio['resultado_anulado'] is None and reinicio['actividades_reiniciadas'] == [MARA[0]]
    despues = filas_base(aplicacion)
    assert despues['progreso_actividad'] == antes['progreso_actividad']
    assert len(despues['respuesta_item']) == 1 and despues['respuesta_item'][0] == antes['respuesta_item'][-1]
    assert actividades(cliente) == estados
    assert actividades(cliente)[MARA[1]] == 'BLOQUEADA'
