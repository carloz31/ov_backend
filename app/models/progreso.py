from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Text, UniqueConstraint, false, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enumerado
from app.models.enums import EstadoProgreso, OrigenEntrada


class ProgresoActividad(Base):
    __tablename__ = "progreso_actividad"
    __table_args__ = (UniqueConstraint("cuenta_id", "actividad_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividad.id"))
    estado: Mapped[EstadoProgreso] = mapped_column(enumerado(EstadoProgreso))
    posicion: Mapped[str | None] = mapped_column(Text)


class ResultadoCaso(Base):
    __tablename__ = "resultado_caso"
    __table_args__ = (CheckConstraint("puntaje BETWEEN 0 AND 100"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    progreso_id: Mapped[int] = mapped_column(ForeignKey("progreso_actividad.id"))
    puntaje: Mapped[float]
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)


class EntradaDiario(Base):
    __tablename__ = "entrada_diario"
    __table_args__ = (
        Index(
            "entrada_guiada_unica", "cuenta_id", "pregunta_id", unique=True,
            sqlite_where=text("origen = 'GUIADA'"),
        ),
        CheckConstraint(
            "(origen = 'GUIADA' AND pregunta_id IS NOT NULL) OR "
            "(origen = 'LIBRE' AND pregunta_id IS NULL)",
            name="pregunta_segun_origen",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    origen: Mapped[OrigenEntrada] = mapped_column(enumerado(OrigenEntrada))
    pregunta_id: Mapped[int | None] = mapped_column(ForeignKey("pregunta_diario.id"))
    texto: Mapped[str] = mapped_column(Text)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)


class CheckIn(Base):
    __tablename__ = "check_in"
    __table_args__ = (
        UniqueConstraint("cuenta_id", "fecha"),
        CheckConstraint("nivel_seguridad BETWEEN 1 AND 5"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    fecha: Mapped[date] = mapped_column(Date)
    nivel_seguridad: Mapped[int]


class Entrevista(Base):
    __tablename__ = "entrevista"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    resumen: Mapped[str] = mapped_column(Text)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)


class EntrevistaAutor(Base):
    __tablename__ = "entrevista_autor"
    entrevista_id: Mapped[int] = mapped_column(ForeignKey("entrevista.id"), primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"), primary_key=True)


class ConversacionVinculo(Base):
    __tablename__ = "conversacion_vinculo"
    __table_args__ = (UniqueConstraint("vinculo_id", "conversacion_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    vinculo_id: Mapped[int] = mapped_column(ForeignKey("vinculo_familiar.id"))
    conversacion_id: Mapped[int] = mapped_column(ForeignKey("conversacion.id"))
    conversado: Mapped[bool] = mapped_column(default=False, server_default=false())
    conversado_en: Mapped[datetime | None] = mapped_column(DateTime)
