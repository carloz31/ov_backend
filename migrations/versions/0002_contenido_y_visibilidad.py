"""contenido y visibilidad

Revisión: 0002
Revisión anterior: 0001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Revisada tras --autogenerate: primero admite filas antiguas, luego exige la clave.
    with op.batch_alter_table('actividad', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contenido', sa.String(), nullable=True))
        batch_op.add_column(sa.Column(
            'visibilidad',
            sa.Enum('SIEMPRE', 'AL_DESBLOQUEAR', name='visibilidad',
                    native_enum=False, create_constraint=True),
            server_default=sa.text("'SIEMPRE'"), nullable=False,
        ))

    actividad = sa.table(
        'actividad', sa.column('codigo', sa.String()), sa.column('contenido', sa.String()),
    )
    op.execute(actividad.update().values(
        contenido=sa.func.replace(sa.func.lower(actividad.c.codigo), '-', '_'),
    ))
    with op.batch_alter_table('actividad', schema=None) as batch_op:
        batch_op.alter_column('contenido', existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('actividad', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_actividad_visibilidad'), type_='check')
        batch_op.drop_column('visibilidad')
        batch_op.drop_column('contenido')
