"""Carga explícita de datos, vaciado y fallos atómicos."""

import pytest
from soporte_estado_desarrollo import filas
from app.database import crear_motor_bd
from app.models import Base
from datos import cargar as carga
from datos import plataforma


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
    command.upgrade(Config(str(Path(__file__).resolve().parents[3] / 'alembic.ini')), 'head')
    assert carga.main(['plataforma']) == 0
    salida = capsys.readouterr().out
    assert 'cuenta: 3' in salida and 'ocupacion: 36' in salida
    with pytest.raises(SystemExit) as error:
        carga.main(['plataforma'])
    assert error.value.code == 1
    assert '--vaciar' in capsys.readouterr().err
    assert carga.main(['plataforma', '--vaciar']) == 0
