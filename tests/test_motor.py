from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as modelos
from app.database import crear_motor_bd
from app.models.base import Base
from app.services.motor import reglas as motor
from app.services.motor.evaluadores import EVALUADORES
from datos.plataforma import cargar as cargar_semilla


FECHA = datetime(2026, 10, 1, 10)


@pytest.fixture
def sesion(tmp_path):
    """Pruebas del núcleo con SQLAlchemy, sin aplicación ni routers."""
    motor_bd = crear_motor_bd(f"sqlite:///{(tmp_path / 'motor.db').as_posix()}")
    Base.metadata.create_all(motor_bd)
    try:
        with Session(motor_bd) as sesion:
            with sesion.begin():
                cargar_semilla(sesion)
            yield sesion
    finally:
        motor_bd.dispose()


def buscar(sesion, modelo, codigo):
    entidad = sesion.scalar(select(modelo).where(modelo.codigo == codigo))
    assert entidad is not None
    return entidad


def agregar_eventos(sesion, cuenta, eventos):
    sesion.add_all([
        modelos.EventoUso(cuenta_id=cuenta.id, tipo=tipo, id_referencia=referencia, fecha_hora=fecha)
        for tipo, referencia, fecha in eventos
    ])
    sesion.flush()


@pytest.mark.parametrize("conteo", list(modelos.TipoConteo))
def test_conteo_inicial_es_cero(sesion, conteo):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    condicion = modelos.CondicionDesbloqueo(
        tipo_evento=modelos.TipoEventoUso.INGRESO, tipo_conteo=conteo, cantidad_minima=1,
    )
    assert motor.contar_eventos(sesion, ana, condicion) == 0


def test_referencias_nulas_no_son_objetos_distintos(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    agregar_eventos(sesion, ana, [(modelos.TipoEventoUso.INGRESO, None, FECHA)] * 3)
    condicion = modelos.CondicionDesbloqueo(
        tipo_evento=modelos.TipoEventoUso.INGRESO,
        tipo_conteo=modelos.TipoConteo.REFERENCIAS_DISTINTAS, cantidad_minima=1,
    )
    assert motor.contar_eventos(sesion, ana, condicion) == 0


def test_evaluador_verdadero_no_reemplaza_condiciones(sesion, monkeypatch):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    monkeypatch.setitem(EVALUADORES, "siempre_verdadero", lambda sesion, cuenta: True)
    regla = modelos.ReglaDesbloqueo(
        codigo="PRUEBA", evaluador_especial="siempre_verdadero",
        condiciones=[modelos.CondicionDesbloqueo(tipo_evento=modelos.TipoEventoUso.INGRESO,
                     tipo_conteo=modelos.TipoConteo.EVENTOS, cantidad_minima=1)],
    )
    resultado = motor.evaluar_regla(sesion, ana, regla)
    assert resultado.cumple is False
    assert resultado.condiciones[0].cumplida is False
    assert resultado.evaluador_especial.cumplido is True


@pytest.mark.parametrize("tipo", list(modelos.TipoObjetivo))
def test_objetivos_inexistentes_no_estan_disponibles(sesion, tipo):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    assert not motor.objetivo_disponible(sesion, ana, tipo, 99999)
    if tipo != modelos.TipoObjetivo.CONVERSACIONES:
        assert not motor.objetivo_disponible(sesion, ana, tipo, None)


def test_regla_sin_condiciones_es_configuracion_invalida(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    regla = modelos.ReglaDesbloqueo(codigo="VACIA", condiciones=[])
    with pytest.raises(ValueError, match="Regla sin condiciones: VACIA"):
        motor.evaluar_regla(sesion, ana, regla)
