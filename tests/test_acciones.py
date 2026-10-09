from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app import models as modelos
from app.services import comun as acciones


FECHA = "2026-10-01T10:00:00"


def post(cliente, nombre, **cuerpo):
    respuesta = cliente.post(f"/acciones/{nombre}", json={"fecha_hora": FECHA, **cuerpo})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def contar(sesion, modelo):
    return sesion.scalar(select(func.count()).select_from(modelo))


def abrir_ciudad_cruda(cliente):
    respuesta = cliente.post("/eventos", json={"cuenta": "est-ana", "tipo": "COMPLETA_ACTIVIDAD",
                                               "referencia": "ACT-13", "fecha_hora": FECHA})
    assert respuesta.status_code == 200


def habilitar_rosa(cliente):
    post(cliente, "completar-actividad", cuenta="apo-rosa", actividad="ACT-P01")
    post(cliente, "completar-actividad", cuenta="apo-rosa", actividad="ACT-P02")
    post(cliente, "escribir-carta", cuenta="apo-rosa", texto="Carta de Rosa")


def test_ingresar_repite_eventos_y_usa_hora_actual_de_lima(cliente):
    zona = timezone(timedelta(hours=-5))
    antes = datetime.now(zona).replace(tzinfo=None)
    respuesta = cliente.post("/acciones/ingresar", json={"cuenta": "est-ana"})
    despues = datetime.now(zona).replace(tzinfo=None)
    assert respuesta.status_code == 200
    registro = respuesta.json()["eventos_registrados"][0]
    assert registro["tipo"] == "INGRESO" and registro["referencia"] is None
    assert antes <= datetime.fromisoformat(registro["fecha_hora"]) <= despues
    assert respuesta.json()["nuevos_desbloqueos"] == []
    post(cliente, "ingresar", cuenta="est-ana")
    assert len(cliente.get("/cuentas/est-ana/eventos").json()) == 2


@pytest.mark.parametrize("nombre,cuerpo", [
    ("resolver-caso", {"actividad": "ACT-01", "puntaje": -1}),
    ("resolver-caso", {"actividad": "ACT-01", "puntaje": 101}),
    ("resolver-caso", {"actividad": "ACT-01", "puntaje": "nan"}),
    ("check-in", {"nivel_seguridad": 0}),
    ("check-in", {"nivel_seguridad": 6}),
    ("check-in", {"nivel_seguridad": 2.5}),
    ("escribir-entrada", {"origen": "GUIADA", "texto": "Sin pregunta"}),
    ("escribir-entrada", {"origen": "LIBRE", "pregunta": "PD-HISTORIA", "texto": "Con pregunta"}),
    ("responder-registro", {"clasificacion": "OTRA", "ampliada": False}),
    ("ingresar", {"fecha_hora": "fecha-invalida"}),
    ("publicar-entrevista", {"autores": [], "resumen": "Vacía"}),
    ("publicar-entrevista", {"autores": ["est-ana", "est-ana"], "resumen": "Duplicada"}),
])
def test_entradas_invalidas_no_generan_estado(cliente, sesion, nombre, cuerpo):
    respuesta = cliente.post(f"/acciones/{nombre}", json={"cuenta": "est-ana", **cuerpo})
    assert respuesta.status_code == 422
    for modelo in (modelos.EventoUso, modelos.Desbloqueo, modelos.ProgresoActividad,
                   modelos.ResultadoCaso, modelos.EntradaDiario, modelos.CheckIn, modelos.Entrevista):
        assert contar(sesion, modelo) == 0


@pytest.mark.parametrize("nombre,cuerpo", [
    ("completar-actividad", {"cuenta": "apo-rosa", "actividad": "ACT-01"}),
    ("escribir-entrada", {"cuenta": "apo-rosa", "origen": "LIBRE", "texto": "No permitida"}),
    ("check-in", {"cuenta": "apo-rosa", "nivel_seguridad": 3}),
    ("publicar-entrevista", {"autores": ["est-ana", "apo-rosa"], "resumen": "No permitida"}),
    ("escribir-carta", {"cuenta": "est-luis", "texto": "Sin vínculo"}),
    ("completar-conversacion", {"cuenta": "est-luis", "conversacion": "CONV-01"}),
    ("resolver-caso", {"cuenta": "est-ana", "actividad": "ACT-01", "puntaje": 70}),
])
def test_accion_no_permitida_responde_409_sin_efectos(cliente, sesion, nombre, cuerpo):
    respuesta = cliente.post(f"/acciones/{nombre}", json=cuerpo)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["mensaje"]
    for modelo in (modelos.EventoUso, modelos.Desbloqueo, modelos.ProgresoActividad,
                   modelos.ResultadoCaso, modelos.EntradaDiario, modelos.CheckIn, modelos.Entrevista,
                   modelos.ConversacionVinculo):
        assert contar(sesion, modelo) == 0


@pytest.mark.parametrize("nombre,cuerpo", [
    ("ingresar", {"cuenta": "no-existe"}),
    ("completar-actividad", {"cuenta": "est-ana", "actividad": "ACT-NO-EXISTE"}),
    ("ver-carrera", {"cuenta": "est-ana", "carrera": "CAR-NO-EXISTE"}),
    ("publicar-entrevista", {"autores": ["est-ana", "no-existe"], "resumen": "Autor desconocido"}),
])
def test_referencias_inexistentes_responden_404(cliente, sesion, nombre, cuerpo):
    assert cliente.post(f"/acciones/{nombre}", json=cuerpo).status_code == 404
    assert contar(sesion, modelos.EventoUso) == 0
    assert contar(sesion, modelos.Entrevista) == 0


def test_completar_caso_mediante_actividad_no_crea_intento(cliente, sesion):
    abrir_ciudad_cruda(cliente)
    respuesta = cliente.post("/acciones/completar-actividad", json={"cuenta": "est-ana", "actividad": "CASO-01"})
    assert respuesta.status_code == 409
    assert contar(sesion, modelos.ResultadoCaso) == 0
    assert contar(sesion, modelos.ProgresoActividad) == 0
    assert contar(sesion, modelos.EventoUso) == 1


def test_puntaje_minimo_inclusivo_y_extremos_validos(cliente, sesion):
    abrir_ciudad_cruda(cliente)
    respuestas = [post(cliente, "resolver-caso", cuenta="est-ana", actividad="CASO-01", puntaje=puntaje)
                  for puntaje in (0, 70, 100)]
    assert not any(evento["tipo"] == "SUPERA_CASO" for evento in respuestas[0]["eventos_registrados"])
    assert any(evento["tipo"] == "SUPERA_CASO" for evento in respuestas[1]["eventos_registrados"])
    assert not any(evento["tipo"] == "SUPERA_CASO" for evento in respuestas[2]["eventos_registrados"])
    assert contar(sesion, modelos.ResultadoCaso) == 3


def test_carta_se_actualiza_sin_repetir_evento(cliente, sesion):
    primera = post(cliente, "escribir-carta", cuenta="est-ana", texto="")
    segunda = post(cliente, "escribir-carta", cuenta="est-ana", texto="Texto actualizado")
    assert len(primera["eventos_registrados"]) == 1
    assert segunda == {"eventos_registrados": [], "nuevos_desbloqueos": []}
    vinculo = sesion.scalar(select(modelos.VinculoFamiliar))
    assert vinculo.carta_estudiante == "Texto actualizado"
    assert vinculo.carta_apoderado is None
    assert contar(sesion, modelos.EventoUso) == 1


def test_conversacion_solo_exige_disponibilidad_de_quien_marca(cliente, sesion):
    habilitar_rosa(cliente)
    assert cliente.get("/cuentas/est-ana/conversaciones").json()["estado"] == "BLOQUEADA"
    primera = post(cliente, "completar-conversacion", cuenta="apo-rosa", conversacion="CONV-01")
    assert {nuevo["regla"] for nuevo in primera["por_cuenta"]["est-ana"]["nuevos_desbloqueos"]} == {"R-PD-CONV-01"}
    segunda = post(cliente, "completar-conversacion", cuenta="apo-rosa", conversacion="CONV-01",
                   fecha_hora="2026-10-03T10:00:00")
    assert all(resultado["eventos_registrados"] == [] for resultado in segunda["por_cuenta"].values())
    conversacion = sesion.scalar(select(modelos.ConversacionVinculo))
    assert conversacion.conversado_en == datetime.fromisoformat(FECHA)
    assert cliente.post("/acciones/completar-conversacion", json={
        "cuenta": "est-ana", "conversacion": "CONV-01",
    }).status_code == 409


def test_fecha_con_zona_conserva_calendario_simulado(cliente):
    primero = post(cliente, "check-in", cuenta="est-ana", nivel_seguridad=1, fecha_hora="2026-10-01T00:01:00+14:00")
    assert primero["eventos_registrados"][0]["fecha_hora"] == "2026-10-01T00:01:00"
    assert cliente.post("/acciones/check-in", json={"cuenta": "est-ana", "nivel_seguridad": 5,
                                                   "fecha_hora": "2026-10-01T23:59:00-05:00"}).status_code == 409


def test_eventos_crudos_omiten_dominio_sin_modificar_progresos(cliente, sesion):
    respuesta = cliente.post("/eventos", json={"cuenta": "est-ana", "tipo": "COMPLETA_ACTIVIDAD",
                                               "referencia": "ACT-04", "fecha_hora": FECHA})
    assert respuesta.status_code == 200
    assert {nuevo["regla"] for nuevo in respuesta.json()["nuevos_desbloqueos"]} == {"R-ACT-05", "R-PD-HISTORIA"}
    assert contar(sesion, modelos.ProgresoActividad) == 0
    assert respuesta.json()["eventos_registrados"] == [{"tipo": "COMPLETA_ACTIVIDAD", "referencia": "ACT-04", "fecha_hora": FECHA}]
    respuesta = cliente.post("/eventos", json={"cuenta": "apo-rosa", "tipo": "PUBLICA_ENTREVISTA"})
    assert respuesta.status_code == 200
    assert respuesta.json()["nuevos_desbloqueos"] == []
    assert contar(sesion, modelos.Entrevista) == 0


@pytest.mark.parametrize("cuerpo,estado_http", [
    ({"tipo": "NO_EXISTE"}, 422),
    ({"tipo": "COMPLETA_ACTIVIDAD", "referencia": "CAR-ENF"}, 404),
    ({"tipo": "COMPLETA_ACTIVIDAD", "referencia": 1}, 422),
    ({"tipo": "REGISTRA_CHECK_IN", "referencia": "CHECK-01"}, 422),
    ({"tipo": "INGRESO", "referencia": "ACT-01"}, 422),
])
def test_referencias_de_eventos_invalidas_no_se_registran(cliente, sesion, cuerpo, estado_http):
    respuesta = cliente.post("/eventos", json={"cuenta": "est-ana", **cuerpo})
    assert respuesta.status_code == estado_http
    assert contar(sesion, modelos.EventoUso) == 0


def test_fallo_despues_de_evaluar_revierte_completar_actividad(cliente, sesion, monkeypatch):
    original = acciones.registrar_eventos

    def fallar(sesion, cuenta, eventos, fecha):
        original(sesion, cuenta, eventos, fecha)
        raise RuntimeError("Fallo después de evaluar")

    monkeypatch.setattr(acciones, "registrar_eventos", fallar)
    with pytest.raises(RuntimeError, match="Fallo después de evaluar"):
        cliente.post("/acciones/completar-actividad", json={"cuenta": "est-ana", "actividad": "ACT-01"})
    assert contar(sesion, modelos.ProgresoActividad) == 0
    assert contar(sesion, modelos.EventoUso) == 0
    assert contar(sesion, modelos.Desbloqueo) == 0


def test_fallo_segundo_autor_revierte_entrevista_completa(cliente, sesion, monkeypatch):
    original = acciones.registrar_eventos

    def fallar_con_luis(sesion, cuenta, eventos, fecha):
        nuevos = original(sesion, cuenta, eventos, fecha)
        if cuenta.codigo == "est-luis":
            raise RuntimeError("Fallo con segundo autor")
        return nuevos

    monkeypatch.setattr(acciones, "registrar_eventos", fallar_con_luis)
    with pytest.raises(RuntimeError, match="Fallo con segundo autor"):
        cliente.post("/acciones/publicar-entrevista", json={"autores": ["est-ana", "est-luis"], "resumen": "Conjunto"})
    for modelo in (modelos.Entrevista, modelos.EntrevistaAutor, modelos.EventoUso, modelos.Desbloqueo):
        assert contar(sesion, modelo) == 0


def test_fallo_segunda_cuenta_revierte_conversacion_y_novedades(cliente, sesion, monkeypatch):
    habilitar_rosa(cliente)
    antes_eventos = contar(sesion, modelos.EventoUso)
    antes_desbloqueos = contar(sesion, modelos.Desbloqueo)
    original = acciones.registrar_eventos

    def fallar_con_rosa(sesion, cuenta, eventos, fecha):
        nuevos = original(sesion, cuenta, eventos, fecha)
        if cuenta.codigo == "apo-rosa":
            raise RuntimeError("Fallo con segunda cuenta")
        return nuevos

    monkeypatch.setattr(acciones, "registrar_eventos", fallar_con_rosa)
    with pytest.raises(RuntimeError, match="Fallo con segunda cuenta"):
        cliente.post("/acciones/completar-conversacion", json={"cuenta": "apo-rosa", "conversacion": "CONV-01"})
    assert contar(sesion, modelos.ConversacionVinculo) == 0
    assert contar(sesion, modelos.EventoUso) == antes_eventos
    assert contar(sesion, modelos.Desbloqueo) == antes_desbloqueos
