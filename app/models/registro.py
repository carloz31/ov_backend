from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enumerado
from app.models.enums import ClasificacionRespuesta, EstadoRespuestaRegistro, OrigenEvaluacion


class ItemRegistro(Base):
    __tablename__ = "item_registro"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    consigna: Mapped[str] = mapped_column(Text)
    min_caracteres: Mapped[int]
    obligatorio: Mapped[bool]
    repregunta_generica: Mapped[str] = mapped_column(Text)


class CriterioCompletitud(Base):
    __tablename__ = "criterio_completitud"
    __table_args__ = (UniqueConstraint("item_registro_id", "codigo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_registro_id: Mapped[int] = mapped_column(ForeignKey("item_registro.id"))
    codigo: Mapped[str]
    descripcion: Mapped[str] = mapped_column(Text)
    orden: Mapped[int]


class ActividadItemRegistro(Base):
    __tablename__ = "actividad_item_registro"
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividad.id"), primary_key=True)
    item_registro_id: Mapped[int] = mapped_column(ForeignKey("item_registro.id"), primary_key=True)
    orden: Mapped[int]


class RespuestaRegistro(Base):
    __tablename__ = "respuesta_registro"
    __table_args__ = (UniqueConstraint("progreso_id", "item_registro_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    progreso_id: Mapped[int] = mapped_column(ForeignKey("progreso_actividad.id"))
    item_registro_id: Mapped[int] = mapped_column(ForeignKey("item_registro.id"))
    texto_inicial: Mapped[str] = mapped_column(Text)
    estado: Mapped[EstadoRespuestaRegistro] = mapped_column(enumerado(EstadoRespuestaRegistro))
    clasificacion_inicial: Mapped[ClasificacionRespuesta | None] = mapped_column(enumerado(ClasificacionRespuesta))
    ampliada: Mapped[bool] = mapped_column(default=False, server_default=false())
    creada_en: Mapped[datetime] = mapped_column(DateTime)
    actualizada_en: Mapped[datetime] = mapped_column(DateTime)


class TurnoSeguimiento(Base):
    __tablename__ = "turno_seguimiento"
    __table_args__ = (
        UniqueConstraint("respuesta_id", "orden"),
        CheckConstraint("orden IN (1, 2)", name="orden_seguimiento_valido"),
        CheckConstraint("json_type(criterios_objetivo) = 'array'", name="criterios_objetivo_lista"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    respuesta_id: Mapped[int] = mapped_column(ForeignKey("respuesta_registro.id"))
    orden: Mapped[int]
    pregunta: Mapped[str] = mapped_column(Text)
    criterios_objetivo: Mapped[list[str]] = mapped_column(JSON(none_as_null=True))
    respuesta: Mapped[str | None] = mapped_column(Text)
    respondido_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime)


class EvaluacionRespuesta(Base):
    __tablename__ = "evaluacion_respuesta"
    __table_args__ = (
        CheckConstraint("numero >= 1 AND numero = CAST(numero AS INTEGER)", name="numero_evaluacion_valido"),
        CheckConstraint("json_type(criterios_faltantes) = 'array'", name="criterios_faltantes_lista"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    respuesta_id: Mapped[int] = mapped_column(ForeignKey("respuesta_registro.id"))
    numero: Mapped[int]
    origen: Mapped[OrigenEvaluacion] = mapped_column(enumerado(OrigenEvaluacion))
    clasificacion: Mapped[ClasificacionRespuesta] = mapped_column(enumerado(ClasificacionRespuesta))
    criterios_faltantes: Mapped[list[str]] = mapped_column(JSON(none_as_null=True))
    pregunta_generada: Mapped[str | None] = mapped_column(Text)
    requiere_atencion: Mapped[bool] = mapped_column(default=False, server_default=false())
    modelo: Mapped[str | None]
    version_prompt: Mapped[str | None]
    latencia_ms: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(Text)
    texto_evaluado: Mapped[str] = mapped_column(Text)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
