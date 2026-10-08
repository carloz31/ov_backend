from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, Text, UniqueConstraint, false, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.parametros import (
    CORRELACION_MINIMA, LIMITE_COINCIDENCIAS, UMBRAL_BEST_FIT, UMBRAL_GREAT_FIT,
)
from app.models.base import Base, enumerado
from app.models.enums import MomentoAplicacion, NivelAjuste, TipoResultado


class Instrumento(Base):
    __tablename__ = "instrumento"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    descripcion: Mapped[str] = mapped_column(Text)
    tipo_resultado: Mapped[TipoResultado] = mapped_column(enumerado(TipoResultado), default=TipoResultado.DESTACADAS)


class Dimension(Base):
    __tablename__ = "dimension"
    id: Mapped[int] = mapped_column(primary_key=True)
    instrumento_id: Mapped[int] = mapped_column(ForeignKey("instrumento.id"))
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    descripcion: Mapped[str] = mapped_column(Text)
    orden: Mapped[int]


class EscalaRespuesta(Base):
    __tablename__ = "escala_respuesta"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]


class OpcionEscala(Base):
    __tablename__ = "opcion_escala"
    __table_args__ = (UniqueConstraint("escala_id", "orden"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    escala_id: Mapped[int] = mapped_column(ForeignKey("escala_respuesta.id"))
    orden: Mapped[int]
    etiqueta: Mapped[str]
    puntaje: Mapped[float]


class ItemInstrumento(Base):
    __tablename__ = "item_instrumento"
    __table_args__ = (UniqueConstraint("instrumento_id", "numero"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    instrumento_id: Mapped[int] = mapped_column(ForeignKey("instrumento.id"))
    codigo: Mapped[str] = mapped_column(unique=True)
    numero: Mapped[int]
    enunciado: Mapped[str] = mapped_column(Text)
    dimension_id: Mapped[int | None] = mapped_column(ForeignKey("dimension.id"))
    escala_id: Mapped[int] = mapped_column(ForeignKey("escala_respuesta.id"))
    inverso: Mapped[bool] = mapped_column(default=False, server_default=false())


class ActividadItem(Base):
    __tablename__ = "actividad_item"
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividad.id"), primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item_instrumento.id"), primary_key=True)
    orden: Mapped[int]


class Aplicacion(Base):
    __tablename__ = "aplicacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    instrumento_id: Mapped[int] = mapped_column(ForeignKey("instrumento.id"))
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    momento: Mapped[MomentoAplicacion] = mapped_column(enumerado(MomentoAplicacion), default=MomentoAplicacion.UNICA)


class AplicacionActividad(Base):
    __tablename__ = "aplicacion_actividad"
    aplicacion_id: Mapped[int] = mapped_column(ForeignKey("aplicacion.id"), primary_key=True)
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividad.id"), primary_key=True)


class Ocupacion(Base):
    __tablename__ = "ocupacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str | None] = mapped_column(unique=True)
    codigo_onet: Mapped[str] = mapped_column(unique=True)
    titulo: Mapped[str]


class PuntajeOcupacion(Base):
    __tablename__ = "puntaje_ocupacion"
    ocupacion_id: Mapped[int] = mapped_column(ForeignKey("ocupacion.id"), primary_key=True)
    dimension_id: Mapped[int] = mapped_column(ForeignKey("dimension.id"), primary_key=True)
    valor: Mapped[float]


class CarreraOcupacion(Base):
    __tablename__ = "carrera_ocupacion"
    carrera_id: Mapped[int] = mapped_column(ForeignKey("carrera.id"), primary_key=True)
    ocupacion_id: Mapped[int] = mapped_column(ForeignKey("ocupacion.id"), primary_key=True)


class RespuestaItem(Base):
    __tablename__ = "respuesta_item"
    __table_args__ = (UniqueConstraint("progreso_id", "item_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    progreso_id: Mapped[int] = mapped_column(ForeignKey("progreso_actividad.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("item_instrumento.id"))
    opcion_id: Mapped[int] = mapped_column(ForeignKey("opcion_escala.id"))
    creada_en: Mapped[datetime] = mapped_column(DateTime)
    actualizada_en: Mapped[datetime] = mapped_column(DateTime)


class ResultadoInstrumento(Base):
    __tablename__ = "resultado_instrumento"
    __table_args__ = (
        Index("resultado_vigente_unico", "cuenta_id", "aplicacion_id", unique=True,
              sqlite_where=text("anulado_en IS NULL"), postgresql_where=text("anulado_en IS NULL")),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    aplicacion_id: Mapped[int] = mapped_column(ForeignKey("aplicacion.id"))
    calculado_en: Mapped[datetime] = mapped_column(DateTime)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime)
    perfil_plano: Mapped[bool] = mapped_column(default=False, server_default=false())


class ResultadoDimension(Base):
    __tablename__ = "resultado_dimension"
    resultado_id: Mapped[int] = mapped_column(ForeignKey("resultado_instrumento.id"), primary_key=True)
    dimension_id: Mapped[int] = mapped_column(ForeignKey("dimension.id"), primary_key=True)
    puntaje: Mapped[float]
    puntaje_maximo: Mapped[float]
    porcentaje: Mapped[float]


class Coincidencia(Base):
    __tablename__ = "coincidencia"
    __table_args__ = (
        UniqueConstraint("resultado_id", "posicion"),
        CheckConstraint(f"posicion BETWEEN 1 AND {LIMITE_COINCIDENCIAS}", name="posicion_valida"),
        CheckConstraint(
            f"(correlacion >= {UMBRAL_BEST_FIT} AND ajuste = 'BEST_FIT') OR "
            f"(correlacion >= {UMBRAL_GREAT_FIT} AND correlacion < {UMBRAL_BEST_FIT} AND ajuste = 'GREAT_FIT') OR "
            f"(correlacion >= {CORRELACION_MINIMA} AND correlacion < {UMBRAL_GREAT_FIT} AND ajuste = 'GOOD_FIT')",
            name="ajuste_segun_correlacion",
        ),
    )
    resultado_id: Mapped[int] = mapped_column(ForeignKey("resultado_instrumento.id"), primary_key=True)
    ocupacion_id: Mapped[int] = mapped_column(ForeignKey("ocupacion.id"), primary_key=True)
    posicion: Mapped[int]
    correlacion: Mapped[float]
    ajuste: Mapped[NivelAjuste] = mapped_column(enumerado(NivelAjuste))
