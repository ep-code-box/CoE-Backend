"""Replace front_tool_name with context in langflow_tool_mappings

Revision ID: 9b2d1f7c1a4a
Revises: 7456428295d9
Create Date: 2025-09-04 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9b2d1f7c1a4a'
down_revision: Union[str, None] = '7456428295d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def has_table(t: str) -> bool:
        try:
            return inspector.has_table(t)
        except Exception:
            return False

    def columns(t: str):
        try:
            return [c['name'] for c in inspector.get_columns(t)] if has_table(t) else []
        except Exception:
            return []

    def indexes(t: str):
        try:
            return [i['name'] for i in inspector.get_indexes(t)] if has_table(t) else []
        except Exception:
            return []

    if has_table('langflow_tool_mappings'):
        ltm_cols = columns('langflow_tool_mappings')
        # Add context column if missing
        if 'context' not in ltm_cols:
            try:
                op.add_column('langflow_tool_mappings', sa.Column('context', sa.String(length=255), nullable=False, server_default='default'))
                # Drop the server default after backfilling existing rows
                op.alter_column('langflow_tool_mappings', 'context', server_default=None)
            except Exception:
                pass
        # Backfill context from front_tool_name if both exist
        try:
            if 'front_tool_name' in ltm_cols:
                conn.exec_driver_sql("UPDATE langflow_tool_mappings SET context = front_tool_name WHERE (context IS NULL OR context = '' OR context = 'default')")
        except Exception:
            pass

        # Create index on context if not exists
        try:
            if 'ix_langflow_tool_mappings_context' not in indexes('langflow_tool_mappings'):
                op.create_index('ix_langflow_tool_mappings_context', 'langflow_tool_mappings', ['context'], unique=False)
        except Exception:
            pass

        # Drop front_tool_name if exists
        if 'front_tool_name' in ltm_cols:
            try:
                # Drop index if present
                if 'ix_langflow_tool_mappings_front_tool_name' in indexes('langflow_tool_mappings'):
                    op.drop_index('ix_langflow_tool_mappings_front_tool_name', table_name='langflow_tool_mappings')
            except Exception:
                pass
            try:
                op.drop_column('langflow_tool_mappings', 'front_tool_name')
            except Exception:
                pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def has_table(t: str) -> bool:
        try:
            return inspector.has_table(t)
        except Exception:
            return False

    def columns(t: str):
        try:
            return [c['name'] for c in inspector.get_columns(t)] if has_table(t) else []
        except Exception:
            return []

    def indexes(t: str):
        try:
            return [i['name'] for i in inspector.get_indexes(t)] if has_table(t) else []
        except Exception:
            return []

    if has_table('langflow_tool_mappings'):
        ltm_cols = columns('langflow_tool_mappings')
        # Re-add front_tool_name
        if 'front_tool_name' not in ltm_cols:
            op.add_column('langflow_tool_mappings', sa.Column('front_tool_name', sa.String(length=255), nullable=False))
        if 'ix_langflow_tool_mappings_front_tool_name' not in indexes('langflow_tool_mappings'):
            op.create_index('ix_langflow_tool_mappings_front_tool_name', 'langflow_tool_mappings', ['front_tool_name'], unique=True)

        # Drop context index and column
        if 'ix_langflow_tool_mappings_context' in indexes('langflow_tool_mappings'):
            op.drop_index('ix_langflow_tool_mappings_context', table_name='langflow_tool_mappings')
        if 'context' in ltm_cols:
            op.drop_column('langflow_tool_mappings', 'context')
