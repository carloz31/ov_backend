"""Atomicidad del reinicio cuando falla un borrado."""

from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from soporte_estado_desarrollo import filas


def test_reinicio_fallido_revierte_borrados(cliente, aplicacion):
    assert cliente.post('/acciones/ingresar', json={'cuenta': 'est-ana'}).status_code == 200
    motor = aplicacion.state.motor_bd
    antes = filas(motor)
    def fallar(conexion, cursor, sentencia, parametros, contexto, varios):
        if sentencia.startswith('DELETE FROM progreso_actividad'):
            raise IntegrityError(sentencia, parametros, RuntimeError('Fallo de prueba'))
    event.listen(motor, 'before_cursor_execute', fallar)
    try:
        assert cliente.post('/desarrollo/reiniciar').status_code == 409
    finally:
        event.remove(motor, 'before_cursor_execute', fallar)
    assert filas(motor) == antes
