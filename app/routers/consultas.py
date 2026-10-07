from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.consultas import (
    estado_cuenta, listar_cuentas, listar_desbloqueos, listar_eventos,
    listar_reglas, marcar_desbloqueos_vistos, progreso_objetivo,
)
from app.database import obtener_sesion
from app.models import Cuenta, TipoObjetivo
from app.schemas import (
    CuentaResumen, DesbloqueoLegible, DesbloqueosMarcados, EstadoCuenta,
    EventoLegible, ProgresoObjetivo, ReglaLegible,
)


router = APIRouter(tags=["Consultas"])
SesionBD = Annotated[Session, Depends(obtener_sesion)]


def obtener_cuenta_demo(cuenta: str, sesion: SesionBD) -> Cuenta:
    resultado = sesion.scalar(select(Cuenta).where(Cuenta.codigo == cuenta))
    if resultado is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return resultado


CuentaDemo = Annotated[Cuenta, Depends(obtener_cuenta_demo)]


@router.get("/reglas", response_model=list[ReglaLegible])
def consultar_reglas(sesion: SesionBD):
    return listar_reglas(sesion)


@router.get("/cuentas", response_model=list[CuentaResumen])
def consultar_cuentas(sesion: SesionBD):
    return listar_cuentas(sesion)


@router.get("/cuentas/{cuenta}/estado", response_model=EstadoCuenta)
def consultar_estado(cuenta_demo: CuentaDemo, sesion: SesionBD):
    return estado_cuenta(sesion, cuenta_demo)


@router.get(
    "/cuentas/{cuenta}/progreso/{tipo_objetivo}/{codigo}",
    response_model=ProgresoObjetivo, response_model_exclude_unset=True,
)
def consultar_progreso(cuenta_demo: CuentaDemo, tipo_objetivo: TipoObjetivo, codigo: str, sesion: SesionBD):
    try:
        return progreso_objetivo(sesion, cuenta_demo, tipo_objetivo, codigo)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.get("/cuentas/{cuenta}/eventos", response_model=list[EventoLegible])
def consultar_eventos(cuenta_demo: CuentaDemo, sesion: SesionBD):
    return listar_eventos(sesion, cuenta_demo)


@router.get("/cuentas/{cuenta}/desbloqueos", response_model=list[DesbloqueoLegible])
def consultar_desbloqueos(cuenta_demo: CuentaDemo, sesion: SesionBD, solo_no_vistos: bool = False):
    return listar_desbloqueos(sesion, cuenta_demo, solo_no_vistos)


@router.post("/cuentas/{cuenta}/desbloqueos/marcar-vistos", response_model=DesbloqueosMarcados)
def marcar_vistos(cuenta_demo: CuentaDemo, sesion: SesionBD):
    cantidad = marcar_desbloqueos_vistos(sesion, cuenta_demo)
    sesion.commit()
    return DesbloqueosMarcados(marcados=cantidad)
