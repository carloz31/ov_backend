from sqlalchemy import CheckConstraint, ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enumerado
from app.models.enums import Audiencia, Espacio, TipoActividad, Visibilidad


class Bloque(Base):
    __tablename__ = "bloque"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    numero: Mapped[int]
    nombre: Mapped[str]
    espacio: Mapped[Espacio] = mapped_column(enumerado(Espacio))
    audiencia: Mapped[Audiencia] = mapped_column(enumerado(Audiencia))


class Actividad(Base):
    __tablename__ = "actividad"
    __table_args__ = (
        CheckConstraint(
            "(tipo = 'CASO' AND puntaje_minimo BETWEEN 0 AND 100 "
            "AND puntaje_minimo IS NOT NULL) OR "
            "(tipo != 'CASO' AND puntaje_minimo IS NULL)",
            name="puntaje_minimo_solo_caso",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    titulo: Mapped[str]
    tipo: Mapped[TipoActividad] = mapped_column(enumerado(TipoActividad))
    contenido: Mapped[str]
    visibilidad: Mapped[Visibilidad] = mapped_column(
        enumerado(Visibilidad), default=Visibilidad.SIEMPRE, server_default=text("'SIEMPRE'"),
    )
    orden: Mapped[int]
    bloque_id: Mapped[int] = mapped_column(ForeignKey("bloque.id"))
    puntaje_minimo: Mapped[float | None]


class Ficha(Base):
    __tablename__ = "ficha"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    titulo: Mapped[str]
    contenido: Mapped[str] = mapped_column(Text)


class Testimonio(Base):
    __tablename__ = "testimonio"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    titulo: Mapped[str]
    descripcion: Mapped[str] = mapped_column(Text)
    enlace: Mapped[str]


class PreguntaDiario(Base):
    __tablename__ = "pregunta_diario"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    pregunta: Mapped[str] = mapped_column(Text)


class Conversacion(Base):
    __tablename__ = "conversacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    titulo: Mapped[str]
    tema: Mapped[str] = mapped_column(Text)


class Insignia(Base):
    __tablename__ = "insignia"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    descripcion: Mapped[str] = mapped_column(Text)
    requisito: Mapped[str] = mapped_column(Text)
    es_oculta: Mapped[bool]
    audiencia: Mapped[Audiencia] = mapped_column(enumerado(Audiencia))


class Nivel(Base):
    __tablename__ = "nivel"
    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(unique=True)
    titulo: Mapped[str]


class FamiliaCarrera(Base):
    __tablename__ = "familia_carrera"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]


class Carrera(Base):
    __tablename__ = "carrera"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    familia_id: Mapped[int] = mapped_column(ForeignKey("familia_carrera.id"))
