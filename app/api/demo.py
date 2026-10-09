from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.dependencies import SesionBD, ejecutar_accion
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
    """Opciones públicas para los formularios; la disponibilidad viene de las consultas por dominio."""
    return servicio_demo.consultar_catalogo(sesion)


@router.post("/reiniciar", response_model=ReinicioDemo)
def reiniciar_demo(sesion: SesionBD):
    ejecutar_accion(sesion, lambda: servicio_demo.reiniciar_demo(sesion))
    return ReinicioDemo(mensaje="Demo reiniciada")
