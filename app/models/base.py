from enum import StrEnum

from sqlalchemy import CheckConstraint, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def enumerado(clase: type[StrEnum]) -> Enum:
    return Enum(
        clase, native_enum=False, create_constraint=True, validate_strings=True,
        values_callable=lambda valores: [valor.value for valor in valores],
    )


class EsquemaVersion(Base):
    __tablename__ = "esquema_version"
    __table_args__ = (CheckConstraint("id = 1"),)
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    version: Mapped[int]
    semilla: Mapped[str]
