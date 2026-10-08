from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, enumerado
from app.models.enums import TipoConteo, TipoEventoUso, TipoObjetivo


class EventoUso(Base):
    __tablename__ = "evento_uso"
    __table_args__ = (Index("evento_cuenta_tipo", "cuenta_id", "tipo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    tipo: Mapped[TipoEventoUso] = mapped_column(enumerado(TipoEventoUso))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    id_referencia: Mapped[int | None]


class ReglaDesbloqueo(Base):
    __tablename__ = "regla_desbloqueo"
    __table_args__ = (
        CheckConstraint(
            "(tipo_objetivo = 'CONVERSACIONES' AND id_objetivo IS NULL) OR "
            "(tipo_objetivo != 'CONVERSACIONES' AND id_objetivo IS NOT NULL)",
            name="objetivo_segun_tipo",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    tipo_objetivo: Mapped[TipoObjetivo] = mapped_column(enumerado(TipoObjetivo))
    id_objetivo: Mapped[int | None]
    evaluador_especial: Mapped[str | None]
    parametro_evaluador: Mapped[int | None] = mapped_column(default=None)
    condiciones: Mapped[list["CondicionDesbloqueo"]] = relationship(
        back_populates="regla", order_by="CondicionDesbloqueo.id", lazy="selectin",
    )


class CondicionDesbloqueo(Base):
    __tablename__ = "condicion_desbloqueo"
    __table_args__ = (CheckConstraint("cantidad_minima >= 1"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    regla_id: Mapped[int] = mapped_column(ForeignKey("regla_desbloqueo.id"))
    tipo_evento: Mapped[TipoEventoUso] = mapped_column(enumerado(TipoEventoUso))
    id_referencia: Mapped[int | None]
    tipo_conteo: Mapped[TipoConteo] = mapped_column(enumerado(TipoConteo))
    cantidad_minima: Mapped[int]
    regla: Mapped[ReglaDesbloqueo] = relationship(back_populates="condiciones")


class Desbloqueo(Base):
    __tablename__ = "desbloqueo"
    __table_args__ = (UniqueConstraint("cuenta_id", "regla_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    regla_id: Mapped[int] = mapped_column(ForeignKey("regla_desbloqueo.id"))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    visto: Mapped[bool] = mapped_column(default=False, server_default=false())
