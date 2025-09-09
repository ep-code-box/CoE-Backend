"""Create api_logs table if missing

Revision ID: 7f8e9d0c1b2a
Revises: 2c3d4e5f6a70
Create Date: 2025-09-09 15:25:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "7f8e9d0c1b2a"
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

    if not has_table("api_logs"):
        op.create_table(
            "api_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("session_id", sa.String(length=100), nullable=True),
            sa.Column("endpoint", sa.String(length=255), nullable=False),
            sa.Column(
                "method",
                sa.Enum("GET", "POST", "PUT", "DELETE", "PATCH", name="httpmethod"),
                nullable=False,
            ),
            sa.Column("request_data", sa.JSON(), nullable=True),
            sa.Column("response_status", sa.Integer(), nullable=True),
            sa.Column("response_time_ms", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", mysql.DATETIME(), server_default=sa.text("current_timestamp()"), nullable=True),
            sa.Column("selected_tool", sa.String(length=100), nullable=True),
            sa.Column("tool_execution_time_ms", sa.Integer(), nullable=True),
            sa.Column("tool_success", sa.Boolean(), nullable=True),
            sa.Column("tool_error_message", sa.Text(), nullable=True),
            mysql_collate="utf8mb4_unicode_ci",
            mysql_default_charset="utf8mb4",
            mysql_engine="InnoDB",
        )
        op.create_index("ix_api_logs_created_at", "api_logs", ["created_at"], unique=False)
        op.create_index("ix_api_logs_endpoint", "api_logs", ["endpoint"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def has_table(name: str) -> bool:
        try:
            return inspector.has_table(name)
        except Exception:
            return False

    if has_table("api_logs"):
        try:
            op.drop_index("ix_api_logs_created_at", table_name="api_logs")
        except Exception:
            pass
        try:
            op.drop_index("ix_api_logs_endpoint", table_name="api_logs")
        except Exception:
            pass
        try:
            op.drop_table("api_logs")
        except Exception:
            pass

