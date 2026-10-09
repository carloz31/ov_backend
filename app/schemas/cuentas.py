from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Rol, TipoEventoUso, TipoObjetivo
from app.schemas.motor import ObjetivoLegible, ProgresoCondicion, ResultadoEvaluador


class CuentaResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
    rol: Rol


class NivelActual(BaseModel):
    numero: int
    titulo: str


class ResumenCuenta(BaseModel):
    cuenta: CuentaResumen
    nivel_actual: NivelActual | None


class ObjetivoProgreso(BaseModel):
    tipo: TipoObjetivo
    codigo: str


class ProgresoRegla(BaseModel):
    regla: str
    cumplida: bool
    condiciones: list[ProgresoCondicion]
    evaluador_especial: ResultadoEvaluador | None = None


class ProgresoObjetivo(BaseModel):
    objetivo: ObjetivoProgreso
    disponible: bool
    reglas: list[ProgresoRegla]


class EventoLegible(BaseModel):
    tipo: TipoEventoUso
    referencia: str | None
    fecha_hora: datetime


class DesbloqueoLegible(BaseModel):
    regla: str
    tipo_objetivo: TipoObjetivo
    objetivo: ObjetivoLegible
    fecha_hora: datetime
    visto: bool


class DesbloqueosMarcados(BaseModel):
    marcados: int
