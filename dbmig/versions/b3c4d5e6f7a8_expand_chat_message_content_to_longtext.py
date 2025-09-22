"""Expand chat message content column to LONGTEXT

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2025-09-22 11:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    try:
        has_table = inspector.has_table("chat_messages")
    except Exception:
        has_table = False

    if has_table:
        op.alter_column(
            "chat_messages",
            "content",
            existing_type=sa.Text(),
            type_=mysql.LONGTEXT(),
            existing_nullable=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    try:
        has_table = inspector.has_table("chat_messages")
    except Exception:
        has_table = False

    if has_table:
        op.alter_column(
            "chat_messages",
            "content",
            existing_type=mysql.LONGTEXT(),
            type_=sa.Text(),
            existing_nullable=False,
        )
