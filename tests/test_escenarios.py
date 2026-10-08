import pytest
from sqlalchemy import func, select

from app import models as modelos
from app.services.motor.reglas import evaluar_regla


FECHA = "2026-10-01T10:00:00"


@pytest.fixture
def reinicio(cliente):
    assert cliente.post("/demo/reiniciar").status_code == 200


def accion(cliente, nombre, cuerpo):
    respuesta = cliente.post(f"/acciones/{nombre}", json={"fecha_hora": FECHA, **cuerpo})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def completar(cliente, actividad, cuenta="est-ana"):
    return accion(cliente, "completar-actividad", {"cuenta": cuenta, "actividad": actividad})


def nuevos_codigos(respuesta):
    return {nuevo["regla"] for nuevo in respuesta["nuevos_desbloqueos"]}


def eventos(respuesta):
    return [(evento["tipo"], evento["referencia"]) for evento in respuesta["eventos_registrados"]]


def estado(cliente, cuenta="est-ana"):
    respuesta = cliente.get(f"/cuentas/{cuenta}/estado")
    assert respuesta.status_code == 200
    return respuesta.json()


def actividades(cliente):
    return {actividad["codigo"]: actividad["estado"]
            for bloque in estado(cliente)["bloques"] for actividad in bloque["actividades"]}


def progreso(cliente, tipo, codigo, cuenta="est-ana"):
    respuesta = cliente.get(f"/cuentas/{cuenta}/progreso/{tipo}/{codigo}")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def completar_inicio(cliente):
    for codigo in ("ACT-01", "ACT-02", "ACT-03"):
        respuesta = completar(cliente, codigo)
    return respuesta


def llevar_a_ana_a_la_ciudad(cliente):
    completar_inicio(cliente)
    for codigo in ("ACT-04", "ACT-05", "ACT-06", "ACT-12", "ACT-13"):
        respuesta = completar(cliente, codigo)
    return respuesta


def llevar_a_ana_a_e8(cliente):
    llevar_a_ana_a_la_ciudad(cliente)
    for codigo in ("HEL-01", "HEL-02", "HEL-03"):
        respuesta = completar(cliente, codigo)
    return respuesta


def resolver(cliente, puntaje):
    return accion(cliente, "resolver-caso", {"cuenta": "est-ana", "actividad": "CASO-01", "puntaje": puntaje})


def llevar_a_ana_a_e9(cliente):
    llevar_a_ana_a_e8(cliente)
    for puntaje in (50, 85, 95):
        resolver(cliente, puntaje)


def llevar_familia_a_e10(cliente):
    llevar_a_ana_a_la_ciudad(cliente)
    for cuenta in ("est-ana", "apo-rosa"):
        accion(cliente, "escribir-carta", {"cuenta": cuenta, "texto": "Una carta"})
    for codigo in ("ACT-P01", "ACT-P02"):
        completar(cliente, codigo, "apo-rosa")


def test_e1_estado_inicial(cliente):
    assert cliente.post("/demo/reiniciar").status_code == 200
    respuesta = cliente.get("/cuentas/est-ana/estado")
    assert respuesta.status_code == 200
    ana = respuesta.json()
    actividades = {actividad["codigo"]: actividad["estado"]
                   for bloque in ana["bloques"] for actividad in bloque["actividades"]}
    assert len(actividades) == 28
    originales = {codigo: estado for codigo, estado in actividades.items() if not codigo.startswith(("LAB-", "REG-"))}
    assert len(originales) == 18
    assert actividades["ACT-01"] == "DISPONIBLE"
    assert all(estado == "BLOQUEADA" for codigo, estado in originales.items() if codigo != "ACT-01")
    assert {codigo: estado for codigo, estado in actividades.items() if codigo.startswith("LAB-")} == {
        "LAB-AUT-E": "DISPONIBLE", "LAB-AUT-S": "BLOQUEADA", "LAB-HAB": "DISPONIBLE",
        "LAB-INT1": "DISPONIBLE", "LAB-INT2": "BLOQUEADA", "LAB-RIA1": "DISPONIBLE",
        "LAB-RIA2": "BLOQUEADA", "LAB-RIA3": "BLOQUEADA", "LAB-RIA4": "BLOQUEADA",
    }
    bloques = {bloque["codigo"]: bloque for bloque in ana["bloques"]}
    assert all(bloques[codigo]["estado"] == "BLOQUEADA" for codigo in ("C1", "C2", "C3", "C4"))
    assert ana["nivel_actual"]["numero"] == 1
    for coleccion in ("fichas", "testimonios", "preguntas_diario"):
        assert ana[coleccion]
        assert all(contenido["estado"] == "BLOQUEADA" for contenido in ana[coleccion])
    assert ana["conversaciones"] == {"estado": "BLOQUEADA"}
    assert "ACT-P01" not in actividades
    assert not any(insignia["codigo"] == "INS-CONOZCO-MI-ROL" for insignia in ana["insignias"])
    ocultas = [insignia for insignia in ana["insignias"] if insignia["codigo"] == "???"]
    assert len(ocultas) == 4
    assert all(insignia == {
        "codigo": "???", "nombre": "Logro oculto", "descripcion": None,
        "requisito": None, "estado": "BLOQUEADA",
    } for insignia in ocultas)
    assert all(insignia["requisito"] for insignia in ana["insignias"] if insignia["codigo"] != "???")

    respuesta = cliente.get("/cuentas/apo-rosa/estado")
    assert respuesta.status_code == 200
    rosa = respuesta.json()
    assert [bloque["codigo"] for bloque in rosa["bloques"]] == ["P1"]
    assert {actividad["codigo"]: actividad["estado"] for bloque in rosa["bloques"]
            for actividad in bloque["actividades"]} == {"ACT-P01": "DISPONIBLE", "ACT-P02": "BLOQUEADA"}
    assert [insignia["codigo"] for insignia in rosa["insignias"]] == ["INS-CONOZCO-MI-ROL"]
    assert rosa["conversaciones"] == {"estado": "BLOQUEADA"}
    assert rosa["nivel_actual"] is None
    assert all(rosa[coleccion] == [] for coleccion in ("fichas", "testimonios", "preguntas_diario", "niveles"))


def test_e2_primer_desbloqueo(cliente, reinicio):
    respuesta = completar(cliente, "ACT-01")
    assert nuevos_codigos(respuesta) == {"R-ACT-02"}
    condicion = respuesta["nuevos_desbloqueos"][0]["condiciones"][0]
    assert (condicion["actual"], condicion["requerido"], condicion["cumplida"]) == (1, 1, True)
    assert actividades(cliente)["ACT-01"] == "COMPLETADA"
    assert actividades(cliente)["ACT-02"] == "DISPONIBLE"


def test_e3_intento_de_saltarse_la_ruta(cliente, reinicio):
    respuesta = cliente.post("/acciones/completar-actividad", json={"cuenta": "est-ana", "actividad": "ACT-04"})
    assert respuesta.status_code == 409
    regla = respuesta.json()["detail"]["progreso"]["reglas"][0]
    assert regla["regla"] == "R-ACT-04"
    assert regla["condiciones"] == [{"tipo_evento": "COMPLETA_ACTIVIDAD", "referencia": "ACT-03",
                                     "tipo_conteo": "EVENTOS", "actual": 0, "requerido": 1, "cumplida": False}]
    assert cliente.get("/cuentas/est-ana/eventos").json() == []


def test_e4_un_evento_varios_desbloqueos(cliente, reinicio):
    completar(cliente, "ACT-01")
    completar(cliente, "ACT-02")
    respuesta = completar(cliente, "ACT-03")
    assert eventos(respuesta) == [("COMPLETA_ACTIVIDAD", "ACT-03"), ("COMPLETA_BLOQUE", "B0")]
    assert nuevos_codigos(respuesta) == {"R-ACT-04", "R-INS-PRIMER-PASO", "R-NIV-2"}
    assert estado(cliente)["nivel_actual"]["numero"] == 2


def test_e5_rehacer_no_suma(cliente, reinicio, sesion):
    completar_inicio(cliente)
    for _ in range(5):
        respuesta = completar(cliente, "ACT-01")
        assert eventos(respuesta) == [("COMPLETA_ACTIVIDAD", "ACT-01")]
        assert nuevos_codigos(respuesta) == set()
    ana = sesion.scalar(select(modelos.Cuenta).where(modelos.Cuenta.codigo == "est-ana"))
    regla = sesion.scalar(select(modelos.ReglaDesbloqueo).where(modelos.ReglaDesbloqueo.codigo == "R-LOG-INCANSABLE"))
    condicion = evaluar_regla(sesion, ana, regla).condiciones[0]
    assert (condicion.actual, condicion.requerido, condicion.tipo_conteo) == (3, 8, modelos.TipoConteo.REFERENCIAS_DISTINTAS)
    assert cliente.get("/cuentas/est-ana/progreso/INSIGNIA/LOG-INCANSABLE").status_code == 403
    assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso).where(
        modelos.EventoUso.tipo == modelos.TipoEventoUso.COMPLETA_ACTIVIDAD)) == 8
    assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso).where(
        modelos.EventoUso.tipo == modelos.TipoEventoUso.COMPLETA_BLOQUE)) == 1
    assert actividades(cliente)["ACT-01"] == "COMPLETADA"


def test_e6_dias_distintos(cliente, reinicio):
    cuerpo = {"cuenta": "est-ana", "nivel_seguridad": 3, "fecha_hora": FECHA}
    accion(cliente, "check-in", cuerpo)
    repetida = cliente.post("/acciones/check-in", json={**cuerpo, "fecha_hora": "2026-10-01T23:00:00"})
    assert repetida.status_code == 409
    accion(cliente, "check-in", {**cuerpo, "fecha_hora": "2026-10-02T10:00:00"})
    respuesta = accion(cliente, "check-in", {**cuerpo, "fecha_hora": "2026-10-03T10:00:00"})
    assert nuevos_codigos(respuesta) == {"R-LOG-CONSTANCIA"}
    logro = next(insignia for insignia in estado(cliente)["insignias"] if insignia["codigo"] == "LOG-CONSTANCIA")
    assert logro["nombre"] == "Constancia" and logro["descripcion"]
    assert logro["estado"] == "OBTENIDA"


def test_e7_llegada_a_la_ciudad(cliente, reinicio):
    completar_inicio(cliente)
    for codigo, regla in (("ACT-04", "R-PD-HISTORIA"), ("ACT-05", "R-PD-ASPIRACIONES"),
                          ("ACT-06", None), ("ACT-12", "R-FIC-PROFESIONES")):
        respuesta = completar(cliente, codigo)
        if regla is not None:
            assert regla in nuevos_codigos(respuesta)
    respuesta = completar(cliente, "ACT-13")
    assert nuevos_codigos(respuesta) == {"R-CIUDAD-C1", "R-CIUDAD-C2", "R-CIUDAD-C3", "R-CIUDAD-C4",
                                        "R-INS-CIUDAD", "R-FIC-MERCADO", "R-NIV-3", "R-LOG-INCANSABLE"}
    actuales = actividades(cliente)
    assert all(actuales[codigo] == "DISPONIBLE" for codigo in ("HEL-01", "HEL-03", "CASO-01", "COMP-13"))
    assert all(actuales[codigo] == "BLOQUEADA" for codigo in ("HEL-02", "CASO-02", "INV-01"))
    assert estado(cliente)["conversaciones"]["estado"] == "BLOQUEADA"
    regla = next(regla for regla in progreso(cliente, "CONVERSACIONES", "-")["reglas"]
                 if regla["regla"] == "R-FAM-ESTUDIANTE")
    assert [condicion["actual"] for condicion in regla["condiciones"]] == [0, 1]
    assert [condicion["cumplida"] for condicion in regla["condiciones"]] == [False, True]


def test_e8_condicion_compuesta_con_varias_actividades(cliente, reinicio):
    llevar_a_ana_a_la_ciudad(cliente)
    regla = progreso(cliente, "ACTIVIDAD", "ACT-17")["reglas"][0]
    assert [condicion["cumplida"] for condicion in regla["condiciones"]] == [True, False]
    assert regla["condiciones"][1]["actual"] == 0
    completar(cliente, "HEL-01")
    completar(cliente, "HEL-02")
    respuesta = completar(cliente, "HEL-03")
    assert ("COMPLETA_BLOQUE", "C1") in eventos(respuesta)
    assert nuevos_codigos(respuesta) == {"R-ACT-17"}
    assert actividades(cliente)["ACT-17"] == "DISPONIBLE"


def test_e9_casos_intento_fallido_reintento_y_repeticion(cliente, reinicio, sesion):
    llevar_a_ana_a_e8(cliente)
    respuesta = resolver(cliente, 50)
    assert actividades(cliente)["CASO-01"] == "COMPLETADA"
    assert nuevos_codigos(respuesta) == {"R-CASO-02"}
    assert eventos(respuesta) == [("COMPLETA_ACTIVIDAD", "CASO-01")]
    assert next(testimonio for testimonio in estado(cliente)["testimonios"]
                if testimonio["codigo"] == "TES-HOSPITAL")["estado"] == "BLOQUEADA"
    assert sesion.scalar(select(func.count()).select_from(modelos.ResultadoCaso)) == 1
    respuesta = resolver(cliente, 85)
    assert ("SUPERA_CASO", "CASO-01") in eventos(respuesta)
    assert nuevos_codigos(respuesta) == {"R-TES-HOSPITAL", "R-INS-PRIMER-CASO", "R-INV-01", "R-NIV-4"}
    respuesta = resolver(cliente, 95)
    assert eventos(respuesta) == [("COMPLETA_ACTIVIDAD", "CASO-01")]
    assert nuevos_codigos(respuesta) == set()
    assert sesion.scalar(select(func.count()).select_from(modelos.ResultadoCaso)) == 3
    assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso).where(
        modelos.EventoUso.tipo == modelos.TipoEventoUso.SUPERA_CASO)) == 1


def test_e10_cuentas_familia_avanzan_a_destiempo(cliente, reinicio):
    llevar_a_ana_a_la_ciudad(cliente)
    respuesta = accion(cliente, "escribir-carta", {"cuenta": "est-ana", "texto": "Carta de Ana"})
    assert nuevos_codigos(respuesta) == {"R-FAM-ESTUDIANTE"}
    assert estado(cliente)["conversaciones"]["estado"] == "DISPONIBLE"
    assert estado(cliente, "apo-rosa")["conversaciones"]["estado"] == "BLOQUEADA"
    respuesta = accion(cliente, "escribir-carta", {"cuenta": "apo-rosa", "texto": "Carta de Rosa"})
    assert nuevos_codigos(respuesta) == set()
    regla = next(regla for regla in progreso(cliente, "CONVERSACIONES", "-", "apo-rosa")["reglas"]
                 if regla["regla"] == "R-FAM-APODERADO")
    assert [condicion["actual"] for condicion in regla["condiciones"]] == [1, 0]
    completar(cliente, "ACT-P01", "apo-rosa")
    respuesta = completar(cliente, "ACT-P02", "apo-rosa")
    assert nuevos_codigos(respuesta) == {"R-FAM-APODERADO", "R-INS-CONOZCO-MI-ROL"}


def test_e11_una_accion_desbloqueos_en_dos_cuentas(cliente, reinicio):
    llevar_familia_a_e10(cliente)
    respuesta = accion(cliente, "completar-conversacion", {"cuenta": "apo-rosa", "conversacion": "CONV-01"})
    assert set(respuesta["por_cuenta"]) == {"est-ana", "apo-rosa"}
    for cuenta in ("est-ana", "apo-rosa"):
        assert eventos(respuesta["por_cuenta"][cuenta]) == [("COMPLETA_CONVERSACION", "CONV-01")]
    assert nuevos_codigos(respuesta["por_cuenta"]["est-ana"]) == {"R-PD-CONV-01"}
    assert nuevos_codigos(respuesta["por_cuenta"]["apo-rosa"]) == set()
    respuesta = accion(cliente, "completar-conversacion", {"cuenta": "est-ana", "conversacion": "CONV-01"})
    assert all(eventos(resultado) == [] and nuevos_codigos(resultado) == set()
               for resultado in respuesta["por_cuenta"].values())
    for cuenta in ("est-ana", "apo-rosa"):
        historial = cliente.get(f"/cuentas/{cuenta}/eventos").json()
        assert len([evento for evento in historial if evento["tipo"] == "COMPLETA_CONVERSACION"]) == 1


def test_e12_coautoria(cliente, reinicio, sesion):
    respuesta = accion(cliente, "publicar-entrevista", {"autores": ["est-ana", "est-luis"], "resumen": "Una entrevista conjunta"})
    assert set(respuesta["por_cuenta"]) == {"est-ana", "est-luis"}
    referencias = set()
    for resultado in respuesta["por_cuenta"].values():
        assert nuevos_codigos(resultado) == {"R-INS-INVESTIGADOR"}
        assert len(eventos(resultado)) == 1
        tipo, referencia = eventos(resultado)[0]
        assert tipo == "PUBLICA_ENTREVISTA" and referencia.startswith("ENT-")
        referencias.add(referencia)
    assert len(referencias) == 1
    assert sesion.scalar(select(func.count()).select_from(modelos.Entrevista)) == 1
    assert sesion.scalar(select(func.count()).select_from(modelos.EntrevistaAutor)) == 2


def test_e13_evaluador_especial(cliente, reinicio):
    for carrera in ("CAR-ENF", "CAR-MED", "CAR-CIV"):
        respuesta = accion(cliente, "ver-carrera", {"cuenta": "est-ana", "carrera": carrera})
        assert nuevos_codigos(respuesta) == set()
    regla = progreso(cliente, "INSIGNIA", "INS-EXPLORADOR")["reglas"][0]
    assert regla["condiciones"][0]["cumplida"] is True
    assert regla["evaluador_especial"]["cumplido"] is False
    respuesta = accion(cliente, "ver-carrera", {"cuenta": "est-ana", "carrera": "CAR-DIS"})
    assert nuevos_codigos(respuesta) == {"R-INS-EXPLORADOR"}
    assert respuesta["nuevos_desbloqueos"][0]["evaluador_especial"]["cumplido"] is True
    assert progreso(cliente, "INSIGNIA", "INS-EXPLORADOR")["reglas"][0]["cumplida"] is True


def test_e14_diario(cliente, reinicio, sesion):
    llevar_a_ana_a_la_ciudad(cliente)
    cuerpo = {"cuenta": "est-ana", "origen": "GUIADA", "pregunta": "PD-HISTORIA", "texto": "Lo que descubrí"}
    accion(cliente, "escribir-entrada", cuerpo)
    assert cliente.post("/acciones/escribir-entrada", json=cuerpo).status_code == 409
    respuesta = accion(cliente, "escribir-entrada", {"cuenta": "est-ana", "origen": "LIBRE", "texto": "Una reflexión libre"})
    assert eventos(respuesta) == [("ESCRIBE_ENTRADA_DIARIO", None), ("ESCRIBE_ENTRADA_LIBRE", None)]
    assert nuevos_codigos(respuesta) == {"R-LOG-PLUMA"}
    assert sesion.scalar(select(func.count()).select_from(modelos.EntradaDiario)) == 2
    bloqueada = cliente.post("/acciones/escribir-entrada", json={**cuerpo, "pregunta": "PD-CONV-01"})
    assert bloqueada.status_code == 409
    assert bloqueada.json()["detail"]["progreso"]["reglas"][0]["regla"] == "R-PD-CONV-01"


def test_e15_respuestas_reflexivas(cliente, reinicio):
    for indice, (clasificacion, ampliada) in enumerate((("VAGA", False), ("VAGA", True), ("ADECUADA", False), ("ADECUADA", False))):
        respuesta = accion(cliente, "responder-registro", {"cuenta": "est-ana", "clasificacion": clasificacion, "ampliada": ampliada})
        assert eventos(respuesta) == ([] if indice == 0 else [("RESPUESTA_REFLEXIVA", None)])
        assert nuevos_codigos(respuesta) == ({"R-LOG-PENSADOR"} if indice == 3 else set())


def test_e16_hasta_el_nivel_5(cliente, reinicio):
    llevar_a_ana_a_e9(cliente)
    completar(cliente, "ACT-17")
    respuesta = completar(cliente, "ACT-18")
    assert nuevos_codigos(respuesta) == {"R-ACT-19", "R-NIV-5"}
    assert estado(cliente)["nivel_actual"]["numero"] == 5
    assert len(estado(cliente)["niveles"]) == 5
    assert all(nivel["estado"] == "OBTENIDO" for nivel in estado(cliente)["niveles"])


def test_e17_novedades_no_vistas(cliente, reinicio):
    completar(cliente, "ACT-01")
    ruta = "/cuentas/est-ana/desbloqueos"
    assert len(cliente.get(f"{ruta}?solo_no_vistos=true").json()) == 1
    assert cliente.post(f"{ruta}/marcar-vistos").status_code == 200
    assert cliente.get(f"{ruta}?solo_no_vistos=true").json() == []
