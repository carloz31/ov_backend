"""Consultas publicas."""

from datetime import datetime
from sqlalchemy import select
from app import models as modelos
from app.services.motor.reglas import registrar_eventos


FECHA = datetime(2026, 10, 1, 10)


def buscar(sesion, modelo, codigo):
    entidad = sesion.scalar(select(modelo).where(modelo.codigo == codigo))
    assert entidad is not None
    return entidad


def test_lista_cuentas_con_codigos_publicos(cliente):
    respuesta = cliente.get("/cuentas")
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"codigo": "apo-rosa", "nombre": "Rosa", "rol": "APODERADO"},
        {"codigo": "est-ana", "nombre": "Ana", "rol": "ESTUDIANTE"},
        {"codigo": "est-luis", "nombre": "Luis", "rol": "ESTUDIANTE"},
    ]


def test_validacion_de_tipo_y_filtro(cliente):
    assert cliente.get("/cuentas/est-ana/progreso/NO_EXISTE/ACT-01").status_code == 422
    assert cliente.get("/cuentas/est-ana/desbloqueos?solo_no_vistos=incorrecto").status_code == 422
    assert cliente.post("/cuentas/no-existe/desbloqueos/marcar-vistos").status_code == 404


def test_eventos_diario_y_check_in_no_exponen_ids(sesion, cliente):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    entrada = modelos.EntradaDiario(cuenta_id=ana.id, origen=modelos.OrigenEntrada.LIBRE,
                                   texto="Una entrada", fecha_hora=FECHA)
    check_in = modelos.CheckIn(cuenta_id=ana.id, fecha=FECHA.date(), nivel_seguridad=3)
    sesion.add_all([entrada, check_in])
    sesion.flush()
    registrar_eventos(sesion, ana, [
        (modelos.TipoEventoUso.ESCRIBE_ENTRADA_DIARIO, entrada.id),
        (modelos.TipoEventoUso.ESCRIBE_ENTRADA_LIBRE, entrada.id),
        (modelos.TipoEventoUso.REGISTRA_CHECK_IN, check_in.id),
    ], FECHA)
    sesion.commit()
    respuesta = cliente.get("/cuentas/est-ana/eventos")
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 3
    assert all(evento["referencia"] is None for evento in respuesta.json())
    assert all("id_referencia" not in evento for evento in respuesta.json())
