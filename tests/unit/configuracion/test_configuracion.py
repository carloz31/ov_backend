"""Configuracion."""

from dataclasses import FrozenInstanceError
import pytest
from app.config import Configuracion, RAIZ_PROYECTO, cargar_configuracion
from app.main import crear_aplicacion


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
