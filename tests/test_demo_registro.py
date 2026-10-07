"""La nueva página y sus recursos sirven contenido sin modificar el registro."""

import re

from sqlalchemy import func, select

from app.models import EvaluacionRespuesta, EventoUso, ProgresoActividad, RespuestaRegistro


def test_pagina_registro_recursos_y_enlace_sin_sql_ni_escrituras(cliente, aplicacion, contador_consultas):
    datos = {'cuenta': 'est-ana', 'actividad': 'REG-ACT08'}
    assert cliente.post('/acciones/guardar-posicion', json={**datos, 'posicion': 'plan'}).status_code == 200
    assert cliente.post('/acciones/registro/enviar', json={**datos, 'item': 'REG-HAB-1', 'texto': 'Asertividad'}).status_code == 200
    registro_antes = cliente.get('/cuentas/est-ana/actividades/REG-ACT08/registro').json()
    auditoria_antes = cliente.get('/demo/registro/est-ana/REG-ACT08/evaluaciones').json()
    eventos_antes = cliente.get('/cuentas/est-ana/eventos').json()
    llamadas_antes = len(aplicacion.state.evaluador_respuestas.contextos)
    with contador_consultas(aplicacion.state.motor_bd) as contador:
        pagina = cliente.get('/demo/registro')
        assert pagina.status_code == 200
        assert pagina.headers['content-type'].startswith('text/html')
        assert '<html lang="es">' in pagina.text
        recursos = re.findall(r'(?:src|href)="(/demo/recursos/[^\"]+)"', pagina.text)
        assert len(recursos) == 3
        for recurso in recursos:
            respuesta = cliente.get(recurso)
            assert respuesta.status_code == 200
            assert respuesta.content
        assert cliente.get('/demo/recursos/contenido/REG-ACT08.json').status_code == 200
        assert 'href="/demo/registro"' in cliente.get('/demo').text
    assert contador.cantidad == 0
    assert cliente.get('/cuentas/est-ana/actividades/REG-ACT08/registro').json() == registro_antes
    assert cliente.get('/demo/registro/est-ana/REG-ACT08/evaluaciones').json() == auditoria_antes
    assert cliente.get('/cuentas/est-ana/eventos').json() == eventos_antes
    assert len(aplicacion.state.evaluador_respuestas.contextos) == llamadas_antes
    assert '/demo/registro' not in cliente.get('/openapi.json').json()['paths']


def test_reinicio_limpia_registros_de_ambas_cuentas_y_permite_primer_envio(cliente, aplicacion):
    datos = {'cuenta': 'est-ana', 'actividad': 'REG-ACT08'}
    adecuada = 'Quiero expresar mi opinión porque en los trabajos grupales me quedo callada.'
    assert cliente.post('/acciones/guardar-posicion', json={**datos, 'posicion': 'plan'}).status_code == 200
    assert cliente.post('/acciones/registro/enviar', json={**datos, 'item': 'REG-HAB-1', 'texto': adecuada}).status_code == 200
    assert cliente.post('/acciones/registro/guardar-borrador', json={**datos, 'item': 'REG-HAB-2', 'texto': 'Mi borrador'}).status_code == 200
    assert cliente.post('/acciones/registro/enviar', json={**datos, 'item': 'REG-HAB-3', 'texto': 'Mejoraré'}).status_code == 200
    luis = {**datos, 'cuenta': 'est-luis'}
    assert cliente.post('/acciones/guardar-posicion', json={**luis, 'posicion': 'plan'}).status_code == 200
    assert cliente.post('/acciones/registro/enviar', json={**luis, 'item': 'REG-HAB-1', 'texto': 'Asertividad'}).status_code == 200
    evaluador = aplicacion.state.evaluador_respuestas
    configuracion = aplicacion.state.configuracion_registro
    llamadas = len(evaluador.contextos)

    assert cliente.post('/demo/reiniciar', json={}).status_code == 200

    for cuenta in ('est-ana', 'est-luis'):
        registro = cliente.get(f'/cuentas/{cuenta}/actividades/REG-ACT08/registro').json()
        assert registro['posicion'] is None and registro['estado'] is None
        assert registro['respuestas'] == []
        assert cliente.get(f'/demo/registro/{cuenta}/REG-ACT08/evaluaciones').json() == []
        assert cliente.get(f'/cuentas/{cuenta}/eventos').json() == []
    with aplicacion.state.fabrica_sesiones() as sesion:
        for tabla in (RespuestaRegistro, EvaluacionRespuesta, ProgresoActividad, EventoUso):
            assert sesion.scalar(select(func.count()).select_from(tabla)) == 0
    assert aplicacion.state.evaluador_respuestas is evaluador
    assert aplicacion.state.configuracion_registro is configuracion
    assert len(evaluador.contextos) == llamadas
    assert len(cliente.get('/actividades/REG-ACT08/items-registro').json()) == 3

    assert cliente.post('/acciones/registro/enviar', json={**datos, 'item': 'REG-HAB-1', 'texto': adecuada}).status_code == 200
    evaluaciones = cliente.get('/demo/registro/est-ana/REG-ACT08/evaluaciones').json()
    assert len(evaluaciones) == 1 and evaluaciones[0]['numero'] == 1
    assert evaluador.contextos[-1].respuestas_anteriores == ()
