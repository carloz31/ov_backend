from fastapi import APIRouter

from app.dependencies import CuentaDemo, SesionBD
from app.schemas.logros import LogrosCuenta
from app.services import logros as servicio_logros


router = APIRouter(tags=["Consultas"])


@router.get("/cuentas/{cuenta}/logros", response_model=LogrosCuenta)
def consultar_logros(cuenta_demo: CuentaDemo, sesion: SesionBD):
    return servicio_logros.logros_cuenta(sesion, cuenta_demo)
