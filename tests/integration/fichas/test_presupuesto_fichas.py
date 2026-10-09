"""Presupuesto fichas."""

from app import models as modelos


def peticion_contada(cliente, motor_bd, contador_consultas, metodo, ruta, datos=None, esperado=200):
    with contador_consultas(motor_bd) as contador:
        respuesta = cliente.request(metodo, ruta, json=datos)
    assert respuesta.status_code == esperado, respuesta.text
    return respuesta.json(), contador


def test_estado_no_crece_con_100_objetos_adicionales(cliente, aplicacion, contador_consultas):
    estado, antes = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                     "GET", "/cuentas/est-ana/fichas")
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        sesion.add_all([modelos.Ficha(codigo=f"FIC-SINT-{numero:03}", titulo="Ficha sintética", contenido="Prueba")
                       for numero in range(100)])
    ampliado, despues = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                         "GET", "/cuentas/est-ana/fichas")
    estado, ampliado = {"fichas": estado}, {"fichas": ampliado}
    assert despues.cantidad == antes.cantidad <= 10
    assert len(ampliado["fichas"]) == len(estado["fichas"]) + 100
    assert all(ficha["estado"] == "DISPONIBLE" for ficha in ampliado["fichas"] if ficha["codigo"].startswith("FIC-SINT-"))
