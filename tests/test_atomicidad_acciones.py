"""R32: fallo posterior a una concesión real."""

import pytest
from app.services import actividades as servicio_actividades
from soporte_plataforma import completar, filas_base


def test_r32_fallo_despues_de_conceder_revierte_completar(cliente, aplicacion, monkeypatch):
    antes = filas_base(aplicacion)
    original = servicio_actividades.responder_con_eventos
    def fallar(*args, **kwargs):
        respuesta = original(*args, **kwargs)
        assert respuesta.nuevos_desbloqueos and respuesta.eventos_registrados
        raise RuntimeError('DATO DE PRUEBA: después de conceder')
    monkeypatch.setattr(servicio_actividades, 'responder_con_eventos', fallar)
    with pytest.raises(RuntimeError, match='después de conceder'):
        completar(cliente, 'mission-welcome')
    assert filas_base(aplicacion) == antes
