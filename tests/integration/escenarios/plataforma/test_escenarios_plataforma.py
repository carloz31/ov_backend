"""P1–P16 de §4.6; cada escenario usa una base independiente."""

import soporte_escenarios_plataforma as escenarios


from soporte_plataforma import (
    CAMINO, FECHA, MARA, actividades, avanzar_camino, completar, estado,
    eventos, filas_base, pedir, progreso, reglas, responder,
)



def test_p01_estado_inicial(cliente):
    escenarios.verificar_p01_estado_inicial(cliente)


def test_p02_primer_paso(cliente):
    escenarios.verificar_p02_primer_paso(cliente)


def test_p03_saltarse_la_ruta(cliente, aplicacion):
    antes = filas_base(aplicacion)
    rechazo = completar(cliente, 'act-07', esperado=409)['detail']['progreso']
    regla, = rechazo['reglas']
    assert regla['regla'] == 'R-act-07'
    assert regla['condiciones'][0]['actual'] == 0 and regla['condiciones'][0]['requerido'] == 1
    assert filas_base(aplicacion) == antes
    assert eventos(cliente) == []


def test_p04_informativa_con_fichas(cliente):
    completar(cliente, 'mission-welcome')
    assert reglas(completar(cliente, 'enc-mitos')) == {
        'R-act-07', 'R-ficha-mitos', 'R-rec-ponteencarrera', 'R-rec-unesco-stem',
    }


def test_p05_repetir_no_suma(cliente):
    avanzar_camino(cliente, 'enc-mitos')
    antes = len(eventos(cliente))
    for _ in range(3):
        respuesta = completar(cliente, 'enc-mitos')
        assert respuesta['nuevos_desbloqueos'] == []
        assert [(e['tipo'], e['referencia']) for e in respuesta['eventos_registrados']] == [('COMPLETA_ACTIVIDAD', 'enc-mitos')]
    assert len(eventos(cliente)) == antes + 3
    assert progreso(cliente, 'INSIGNIA', 'I2')['reglas'][0]['evaluador_especial']['cumplido'] is False
    assert actividades(cliente)['enc-mitos'] == 'COMPLETADA'


def test_p06_un_evento_varios_desbloqueos(cliente):
    avanzar_camino(cliente, 'act-07')
    assert reglas(completar(cliente, 'mission-story')) == {'R-mission-future', 'R-I2', 'R-NIV-2'}
    assert estado(cliente)['nivel_actual']['numero'] == 2


def test_p07_llegada_a_la_ciudad(cliente):
    escenarios.verificar_p07_llegada_a_la_ciudad(cliente)


def test_p08_cuestionario_incompleto(cliente, aplicacion):
    avanzar_camino(cliente)
    respuesta = responder(cliente, 'act-tip-01', fin=3)
    assert respuesta['progreso'] == {'estado': 'EN_CURSO', 'respondidos': 3, 'total': 5}
    antes = filas_base(aplicacion)
    assert completar(cliente, 'act-tip-01', esperado=409)['detail']['items_faltantes'] == ['RIASEC-04', 'RIASEC-05']
    assert filas_base(aplicacion) == antes
    assert actividades(cliente)['act-tip-01'] == 'EN_CURSO'


def test_p09_retomar(cliente):
    avanzar_camino(cliente)
    responder(cliente, 'act-tip-01', fin=3)
    guardadas = pedir(cliente, 'GET', '/cuentas/est-ana/actividades/act-tip-01/respuestas')['respuestas']
    assert [(r['item'], r['opcion']['orden']) for r in guardadas] == [('RIASEC-01', 4), ('RIASEC-02', 4), ('RIASEC-03', 5)]
    responder(cliente, 'act-tip-01', inicio=3)
    respuesta = completar(cliente, 'act-tip-01')
    assert reglas(respuesta) == {'R-act-tip-02'} and respuesta['resultados_generados'] == []


def test_p10_resultado(cliente):
    escenarios.verificar_p10_resultado(cliente)


def test_p11_perfil_plano(cliente):
    avanzar_camino(cliente, cuenta='est-luis')
    for actividad in MARA:
        responder(cliente, actividad, cuenta='est-luis', opcion=3)
        completar(cliente, actividad, cuenta='est-luis')
    resultado = pedir(cliente, 'GET', '/cuentas/est-luis/instrumentos/TEST-RIASEC/resultado')
    assert resultado['perfil_plano'] is True
    assert resultado['coincidencias'] == resultado['carreras_recomendadas'] == []


def test_p12_avisos(cliente):
    avanzar_camino(cliente)
    ruta = '/cuentas/est-ana/desbloqueos?solo_no_vistos=true'
    no_vistos = pedir(cliente, 'GET', ruta)
    assert no_vistos and all(d['visto'] is False for d in no_vistos)
    assert pedir(cliente, 'POST', '/cuentas/est-ana/desbloqueos/marcar-vistos')['marcados'] == len(no_vistos)
    assert pedir(cliente, 'GET', ruta) == []


def test_p13_progreso_de_lo_bloqueado(cliente):
    completar(cliente, 'mission-welcome')
    ciudad = progreso(cliente, 'BLOQUE', 'CIUDAD')['reglas'][0]['condiciones'][0]
    assert (ciudad['tipo_evento'], ciudad['referencia'], ciudad['actual'], ciudad['requerido']) == ('COMPLETA_BLOQUE', 'CAMINO', 0, 1)
    insignia = progreso(cliente, 'INSIGNIA', 'I2')['reglas'][0]
    assert insignia['condiciones'][0]['cumplida'] is True
    assert insignia['evaluador_especial'] == {'nombre': 'misiones_camino_sin_inicio', 'cumplido': False}
    cierre = progreso(cliente, 'ACTIVIDAD', 'act-tip-final')['reglas'][0]['condiciones'][0]
    assert (cierre['referencia'], cierre['actual'], cierre['requerido']) == ('act-tip-14', 0, 1)


def test_p14_audiencia(cliente):
    rosa = estado(cliente, 'apo-rosa')
    assert rosa['bloques'] == rosa['fichas'] == rosa['insignias'] == []
    assert rosa['nivel_actual'] is None


def test_p16_eventos_nuevos(cliente):
    for evento, insignia in (('INVITA_A_CREW', 'I4'), ('FORMA_CREW', 'I5'), ('VENCE_DESAFIO_INTACTO', 'I10')):
        respuesta = pedir(cliente, 'POST', '/eventos', {'cuenta': 'est-ana', 'tipo': evento, 'fecha_hora': FECHA})
        assert reglas(respuesta) == {f'R-{insignia}'}
        assert respuesta['eventos_registrados'] == [{'tipo': evento, 'referencia': None, 'fecha_hora': FECHA}]
    oculto, = [i for i in estado(cliente)['insignias'] if i['codigo'] == 'I10']
    assert oculto['estado'] == 'OBTENIDA' and oculto['nombre'] == 'Luz sin fisuras'
    assert oculto['requisito'] == 'Vence al enemigo sin perder destellos en tu primera victoria.'
