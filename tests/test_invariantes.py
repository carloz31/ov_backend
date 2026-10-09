
from collections import Counter

from sqlalchemy import select

from app import models as modelos


FECHA = "2026-10-01T10:00:00"


def accion(cliente, nombre, cuenta="est-ana", **datos):
    cuerpo = {"fecha_hora": FECHA, **datos}
    if nombre != "publicar-entrevista":
        cuerpo["cuenta"] = cuenta
    respuesta = cliente.post(f"/acciones/{nombre}", json=cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def historial(cliente, cuenta):
    respuesta = cliente.get(f"/cuentas/{cuenta}/eventos")
    assert respuesta.status_code == 200, respuesta.text
    return Counter((evento["tipo"], evento["referencia"]) for evento in respuesta.json())


def filas(aplicacion, modelo):
    with aplicacion.state.fabrica_sesiones() as sesion:
        tabla = modelo.__table__
        return list(sesion.execute(select(tabla).order_by(*tabla.primary_key.columns)).tuples())


def test_check_in_unico_por_dia_con_aislamiento_entre_estudiantes(cliente, aplicacion):
    # Invariante 8: la unicidad es por cuenta y fecha, no global.
    for cuenta in ("est-ana", "est-luis"):
        accion(cliente, "check-in", cuenta, nivel_seguridad=3)
        antes = filas(aplicacion, modelos.CheckIn), filas(aplicacion, modelos.EventoUso)
        duplicado = cliente.post("/acciones/check-in", json={
            "cuenta": cuenta, "nivel_seguridad": 5, "fecha_hora": "2026-10-01T23:59:59",
        })
        assert duplicado.status_code == 409
        assert (filas(aplicacion, modelos.CheckIn), filas(aplicacion, modelos.EventoUso)) == antes
        accion(cliente, "check-in", cuenta, nivel_seguridad=1, fecha_hora="2026-10-02T00:00:00")
        assert historial(cliente, cuenta)[("REGISTRA_CHECK_IN", None)] == 2
    assert len(filas(aplicacion, modelos.CheckIn)) == 4
