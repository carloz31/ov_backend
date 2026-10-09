"""R3: carga explícita, atomicidad y clasificación completa del reinicio."""


import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from app.database import crear_motor_bd
from app.models import Base
from app.services.desarrollo import TABLAS_DE_ESTADO
from datos import cargar as carga
from datos import plataforma


CATALOGO = {
    'cuenta', 'vinculo_familiar', 'bloque', 'actividad', 'ficha', 'testimonio',
    'pregunta_diario', 'conversacion', 'insignia', 'nivel', 'familia_carrera', 'carrera',
    'regla_desbloqueo', 'condicion_desbloqueo', 'instrumento', 'dimension',
    'escala_respuesta', 'opcion_escala', 'item_instrumento', 'actividad_item',
    'aplicacion', 'aplicacion_actividad', 'ocupacion', 'puntaje_ocupacion',
    'carrera_ocupacion', 'item_registro', 'criterio_completitud', 'actividad_item_registro',
}
ESTADO = {
    'progreso_actividad', 'resultado_caso', 'entrada_diario', 'check_in', 'entrevista',
    'entrevista_autor', 'conversacion_vinculo', 'evento_uso', 'desbloqueo',
    'respuesta_item', 'resultado_instrumento', 'resultado_dimension', 'coincidencia',
    'respuesta_registro', 'turno_seguimiento', 'evaluacion_respuesta',
}


def filas(motor):
    with motor.connect() as conexion:
        return {tabla.name: conexion.execute(select(tabla).order_by(*tabla.primary_key.columns)).all()
                for tabla in Base.metadata.sorted_tables}


def test_todas_las_tablas_clasificadas_sin_solapamientos():
    assert CATALOGO.isdisjoint(ESTADO)
    assert CATALOGO | ESTADO == set(Base.metadata.tables)
    assert set(TABLAS_DE_ESTADO) == ESTADO
    assert len(TABLAS_DE_ESTADO) == len(ESTADO)


@pytest.mark.parametrize('conjunto', ['plataforma'])
def test_carga_conteos_recarga_rechazada_y_vaciado(tmp_path, conjunto):
    url = f'sqlite:///{(tmp_path / "carga.db").as_posix()}'
    conteos = carga.preparar_base(url, conjunto, crear_tablas=True)
    assert set(conteos) == set(carga.TABLAS_PRINCIPALES)
    assert conteos['cuenta'] == 3 and conteos['actividad'] > 0
    motor = crear_motor_bd(url)
    try:
        antes = filas(motor)
        with pytest.raises(ValueError, match='--vaciar'):
            carga.preparar_base(url, conjunto)
        assert filas(motor) == antes
        assert carga.preparar_base(url, conjunto, vaciar=True) == conteos
        assert filas(motor) == antes
    finally:
        motor.dispose()


@pytest.mark.parametrize('vaciar', [False, True])
def test_carga_fallida_es_atomica(tmp_path, monkeypatch, vaciar):
    url = f'sqlite:///{(tmp_path / "atomica.db").as_posix()}'
    motor = crear_motor_bd(url)
    if vaciar:
        carga.preparar_base(url, 'plataforma', crear_tablas=True)
    else:
        Base.metadata.create_all(motor)
    antes = filas(motor)
    def fallar(sesion):
        plataforma.cargar(sesion)
        raise ValueError('Fallo después de la carga completa')
    monkeypatch.setitem(carga.CONJUNTOS, 'plataforma', fallar)
    try:
        with pytest.raises(ValueError, match='Fallo después'):
            carga.preparar_base(url, 'plataforma', vaciar=vaciar)
        assert filas(motor) == antes
    finally:
        motor.dispose()


def test_conjunto_invalido_no_abre_base(tmp_path):
    ruta = tmp_path / 'no_creada.db'
    with pytest.raises(ValueError, match='conjunto'):
        carga.preparar_base(f'sqlite:///{ruta.as_posix()}', 'otro', crear_tablas=True)
    assert not ruta.exists()


def test_cli_rechaza_crear_tablas(tmp_path, monkeypatch, capsys):
    ruta = tmp_path / 'no_creada.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{ruta.as_posix()}')
    with pytest.raises(SystemExit) as error:
        carga.main(['plataforma', '--crear-tablas'])
    assert error.value.code == 2
    assert '--crear-tablas' in capsys.readouterr().err
    assert not ruta.exists()


def test_cli_sin_esquema_y_carga_tras_migracion(tmp_path, monkeypatch, capsys):
    from alembic import command
    from alembic.config import Config
    from pathlib import Path

    url = f'sqlite:///{(tmp_path / "cli.db").as_posix()}'
    monkeypatch.setenv('DATABASE_URL', url)
    with pytest.raises(SystemExit) as error:
        carga.main(['plataforma'])
    assert error.value.code == 1
    assert 'uv run alembic upgrade head' in capsys.readouterr().err
    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini')), 'head')
    assert carga.main(['plataforma']) == 0
    salida = capsys.readouterr().out
    assert 'cuenta: 3' in salida and 'ocupacion: 36' in salida
    with pytest.raises(SystemExit) as error:
        carga.main(['plataforma'])
    assert error.value.code == 1
    assert '--vaciar' in capsys.readouterr().err
    assert carga.main(['plataforma', '--vaciar']) == 0


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
