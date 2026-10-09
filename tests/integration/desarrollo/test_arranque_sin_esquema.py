"""Arranque sin esquema."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from app.database import MENSAJE_SIN_ESQUEMA, crear_motor_bd
from app.main import crear_aplicacion


@pytest.mark.parametrize('parcial', [False, True])
def test_arranque_sin_esquema_falla_sin_crear_tablas(tmp_path, parcial):
    ruta = tmp_path / 'sin_esquema.db'
    url = f'sqlite:///{ruta.as_posix()}'
    motor = crear_motor_bd(url)
    if parcial:
        with motor.begin() as conexion:
            # DATO DE PRUEBA: tabla parcial con datos que el arranque debe conservar.
            conexion.execute(text('CREATE TABLE cuenta (id INTEGER PRIMARY KEY, codigo TEXT)'))
            conexion.execute(text("INSERT INTO cuenta VALUES (1, 'dato-anterior')"))
    motor.dispose()
    antes = ruta.read_bytes() if parcial else None
    with pytest.raises(RuntimeError) as error:
        with TestClient(crear_aplicacion(url)):
            pass
    assert str(error.value) == MENSAJE_SIN_ESQUEMA
    motor = crear_motor_bd(url)
    try:
        assert inspect(motor).get_table_names() == (['cuenta'] if parcial else [])
        if parcial:
            assert ruta.read_bytes() == antes
            with motor.connect() as conexion:
                assert conexion.execute(text('SELECT codigo FROM cuenta')).scalars().all() == ['dato-anterior']
    finally:
        motor.dispose()
