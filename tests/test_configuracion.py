"""R3: configuración única, precedencias y aislamiento de entornos."""

from dataclasses import FrozenInstanceError
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text

from app.config import Configuracion, RAIZ_PROYECTO, cargar_configuracion
from app.database import MENSAJE_SIN_ESQUEMA, crear_motor_bd
from app.main import crear_aplicacion
from app.models import Base
from datos.cargar import preparar_base


def test_valores_predeterminados_y_ruta_independiente_del_directorio(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    configuracion = cargar_configuracion(entorno={}, ruta_env=tmp_path / 'ausente')
    assert configuracion == Configuracion()
    assert configuracion.url_bd == f'sqlite:///{(RAIZ_PROYECTO / "ov.db").as_posix()}'
    assert configuracion.entorno == 'desarrollo'
    with pytest.raises(FrozenInstanceError):
        configuracion.entorno = 'produccion'


@pytest.mark.parametrize('url', ['sqlite:///otra.db', 'sqlite+pysqlite:///otra.db'])
def test_sqlite_relativa_desde_raiz_conserva_dialectos(url, tmp_path):
    configuracion = cargar_configuracion({'DATABASE_URL': url}, tmp_path / 'ausente')
    assert configuracion.url_bd == url.replace('otra.db', (RAIZ_PROYECTO / 'otra.db').as_posix())


@pytest.mark.parametrize('url', ['sqlite:///:memory:', 'sqlite://',
                                'postgresql+psycopg://ov:clave@localhost/ov'])
def test_urls_sin_ruta_relativa_se_conservan(url, tmp_path):
    assert cargar_configuracion({'DATABASE_URL': url}, tmp_path / 'ausente').url_bd == url


def test_ruta_absoluta_y_precedencia_env(tmp_path, monkeypatch):
    archivo = tmp_path / '.env'
    archivo.write_text('DATABASE_URL=sqlite:///desde_archivo.db\nENTORNO=produccion\nEVALUADOR=falso\n', encoding='utf-8')
    ruta = tmp_path / 'desde_proceso.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{ruta.as_posix()}')
    configuracion = cargar_configuracion(ruta_env=archivo)
    assert configuracion.url_bd == f'sqlite:///{ruta.as_posix()}'
    assert configuracion.entorno == 'produccion'
    assert not ruta.exists()
    assert cargar_configuracion({}, archivo).url_bd.endswith('/desde_archivo.db')


@pytest.mark.parametrize('variables,mensaje', [
    ({'DATABASE_URL': ''}, 'DATABASE_URL no puede estar vacía'),
    ({'DATABASE_URL': '  '}, 'DATABASE_URL no puede estar vacía'),
    ({'DATABASE_URL': 'valor-secreto-invalido'}, 'DATABASE_URL no es una URL válida'),
    ({'ENTORNO': ''}, 'ENTORNO debe ser desarrollo o produccion'),
    ({'ENTORNO': 'otro'}, 'ENTORNO debe ser desarrollo o produccion'),
])
def test_configuracion_invalida_sin_filtrar_valores(variables, mensaje, tmp_path):
    with pytest.raises(ValueError) as error:
        cargar_configuracion(variables, tmp_path / 'ausente')
    assert str(error.value) == mensaje


def test_fabrica_argumento_prevalece_incluso_sobre_url_invalida(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', '')
    aplicacion = crear_aplicacion('sqlite:///:memory:')
    try:
        assert aplicacion.state.motor_bd.url.database == ':memory:'
        assert not hasattr(aplicacion.state, 'semilla')
        assert not hasattr(aplicacion.state, 'obtener_cargador_semilla')
    finally:
        aplicacion.state.motor_bd.dispose()


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


def test_arranque_con_esquema_y_catalogo_vacio_no_siembra(tmp_path):
    url = f'sqlite:///{(tmp_path / "vacia.db").as_posix()}'
    motor = crear_motor_bd(url)
    Base.metadata.create_all(motor)
    motor.dispose()
    aplicacion = crear_aplicacion(url)
    with TestClient(aplicacion) as cliente:
        assert cliente.get('/cuentas').json() == []
        assert cliente.get('/reglas').json() == []
        assert cliente.get('/instrumentos').json() == []
        assert aplicacion.state.posiciones_registro == {}
        with aplicacion.state.fabrica_sesiones() as sesion:
            assert all(sesion.execute(select(tabla)).first() is None for tabla in Base.metadata.sorted_tables)


def test_demo_solo_en_desarrollo_sin_contaminar_instancias(tmp_path, monkeypatch):
    url = f'sqlite:///{(tmp_path / "entornos.db").as_posix()}'
    preparar_base(url, 'demo', crear_tablas=True)
    for entorno in ('produccion', 'desarrollo', 'produccion'):
        monkeypatch.setenv('ENTORNO', entorno)
        aplicacion = crear_aplicacion(url)
        with TestClient(aplicacion) as cliente:
            assert cliente.get('/cuentas').status_code == 200
            rutas = ['/demo', '/demo/registro', '/demo/instrumentos', '/demo/catalogo',
                     '/demo/recursos/contenido/REG-ACT08.json',
                     '/demo/registro/est-ana/REG-ACT08/evaluaciones']
            for ruta in rutas:
                assert cliente.get(ruta).status_code == (200 if entorno == 'desarrollo' else 404)
            assert cliente.post('/demo/reiniciar').status_code == (200 if entorno == 'desarrollo' else 404)
            assert any(ruta.startswith('/demo') for ruta in aplicacion.openapi()['paths']) == (entorno == 'desarrollo')
