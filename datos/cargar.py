"""Carga explícita y transaccional de conjuntos de datos."""

import argparse

from sqlalchemy import Engine, delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import cargar_configuracion
from app.database import comprobar_tablas, crear_motor_bd, es_sqlite_en_memoria
from app.models import Base
from datos import demo, plataforma
from datos.demo.registro import cargar_definiciones_registro


CONJUNTOS = {'demo': demo.cargar, 'plataforma': plataforma.cargar}
TABLAS_PRINCIPALES = (
    'cuenta', 'actividad', 'regla_desbloqueo', 'item_instrumento', 'ocupacion', 'item_registro',
)
MENSAJE_SIN_ESQUEMA_CARGA = (
    'La base no tiene el esquema. Ejecuta `uv run alembic upgrade head`.'
)


def preparar_base(
    url: str, conjunto: str, *, crear_tablas: bool = False, vaciar: bool = False,
) -> dict[str, int]:
    if conjunto not in CONJUNTOS:
        raise ValueError('El conjunto debe ser demo o plataforma')
    motor = crear_motor_bd(url)
    try:
        if crear_tablas:
            Base.metadata.create_all(motor)
        try:
            comprobar_tablas(motor)
        except RuntimeError:
            raise RuntimeError(MENSAJE_SIN_ESQUEMA_CARGA) from None
        with Session(motor) as sesion, sesion.begin():
            if vaciar:
                for tabla in reversed(Base.metadata.sorted_tables):
                    sesion.execute(delete(tabla))
            elif any(sesion.execute(select(tabla).limit(1)).first() is not None
                     for tabla in Base.metadata.sorted_tables):
                raise ValueError('La base ya contiene datos. Usa --vaciar para volver a cargarla.')
            CONJUNTOS[conjunto](sesion)
            sesion.flush()
            return {nombre: sesion.scalar(select(func.count()).select_from(Base.metadata.tables[nombre]))
                    for nombre in TABLAS_PRINCIPALES}
    finally:
        motor.dispose()


def preparar_base_registro_en_memoria(motor: Engine) -> None:
    """Excepción autorizada para el script manual: sin Excel ni estado de cuentas."""
    if not es_sqlite_en_memoria(motor):
        raise ValueError('La preparación de registro requiere una base SQLite en memoria')
    Base.metadata.create_all(motor)
    with Session(motor) as sesion, sesion.begin():
        cargar_definiciones_registro(sesion)


def main(argumentos=None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument('conjunto', choices=CONJUNTOS)
    analizador.add_argument('--vaciar', action='store_true')
    opciones = analizador.parse_args(argumentos)
    try:
        conteos = preparar_base(cargar_configuracion().url_bd, opciones.conjunto,
                               vaciar=opciones.vaciar)
    except (OSError, ValueError, RuntimeError) as error:
        analizador.exit(1, f'No se pudieron cargar los datos: {error}\n')
    except SQLAlchemyError:
        analizador.exit(1, 'No se pudieron cargar los datos: no se pudo acceder a la base de datos.\n')
    for tabla, cantidad in conteos.items():
        print(f'{tabla}: {cantidad}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
