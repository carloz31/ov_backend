import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import Request
from sqlalchemy import Engine, String, create_engine, event, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import FunctionElement


class TipoJSON(FunctionElement):
    """Tipo del valor JSON exterior; compartido por modelos y migraciones."""

    type = String()
    inherit_cache = True


@compiles(TipoJSON, 'sqlite')
def compilar_tipo_json_sqlite(elemento, compilador, **opciones):
    return f'json_type({compilador.process(elemento.clauses, **opciones)})'


@compiles(TipoJSON, 'postgresql')
def compilar_tipo_json_postgresql(elemento, compilador, **opciones):
    return f'json_typeof({compilador.process(elemento.clauses, **opciones)})'


def crear_motor_bd(url: str) -> Engine:
    if make_url(url).get_backend_name() != 'sqlite':
        return create_engine(url, pool_pre_ping=True)
    motor_bd = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(motor_bd, "connect")
    def activar_claves_foraneas(conexion: sqlite3.Connection, registro) -> None:
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return motor_bd


@contextmanager
def conexion_migraciones(motor_bd: Engine):
    """Permite reconstruir tablas referenciadas en SQLite durante una migración."""
    with motor_bd.connect() as conexion:
        sqlite = motor_bd.url.get_backend_name() == 'sqlite'
        if sqlite:
            conexion.exec_driver_sql('PRAGMA foreign_keys=OFF')
            conexion.commit()
        try:
            yield conexion
            if sqlite and conexion.exec_driver_sql('PRAGMA foreign_key_check').first() is not None:
                raise RuntimeError('La migración dejó referencias inválidas en la base de datos.')
        finally:
            if sqlite:
                conexion.exec_driver_sql('PRAGMA foreign_keys=ON')


def obtener_sesion(peticion: Request) -> Iterator[Session]:
    from app.core.contexto import ContextoConsultas

    with peticion.app.state.fabrica_sesiones() as sesion:
        sesion.info['contexto_consultas'] = ContextoConsultas(sesion)
        yield sesion


MENSAJE_SIN_ESQUEMA = (
    'La base no tiene el esquema. Ejecuta `uv run alembic upgrade head` '
    'y carga datos con `uv run python -m datos.cargar plataforma`.'
)


def comprobar_tablas(motor_bd: Engine) -> None:
    """Comprueba presencia; Alembic gestiona la estructura."""
    from app.models import Base

    if not set(Base.metadata.tables).issubset(inspect(motor_bd).get_table_names()):
        raise RuntimeError(MENSAJE_SIN_ESQUEMA)


def es_sqlite_en_memoria(motor_bd: Engine) -> bool:
    return motor_bd.url.get_backend_name() == 'sqlite' and motor_bd.url.database == ':memory:'


def es_bloqueo_temporal(error: OperationalError) -> bool:
    return getattr(error.orig, 'sqlite_errorname', '') in (
        'SQLITE_BUSY', 'SQLITE_BUSY_SNAPSHOT', 'SQLITE_LOCKED',
    ) or any(getattr(error.orig, atributo, None) in ('40001', '55P03')
             for atributo in ('pgcode', 'sqlstate'))
