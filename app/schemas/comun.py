from typing import Literal

from pydantic import BaseModel


EstadoDisponibilidad = Literal["DISPONIBLE", "BLOQUEADA"]


class ContenidoEstado(BaseModel):
    codigo: str
    titulo: str
    estado: EstadoDisponibilidad
