"""Humo opcional: una base PostgreSQL accesible mediante TEST_POSTGRES_URL."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from app.database import crear_motor_bd
from app.main import crear_aplicacion
from datos.cargar import preparar_base
import soporte_escenarios_plataforma as escenarios


@pytest.mark.skipif(not os.environ.get('TEST_POSTGRES_URL'), reason='Falta TEST_POSTGRES_URL')
@pytest.mark.parametrize('escenario', ['p01_estado_inicial', 'p02_primer_paso',
                                      'p07_llegada_a_la_ciudad', 'p10_resultado'])
def test_postgresql_por_http(monkeypatch, escenario):
    url_original = make_url(os.environ['TEST_POSTGRES_URL'])
    assert url_original.get_backend_name() == 'postgresql'
    esquema = f'ov_prueba_{uuid4().hex}'
    administrador = crear_motor_bd(url_original)
    creado = False
    try:
        with administrador.begin() as conexion:
            conexion.execute(CreateSchema(esquema))
        creado = True
        opciones = url_original.query.get('options', '')
        url = url_original.update_query_dict({'options': f'{opciones} -csearch_path={esquema}'.strip()})
        url_texto = url.render_as_string(hide_password=False)
        monkeypatch.setenv('DATABASE_URL', url_texto)
        monkeypatch.setenv('ENTORNO', 'desarrollo')
        configuracion = Config(str(Path(__file__).resolve().parents[3] / 'alembic.ini'))
        command.upgrade(configuracion, 'head')
        preparar_base(url_texto, 'plataforma')
        with TestClient(crear_aplicacion(url_texto)) as cliente:
            getattr(escenarios, f'verificar_{escenario}')(cliente)
    finally:
        try:
            if creado:
                with administrador.begin() as conexion:
                    conexion.execute(DropSchema(esquema, cascade=True))
        finally:
            administrador.dispose()
