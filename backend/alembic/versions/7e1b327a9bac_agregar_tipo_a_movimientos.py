"""agregar tipo a movimientos

Revision ID: 7e1b327a9bac
Revises: 4083cc9c5727
Create Date: 2026-10-18 16:05:32.547778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e1b327a9bac"
down_revision: Union[str, Sequence[str], None] = "4083cc9c5727"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "movimientos",
        sa.Column("tipo", sa.String(length=20), nullable=True),
    )
    op.create_check_constraint(
        "ck_movimientos_tipo_valido",
        "movimientos",
        "tipo IS NULL OR tipo IN ('entrada', 'traslado', 'salida')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_movimientos_tipo_valido",
        "movimientos",
        type_="check",
    )
    op.drop_column("movimientos", "tipo")
