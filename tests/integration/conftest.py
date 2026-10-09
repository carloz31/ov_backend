"""Bases aisladas por prueba; las plantillas se incorporan en P4."""

import pytest
from fastapi.testclient import TestClient
from soporte_consultas import MedidorPeticiones
from soporte_fixtures import contador_consultas

from app.main import crear_aplicacion
from datos.cargar import preparar_base


@pytest.fixture
def aplicacion(tmp_path):
    url = f"sqlite:///{(tmp_path / 'prueba.db').as_posix()}"
    preparar_base(url, 'plataforma', crear_tablas=True)
    return crear_aplicacion(url)


@pytest.fixture
def aplicacion_plataforma(tmp_path):
    url = f"sqlite:///{(tmp_path / 'plataforma.db').as_posix()}"
    preparar_base(url, 'plataforma', crear_tablas=True)
    return crear_aplicacion(url)


@pytest.fixture
def cliente(aplicacion):
    with TestClient(aplicacion) as cliente:
        yield cliente


@pytest.fixture
def sesion(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones() as sesion:
        yield sesion


@pytest.fixture
def medidor_peticiones(cliente, aplicacion):
    return MedidorPeticiones(cliente, aplicacion.state.motor_bd)
