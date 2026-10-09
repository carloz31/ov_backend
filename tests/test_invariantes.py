from soporte_dominios import consultar_dominios

from collections import Counter

import pytest
from sqlalchemy import select

from app import models as modelos


FECHA = "2026-10-01T10:00:00"
RUTA_CIUDAD = ("ACT-01", "ACT-02", "ACT-03", "ACT-04", "ACT-05", "ACT-06", "ACT-12", "ACT-13")
RUTA_HELENA = ("HEL-01", "HEL-02", "HEL-03")
RUTA_FINAL = ("ACT-17", "ACT-18", "ACT-19")
CUENTAS = ("est-ana", "est-luis", "apo-rosa")


def accion(cliente, nombre, cuenta="est-ana", **datos):
    cuerpo = {"fecha_hora": FECHA, **datos}
    if nombre != "publicar-entrevista":
        cuerpo["cuenta"] = cuenta
    respuesta = cliente.post(f"/acciones/{nombre}", json=cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def completar(cliente, codigos, cuenta="est-ana"):
    for codigo in codigos:
        accion(cliente, "completar-actividad", cuenta, actividad=codigo)


def estado(cliente, cuenta="est-ana"):
    respuesta = cliente.get(f"/cuentas/{cuenta}/resumen")
    assert respuesta.status_code == 200, respuesta.text
    return consultar_dominios(cliente, cuenta, resumen=respuesta.json())


def historial(cliente, cuenta):
    respuesta = cliente.get(f"/cuentas/{cuenta}/eventos")
    assert respuesta.status_code == 200, respuesta.text
    return Counter((evento["tipo"], evento["referencia"]) for evento in respuesta.json())


def filas(aplicacion, modelo):
    with aplicacion.state.fabrica_sesiones() as sesion:
        tabla = modelo.__table__
        return list(sesion.execute(select(tabla).order_by(*tabla.primary_key.columns)).tuples())


def desbloqueos(aplicacion):
    with aplicacion.state.fabrica_sesiones() as sesion:
        return {(cuenta, regla): (identificador, fecha, visto)
                for cuenta, regla, identificador, fecha, visto in sesion.execute(select(
                    modelos.Cuenta.codigo, modelos.ReglaDesbloqueo.codigo,
                    modelos.Desbloqueo.id, modelos.Desbloqueo.fecha_hora, modelos.Desbloqueo.visto,
                ).join(modelos.Desbloqueo, modelos.Desbloqueo.cuenta_id == modelos.Cuenta.id)
                  .join(modelos.ReglaDesbloqueo, modelos.ReglaDesbloqueo.id == modelos.Desbloqueo.regla_id))}


def test_desbloqueos_unicos_permanentes_y_nivel_monotono_en_recorrido(cliente, aplicacion):
    # Invariantes 1, 2 y 9: observar persistencia y nivel después de cada acción real.
    pasos = [("completar-actividad", {"actividad": codigo}) for codigo in RUTA_CIUDAD + RUTA_HELENA]
    pasos += [("resolver-caso", {"actividad": "CASO-01", "puntaje": 85})]
    pasos += [("completar-actividad", {"actividad": codigo}) for codigo in RUTA_FINAL]
    pasos += [
        ("completar-actividad", {"cuenta": "est-luis", "actividad": "ACT-01"}),
        ("completar-actividad", {"cuenta": "apo-rosa", "actividad": "ACT-P01"}),
        ("completar-actividad", {"cuenta": "apo-rosa", "actividad": "ACT-P02"}),
        ("publicar-entrevista", {"autores": ["est-ana", "est-luis"], "resumen": "En conjunto"}),
        ("escribir-entrada", {"origen": "LIBRE", "texto": "Una reflexión"}),
        ("resolver-caso", {"actividad": "CASO-01", "puntaje": 0, "fecha_hora": "2026-09-01T10:00:00"}),
        ("completar-actividad", {"actividad": "ACT-01", "fecha_hora": "2026-09-01T10:00:00"}),
        ("ingresar", {}),
    ]
    anterior = {}
    niveles = [1]
    for nombre, datos in pasos:
        cuenta = datos.pop("cuenta", "est-ana")
        respuesta = accion(cliente, nombre, cuenta, **datos)
        actual = desbloqueos(aplicacion)
        assert anterior.items() <= actual.items(), "Se eliminó o modificó un desbloqueo existente"
        assert len(filas(aplicacion, modelos.Desbloqueo)) == len(actual), "Se duplicó (cuenta, regla)"
        resultados = respuesta.get("por_cuenta", {cuenta: respuesta})
        anunciados = {(autor, nuevo["regla"]) for autor, resultado in resultados.items()
                      for nuevo in resultado["nuevos_desbloqueos"]}
        assert anunciados == actual.keys() - anterior.keys()
        nivel = estado(cliente)["nivel_actual"]["numero"]
        assert nivel >= niveles[-1]
        niveles.append(nivel)
        # Desde el nivel 3 también comprobar que los eventos conservan el indicador visto.
        if nivel >= 3:
            assert cliente.post("/cuentas/est-ana/desbloqueos/marcar-vistos").status_code == 200
        anterior = desbloqueos(aplicacion)
    assert set(niveles) == {1, 2, 3, 4, 5}
    assert estado(cliente, "est-luis")["nivel_actual"]["numero"] == 1
    assert estado(cliente, "apo-rosa")["nivel_actual"] is None
    assert ("est-ana", "R-INS-INVESTIGADOR") in anterior
    assert ("est-luis", "R-INS-INVESTIGADOR") in anterior


@pytest.mark.parametrize("en_ciudad,nombre,actividad", [
    (False, "completar-actividad", "HEL-01"),
    (False, "resolver-caso", "CASO-01"),
    (True, "completar-actividad", "ACT-17"),
    (True, "completar-actividad", "HEL-02"),
    (True, "completar-actividad", "INV-01"),
    (True, "resolver-caso", "CASO-02"),
])
def test_actividad_bloqueada_no_altera_estado_ni_historial(cliente, aplicacion, en_ciudad, nombre, actividad):
    # Invariante 3: bloque contenedor, cadena propia y condición compuesta.
    if en_ciudad:
        completar(cliente, RUTA_CIUDAD)
    modelos_estado = (modelos.EventoUso, modelos.Desbloqueo, modelos.ProgresoActividad, modelos.ResultadoCaso)
    antes = {modelo: filas(aplicacion, modelo) for modelo in modelos_estado}
    estado_antes = estado(cliente)
    respuesta = cliente.post(f"/acciones/{nombre}", json={
        "cuenta": "est-ana", "actividad": actividad, "puntaje": 100, "fecha_hora": FECHA,
    })
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["progreso"]["disponible"] is False
    assert {modelo: filas(aplicacion, modelo) for modelo in modelos_estado} == antes
    assert estado(cliente) == estado_antes


def test_audiencias_se_conservan_tras_eventos_compartidos(cliente):
    # Invariante 4: verificar el estado después de avanzar, no solo en la semilla.
    completar(cliente, RUTA_CIUDAD)
    completar(cliente, ("ACT-P01", "ACT-P02"), "apo-rosa")
    for cuenta in ("est-ana", "apo-rosa"):
        accion(cliente, "escribir-carta", cuenta, texto="Carta familiar")
    accion(cliente, "completar-conversacion", "apo-rosa", conversacion="CONV-01")
    accion(cliente, "publicar-entrevista", autores=["est-ana", "est-luis"], resumen="En conjunto")
    for cuenta in CUENTAS:
        actual = estado(cliente, cuenta)
        bloques = {bloque["codigo"] for bloque in actual["bloques"]}
        actividades = {actividad["codigo"] for bloque in actual["bloques"] for actividad in bloque["actividades"]}
        insignias = {insignia["codigo"] for insignia in actual["insignias"]}
        assert "conversaciones" in actual
        if cuenta == "apo-rosa":
            assert bloques == {"P1"}
            assert actividades == {"ACT-P01", "ACT-P02"}
            assert insignias == {"INS-CONOZCO-MI-ROL"}
            assert actual["nivel_actual"] is None
            assert all(actual[campo] == [] for campo in ("fichas", "testimonios", "preguntas_diario", "niveles"))
        else:
            assert bloques == {"B0", "B1", "B3", "B5", "C1", "C2", "C3", "C4", "LAB", "REG"}
            assert actividades == set(RUTA_CIUDAD + RUTA_HELENA + RUTA_FINAL + ("CASO-01", "CASO-02", "COMP-13", "INV-01")) | {
                "LAB-AUT-E", "LAB-AUT-S", "LAB-HAB", "LAB-INT1", "LAB-INT2",
                "LAB-RIA1", "LAB-RIA2", "LAB-RIA3", "LAB-RIA4",
                "REG-ACT08",
            }
            assert "INS-CONOZCO-MI-ROL" not in insignias
            assert {ficha["codigo"] for ficha in actual["fichas"]} == {"FIC-PROFESIONES", "FIC-MERCADO", "FIC-INSTITUCIONES"}
            assert {testimonio["codigo"] for testimonio in actual["testimonios"]} == {"TES-HOSPITAL", "TES-OBRA"}
            assert {pregunta["codigo"] for pregunta in actual["preguntas_diario"]} == {"PD-HISTORIA", "PD-ASPIRACIONES", "PD-CONV-01"}
            assert {nivel["numero"] for nivel in actual["niveles"]} == {1, 2, 3, 4, 5}


def test_eventos_de_primera_vez_y_repeticiones_por_cuenta_y_referencia(cliente, aplicacion):
    # Invariantes 5, 6 y 7: todos los tipos de actividad y varias referencias/cuentas.
    completar(cliente, RUTA_CIUDAD + RUTA_HELENA)
    for codigo in ("CASO-01", "CASO-02"):
        accion(cliente, "resolver-caso", actividad=codigo, puntaje=80)
    ruta_ana = RUTA_CIUDAD + RUTA_HELENA + ("COMP-13", "INV-01") + RUTA_FINAL
    completar(cliente, ("COMP-13", "INV-01") + RUTA_FINAL)
    completar(cliente, RUTA_CIUDAD[:3], "est-luis")
    completar(cliente, ("ACT-P01", "ACT-P02"), "apo-rosa")
    antes = filas(aplicacion, modelos.ProgresoActividad)
    for cuenta, ruta in (("est-ana", ruta_ana), ("est-luis", RUTA_CIUDAD[:3]), ("apo-rosa", ("ACT-P01", "ACT-P02"))):
        completar(cliente, ruta, cuenta)
    for codigo in ("CASO-01", "CASO-02"):
        for puntaje in (0, 100):
            accion(cliente, "resolver-caso", actividad=codigo, puntaje=puntaje)
    assert filas(aplicacion, modelos.ProgresoActividad) == antes
    for cuenta in ("est-ana", "apo-rosa"):
        for texto in ("Primera carta", "Carta actualizada"):
            accion(cliente, "escribir-carta", cuenta, texto=texto)
    for codigo in ("CONV-01", "CONV-02"):
        accion(cliente, "completar-conversacion", "apo-rosa", conversacion=codigo)
    conversaciones = filas(aplicacion, modelos.ConversacionVinculo)
    for codigo in ("CONV-01", "CONV-02"):
        for cuenta in ("est-ana", "apo-rosa"):
            respuesta = accion(cliente, "completar-conversacion", cuenta, conversacion=codigo,
                               fecha_hora="2026-10-02T10:00:00")
            assert all(resultado == {"eventos_registrados": [], "nuevos_desbloqueos": []}
                       for resultado in respuesta["por_cuenta"].values())
    assert filas(aplicacion, modelos.ConversacionVinculo) == conversaciones
    tipos_unicos = {"COMPLETA_BLOQUE", "SUPERA_CASO", "ESCRIBE_CARTA", "COMPLETA_CONVERSACION"}
    for cuenta, bloques, ruta in (
        ("est-ana", ("B0", "B1", "B3", "B5", "C1", "C2", "C3", "C4"), ruta_ana),
        ("est-luis", ("B0",), RUTA_CIUDAD[:3]),
        ("apo-rosa", ("P1",), ("ACT-P01", "ACT-P02")),
    ):
        conteos = historial(cliente, cuenta)
        esperados = {("COMPLETA_BLOQUE", codigo): 1 for codigo in bloques}
        if cuenta != "est-luis":
            esperados[("ESCRIBE_CARTA", "VIN-ANA")] = 1
            esperados.update({("COMPLETA_CONVERSACION", codigo): 1 for codigo in ("CONV-01", "CONV-02")})
        if cuenta == "est-ana":
            esperados.update({("SUPERA_CASO", codigo): 1 for codigo in ("CASO-01", "CASO-02")})
        assert {clave: cantidad for clave, cantidad in conteos.items() if clave[0] in tipos_unicos} == esperados
        completadas = {("COMPLETA_ACTIVIDAD", codigo): 2 for codigo in ruta}
        if cuenta == "est-ana":
            completadas.update({("COMPLETA_ACTIVIDAD", codigo): 3 for codigo in ("CASO-01", "CASO-02")})
        assert {clave: cantidad for clave, cantidad in conteos.items() if clave[0] == "COMPLETA_ACTIVIDAD"} == completadas
        estados = {actividad["estado"] for bloque in estado(cliente, cuenta)["bloques"]
                   for actividad in bloque["actividades"] if ("COMPLETA_ACTIVIDAD", actividad["codigo"]) in completadas}
        assert estados == {"COMPLETADA"}
    assert len(filas(aplicacion, modelos.ResultadoCaso)) == 6


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


def test_diario_guiado_unico_por_cuenta_y_pregunta_y_libre_repetible(cliente, aplicacion):
    # Invariante 8: cambiar el día no permite responder otra vez la misma pregunta.
    for cuenta in ("est-ana", "est-luis"):
        completar(cliente, RUTA_CIUDAD[:5], cuenta)
        for pregunta in ("PD-HISTORIA", "PD-ASPIRACIONES"):
            accion(cliente, "escribir-entrada", cuenta, origen="GUIADA", pregunta=pregunta, texto="Respuesta")
            antes = filas(aplicacion, modelos.EntradaDiario), filas(aplicacion, modelos.EventoUso)
            duplicado = cliente.post("/acciones/escribir-entrada", json={
                "cuenta": cuenta, "origen": "GUIADA", "pregunta": pregunta,
                "texto": "Otra respuesta", "fecha_hora": "2026-10-02T10:00:00",
            })
            assert duplicado.status_code == 409
            assert (filas(aplicacion, modelos.EntradaDiario), filas(aplicacion, modelos.EventoUso)) == antes
        for _ in range(2):
            accion(cliente, "escribir-entrada", cuenta, origen="LIBRE", texto="Reflexión libre")
        conteos = historial(cliente, cuenta)
        assert conteos[("ESCRIBE_ENTRADA_DIARIO", None)] == 4
        assert conteos[("ESCRIBE_ENTRADA_LIBRE", None)] == 2
        assert all(pregunta["respondida"] for pregunta in estado(cliente, cuenta)["preguntas_diario"]
                   if pregunta["codigo"] in {"PD-HISTORIA", "PD-ASPIRACIONES"})
    assert len(filas(aplicacion, modelos.EntradaDiario)) == 8
