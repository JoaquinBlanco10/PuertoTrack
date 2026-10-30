"""crear tabla de auditoria

Revision ID: cbaff025a858
Revises: 7e1b327a9bac
Create Date: 2026-10-18 17:48:38.687794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "cbaff025a858"
down_revision: Union[str, Sequence[str], None] = "7e1b327a9bac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("accion", sa.String(length=50), nullable=False),
        sa.Column("entidad", sa.String(length=50), nullable=False),
        sa.Column("entidad_id", sa.Integer(), nullable=False),
        sa.Column(
            "datos_anteriores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "datos_nuevos",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuarios.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_accion"),
        "audit_logs",
        ["accion"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_entidad"),
        "audit_logs",
        ["entidad"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_entidad_id"),
        "audit_logs",
        ["entidad_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_fecha"),
        "audit_logs",
        ["fecha"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_usuario_id"),
        "audit_logs",
        ["usuario_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_audit_logs_usuario_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_fecha"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entidad_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entidad"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_accion"), table_name="audit_logs")
    op.drop_table("audit_logs")
