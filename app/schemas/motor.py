from pydantic import BaseModel

from app.models import TipoConteo, TipoEventoUso, TipoObjetivo


class ObjetivoLegible(BaseModel):
    codigo: str
    nombre: str


class CondicionLegible(BaseModel):
    tipo_evento: TipoEventoUso
    referencia: str | None
    tipo_conteo: TipoConteo
    cantidad_minima: int


class ReglaLegible(BaseModel):
    regla: str
    nombre: str
    tipo_objetivo: TipoObjetivo
    objetivo: ObjetivoLegible
    condiciones: list[CondicionLegible]
    evaluador_especial: str | None


class ProgresoCondicion(BaseModel):
    tipo_evento: TipoEventoUso
    referencia: str | None
    tipo_conteo: TipoConteo
    actual: int
    requerido: int
    cumplida: bool


class ResultadoEvaluador(BaseModel):
    nombre: str
    cumplido: bool


class ResultadoRegla(BaseModel):
    cumple: bool
    condiciones: list[ProgresoCondicion]
    evaluador_especial: ResultadoEvaluador | None = None


class DesbloqueoNuevo(BaseModel):
    regla: str
    tipo_objetivo: TipoObjetivo
    objetivo: ObjetivoLegible
    condiciones: list[ProgresoCondicion]
    evaluador_especial: ResultadoEvaluador | None = None
