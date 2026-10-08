from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models import EstadoProgreso, OrigenEntrada, TipoEventoUso
from app.schemas.cuentas import EventoLegible
from app.schemas.motor import DesbloqueoNuevo


class FechaAccion(BaseModel):
    fecha_hora: datetime | None = None


class AccionCuenta(FechaAccion):
    cuenta: str


class CompletarActividadEntrada(AccionCuenta):
    actividad: str


class ReiniciarInstrumentoEntrada(AccionCuenta):
    instrumento: str
    aplicacion: str | None = None


class RespuestaItemEntrada(BaseModel):
    item: str
    opcion: int = Field(ge=1, strict=True)


class ResponderItemsEntrada(CompletarActividadEntrada):
    respuestas: list[RespuestaItemEntrada] = Field(min_length=1)

    @model_validator(mode="after")
    def validar_items_distintos(self):
        if len({respuesta.item for respuesta in self.respuestas}) != len(self.respuestas):
            raise ValueError("Los ítems no pueden repetirse en el mismo envío")
        return self


class RespuestaItemGuardada(BaseModel):
    item: str
    opcion: int


class ProgresoRespuestas(BaseModel):
    estado: EstadoProgreso
    respondidos: int
    total: int


class RespuestaItemsGuardados(BaseModel):
    cuenta: str
    actividad: str
    respuestas_guardadas: list[RespuestaItemGuardada]
    progreso: ProgresoRespuestas


class ResolverCasoEntrada(CompletarActividadEntrada):
    puntaje: float = Field(ge=0, le=100, allow_inf_nan=False)


class ResponderRegistroEntrada(AccionCuenta):
    clasificacion: Literal["ADECUADA", "VAGA"]
    ampliada: bool


class EscribirEntradaEntrada(AccionCuenta):
    origen: OrigenEntrada
    pregunta: str | None = None
    texto: str

    @model_validator(mode="after")
    def validar_pregunta(self):
        if self.origen == OrigenEntrada.GUIADA and self.pregunta is None:
            raise ValueError("Una entrada GUIADA requiere pregunta")
        if self.origen == OrigenEntrada.LIBRE and self.pregunta is not None:
            raise ValueError("Una entrada LIBRE no admite pregunta")
        return self


class CheckInEntrada(AccionCuenta):
    nivel_seguridad: int = Field(ge=1, le=5)


class VerCarreraEntrada(AccionCuenta):
    carrera: str


class PublicarEntrevistaEntrada(FechaAccion):
    autores: list[str] = Field(min_length=1)
    resumen: str

    @model_validator(mode="after")
    def validar_autores(self):
        if len(set(self.autores)) != len(self.autores):
            raise ValueError("Los autores no pueden repetirse")
        return self


class EscribirCartaEntrada(AccionCuenta):
    texto: str


class CompletarConversacionEntrada(AccionCuenta):
    conversacion: str


class EventoEntrada(AccionCuenta):
    tipo: TipoEventoUso
    referencia: str | None = None


class RespuestaAccion(BaseModel):
    eventos_registrados: list[EventoLegible]
    nuevos_desbloqueos: list[DesbloqueoNuevo]


class ResultadoGenerado(BaseModel):
    instrumento: str
    aplicacion: str


class RespuestaCompletarActividad(RespuestaAccion):
    resultados_generados: list[ResultadoGenerado]


class ResultadoAnulado(BaseModel):
    instrumento: str
    aplicacion: str
    calculado_en: datetime
    anulado_en: datetime


class RespuestaReiniciarInstrumento(RespuestaAccion):
    cuenta: str
    instrumento: str
    aplicacion: str
    resultado_anulado: ResultadoAnulado | None
    actividades_reiniciadas: list[str]


class RespuestaAgrupada(BaseModel):
    por_cuenta: dict[str, RespuestaAccion]
