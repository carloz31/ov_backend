"""Contratos del registro: respuestas públicas y auditoría de demo separadas."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.models import EstadoProgreso
from app.models.enums import ClasificacionRespuesta, EstadoRespuestaRegistro, OrigenEvaluacion
from app.schemas.acciones import CompletarActividadEntrada, RespuestaAccion


class GuardarPosicionEntrada(CompletarActividadEntrada):
    posicion: str


class AccionItemRegistroEntrada(CompletarActividadEntrada):
    item: str


class TextoRegistroEntrada(AccionItemRegistroEntrada):
    texto: str


class ResponderSeguimientoEntrada(TextoRegistroEntrada):
    orden: Annotated[int, Field(strict=True, ge=1, le=2)] | None = None


class PosicionGuardada(BaseModel):
    posicion: str
    estado: EstadoProgreso


class EstadoItemRegistro(BaseModel):
    item: str
    estado: EstadoRespuestaRegistro


class MensajeRespuestaRegistro(BaseModel):
    tipo: Literal['respuesta'] = 'respuesta'
    texto: str
    orden: int | None = None
    borrador: bool | None = None


class MensajePreguntaRegistro(BaseModel):
    tipo: Literal['pregunta'] = 'pregunta'
    orden: int
    texto: str


MensajeRegistro = Annotated[MensajeRespuestaRegistro | MensajePreguntaRegistro, Field(discriminator='tipo')]


class RespuestaEnvioRegistro(EstadoItemRegistro, RespuestaAccion):
    conversacion: list[MensajeRegistro]


class ItemRegistroPublico(BaseModel):
    codigo: str
    nombre: str
    consigna: str
    min_caracteres: int
    obligatorio: bool


class RespuestaRegistroPublica(EstadoItemRegistro):
    conversacion: list[MensajeRegistro]


class RegistroConsultado(BaseModel):
    posicion: str | None
    estado: EstadoProgreso | None
    respuestas: list[RespuestaRegistroPublica]


class EvaluacionRegistroDemo(BaseModel):
    item: str
    numero: int
    origen: OrigenEvaluacion
    clasificacion: ClasificacionRespuesta
    criterios_faltantes: list[str]
    pregunta_generada: str | None
    requiere_atencion: bool
    modelo: str | None
    version_prompt: str | None
    latencia_ms: int | None
    error: str | None
    texto_evaluado: str
    fecha_hora: datetime
