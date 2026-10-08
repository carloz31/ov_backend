from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enumerado
from app.models.enums import Rol


class Cuenta(Base):
    __tablename__ = "cuenta"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    rol: Mapped[Rol] = mapped_column(enumerado(Rol))


class VinculoFamiliar(Base):
    __tablename__ = "vinculo_familiar"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    estudiante_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    apoderado_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    carta_estudiante: Mapped[str | None] = mapped_column(Text)
    carta_apoderado: Mapped[str | None] = mapped_column(Text)
