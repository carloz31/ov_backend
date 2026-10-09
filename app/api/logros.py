from fastapi import APIRouter

from app.dependencies import CuentaConsultada, SesionBD
from app.schemas.logros import LogrosCuenta
from app.services import logros as servicio_logros


router = APIRouter(tags=["Consultas"])


@router.get("/cuentas/{cuenta}/logros", response_model=LogrosCuenta)
def consultar_logros(cuenta_consultada: CuentaConsultada, sesion: SesionBD):
    return servicio_logros.logros_cuenta(sesion, cuenta_consultada)
