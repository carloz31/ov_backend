"""Restricciones resultados."""

from datetime import datetime
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app import models as modelos


FECHA = datetime(2026, 10, 1, 10)


def buscar(sesion, modelo, codigo):
    return sesion.scalar(select(modelo).where(modelo.codigo == codigo))


def test_dos_resultados_vigentes_prohibidos(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    aplicacion = buscar(sesion, modelos.Aplicacion, "APL-RIASEC")
    resultado = modelos.ResultadoInstrumento(cuenta_id=ana.id, aplicacion_id=aplicacion.id, calculado_en=FECHA)
    sesion.add(resultado)
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelos.ResultadoInstrumento(cuenta_id=ana.id, aplicacion_id=aplicacion.id, calculado_en=FECHA))
            sesion.flush()
    resultado.anulado_en = FECHA
    sesion.flush()
    sesion.add(modelos.ResultadoInstrumento(cuenta_id=ana.id, aplicacion_id=aplicacion.id, calculado_en=FECHA))
    sesion.flush()
    assert sesion.scalar(select(func.count()).select_from(modelos.ResultadoInstrumento)) == 2


@pytest.mark.parametrize("correlacion, ajuste, posicion", [
    (-0.1, "GOOD_FIT", 1), (0.7, "BEST_FIT", 1), (0.729, "GREAT_FIT", 1),
    (0.607, "GREAT_FIT", 1), (0.608, "GOOD_FIT", 1), (0.9, "BEST_FIT", 0), (0.9, "BEST_FIT", 11),
])
def test_coincidencias_rechazan_ajustes_y_posiciones_invalidas(sesion, correlacion, ajuste, posicion):
    # Ocupación independiente del Excel, únicamente para probar restricciones SQL.
    ocupacion = modelos.Ocupacion(codigo_onet="PRUEBA", titulo="Prueba SQL")
    sesion.add(ocupacion)
    resultado = modelos.ResultadoInstrumento(cuenta_id=buscar(sesion, modelos.Cuenta, "est-ana").id,
                                             aplicacion_id=buscar(sesion, modelos.Aplicacion, "APL-RIASEC").id,
                                             calculado_en=FECHA)
    sesion.add(resultado)
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelos.Coincidencia(resultado_id=resultado.id, ocupacion_id=ocupacion.id,
                                          posicion=posicion, correlacion=correlacion, ajuste=ajuste))
            sesion.flush()
