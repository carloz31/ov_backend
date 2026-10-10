"""Actividades del apoderado en plataforma y piloto (§4.3)."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from soporte_plataforma import BLOQUE_FAMILIA, FECHA, completar, estado, eventos, pedir


@pytest.fixture(params=['aplicacion', 'aplicacion_piloto'], ids=['plataforma', 'piloto'])
def cliente_apoderado(request):
    with TestClient(request.getfixturevalue(request.param)) as cliente:
        yield cliente


def actividades(cliente, cuenta='apo-rosa'):
    return pedir(cliente, 'GET', f'/cuentas/{cuenta}/actividades')


def test_familia_inicial_visible_y_separada_del_estudiante(cliente_apoderado):
    cliente = cliente_apoderado
    assert actividades(cliente) == [BLOQUE_FAMILIA]
    assert [b['codigo'] for b in actividades(cliente, 'est-ana')] == ['CAMINO', 'CIUDAD']
    assert eventos(cliente, 'apo-rosa') == []


def test_segunda_bloqueada_no_escribe_estado_ni_eventos(cliente_apoderado):
    cliente = cliente_apoderado
    antes = estado(cliente, 'apo-rosa')
    rechazo = completar(cliente, 'pad-02-info', 'apo-rosa', esperado=409)
    condicion, = rechazo['detail']['progreso']['reglas'][0]['condiciones']
    assert (condicion['referencia'], condicion['actual'], condicion['requerido']) == ('pad-01-rol', 0, 1)
    assert estado(cliente, 'apo-rosa') == antes
    assert eventos(cliente, 'apo-rosa') == []


def test_primera_desbloquea_solo_la_segunda(cliente_apoderado):
    cliente = cliente_apoderado
    respuesta = completar(cliente, 'pad-01-rol', 'apo-rosa')
    assert respuesta['eventos_registrados'] == [
        {'tipo': 'COMPLETA_ACTIVIDAD', 'referencia': 'pad-01-rol', 'fecha_hora': FECHA},
    ]
    assert [(d['regla'], d['tipo_objetivo'], d['objetivo']['codigo']) for d in respuesta['nuevos_desbloqueos']] == [
        ('R-pad-02-info', 'ACTIVIDAD', 'pad-02-info'),
    ]
    assert respuesta['resultados_generados'] == []
    esperado = deepcopy(BLOQUE_FAMILIA)
    esperado['actividades'][0]['estado'] = 'COMPLETADA'
    esperado['actividades'][1]['estado'] = 'DISPONIBLE'
    assert actividades(cliente) == [esperado]


def test_segunda_completa_familia_sin_nuevos_desbloqueos(cliente_apoderado):
    cliente = cliente_apoderado
    completar(cliente, 'pad-01-rol', 'apo-rosa')
    respuesta = completar(cliente, 'pad-02-info', 'apo-rosa')
    assert respuesta['eventos_registrados'] == [
        {'tipo': 'COMPLETA_ACTIVIDAD', 'referencia': 'pad-02-info', 'fecha_hora': FECHA},
        {'tipo': 'COMPLETA_BLOQUE', 'referencia': 'FAMILIA', 'fecha_hora': FECHA},
    ]
    assert respuesta['nuevos_desbloqueos'] == respuesta['resultados_generados'] == []
    assert [a['estado'] for a in actividades(cliente)[0]['actividades']] == ['COMPLETADA', 'COMPLETADA']


def test_repeticiones_no_duplican_el_evento_del_bloque(cliente_apoderado):
    cliente = cliente_apoderado
    for codigo in ('pad-01-rol', 'pad-02-info'):
        completar(cliente, codigo, 'apo-rosa')
    for codigo in ('pad-01-rol', 'pad-02-info'):
        respuesta = completar(cliente, codigo, 'apo-rosa')
        assert respuesta['eventos_registrados'] == [
            {'tipo': 'COMPLETA_ACTIVIDAD', 'referencia': codigo, 'fecha_hora': FECHA},
        ]
        assert respuesta['nuevos_desbloqueos'] == []
    historial = eventos(cliente, 'apo-rosa')
    assert sum(e['tipo'] == 'COMPLETA_BLOQUE' and e['referencia'] == 'FAMILIA' for e in historial) == 1
    assert sum(e['tipo'] == 'COMPLETA_ACTIVIDAD' for e in historial) == 4
    assert [a['estado'] for a in actividades(cliente)[0]['actividades']] == ['COMPLETADA', 'COMPLETADA']


def test_otras_audiencias_se_rechazan_sin_efectos(cliente_apoderado):
    cliente = cliente_apoderado
    for cuenta, codigo in (('est-ana', 'pad-01-rol'), ('apo-rosa', 'mission-welcome')):
        antes = estado(cliente, cuenta)
        completar(cliente, codigo, cuenta, esperado=409)
        assert estado(cliente, cuenta) == antes
        assert eventos(cliente, cuenta) == []


def test_completar_no_otorga_logros_niveles_fichas_ni_afecta_al_estudiante(cliente_apoderado):
    cliente = cliente_apoderado
    estudiante = estado(cliente)
    for codigo in ('pad-01-rol', 'pad-02-info', 'pad-01-rol', 'pad-02-info'):
        respuesta = completar(cliente, codigo, 'apo-rosa')
        assert {d['regla'] for d in respuesta['nuevos_desbloqueos']} <= {'R-pad-02-info'}
        assert respuesta['resultados_generados'] == []
        rosa = estado(cliente, 'apo-rosa')
        assert rosa['nivel_actual'] is None
        assert rosa['niveles'] == rosa['insignias'] == rosa['fichas'] == []
        assert estado(cliente) == estudiante
    assert eventos(cliente) == []
    assert {d['regla'] for d in pedir(cliente, 'GET', '/cuentas/apo-rosa/desbloqueos')} == {'R-pad-02-info'}
