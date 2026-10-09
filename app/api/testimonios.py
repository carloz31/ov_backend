from fastapi import APIRouter

from app.dependencies import CuentaConsultada, SesionBD
from app.schemas.comun import ContenidoEstado
from app.services import testimonios as servicio_testimonios


router = APIRouter(tags=["Consultas"])


@router.get("/cuentas/{cuenta}/testimonios", response_model=list[ContenidoEstado])
def consultar_testimonios(cuenta_consultada: CuentaConsultada, sesion: SesionBD):
    return servicio_testimonios.listar_testimonios_cuenta(sesion, cuenta_consultada)
