import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Request
from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.base import Base


RUTA_BASE = Path(__file__).resolve().parents[1] / "demo.db"
URL_BASE = f"sqlite:///{RUTA_BASE.as_posix()}"
VERSION_ESQUEMA = 5
MENSAJE_ESQUEMA_ANTERIOR = (
    "La base {archivo} tiene un esquema anterior. Bórrala y vuelve a iniciar la aplicación."
)


def validar_version_esquema(motor_bd: Engine, semilla: str = 'demo') -> None:
    """Inspecciona antes de create_all; nunca repara una base existente."""
    ruta = motor_bd.url.database
    archivo = Path(ruta).name if ruta else ':memory:'
    mensaje = MENSAJE_ESQUEMA_ANTERIOR.format(archivo=archivo)
    if ruta and ruta != ":memory:" and not Path(ruta).exists():
        return
    try:
        with motor_bd.connect() as conexion:
            inspector = inspect(conexion)
            tablas = set(inspector.get_table_names())
            if ruta == ":memory:" and not tablas:
                return
            if tablas != set(Base.metadata.tables):
                raise RuntimeError(mensaje)
            # La estructura debe coincidir antes de leer la semilla, sembrar
            # o abrir la caché; las versiones anteriores no se migran.
            for tabla in Base.metadata.sorted_tables:
                if {columna['name'] for columna in inspector.get_columns(tabla.name)} != set(tabla.columns.keys()):
                    raise RuntimeError(mensaje)
            versiones = conexion.execute(text("SELECT id, version, semilla FROM esquema_version")).all()
            if len(versiones) != 1 or versiones[0][:2] != (1, VERSION_ESQUEMA):
                raise RuntimeError(mensaje)
            from app.models import TipoEventoUso

            restricciones = inspector.get_multi_check_constraints(
                filter_names=['evento_uso', 'condicion_desbloqueo'],
            )
            esperados = {tipo.value for tipo in TipoEventoUso}
            for tabla, columna in (('evento_uso', 'tipo'), ('condicion_desbloqueo', 'tipo_evento')):
                comprobaciones = [restriccion['sqltext'] for restriccion in restricciones[None, tabla]
                                  if restriccion['name'] == 'tipoeventouso']
                if len(comprobaciones) != 1:
                    raise RuntimeError(mensaje)
                expresion = re.fullmatch(rf'"?{columna}"?\s+IN\s*\((.*?)\)',
                                         comprobaciones[0].strip(), re.IGNORECASE)
                if expresion is None or not re.fullmatch(r"\s*'\w+'(?:\s*,\s*'\w+')*\s*", expresion[1]):
                    raise RuntimeError(mensaje)
                if set(re.findall(r"'(\w+)'", expresion[1])) != esperados:
                    raise RuntimeError(mensaje)
            semilla_base = versiones[0].semilla
            if semilla_base != semilla:
                raise RuntimeError(
                    f'La base {archivo} fue creada con la semilla {semilla_base}; '
                    f'la aplicación está configurada con {semilla}. '
                    'Usa otra RUTA_BD o borra el archivo.'
                )
    except SQLAlchemyError as error:
        raise RuntimeError(mensaje) from error


def crear_motor_bd(url: str) -> Engine:
    motor_bd = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(motor_bd, "connect")
    def activar_claves_foraneas(conexion: sqlite3.Connection, registro) -> None:
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return motor_bd


def obtener_sesion(peticion: Request) -> Iterator[Session]:
    from app.core.contexto import ContextoConsultas

    with peticion.app.state.fabrica_sesiones() as sesion:
        sesion.info['contexto_consultas'] = ContextoConsultas(sesion)
        yield sesion


def recrear_esquema_demo(conexion) -> None:
    """Compatibilidad de R2: mantiene atómico el reinicio con DDL en SQLite."""
    conexion.exec_driver_sql("BEGIN")
    Base.metadata.drop_all(conexion)
    Base.metadata.create_all(conexion)


def es_bloqueo_temporal(error) -> bool:
    return getattr(error.orig, 'sqlite_errorname', '') in (
        'SQLITE_BUSY', 'SQLITE_BUSY_SNAPSHOT', 'SQLITE_LOCKED',
    )
