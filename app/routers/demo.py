from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, obtener_sesion
from app.models import Actividad, Carrera, Conversacion, Cuenta, FamiliaCarrera, VinculoFamiliar
from app.schemas import ReinicioDemo
from app.seed import obtener_cargador_semilla
from app.contenido_registro import cargar_posiciones_registro


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
def consultar_catalogo(sesion: Annotated[Session, Depends(obtener_sesion)]):
    """Opciones públicas para los formularios; la disponibilidad viene de /estado."""
    cuentas = {cuenta.id: cuenta.codigo for cuenta in sesion.scalars(select(Cuenta))}
    return {
        "actividades": [
            {"codigo": actividad.codigo, "tipo": actividad.tipo,
             "puntaje_minimo": actividad.puntaje_minimo}
            for actividad in sesion.scalars(select(Actividad).order_by(Actividad.codigo))
        ],
        "carreras": [
            {"codigo": carrera.codigo, "nombre": carrera.nombre,
             "familia": familia.nombre}
            for carrera, familia in sesion.execute(
                select(Carrera, FamiliaCarrera).join(FamiliaCarrera).order_by(Carrera.codigo)
            )
        ],
        "conversaciones": [
            {"codigo": conversacion.codigo, "titulo": conversacion.titulo}
            for conversacion in sesion.scalars(select(Conversacion).order_by(Conversacion.codigo))
        ],
        "vinculos": [
            {"codigo": vinculo.codigo, "estudiante": cuentas[vinculo.estudiante_id],
             "apoderado": cuentas[vinculo.apoderado_id]}
            for vinculo in sesion.scalars(select(VinculoFamiliar).order_by(VinculoFamiliar.codigo))
        ],
    }


@router.post("/reiniciar", response_model=ReinicioDemo)
def reiniciar_demo(peticion: Request):
    try:
        semilla = peticion.app.state.semilla
        cargar = obtener_cargador_semilla(semilla)
        with peticion.app.state.motor_bd.begin() as conexion:
            # SQLite no inicia una transacción para DDL en su modo heredado.
            # BEGIN explícito permite restaurar también las tablas si falla la semilla.
            conexion.exec_driver_sql("BEGIN")
            Base.metadata.drop_all(conexion)
            Base.metadata.create_all(conexion)
            with Session(bind=conexion) as sesion:
                cargar(sesion)
                posiciones = cargar_posiciones_registro(sesion) if semilla == 'demo' else {}
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"mensaje": str(error)}) from error
    peticion.app.state.motor_bd.cache_definiciones.recargar()
    peticion.app.state.posiciones_registro = posiciones
    return ReinicioDemo(mensaje="Demo reiniciada")
