from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.exceptions import ErrorAccion, traducir_error_accion
from app.models import Cuenta
from app.services import cuentas as servicio_cuentas


SesionBD = Annotated[Session, Depends(obtener_sesion)]


def obtener_cuenta(cuenta: str, sesion: SesionBD) -> Cuenta:
    resultado = servicio_cuentas.obtener_cuenta(sesion, cuenta)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return resultado


CuentaConsultada = Annotated[Cuenta, Depends(obtener_cuenta)]


def ejecutar_accion(sesion: Session, operacion: Callable):
    try:
        with sesion.begin():
            return operacion()
    except ErrorAccion as error:
        raise traducir_error_accion(error) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail={
            "mensaje": "La acción entra en conflicto con el estado actual de la cuenta",
        }) from error
