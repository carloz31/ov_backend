from fastapi import APIRouter

from app.dependencies import CuentaDemo, SesionBD
from app.schemas.actividades import BloqueActividades
from app.services import actividades as servicio_actividades


router = APIRouter(tags=["Consultas"])


@router.get("/cuentas/{cuenta}/actividades", response_model=list[BloqueActividades])
def consultar_actividades(cuenta_demo: CuentaDemo, sesion: SesionBD):
    return servicio_actividades.listar_bloques_cuenta(sesion, cuenta_demo)
