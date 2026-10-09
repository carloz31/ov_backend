"""I1–I14 mediante acciones y consultas públicas; invariantes y atomicidad."""


import pytest
from sqlalchemy import func, select

from app import models as modelos


@pytest.fixture(autouse=True)
def reiniciar_instrumentos(cliente):
    assert cliente.post("/desarrollo/reiniciar").status_code == 200


def contar(aplicacion, modelo):
    with aplicacion.state.fabrica_sesiones() as sesion:
        return sesion.scalar(select(func.count()).select_from(modelo))


@pytest.mark.parametrize("respuestas", [
    [], [{"item": "RIASEC-01", "opcion": 1}] * 2,
    [{"item": "RIASEC-01", "opcion": True}], [{"item": "RIASEC-01", "opcion": 1.5}],
    [{"item": "RIASEC-01", "opcion": "2"}], [{"item": "RIASEC-01", "opcion": 0}],
])
def test_entrada_invalida_no_crea_progreso_ni_respuestas(cliente, aplicacion, respuestas):
    assert cliente.post("/acciones/responder-items", json={
        "cuenta": "est-ana", "actividad": "LAB-RIA1", "respuestas": respuestas,
    }).status_code == 422
    assert contar(aplicacion, modelos.ProgresoActividad) == contar(aplicacion, modelos.RespuestaItem) == 0
    assert contar(aplicacion, modelos.EventoUso) == 0
