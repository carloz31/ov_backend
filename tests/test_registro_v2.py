"""Casos adicionales del seguimiento v2: transiciones, auditoría y concurrencia."""

import json

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from test_registro import (
    EvaluadorInterviene, FECHA, accion_registro, comprobar_publico, estado_registro,
    fila_respuesta, fotografia, historial_registro, registro_demo, turnos_guardados,
)

from app.services.registro import acciones as acciones_registro


@pytest.mark.parametrize('estado', ['ausente', 'borrador', 'final_sin_turnos', 'final_sin_responder'])
def test_seguimiento_rechaza_sin_turno_respondible_y_no_escribe(cliente, aplicacion, registro_demo, estado):
    if estado == 'borrador':
        assert accion_registro(cliente, 'guardar-borrador').status_code == 200
    elif estado == 'final_sin_turnos':
        assert accion_registro(cliente, 'enviar').status_code == 200
    elif estado == 'final_sin_responder':
        assert accion_registro(cliente, 'enviar', texto='Inicial [vaga]').status_code == 200
        assert accion_registro(cliente, 'continuar-sin-responder').status_code == 200
    antes = fotografia(aplicacion)
    llamadas = len(registro_demo.contextos)
    respuesta = accion_registro(cliente, 'responder-seguimiento', orden=1)
    assert respuesta.status_code == 409
    assert fotografia(aplicacion) == antes and len(registro_demo.contextos) == llamadas


@pytest.mark.parametrize('orden', [None, 0, 3, -1, True, 1.5, '1'])
def test_edicion_exige_orden_valido_sin_coercion(cliente, aplicacion, registro_demo, orden):
    assert accion_registro(cliente, 'enviar', texto='Inicial [vaga]').status_code == 200
    assert accion_registro(cliente, 'responder-seguimiento').status_code == 200
    antes = fotografia(aplicacion)
    respuesta = accion_registro(cliente, 'responder-seguimiento', orden=orden)
    assert respuesta.status_code == 422
    assert fotografia(aplicacion) == antes and len(registro_demo.contextos) == 2


def test_pendiente_rechaza_reescritura_inicial_y_orden_de_edicion(cliente, aplicacion, registro_demo):
    assert accion_registro(cliente, 'enviar', texto='Inicial [vaga]').status_code == 200
    antes = fotografia(aplicacion)
    assert accion_registro(cliente, 'enviar', texto='Reescritura indebida').status_code == 409
    assert accion_registro(cliente, 'responder-seguimiento', orden=1).status_code == 422
    assert fotografia(aplicacion) == antes and len(registro_demo.contextos) == 1


@pytest.mark.parametrize('texto', ['', ' \t\n', '\u2003\u00a0'])
@pytest.mark.parametrize('final', [False, True])
def test_turno_vacio_no_evalua_ni_sobrescribe_borrador(cliente, aplicacion, registro_demo, texto, final):
    assert accion_registro(cliente, 'enviar', texto='Inicial [vaga]').status_code == 200
    assert accion_registro(cliente, 'guardar-borrador', texto='Borrador recuperable').status_code == 200
    if final:
        assert accion_registro(cliente, 'responder-seguimiento').status_code == 200
    antes = fotografia(aplicacion)
    llamadas = len(registro_demo.contextos)
    datos = {'orden': 1} if final else {}
    assert accion_registro(cliente, 'responder-seguimiento', texto=texto, **datos).status_code == 422
    assert fotografia(aplicacion) == antes and len(registro_demo.contextos) == llamadas


def test_borrador_vacio_en_turno_se_retoma_sin_modificar_el_inicial(cliente, aplicacion, registro_demo):
    assert accion_registro(cliente, 'enviar', texto='Inicial [vaga]').status_code == 200
    assert accion_registro(cliente, 'guardar-borrador', texto='').status_code == 200
    conversacion = comprobar_publico(estado_registro(cliente))['respuestas'][0]['conversacion']
    assert conversacion[0]['texto'] == 'Inicial [vaga]'
    assert conversacion[-1] == dict(tipo='respuesta', texto='', orden=1, borrador=True)
    assert turnos_guardados(aplicacion)[0]['respondido_en'] is None and len(registro_demo.contextos) == 1


@pytest.mark.parametrize('respondio_primero', [False, True])
def test_continuar_descarta_borrador_y_reflexiva_depende_de_turno_enviado(
        cliente, aplicacion, registro_demo, respondio_primero):
    primera = accion_registro(cliente, 'enviar', texto='Inicial [vaga]').json()
    if respondio_primero:
        primera = accion_registro(cliente, 'responder-seguimiento', texto='Primer turno [vaga]').json()
    assert accion_registro(cliente, 'guardar-borrador', texto='Todavía no enviar esto').status_code == 200
    historial = historial_registro(cliente).json()
    resultado = comprobar_publico(accion_registro(cliente, 'continuar-sin-responder'))
    assert resultado['estado'] == 'FINAL' and resultado['conversacion'] == primera['conversacion']
    assert len(resultado['eventos_registrados']) == int(respondio_primero)
    assert fila_respuesta(aplicacion)['ampliada'] is respondio_primero
    assert turnos_guardados(aplicacion)[-1]['respuesta'] is None
    assert turnos_guardados(aplicacion)[-1]['respondido_en'] is None
    assert historial_registro(cliente).json() == historial
    antes = fotografia(aplicacion)
    assert accion_registro(cliente, 'continuar-sin-responder').status_code == 409
    assert fotografia(aplicacion) == antes


def test_criterio_cumplido_no_puede_reaparecer_en_seguimiento(cliente, aplicacion, registro_demo):
    assert accion_registro(cliente, 'enviar', texto='Inicial [falta:C2]').status_code == 200
    resultado = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', texto='[falta:C1]'))
    assert resultado['estado'] == 'FINAL' and len(resultado['eventos_registrados']) == 1
    historial = historial_registro(cliente).json()
    assert historial[-1]['origen'] == 'RESPALDO_LONGITUD' and historial[-1]['clasificacion'] == 'NO_EVALUADA'
    assert historial[-1]['pregunta_generada'] is None and historial[-1]['error']
    assert len(turnos_guardados(aplicacion)) == 1


def test_borrador_del_segundo_turno_no_entra_en_contexto_hasta_el_envio(cliente, aplicacion, registro_demo):
    assert accion_registro(cliente, 'enviar', texto='Inicial [falta:C2]').status_code == 200
    assert accion_registro(cliente, 'responder-seguimiento', texto='Primer turno [vaga]').status_code == 200
    assert accion_registro(cliente, 'guardar-borrador', texto='Borrador descartado [falla]').status_code == 200
    historial = historial_registro(cliente).json()
    resultado = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', texto='El jueves'))
    assert resultado['estado'] == 'FINAL'
    contexto = registro_demo.contextos[-1]
    assert [t.respuesta for t in contexto.conversacion.turnos] == ['Primer turno [vaga]', 'El jueves']
    assert 'Borrador descartado' not in repr(contexto)
    assert historial_registro(cliente).json()[:2] == historial
    assert json.loads(historial_registro(cliente).json()[-1]['texto_evaluado'])['turnos'][1]['respuesta'] == 'El jueves'


def test_editar_segundo_turno_preserva_preguntas_y_toda_la_auditoria(cliente, aplicacion, registro_demo):
    assert accion_registro(cliente, 'enviar', texto='Inicial [vaga]').status_code == 200
    for _ in range(2):
        assert accion_registro(cliente, 'responder-seguimiento', texto='Sigo [vaga]').status_code == 200
    antes = turnos_guardados(aplicacion)
    historial = historial_registro(cliente).json()
    resultado = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', orden=2, texto='Edición [falla]'))
    assert resultado['eventos_registrados'] == resultado['nuevos_desbloqueos'] == []
    despues = turnos_guardados(aplicacion)
    assert despues[0] == antes[0]
    assert despues[1] == {**antes[1], 'respuesta': 'Edición [falla]'}
    assert historial_registro(cliente).json() == historial and len(registro_demo.contextos) == 3


def test_otro_final_conserva_pregunta_sin_responder_en_contexto(cliente, registro_demo):
    primera = accion_registro(cliente, 'enviar', texto='Inicial [vaga]').json()
    assert accion_registro(cliente, 'guardar-borrador', texto='Borrador que no se envió').status_code == 200
    assert accion_registro(cliente, 'continuar-sin-responder').status_code == 200
    assert accion_registro(cliente, 'enviar', item='REG-HAB-2', texto='Nueva respuesta').status_code == 200
    anterior = registro_demo.contextos[-1].respuestas_anteriores[0].conversacion
    assert anterior.texto_inicial == 'Inicial [vaga]'
    assert [(t.pregunta, t.respuesta) for t in anterior.turnos] == [(primera['conversacion'][1]['texto'], None)]
    assert 'Borrador que no se envió' not in repr(registro_demo.contextos[-1])


def test_r14_seguimiento_con_reloj_y_fecha_fijos_descarta_evaluacion(cliente, aplicacion, registro_demo, monkeypatch):
    class RelojFijo(acciones_registro.datetime):
        @classmethod
        def now(cls, tz=None):
            return FECHA.replace(tzinfo=tz)
    monkeypatch.setattr(acciones_registro, 'datetime', RelojFijo)
    assert accion_registro(cliente, 'enviar', texto='Inicial [vaga]').status_code == 200
    marca = fila_respuesta(aplicacion)['actualizada_en']
    def intervenir():
        assert accion_registro(cliente, 'guardar-borrador', texto='Borrador paralelo').status_code == 200
    aplicacion.state.evaluador_respuestas = EvaluadorInterviene(intervenir)
    historial = historial_registro(cliente).json()
    assert accion_registro(cliente, 'responder-seguimiento', texto='Respuesta original [vaga]').status_code == 409
    assert turnos_guardados(aplicacion)[0]['respuesta'] == 'Borrador paralelo'
    assert turnos_guardados(aplicacion)[0]['respondido_en'] is None
    assert (fila_respuesta(aplicacion)['actualizada_en'] - marca).total_seconds() == 0.000001
    assert historial_registro(cliente).json() == historial


@pytest.mark.parametrize('seguimiento', [False, True])
def test_error_al_crear_turno_revierte_respuesta_y_auditoria(cliente, aplicacion, registro_demo, seguimiento):
    if seguimiento:
        assert accion_registro(cliente, 'enviar', texto='Inicial [vaga]').status_code == 200
    antes = fotografia(aplicacion)
    def fallar(conexion, cursor, sentencia, parametros, contexto_sql, muchos):
        if sentencia.startswith('INSERT INTO turno_seguimiento '):
            raise IntegrityError('Fallo simulado', {}, Exception('Detalle interno'))
    event.listen(aplicacion.state.motor_bd, 'after_cursor_execute', fallar)
    try:
        resultado = accion_registro(cliente, 'responder-seguimiento' if seguimiento else 'enviar', texto='Texto [vaga]')
    finally:
        event.remove(aplicacion.state.motor_bd, 'after_cursor_execute', fallar)
    assert resultado.status_code == 409 and 'Detalle interno' not in resultado.text
    assert fotografia(aplicacion) == antes
