from pydantic import BaseModel

from app.schemas.comun import EstadoDisponibilidad


class ConversacionesEstado(BaseModel):
    estado: EstadoDisponibilidad
