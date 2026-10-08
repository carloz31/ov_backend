import pytest
from fastapi.testclient import TestClient
from soporte_consultas import ContadorConsultas, MedidorPeticiones

from app.main import crear_aplicacion
from datos import ocupaciones
from datos.demo import instrumentos as semilla_instrumentos


@pytest.fixture(autouse=True)
def usar_evaluador_falso(monkeypatch):
    monkeypatch.setenv("EVALUADOR", "falso")


@pytest.fixture(autouse=True)
def catalogo_opcional_solo_en_pruebas(monkeypatch):
    # Producción siempre exige el Excel. Sin él, las pruebas ajenas al catálogo
    # pueden cargar las definiciones sin fabricar ocupaciones ni sus puntajes.
    if not ocupaciones.RUTA_OCUPACIONES.is_file():
        monkeypatch.setattr(semilla_instrumentos, "cargar_catalogo_ocupaciones", lambda sesion: None)


@pytest.fixture
def aplicacion(tmp_path):
    return crear_aplicacion(f"sqlite:///{(tmp_path / 'prueba.db').as_posix()}")


@pytest.fixture
def cliente(aplicacion):
    with TestClient(aplicacion) as cliente:
        yield cliente


@pytest.fixture
def sesion(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones() as sesion:
        yield sesion


@pytest.fixture
def contador_consultas():
    return ContadorConsultas


@pytest.fixture
def medidor_peticiones(cliente, aplicacion):
    return MedidorPeticiones(cliente, aplicacion.state.motor_bd)
