from fastapi import APIRouter

from app.dependencies import CuentaDemo, SesionBD
from app.schemas.diario import PreguntaDiarioEstado
from app.services import diario as servicio_diario


router = APIRouter(tags=["Consultas"])


@router.get("/cuentas/{cuenta}/diario/preguntas", response_model=list[PreguntaDiarioEstado])
def consultar_diario(cuenta_demo: CuentaDemo, sesion: SesionBD):
    return servicio_diario.listar_preguntas_cuenta(sesion, cuenta_demo)
