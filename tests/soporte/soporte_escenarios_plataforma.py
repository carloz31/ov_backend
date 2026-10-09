"""Verificadores de escenarios compartidos entre SQLite y PostgreSQL."""

from soporte_plataforma import CAMINO, MARA, actividades, avanzar_camino, completar, estado, pedir, reglas, responder


def verificar_p01_estado_inicial(cliente):
    inicial = estado(cliente)
    estados = actividades(cliente)
    assert estados['mission-welcome'] == 'DISPONIBLE'
    assert all(estados[c] == 'BLOQUEADA' for c in CAMINO[1:] + MARA + ('act-tip-final',))
    assert {b['codigo']: b['estado'] for b in inicial['bloques']} == {'CAMINO': 'DISPONIBLE', 'CIUDAD': 'BLOQUEADA'}
    assert len(inicial['fichas']) == 4 and all(f['estado'] == 'BLOQUEADA' for f in inicial['fichas'])
    visibles = {i['codigo']: i for i in inicial['insignias'] if i['codigo'] != '???'}
    assert set(visibles) == {f'I{n}' for n in range(1, 10)}
    assert all(i['estado'] == 'BLOQUEADA' and i['requisito'] for i in visibles.values())
    oculto, = [i for i in inicial['insignias'] if i['codigo'] == '???']
    assert oculto['estado'] == 'BLOQUEADA' and oculto['requisito'] is None
    assert inicial['conversaciones']['estado'] == 'BLOQUEADA'
    assert inicial['nivel_actual']['numero'] == 1
    assert inicial['testimonios'] == inicial['preguntas_diario'] == []


def verificar_p02_primer_paso(cliente):
    assert reglas(completar(cliente, 'mission-welcome')) == {'R-enc-mitos', 'R-first-steps', 'R-I1'}


def verificar_p07_llegada_a_la_ciudad(cliente):
    respuesta = avanzar_camino(cliente)
    assert [(e['tipo'], e['referencia']) for e in respuesta['eventos_registrados']] == [
        ('COMPLETA_ACTIVIDAD', 'mission-next-step'), ('COMPLETA_BLOQUE', 'CAMINO'),
    ]
    assert reglas(respuesta) == {'R-ciudad', 'R-I3', 'R-NIV-3', 'R-FAM-ESTUDIANTE'}
    estados = actividades(cliente)
    assert estados['act-tip-01'] == 'DISPONIBLE'
    assert all(estados[c] == 'BLOQUEADA' for c in MARA[1:] + ('act-tip-final',))
    assert estado(cliente)['nivel_actual']['numero'] == 3


def verificar_p10_resultado(cliente):
    avanzar_camino(cliente)
    for actividad in MARA:
        responder(cliente, actividad)
        respuesta = completar(cliente, actividad)
        if actividad != 'act-tip-14':
            assert respuesta['resultados_generados'] == []
    assert respuesta['resultados_generados'] == [{'instrumento': 'TEST-RIASEC', 'aplicacion': 'APL-RIASEC'}]
    assert reglas(respuesta) == {'R-act-tip-final'}
    resultado = pedir(cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado')
    assert {d['codigo']: d['porcentaje'] for d in resultado['dimensiones']} == {'I': 100, 'R': 75, 'A': 50, 'S': 0, 'E': 0, 'C': 0}
    assert resultado['codigo_interes'] == {'codigo': 'IRA', 'hay_empate': False}
    coincidencias = resultado['coincidencias']
    assert len(coincidencias) == 10 and all(c['codigo'] for c in coincidencias)
    assert [c['posicion'] for c in coincidencias] == list(range(1, 11))
    assert [c['correlacion'] for c in coincidencias] == sorted((c['correlacion'] for c in coincidencias), reverse=True)
    assert coincidencias[0]['codigo'] == 'geologist' and coincidencias[0]['ajuste'] == 'BEST_FIT'
    carreras = resultado['carreras_recomendadas']
    assert {c['codigo'] for c in carreras} == {'environmental-engineering', 'civil-engineering', 'veterinary-medicine'}
    assert all(c['via'] and all(v in coincidencias for v in c['via']) for c in carreras)
