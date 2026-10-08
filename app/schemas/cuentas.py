from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models import Espacio, Rol, TipoEventoUso, TipoObjetivo
from app.schemas.comun import ContenidoEstado, EstadoDisponibilidad
from app.schemas.comunidad import ConversacionesEstado
from app.schemas.diario import PreguntaDiarioEstado
from app.schemas.logros import InsigniaEstado, NivelEstado
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


class ActividadEstado(BaseModel):
    codigo: str
    titulo: str
    estado: Literal["BLOQUEADA", "DISPONIBLE", "EN_CURSO", "COMPLETADA"]


class BloqueEstado(BaseModel):
    codigo: str
    nombre: str
    espacio: Espacio
    estado: EstadoDisponibilidad
    actividades: list[ActividadEstado]


class EstadoCuenta(BaseModel):
    cuenta: CuentaResumen
    nivel_actual: NivelActual | None
    bloques: list[BloqueEstado]
    fichas: list[ContenidoEstado]
    testimonios: list[ContenidoEstado]
    preguntas_diario: list[PreguntaDiarioEstado]
    conversaciones: ConversacionesEstado
    insignias: list[InsigniaEstado]
    niveles: list[NivelEstado]


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
