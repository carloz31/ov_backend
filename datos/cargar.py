from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import Base
from datos import demo


def obtener_cargador_semilla(semilla: str):
    if semilla == 'demo':
        return demo.cargar_semilla
    if semilla == 'plataforma':
        from datos.plataforma import cargar_semilla_plataforma

        return cargar_semilla_plataforma
    raise ValueError('SEMILLA debe ser demo o plataforma')


def cargar_semilla_si_vacia(sesion: Session, semilla: str = 'demo') -> None:
    cargar = obtener_cargador_semilla(semilla)
    if any(
        sesion.execute(select(tabla).limit(1)).first() is not None
        for tabla in Base.metadata.sorted_tables
    ):
        return
    cargar(sesion)
