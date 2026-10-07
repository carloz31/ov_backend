"""Iteración 1 · F1: configuración, esquema y compatibilidad de la demo."""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app import models as modelos
from app.configuracion_base import RAIZ_PROYECTO, cargar_configuracion_base
from app.database import Base, crear_motor_bd
from app.main import crear_aplicacion
from test_instrumentos import aplicar_cadena, CADENA_B, REQUIERE_OCUPACIONES


@pytest.mark.parametrize('semilla,archivo', [('demo', 'demo.db'), ('plataforma', 'plataforma.db')])
def test_archivo_predeterminado_por_semilla(semilla, archivo, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    configuracion = cargar_configuracion_base(entorno={'SEMILLA': semilla})
    assert configuracion.semilla == semilla
    assert configuracion.url_bd == f'sqlite:///{(RAIZ_PROYECTO / archivo).as_posix()}'


def test_demo_por_defecto_y_ruta_relativa_desde_raiz():
    assert cargar_configuracion_base(entorno={}).semilla == 'demo'
    assert cargar_configuracion_base(entorno={'RUTA_BD': 'otra.db'}).url_bd == (
        f'sqlite:///{(RAIZ_PROYECTO / "otra.db").as_posix()}'
    )


def test_ruta_absoluta_y_argumentos_explicitos_prevalecen(tmp_path):
    ruta = tmp_path / 'desde_entorno.db'
    assert cargar_configuracion_base(entorno={'RUTA_BD': str(ruta)}).url_bd == f'sqlite:///{ruta.as_posix()}'
    configuracion = cargar_configuracion_base('sqlite:///:memory:', 'demo',
        entorno={'SEMILLA': 'plataforma', 'RUTA_BD': ''})
    assert configuracion.semilla == 'demo'
    assert configuracion.url_bd == 'sqlite:///:memory:'


@pytest.mark.parametrize('valores,mensaje', [
    ({'SEMILLA': ''}, 'SEMILLA debe ser demo o plataforma'),
    ({'SEMILLA': 'desconocida'}, 'SEMILLA debe ser demo o plataforma'),
    ({'RUTA_BD': ''}, 'RUTA_BD no puede estar vacía'),
    ({'RUTA_BD': '   '}, 'RUTA_BD no puede estar vacía'),
])
def test_configuracion_invalida_sin_abrir_base(valores, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        cargar_configuracion_base(entorno=valores)


def test_fabrica_lee_entorno_y_conserva_url_explicita(tmp_path, monkeypatch):
    ruta = tmp_path / 'entorno.db'
    monkeypatch.setenv('SEMILLA', 'plataforma')
    monkeypatch.setenv('RUTA_BD', str(ruta))
    aplicacion = crear_aplicacion()
    try:
        assert aplicacion.state.semilla == 'plataforma'
        assert Path(aplicacion.state.motor_bd.url.database) == ruta
        assert not ruta.exists()
    finally:
        aplicacion.state.motor_bd.dispose()
    explicita = crear_aplicacion('sqlite:///:memory:', semilla='demo')
    try:
        assert explicita.state.semilla == 'demo'
        assert explicita.state.motor_bd.url.database == ':memory:'
    finally:
        explicita.state.motor_bd.dispose()


def test_demo_explicita_arranca_y_reinicia_con_entorno_plataforma(tmp_path, monkeypatch):
    monkeypatch.setenv('SEMILLA', 'plataforma')
    ruta = tmp_path / 'demo_explicita.db'
    aplicacion = crear_aplicacion(f'sqlite:///{ruta.as_posix()}', semilla='demo')
    with TestClient(aplicacion) as cliente:
        assert cliente.get('/cuentas').status_code == 200
        assert cliente.post('/demo/reiniciar').status_code == 200
        assert aplicacion.state.posiciones_registro == {'REG-ACT08': ('explicacion', 'plan')}
        with aplicacion.state.fabrica_sesiones() as sesion:
            assert sesion.execute(select(modelos.EsquemaVersion.version, modelos.EsquemaVersion.semilla)).all() == [(5, 'demo')]


def test_columnas_y_restricciones_nuevas_con_demo_intacta(sesion, aplicacion):
    inspector = inspect(aplicacion.state.motor_bd)
    assert len(inspector.get_table_names()) == 45
    version = {columna['name']: columna for columna in inspector.get_columns('esquema_version')}
    ocupacion = {columna['name']: columna for columna in inspector.get_columns('ocupacion')}
    assert set(version) == {'id', 'version', 'semilla'}
    assert version['semilla']['nullable'] is False
    assert set(ocupacion) == {'id', 'codigo', 'codigo_onet', 'titulo'}
    assert ocupacion['codigo']['nullable'] is True
    assert any(restriccion['column_names'] == ['codigo']
               for restriccion in inspector.get_unique_constraints('ocupacion'))
    assert all(codigo is None for codigo in sesion.scalars(select(modelos.Ocupacion.codigo)))
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.execute(text('UPDATE esquema_version SET semilla = NULL'))
    # DATO DE PRUEBA: ocupaciones sintéticas para unicidad y nulos múltiples.
    sesion.add_all([
        modelos.Ocupacion(codigo_onet='PRUEBA-NULO-1', titulo='Prueba'),
        modelos.Ocupacion(codigo_onet='PRUEBA-NULO-2', titulo='Prueba'),
        modelos.Ocupacion(codigo='ocupacion-prueba', codigo_onet='PRUEBA-CODIGO-1', titulo='Prueba'),
    ])
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelos.Ocupacion(codigo='ocupacion-prueba', codigo_onet='PRUEBA-CODIGO-2', titulo='Prueba'))
            sesion.flush()


@pytest.mark.parametrize('semilla_base,semilla_configurada', [('demo', 'plataforma'), ('plataforma', 'demo')])
def test_semilla_distinta_rechaza_base_sin_modificarla(tmp_path, semilla_base, semilla_configurada):
    ruta = tmp_path / 'otra_semilla.db'
    motor = crear_motor_bd(f'sqlite:///{ruta.as_posix()}')
    try:
        Base.metadata.create_all(motor)
        # DATO DE PRUEBA: marca de semilla; no contiene datos de plataforma.
        with motor.begin() as conexion:
            conexion.execute(text('INSERT INTO esquema_version VALUES (1, 5, :semilla)'), {'semilla': semilla_base})
    finally:
        motor.dispose()
    antes = ruta.read_bytes()
    with pytest.raises(RuntimeError) as error:
        with TestClient(crear_aplicacion(f'sqlite:///{ruta.as_posix()}', semilla=semilla_configurada)):
            pass
    assert str(error.value) == (
        f'La base otra_semilla.db fue creada con la semilla {semilla_base}; '
        f'la aplicación está configurada con {semilla_configurada}. Usa otra RUTA_BD o borra el archivo.'
    )
    assert ruta.read_bytes() == antes


@pytest.mark.parametrize('variante', ['version_cuatro', 'sin_semilla', 'sin_codigo', 'registro_v1'])
def test_esquema_anterior_o_incompatible_no_se_migra(tmp_path, variante):
    ruta = tmp_path / 'incompatible.db'
    motor = crear_motor_bd(f'sqlite:///{ruta.as_posix()}')
    try:
        Base.metadata.create_all(motor)
        with motor.begin() as conexion:
            conexion.execute(text("INSERT INTO esquema_version VALUES (1, 5, 'demo')"))
            if variante == 'version_cuatro':
                conexion.execute(text('UPDATE esquema_version SET version = 4'))
                conexion.exec_driver_sql('ALTER TABLE esquema_version DROP COLUMN semilla')
            elif variante == 'sin_semilla':
                conexion.exec_driver_sql('ALTER TABLE esquema_version DROP COLUMN semilla')
            elif variante == 'sin_codigo':
                # SQLite no permite DROP COLUMN de una columna UNIQUE.
                conexion.exec_driver_sql('ALTER TABLE ocupacion RENAME COLUMN codigo TO codigo_anterior')
            else:
                conexion.exec_driver_sql('ALTER TABLE respuesta_registro RENAME COLUMN texto_inicial TO texto')
    finally:
        motor.dispose()
    antes = ruta.read_bytes()
    with pytest.raises(RuntimeError) as error:
        with TestClient(crear_aplicacion(f'sqlite:///{ruta.as_posix()}', semilla='demo')):
            pass
    assert str(error.value) == 'La base incompatible.db tiene un esquema anterior. Bórrala y vuelve a iniciar la aplicación.'
    assert ruta.read_bytes() == antes


@REQUIERE_OCUPACIONES
@pytest.mark.parametrize('codigo', [None, 'range-manager-prueba'])
def test_codigo_ocupacion_en_resultado_historial_y_via(cliente, aplicacion, codigo):
    list(aplicar_cadena(cliente, CADENA_B))
    if codigo is not None:
        # DATO DE PRUEBA: código sintético, solo en esta base temporal.
        with aplicacion.state.fabrica_sesiones.begin() as sesion:
            ocupacion = sesion.scalar(select(modelos.Ocupacion).where(modelos.Ocupacion.codigo_onet == '19-1031.02'))
            ocupacion.codigo = codigo
    ruta = '/cuentas/est-ana/instrumentos/TEST-RIASEC'
    vigente = cliente.get(f'{ruta}/resultado').json()
    assert vigente['coincidencias'][0]['codigo'] == codigo
    assert vigente['coincidencias'][0]['codigo_onet'] == '19-1031.02'
    assert vigente['carreras_recomendadas'][0]['via'][0] == vigente['coincidencias'][0]
    assert all(afin['codigo'] is None for afin in vigente['coincidencias'][1:])
    assert cliente.get(f'{ruta}/historial').json() == [{**vigente, 'anulado_en': None}]
    respuesta = cliente.post('/acciones/reiniciar-instrumento', json={
        'cuenta': 'est-ana', 'instrumento': 'TEST-RIASEC', 'fecha_hora': '2026-10-02T10:00:00',
    })
    assert respuesta.status_code == 200
    assert cliente.get(f'{ruta}/historial').json() == [{**vigente, 'anulado_en': '2026-10-02T10:00:00'}]
