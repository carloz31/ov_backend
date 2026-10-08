from typing import Literal

from pydantic import BaseModel

from app.models import Espacio, TipoActividad, Visibilidad
from app.schemas.comun import EstadoDisponibilidad


class ActividadCuenta(BaseModel):
    codigo: str
    titulo: str
    tipo: TipoActividad
    orden: int
    contenido: str
    visibilidad: Visibilidad
    visible: bool
    estado: Literal["BLOQUEADA", "DISPONIBLE", "EN_CURSO", "COMPLETADA"]


class BloqueActividades(BaseModel):
    codigo: str
    nombre: str
    numero: int
    espacio: Espacio
    estado: EstadoDisponibilidad
    actividades: list[ActividadCuenta]
