"""R15: reinicio transaccional sin alterar el catálogo ni la caché."""

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from app.models import Base
from app.services.desarrollo import TABLAS_DE_ESTADO
from datos import cargar, plataforma
from soporte_estado_desarrollo import llenar_estado
from soporte_plataforma import filas_base, pedir


def test_r15_reinicio_completo_idempotente_y_atomico(cliente, aplicacion, monkeypatch):
    llenar_estado(aplicacion)
    pedir(cliente, 'POST', '/acciones/escribir-carta', {'cuenta': 'est-ana', 'texto': 'DATO DE PRUEBA'})
    antes = filas_base(aplicacion)
    assert all(antes[nombre] for nombre in TABLAS_DE_ESTADO)
    motor = aplicacion.state.motor_bd
    cache = motor.cache_definiciones.actual
    def prohibido(*args, **kwargs):
        pytest.fail('El reinicio no puede cargar catálogos ni recrear tablas')
    monkeypatch.setattr(plataforma, 'cargar', prohibido)
    monkeypatch.setitem(cargar.CONJUNTOS, 'plataforma', prohibido)
    monkeypatch.setattr(Base.metadata, 'create_all', prohibido)
    monkeypatch.setattr(Base.metadata, 'drop_all', prohibido)
    def fallar(conexion, cursor, sentencia, parametros, contexto, varios):
        if sentencia.startswith('DELETE FROM progreso_actividad'):
            raise IntegrityError(sentencia, parametros, RuntimeError('DATO DE PRUEBA'))
    event.listen(motor, 'before_cursor_execute', fallar)
    try:
        pedir(cliente, 'POST', '/desarrollo/reiniciar', esperado=409)
    finally:
        event.remove(motor, 'before_cursor_execute', fallar)
    assert filas_base(aplicacion) == antes and motor.cache_definiciones.actual is cache
    for _ in range(2):
        assert pedir(cliente, 'POST', '/desarrollo/reiniciar') == {'mensaje': 'Datos de prueba reiniciados'}
        despues = filas_base(aplicacion)
        assert all(despues[nombre] == [] for nombre in TABLAS_DE_ESTADO)
        assert all(despues[nombre] == filas for nombre, filas in antes.items() if nombre not in TABLAS_DE_ESTADO)
        assert motor.cache_definiciones.actual is cache
