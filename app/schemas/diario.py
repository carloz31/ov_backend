from pydantic import BaseModel

from app.schemas.comun import EstadoDisponibilidad


class PreguntaDiarioEstado(BaseModel):
    codigo: str
    pregunta: str
    estado: EstadoDisponibilidad
    respondida: bool
