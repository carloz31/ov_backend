from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.dependencies import SesionBD
from app.schemas.demo import ReinicioDemo
from app.services import demo as servicio_demo


router = APIRouter(prefix="/demo", tags=["Demo"])
RUTA_ESTATICOS = Path(__file__).resolve().parents[1] / "static"


@router.get("", response_class=FileResponse, include_in_schema=False)
def mostrar_demo():
    return FileResponse(RUTA_ESTATICOS / "demo.html", media_type="text/html")


@router.get("/instrumentos", response_class=FileResponse, include_in_schema=False)
def mostrar_instrumentos():
    return FileResponse(RUTA_ESTATICOS / "instrumentos.html", media_type="text/html")


@router.get("/registro", response_class=FileResponse, include_in_schema=False)
def mostrar_registro():
    return FileResponse(RUTA_ESTATICOS / "registro.html", media_type="text/html")


@router.get("/catalogo")
def consultar_catalogo(sesion: SesionBD):
    """Opciones públicas para los formularios; la disponibilidad viene de /estado."""
    return servicio_demo.consultar_catalogo(sesion)


@router.post("/reiniciar", response_model=ReinicioDemo)
def reiniciar_demo(peticion: Request):
    try:
        posiciones = servicio_demo.reiniciar_demo(
            peticion.app.state.motor_bd, peticion.app.state.semilla,
            peticion.app.state.obtener_cargador_semilla,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"mensaje": str(error)}) from error
    servicio_demo.recargar_cache_demo(peticion.app.state.motor_bd)
    peticion.app.state.posiciones_registro = posiciones
    return ReinicioDemo(mensaje="Demo reiniciada")
