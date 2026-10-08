"""Migraciones sobre la URL efectiva de configuración, sin cargar datos."""

from alembic import context

from app.config import cargar_configuracion
from app.database import crear_motor_bd
from app.models import Base


target_metadata = Base.metadata


def ejecutar_migraciones_desconectadas() -> None:
    context.configure(
        url=cargar_configuracion().url_bd,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def ejecutar_migraciones_conectadas() -> None:
    motor = crear_motor_bd(cargar_configuracion().url_bd)
    try:
        with motor.connect() as conexion:
            context.configure(
                connection=conexion,
                target_metadata=target_metadata,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        motor.dispose()


if context.is_offline_mode():
    ejecutar_migraciones_desconectadas()
else:
    ejecutar_migraciones_conectadas()
