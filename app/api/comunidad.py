from fastapi import APIRouter

from app.dependencies import CuentaDemo, SesionBD
from app.schemas.comunidad import ConversacionesEstado
from app.services import comunidad as servicio_comunidad


router = APIRouter(tags=["Consultas"])


@router.get("/cuentas/{cuenta}/conversaciones", response_model=ConversacionesEstado)
def consultar_comunidad(cuenta_demo: CuentaDemo, sesion: SesionBD):
    return servicio_comunidad.estado_conversaciones(sesion, cuenta_demo)
