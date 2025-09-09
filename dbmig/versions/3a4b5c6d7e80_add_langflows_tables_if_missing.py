"""Create langflows and langflow_tool_mappings if missing

Revision ID: 3a4b5c6d7e80
Revises: 2c3d4e5f6a70
Create Date: 2025-09-09 00:10:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "3a4b5c6d7e80"
down_revision: Union[str, None] = "2c3d4e5f6a70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def has_table(name: str) -> bool:
        try:
            return inspector.has_table(name)
        except Exception:
            return False

    # langflows
    if not has_table("langflows"):
        op.create_table(
            "langflows",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("flow_id", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("flow_data", mysql.LONGTEXT(charset="utf8mb4", collation="utf8mb4_bin"), nullable=False),
            sa.Column("created_at", mysql.DATETIME(), server_default=sa.text("current_timestamp()"), nullable=True),
            sa.Column("updated_at", mysql.DATETIME(), server_default=sa.text("current_timestamp() ON UPDATE current_timestamp()"), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            mysql_collate="utf8mb4_unicode_ci",
            mysql_default_charset="utf8mb4",
            mysql_engine="InnoDB",
        )
        op.create_index("ix_langflows_name", "langflows", ["name"], unique=True)
        op.create_index("ix_langflows_id", "langflows", ["id"], unique=False)
        op.create_index("ix_langflows_flow_id", "langflows", ["flow_id"], unique=True)

    # langflow_tool_mappings
    if not has_table("langflow_tool_mappings"):
        op.create_table(
            "langflow_tool_mappings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("flow_id", sa.String(length=255), nullable=False),
            sa.Column("context", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", mysql.DATETIME(), server_default=sa.text("current_timestamp()"), nullable=True),
            sa.Column("updated_at", mysql.DATETIME(), server_default=sa.text("current_timestamp() ON UPDATE current_timestamp()"), nullable=True),
            sa.ForeignKeyConstraint(["flow_id"], ["langflows.flow_id"], name="langflow_tool_mappings_ibfk_1"),
            mysql_collate="utf8mb4_unicode_ci",
            mysql_default_charset="utf8mb4",
            mysql_engine="InnoDB",
        )
        op.create_index(
            "ix_langflow_tool_mappings_tool_contexts",
            "langflow_tool_mappings",
            ["context"],
            unique=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def has_table(name: str) -> bool:
        try:
            return inspector.has_table(name)
        except Exception:
            return False

    if has_table("langflow_tool_mappings"):
        try:
            op.drop_index("ix_langflow_tool_mappings_tool_contexts", table_name="langflow_tool_mappings")
        except Exception:
            pass
        try:
            op.drop_table("langflow_tool_mappings")
        except Exception:
            pass
    if has_table("langflows"):
        try:
            op.drop_index("ix_langflows_flow_id", table_name="langflows")
        except Exception:
            pass
        try:
            op.drop_index("ix_langflows_id", table_name="langflows")
        except Exception:
            pass
        try:
            op.drop_index("ix_langflows_name", table_name="langflows")
        except Exception:
            pass
        try:
            op.drop_table("langflows")
        except Exception:
            pass

