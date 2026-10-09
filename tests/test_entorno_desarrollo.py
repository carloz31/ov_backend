"""R16: arranque vacío y rutas exclusivas de desarrollo."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.database import crear_motor_bd
from app.main import crear_aplicacion
from app.models import Base
from datos import plataforma


def test_r16_entornos_aislados_sin_rutas_retiradas_ni_lecturas(tmp_path, monkeypatch):
    url = f'sqlite:///{(tmp_path / "vacia.db").as_posix()}'
    motor = crear_motor_bd(url)
    Base.metadata.create_all(motor)
    motor.dispose()
    def prohibido(*args, **kwargs):
        pytest.fail('El arranque no siembra ni lee archivos de datos')
    monkeypatch.setattr(plataforma, 'cargar', prohibido)
    leer = Path.read_text
    def leer_solo_configuracion(ruta, *args, **kwargs):
        if 'datos' in ruta.parts or 'static' in ruta.parts:
            prohibido()
        return leer(ruta, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', leer_solo_configuracion)
    monkeypatch.setenv('ENTORNO', 'desarrollo')
    desarrollo = crear_aplicacion(url)
    monkeypatch.setenv('ENTORNO', 'produccion')
    produccion = crear_aplicacion(url)
    for aplicacion, esperado in ((desarrollo, 200), (produccion, 404)):
        with TestClient(aplicacion) as cliente:
            rutas = cliente.get('/openapi.json').json()['paths']
            assert all(not ruta.startswith('/demo') for ruta in rutas)
            for ruta in ('/demo', '/demo/instrumentos', '/demo/registro', '/demo/catalogo',
                         '/demo/recursos/demo.js', '/demo/registro/est-ana/REG-ACT08/evaluaciones'):
                assert cliente.get(ruta).status_code == 404
            assert cliente.post('/demo/reiniciar').status_code == 404
            assert cliente.post('/acciones/guardar-posicion', json={}).status_code == 404
            assert cliente.post('/desarrollo/reiniciar').status_code == esperado
            assert cliente.get('/cuentas').json() == []
            with aplicacion.state.motor_bd.connect() as conexion:
                assert all(conexion.execute(select(tabla)).first() is None for tabla in Base.metadata.sorted_tables)
            assert aplicacion.title == 'Plataforma de orientación vocacional'
