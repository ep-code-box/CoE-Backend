"""Create chat_messages and conversation_summaries if missing

Revision ID: 2c3d4e5f6a70
Revises: 1a2b3c4d5e6f
Create Date: 2025-09-09 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "2c3d4e5f6a70"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
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

    # chat_messages table (as expected by Backend ORM)
    if not has_table("chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("session_id", sa.String(length=100), nullable=False),
            sa.Column("role", sa.String(length=50), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("timestamp", mysql.DATETIME(), server_default=sa.text("current_timestamp()"), nullable=True),
            sa.Column("turn_number", sa.Integer(), nullable=False),
            sa.Column("selected_tool", sa.String(length=100), nullable=True),
            sa.Column("tool_execution_time_ms", sa.Integer(), nullable=True),
            sa.Column("tool_success", sa.Boolean(), nullable=True),
            sa.Column("tool_metadata", sa.JSON(), nullable=True),
            mysql_collate="utf8mb4_unicode_ci",
            mysql_default_charset="utf8mb4",
            mysql_engine="InnoDB",
        )
        op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"], unique=False)
        op.create_index("ix_chat_messages_timestamp", "chat_messages", ["timestamp"], unique=False)

    # conversation_summaries table (create only if missing; do not alter if exists)
    if not has_table("conversation_summaries"):
        op.create_table(
            "conversation_summaries",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("session_id", sa.String(length=100), nullable=False),
            sa.Column("summary_content", sa.Text(), nullable=False),
            sa.Column("total_turns", sa.Integer(), server_default=sa.text("0"), nullable=True),
            sa.Column("tools_used", sa.JSON(), nullable=True),
            sa.Column("group_name", sa.String(length=255), nullable=True),
            sa.Column("created_at", mysql.DATETIME(), server_default=sa.text("current_timestamp()"), nullable=True),
            mysql_collate="utf8mb4_unicode_ci",
            mysql_default_charset="utf8mb4",
            mysql_engine="InnoDB",
        )
        op.create_index("ix_conversation_summaries_session_id", "conversation_summaries", ["session_id"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def has_table(name: str) -> bool:
        try:
            return inspector.has_table(name)
        except Exception:
            return False

    # Downgrade is conservative: do not drop if not present
    if has_table("conversation_summaries"):
        try:
            op.drop_table("conversation_summaries")
        except Exception:
            pass
    if has_table("chat_messages"):
        try:
            op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
        except Exception:
            pass
        try:
            op.drop_index("ix_chat_messages_timestamp", table_name="chat_messages")
        except Exception:
            pass
        try:
            op.drop_table("chat_messages")
        except Exception:
            pass

