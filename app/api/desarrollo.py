from fastapi import APIRouter

from app.dependencies import SesionBD, ejecutar_accion
from app.schemas.desarrollo import ReinicioDesarrollo
from app.services import desarrollo as servicio_desarrollo


router = APIRouter(prefix="/desarrollo", tags=["Desarrollo"])


@router.post("/reiniciar", response_model=ReinicioDesarrollo)
def reiniciar(sesion: SesionBD):
    ejecutar_accion(sesion, lambda: servicio_desarrollo.reiniciar_estado(sesion))
    return ReinicioDesarrollo(mensaje="Datos de prueba reiniciados")
