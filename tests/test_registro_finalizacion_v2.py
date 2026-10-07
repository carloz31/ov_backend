"""Integración de conversaciones v2 con completar y el motor (R13b/R13c)."""

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from test_registro import (
    CODIGOS_ITEMS, FECHA, accion_registro, comprobar_publico, completar_registro,
    estado_registro, fila_respuesta, fotografia, historial_registro, registro_demo,
    turnos_guardados,
)


@pytest.mark.parametrize('pendiente', ['borrador', 'generico', 'turno_1', 'turno_2'])
def test_r13b_pendiente_impide_completar_sin_escrituras_y_luego_finaliza(
        cliente, aplicacion, registro_demo, contador_consultas, pendiente):
    for item in CODIGOS_ITEMS[:2]:
        assert accion_registro(cliente, 'enviar', item=item).status_code == 200
    item = 'REG-HAB-3'
    if pendiente == 'borrador':
        assert accion_registro(cliente, 'guardar-borrador', item=item).status_code == 200
    else:
        inicial = 'Corto [falla]' if pendiente == 'generico' else 'Inicial [vaga]'
        assert accion_registro(cliente, 'enviar', item=item, texto=inicial).status_code == 200
        if pendiente == 'turno_2':
            assert accion_registro(cliente, 'responder-seguimiento', item=item,
                                  texto='Primer turno [vaga]').status_code == 200
        assert accion_registro(cliente, 'guardar-borrador', item=item,
                              texto='Todavía estoy pensando').status_code == 200
    antes = fotografia(aplicacion)
    llamadas = len(registro_demo.contextos)
    with contador_consultas(aplicacion.state.motor_bd) as contador:
        rechazada = completar_registro(cliente)
    assert rechazada.status_code == 409
    assert rechazada.json()['detail'] == {
        'mensaje': 'Faltan ítems de registro por finalizar', 'items_faltantes': [item]}
    assert all(e.sentencia.lstrip().upper().startswith('SELECT') for e in contador.ejecuciones)
    assert fotografia(aplicacion) == antes and len(registro_demo.contextos) == llamadas

    accion = 'enviar' if pendiente == 'borrador' else 'responder-seguimiento'
    assert accion_registro(cliente, accion, item=item).json()['estado'] == 'FINAL'
    finales = fotografia(aplicacion)
    llamadas = len(registro_demo.contextos)
    resultado = comprobar_publico(completar_registro(cliente))
    assert resultado['eventos_registrados'] == [
        {'tipo': 'COMPLETA_ACTIVIDAD', 'referencia': 'REG-ACT08', 'fecha_hora': FECHA.isoformat()},
        {'tipo': 'COMPLETA_BLOQUE', 'referencia': 'REG', 'fecha_hora': FECHA.isoformat()},
    ]
    assert resultado['resultados_generados'] == []
    assert estado_registro(cliente).json()['estado'] == 'COMPLETADA'
    despues = fotografia(aplicacion)
    for tabla in ('respuesta_registro', 'turno_seguimiento', 'evaluacion_respuesta'):
        assert despues[tabla] == finales[tabla]
    assert len(registro_demo.contextos) == llamadas


@pytest.mark.parametrize('salida', ['vaga', 'fallo', 'atencion', 'continuar'])
def test_completar_acepta_finalizacion_del_segundo_turno_y_conserva_la_conversacion(
        cliente, aplicacion, registro_demo, salida):
    for item in CODIGOS_ITEMS[:2]:
        assert accion_registro(cliente, 'enviar', item=item).status_code == 200
    item = 'REG-HAB-3'
    assert accion_registro(cliente, 'enviar', item=item, texto='Inicial [vaga]').status_code == 200
    assert accion_registro(cliente, 'responder-seguimiento', item=item,
                          texto='Primer turno [vaga]').status_code == 200
    if salida == 'continuar':
        assert accion_registro(cliente, 'guardar-borrador', item=item,
                              texto='Borrador sin enviar').status_code == 200
        final = accion_registro(cliente, 'continuar-sin-responder', item=item)
    else:
        marcador = {'vaga': '[vaga]', 'fallo': '[falla]', 'atencion': '[atencion]'}[salida]
        final = accion_registro(cliente, 'responder-seguimiento', item=item, texto='Segundo turno ' + marcador)
    assert comprobar_publico(final)['estado'] == 'FINAL'
    respuesta = fila_respuesta(aplicacion, item=item)
    assert respuesta['clasificacion_inicial'] == 'VAGA' and respuesta['ampliada'] is True
    assert len(turnos_guardados(aplicacion, item=item)) == 2
    antes = fotografia(aplicacion)
    conversacion = estado_registro(cliente).json()['respuestas']
    llamadas = len(registro_demo.contextos)
    assert completar_registro(cliente).status_code == 200
    despues = fotografia(aplicacion)
    for tabla in ('respuesta_registro', 'turno_seguimiento', 'evaluacion_respuesta'):
        assert despues[tabla] == antes[tabla]
    assert estado_registro(cliente).json()['respuestas'] == conversacion
    assert estado_registro(cliente).json()['estado'] == 'COMPLETADA'
    assert len(registro_demo.contextos) == llamadas


def test_r13c_seguimientos_generan_tres_reflexivas_y_un_solo_logro(
        cliente, aplicacion, registro_demo):
    antes = fotografia(aplicacion)
    for numero, item in enumerate(CODIGOS_ITEMS, start=1):
        inicial = 'Corto [falla]' if numero == 1 else 'Inicial [vaga]'
        pendiente = comprobar_publico(accion_registro(cliente, 'enviar', item=item, texto=inicial))
        assert pendiente['eventos_registrados'] == [] and pendiente['nuevos_desbloqueos'] == []
        if numero == 3:
            pendiente = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', item=item,
                                                         texto='Primer turno [vaga]'))
            assert pendiente['eventos_registrados'] == [] and pendiente['nuevos_desbloqueos'] == []
        final = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', item=item))
        assert final['eventos_registrados'] == [
            {'tipo': 'RESPUESTA_REFLEXIVA', 'referencia': None, 'fecha_hora': FECHA.isoformat()}]
        assert len(final['nuevos_desbloqueos']) == int(numero == 3)
        if numero == 3:
            logro = final['nuevos_desbloqueos'][0]
            assert logro['objetivo']['codigo'] == 'LOG-PENSADOR' and logro['regla'] == 'R-LOG-PENSADOR'
            assert logro['condiciones'] == [{
                'tipo_evento': 'RESPUESTA_REFLEXIVA', 'referencia': None, 'tipo_conteo': 'EVENTOS',
                'actual': 3, 'requerido': 3, 'cumplida': True}]
        fila = fila_respuesta(aplicacion, item=item)
        assert fila['clasificacion_inicial'] == 'VAGA' and fila['ampliada'] is True
    for _ in range(2):
        assert completar_registro(cliente).json()['nuevos_desbloqueos'] == []
    despues = fotografia(aplicacion)
    for tabla in ('regla_desbloqueo', 'condicion_desbloqueo'):
        assert despues[tabla] == antes[tabla]
    reflexivas = [e for e in despues['evento_uso'] if e.tipo == 'RESPUESTA_REFLEXIVA']
    assert len(reflexivas) == 3 and all(e.id_referencia is None for e in reflexivas)
    assert len(despues['desbloqueo']) == 1


def test_rehacer_conserva_turnos_respondidos_y_omitidos_y_permite_editar_sin_reevaluar(
        cliente, aplicacion, registro_demo):
    assert cliente.post('/acciones/guardar-posicion', json={
        'cuenta': 'est-ana', 'actividad': 'REG-ACT08', 'posicion': 'plan'}).status_code == 200
    for item in CODIGOS_ITEMS:
        assert accion_registro(cliente, 'enviar', item=item, texto='Inicial [vaga]').status_code == 200
        assert accion_registro(cliente, 'responder-seguimiento', item=item,
                              texto='Primer turno [vaga]').status_code == 200
        accion = 'continuar-sin-responder' if item == 'REG-HAB-2' else 'responder-seguimiento'
        assert accion_registro(cliente, accion, item=item).json()['estado'] == 'FINAL'
    respuestas = [fila_respuesta(aplicacion, item=item) for item in CODIGOS_ITEMS]
    turnos = {item: turnos_guardados(aplicacion, item=item) for item in CODIGOS_ITEMS}
    historial = historial_registro(cliente).json()
    conversacion = estado_registro(cliente).json()['respuestas']
    llamadas = len(registro_demo.contextos)
    for numero in range(2):
        resultado = comprobar_publico(completar_registro(cliente))
        assert [e['tipo'] for e in resultado['eventos_registrados']] == (
            ['COMPLETA_ACTIVIDAD', 'COMPLETA_BLOQUE'] if numero == 0 else ['COMPLETA_ACTIVIDAD'])
        assert [fila_respuesta(aplicacion, item=item) for item in CODIGOS_ITEMS] == respuestas
        assert {item: turnos_guardados(aplicacion, item=item) for item in CODIGOS_ITEMS} == turnos
        assert historial_registro(cliente).json() == historial
        assert estado_registro(cliente).json() == {
            'posicion': 'plan', 'estado': 'COMPLETADA', 'respuestas': conversacion}
    assert turnos['REG-HAB-2'][1]['respuesta'] is None
    for accion, datos in [('enviar', {}), ('responder-seguimiento', {'orden': 1}),
                          ('responder-seguimiento', {'orden': 2})]:
        editada = comprobar_publico(accion_registro(cliente, accion, texto='Edición [falla]', **datos))
        assert editada['estado'] == 'FINAL' and editada['eventos_registrados'] == []
        assert editada['nuevos_desbloqueos'] == []
    for anterior, editado in zip(turnos['REG-HAB-1'], turnos_guardados(aplicacion)):
        assert editado == {**anterior, 'respuesta': 'Edición [falla]'}
    fila = fila_respuesta(aplicacion)
    assert fila['texto_inicial'] == 'Edición [falla]'
    assert fila['actualizada_en'] > respuestas[0]['actualizada_en']
    for campo in ('clasificacion_inicial', 'ampliada', 'creada_en', 'primer_texto_evaluado'):
        assert fila[campo] == respuestas[0][campo]
    assert len(registro_demo.contextos) == llamadas and historial_registro(cliente).json() == historial
    ultima = comprobar_publico(completar_registro(cliente))
    assert [e['tipo'] for e in ultima['eventos_registrados']] == ['COMPLETA_ACTIVIDAD']
    assert ultima['nuevos_desbloqueos'] == [] and ultima['resultados_generados'] == []
    assert fila_respuesta(aplicacion) == fila
    eventos = fotografia(aplicacion)['evento_uso']
    assert sum(e.tipo == 'RESPUESTA_REFLEXIVA' for e in eventos) == 3
    assert sum(e.tipo == 'COMPLETA_ACTIVIDAD' for e in eventos) == 3
    assert sum(e.tipo == 'COMPLETA_BLOQUE' for e in eventos) == 1


def test_error_sql_al_completar_revierte_progreso_y_eventos_conservando_conversaciones(
        cliente, aplicacion, registro_demo):
    for item in CODIGOS_ITEMS:
        assert accion_registro(cliente, 'enviar', item=item, texto='Inicial [vaga]').status_code == 200
        assert accion_registro(cliente, 'responder-seguimiento', item=item).status_code == 200
    antes = fotografia(aplicacion)
    llamadas = len(registro_demo.contextos)
    def fallar_lote_eventos(conexion, cursor, sentencia, parametros, contexto_sql, muchos):
        # El motor inserta ambos eventos juntos; se falla después de ejecutar el lote.
        if sentencia.startswith('INSERT INTO evento_uso '):
            raise IntegrityError('Fallo SQL simulado', {}, Exception('Detalle interno'))
    event.listen(aplicacion.state.motor_bd, 'after_cursor_execute', fallar_lote_eventos)
    try:
        fallida = completar_registro(cliente)
    finally:
        event.remove(aplicacion.state.motor_bd, 'after_cursor_execute', fallar_lote_eventos)
    assert fallida.status_code == 409 and 'Detalle interno' not in fallida.text
    assert fotografia(aplicacion) == antes and len(registro_demo.contextos) == llamadas
    resultado = comprobar_publico(completar_registro(cliente))
    assert [e['tipo'] for e in resultado['eventos_registrados']] == ['COMPLETA_ACTIVIDAD', 'COMPLETA_BLOQUE']
