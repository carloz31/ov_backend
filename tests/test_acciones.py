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
    ("ingresar", {"cuenta": "no-existe"}),
    ("completar-actividad", {"cuenta": "est-ana", "actividad": "ACT-NO-EXISTE"}),
    ("ver-carrera", {"cuenta": "est-ana", "carrera": "CAR-NO-EXISTE"}),
    ("publicar-entrevista", {"autores": ["est-ana", "no-existe"], "resumen": "Autor desconocido"}),
])
def test_referencias_inexistentes_responden_404(cliente, sesion, nombre, cuerpo):
    assert cliente.post(f"/acciones/{nombre}", json=cuerpo).status_code == 404
    assert contar(sesion, modelos.EventoUso) == 0
    assert contar(sesion, modelos.Entrevista) == 0


def test_carta_se_actualiza_sin_repetir_evento(cliente, sesion):
    primera = post(cliente, "escribir-carta", cuenta="est-ana", texto="")
    segunda = post(cliente, "escribir-carta", cuenta="est-ana", texto="Texto actualizado")
    assert len(primera["eventos_registrados"]) == 1
    assert segunda == {"eventos_registrados": [], "nuevos_desbloqueos": []}
    vinculo = sesion.scalar(select(modelos.VinculoFamiliar))
    assert vinculo.carta_estudiante == "Texto actualizado"
    assert vinculo.carta_apoderado is None
    assert contar(sesion, modelos.EventoUso) == 1


def test_fecha_con_zona_conserva_calendario_simulado(cliente):
    primero = post(cliente, "check-in", cuenta="est-ana", nivel_seguridad=1, fecha_hora="2026-10-01T00:01:00+14:00")
    assert primero["eventos_registrados"][0]["fecha_hora"] == "2026-10-01T00:01:00"
    assert cliente.post("/acciones/check-in", json={"cuenta": "est-ana", "nivel_seguridad": 5,
                                                   "fecha_hora": "2026-10-01T23:59:00-05:00"}).status_code == 409


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
