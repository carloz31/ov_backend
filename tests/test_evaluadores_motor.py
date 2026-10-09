"""R05: diversidad de familias y parámetros por regla."""

from sqlalchemy import select
from app import models as m
from app.services.motor import reglas as motor
from soporte_retiro import FECHA_BD, agregar_eventos, buscar, condicion, regla


def test_r05_familias_distintas_y_parametro_por_regla(sesion):
    ana = buscar(sesion, m.Cuenta, 'est-ana')
    carreras = list(sesion.scalars(select(m.Carrera).order_by(m.Carrera.id)))
    otra = m.Carrera(codigo='carrera-prueba', nombre='DATO DE PRUEBA', familia_id=carreras[0].familia_id)
    sesion.add(otra)
    sesion.flush()
    ficha = sesion.scalar(select(m.Ficha))
    reglas = [regla(sesion, f'R-PRUEBA-FAM-{n}', 'FICHA', ficha.id,
                   [condicion('VISTA_CARRERA')], 'carreras_de_3_familias', n) for n in (2, 3)]
    agregar_eventos(sesion, ana, [('VISTA_CARRERA', referencia, FECHA_BD)
        for referencia in (carreras[0].id, carreras[0].id, otra.id, None, 999999)])
    assert all(not motor.evaluar_regla(sesion, ana, r).cumple for r in reglas)
    familias = {carreras[0].familia_id}
    for carrera in carreras[1:]:
        if carrera.familia_id in familias:
            continue
        familias.add(carrera.familia_id)
        agregar_eventos(sesion, ana, [('VISTA_CARRERA', carrera.id, FECHA_BD)])
        assert [motor.evaluar_regla(sesion, ana, r).cumple for r in reglas] == [True, len(familias) >= 3]
        if len(familias) == 3:
            break
