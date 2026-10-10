"""espacio portal familia

Revisión: 0003
Revisión anterior: 0002
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --autogenerate no detectó el cambio del CHECK del enumerado no nativo.
    with op.batch_alter_table('bloque', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_bloque_espacio'), type_='check')
        batch_op.create_check_constraint(
            op.f('ck_bloque_espacio'),
            "espacio IN ('MISIONES_CAMPO', 'CIUDAD', 'PORTAL_FAMILIA')",
        )


def downgrade() -> None:
    # Evita iniciar una reconstrucción que dejaría una tabla temporal en SQLite.
    if not context.is_offline_mode():
        bloque = sa.table('bloque', sa.column('espacio', sa.String()))
        familias = sa.select(bloque.c.espacio).where(bloque.c.espacio == 'PORTAL_FAMILIA').limit(1)
        if op.get_bind().execute(familias).first() is not None:
            raise RuntimeError('No se puede volver a 0002: existen bloques PORTAL_FAMILIA.')
    with op.batch_alter_table('bloque', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_bloque_espacio'), type_='check')
        batch_op.create_check_constraint(
            op.f('ck_bloque_espacio'), "espacio IN ('MISIONES_CAMPO', 'CIUDAD')",
        )
