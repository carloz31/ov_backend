from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.exceptions import ErrorAccion, traducir_error_accion


SesionBD = Annotated[Session, Depends(obtener_sesion)]


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
