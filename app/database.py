from collections.abc import Iterator
from pathlib import Path
import sqlite3

from fastapi import Request
from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session


RUTA_BASE = Path(__file__).resolve().parents[1] / "demo.db"
URL_BASE = f"sqlite:///{RUTA_BASE.as_posix()}"
VERSION_ESQUEMA = 4
MENSAJE_ESQUEMA_ANTERIOR = (
    "La base demo.db tiene un esquema anterior. Bórrala y vuelve a iniciar la aplicación."
)


class Base(DeclarativeBase):
    pass


def validar_version_esquema(motor_bd: Engine) -> None:
    """Inspecciona antes de create_all; nunca repara una base existente."""
    ruta = motor_bd.url.database
    if ruta and ruta != ":memory:" and not Path(ruta).exists():
        return
    try:
        with motor_bd.connect() as conexion:
            inspector = inspect(conexion)
            tablas = set(inspector.get_table_names())
            if ruta == ":memory:" and not tablas:
                return
            if tablas != set(Base.metadata.tables):
                raise RuntimeError(MENSAJE_ESQUEMA_ANTERIOR)
            versiones = conexion.execute(text("SELECT id, version FROM esquema_version")).all()
            if versiones != [(1, VERSION_ESQUEMA)]:
                raise RuntimeError(MENSAJE_ESQUEMA_ANTERIOR)
            # Registro v1 y v2 usan versión 4: sus nombres de tablas y columnas
            # deben coincidir antes de intentar sembrar o abrir la caché.
            for tabla in Base.metadata.sorted_tables:
                if {columna['name'] for columna in inspector.get_columns(tabla.name)} != set(tabla.columns.keys()):
                    raise RuntimeError(MENSAJE_ESQUEMA_ANTERIOR)
    except SQLAlchemyError as error:
        raise RuntimeError(MENSAJE_ESQUEMA_ANTERIOR) from error


def crear_motor_bd(url: str) -> Engine:
    motor_bd = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(motor_bd, "connect")
    def activar_claves_foraneas(conexion: sqlite3.Connection, registro) -> None:
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return motor_bd


def obtener_sesion(peticion: Request) -> Iterator[Session]:
    from app.contexto_consultas import ContextoConsultas

    with peticion.app.state.fabrica_sesiones() as sesion:
        sesion.info['contexto_consultas'] = ContextoConsultas(sesion)
        yield sesion
