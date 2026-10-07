from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import EstadoProgreso, Espacio, OrigenEntrada, Rol, TipoConteo, TipoEventoUso, TipoObjetivo


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


class ReinicioDemo(BaseModel):
    mensaje: str


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


EstadoDisponibilidad = Literal["DISPONIBLE", "BLOQUEADA"]


class CuentaResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
    rol: Rol


class NivelActual(BaseModel):
    numero: int
    titulo: str


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


class ContenidoEstado(BaseModel):
    codigo: str
    titulo: str
    estado: EstadoDisponibilidad


class PreguntaDiarioEstado(BaseModel):
    codigo: str
    pregunta: str
    estado: EstadoDisponibilidad
    respondida: bool


class ConversacionesEstado(BaseModel):
    estado: EstadoDisponibilidad


class InsigniaEstado(BaseModel):
    codigo: str
    nombre: str
    descripcion: str | None
    requisito: str | None
    estado: Literal["BLOQUEADA", "OBTENIDA"]


class NivelEstado(NivelActual):
    estado: Literal["BLOQUEADO", "OBTENIDO"]


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
