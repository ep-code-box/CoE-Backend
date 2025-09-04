"""로컬 DB 수동 변경 사항 동기화

Revision ID: 7456428295d9
Revises: 
Create Date: 2025-09-04 14:26:18.910284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '7456428295d9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 방어적으로 처리: 존재 여부 확인 후 드롭/생성 수행
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

    # rag_analysis_results
    try:
        if 'analysis_id' in indexes('rag_analysis_results'):
            conn.exec_driver_sql("DROP INDEX IF EXISTS analysis_id ON rag_analysis_results")
    except Exception:
        pass
    try:
        if 'idx_analysis_id' in indexes('rag_analysis_results'):
            conn.exec_driver_sql("DROP INDEX IF EXISTS idx_analysis_id ON rag_analysis_results")
    except Exception:
        pass
    try:
        if 'idx_git_url' in indexes('rag_analysis_results'):
            conn.exec_driver_sql("DROP INDEX IF EXISTS idx_git_url ON rag_analysis_results")
    except Exception:
        pass
    if has_table('rag_analysis_results'):
        try:
            op.drop_table('rag_analysis_results')
        except Exception:
            pass

    # schema_migrations
    try:
        if 'idx_version' in indexes('schema_migrations'):
            conn.exec_driver_sql("DROP INDEX IF EXISTS idx_version ON schema_migrations")
    except Exception:
        pass
    try:
        if 'version' in indexes('schema_migrations'):
            conn.exec_driver_sql("DROP INDEX IF EXISTS version ON schema_migrations")
    except Exception:
        pass
    if has_table('schema_migrations'):
        try:
            op.drop_table('schema_migrations')
        except Exception:
            pass

    # repository_analyses
    for idx in ['idx_commit_hash', 'idx_repo_analysis_id', 'idx_repository_url']:
        try:
            if idx in indexes('repository_analyses'):
                conn.exec_driver_sql(f"DROP INDEX IF EXISTS {idx} ON repository_analyses")
        except Exception:
            pass
    if has_table('repository_analyses'):
        try:
            op.drop_table('repository_analyses')
        except Exception:
            pass

    # analysis_requests
    try:
        if 'analysis_id' in indexes('analysis_requests'):
            conn.exec_driver_sql("DROP INDEX IF EXISTS analysis_id ON analysis_requests")
    except Exception:
        pass
    if has_table('analysis_requests'):
        try:
            op.drop_table('analysis_requests')
        except Exception:
            pass

    # chat_messages 컬럼 드롭
    if 'chat_messages' in inspector.get_table_names():
        if 'tool_call_id' in columns('chat_messages'):
            try:
                op.drop_column('chat_messages', 'tool_call_id')
            except Exception:
                pass
        if 'tool_name' in columns('chat_messages'):
            try:
                op.drop_column('chat_messages', 'tool_name')
            except Exception:
                pass

    # conversation_summaries 컬럼 추가/변경/인덱스
    if has_table('conversation_summaries'):
        conv_cols = columns('conversation_summaries')
        if 'id' not in conv_cols:
            try:
                op.add_column('conversation_summaries', sa.Column('id', sa.Integer(), nullable=False))
            except Exception:
                pass
        if 'session_id' not in conv_cols:
            try:
                op.add_column('conversation_summaries', sa.Column('session_id', sa.String(length=100), nullable=False))
            except Exception:
                pass
        if 'summary_content' not in conv_cols:
            try:
                op.add_column('conversation_summaries', sa.Column('summary_content', sa.Text(), nullable=False))
            except Exception:
                pass
        if 'total_turns' not in conv_cols:
            try:
                op.add_column('conversation_summaries', sa.Column('total_turns', sa.Integer(), nullable=True))
            except Exception:
                pass
        if 'tools_used' not in conv_cols:
            try:
                op.add_column('conversation_summaries', sa.Column('tools_used', sa.JSON(), nullable=True))
            except Exception:
                pass
        if 'created_at' in conv_cols:
            try:
                op.alter_column('conversation_summaries', 'created_at', existing_type=mysql.DATETIME(), nullable=True)
            except Exception:
                pass
        # 인덱스
        if op.f('ix_conversation_summaries_id') not in indexes('conversation_summaries'):
            try:
                op.create_index(op.f('ix_conversation_summaries_id'), 'conversation_summaries', ['id'], unique=False)
            except Exception:
                pass
        # 불필요한 컬럼 드롭
        for col in ['conversation_id', 'updated_at', 'summary']:
            if col in columns('conversation_summaries'):
                try:
                    op.drop_column('conversation_summaries', col)
                except Exception:
                    pass

    # langflow_tool_mappings
    if has_table('langflow_tool_mappings'):
        ltm_cols = columns('langflow_tool_mappings')
        if 'front_tool_name' not in ltm_cols:
            try:
                op.add_column('langflow_tool_mappings', sa.Column('front_tool_name', sa.String(length=255), nullable=False))
            except Exception:
                pass
        # drop old index if exists
        try:
            if 'ix_langflow_tool_mappings_tool_contexts' in indexes('langflow_tool_mappings'):
                conn.exec_driver_sql("DROP INDEX IF EXISTS ix_langflow_tool_mappings_tool_contexts ON langflow_tool_mappings")
        except Exception:
            pass
        # create new index if missing
        try:
            if op.f('ix_langflow_tool_mappings_front_tool_name') not in indexes('langflow_tool_mappings'):
                op.create_index(op.f('ix_langflow_tool_mappings_front_tool_name'), 'langflow_tool_mappings', ['front_tool_name'], unique=True)
        except Exception:
            pass
        if 'context' in ltm_cols:
            try:
                op.drop_column('langflow_tool_mappings', 'context')
            except Exception:
                pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('langflow_tool_mappings', sa.Column('context', mysql.VARCHAR(length=255), nullable=False))
    op.drop_index(op.f('ix_langflow_tool_mappings_front_tool_name'), table_name='langflow_tool_mappings')
    op.create_index('ix_langflow_tool_mappings_tool_contexts', 'langflow_tool_mappings', ['context'], unique=True)
    op.drop_column('langflow_tool_mappings', 'front_tool_name')
    op.add_column('conversation_summaries', sa.Column('summary', mysql.TEXT(), nullable=False))
    op.add_column('conversation_summaries', sa.Column('updated_at', mysql.DATETIME(), nullable=False))
    op.add_column('conversation_summaries', sa.Column('conversation_id', mysql.VARCHAR(length=255), nullable=False))
    op.drop_index(op.f('ix_conversation_summaries_id'), table_name='conversation_summaries')
    op.alter_column('conversation_summaries', 'created_at',
               existing_type=mysql.DATETIME(),
               nullable=False)
    op.drop_column('conversation_summaries', 'tools_used')
    op.drop_column('conversation_summaries', 'total_turns')
    op.drop_column('conversation_summaries', 'summary_content')
    op.drop_column('conversation_summaries', 'session_id')
    op.drop_column('conversation_summaries', 'id')
    op.add_column('chat_messages', sa.Column('tool_name', mysql.VARCHAR(length=100), nullable=True))
    op.add_column('chat_messages', sa.Column('tool_call_id', mysql.VARCHAR(length=255), nullable=True))
    op.create_table('analysis_requests',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
    sa.Column('analysis_id', mysql.VARCHAR(length=255), nullable=False),
    sa.Column('status', mysql.VARCHAR(length=50), nullable=False),
    sa.Column('repositories', mysql.LONGTEXT(charset='utf8mb4', collation='utf8mb4_bin'), nullable=True),
    sa.Column('include_ast', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
    sa.Column('include_tech_spec', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
    sa.Column('include_correlation', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
    sa.Column('group_name', mysql.VARCHAR(length=255), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=False),
    sa.Column('updated_at', mysql.DATETIME(), nullable=False),
    sa.Column('completed_at', mysql.DATETIME(), nullable=True),
    sa.Column('error_message', mysql.TEXT(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('analysis_id', 'analysis_requests', ['analysis_id'], unique=True)
    op.create_table('repository_analyses',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
    sa.Column('analysis_id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('repository_url', mysql.VARCHAR(length=500), nullable=False),
    sa.Column('repository_name', mysql.VARCHAR(length=255), nullable=True),
    sa.Column('branch', mysql.VARCHAR(length=100), server_default=sa.text("'main'"), nullable=True),
    sa.Column('clone_path', mysql.VARCHAR(length=500), nullable=True),
    sa.Column('status', mysql.VARCHAR(length=50), server_default=sa.text("'PENDING'"), nullable=True),
    sa.Column('commit_hash', mysql.VARCHAR(length=40), nullable=True),
    sa.Column('commit_date', mysql.DATETIME(), nullable=True),
    sa.Column('commit_author', mysql.VARCHAR(length=255), nullable=True),
    sa.Column('commit_message', mysql.MEDIUMTEXT(), nullable=True),
    sa.Column('files_count', mysql.INTEGER(display_width=11), server_default=sa.text('0'), autoincrement=False, nullable=True),
    sa.Column('lines_of_code', mysql.INTEGER(display_width=11), server_default=sa.text('0'), autoincrement=False, nullable=True),
    sa.Column('languages', mysql.LONGTEXT(charset='utf8mb4', collation='utf8mb4_bin'), nullable=True),
    sa.Column('frameworks', mysql.LONGTEXT(charset='utf8mb4', collation='utf8mb4_bin'), nullable=True),
    sa.Column('dependencies', mysql.LONGTEXT(charset='utf8mb4', collation='utf8mb4_bin'), nullable=True),
    sa.Column('ast_data', mysql.MEDIUMTEXT(), nullable=True),
    sa.Column('tech_specs', mysql.LONGTEXT(charset='utf8mb4', collation='utf8mb4_bin'), nullable=True),
    sa.Column('code_metrics', mysql.LONGTEXT(charset='utf8mb4', collation='utf8mb4_bin'), nullable=True),
    sa.Column('documentation_files', mysql.LONGTEXT(charset='utf8mb4', collation='utf8mb4_bin'), nullable=True),
    sa.Column('config_files', mysql.LONGTEXT(charset='utf8mb4', collation='utf8mb4_bin'), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), server_default=sa.text('current_timestamp()'), nullable=True),
    sa.Column('updated_at', mysql.DATETIME(), server_default=sa.text('current_timestamp() ON UPDATE current_timestamp()'), nullable=True),
    sa.ForeignKeyConstraint(['analysis_id'], ['analysis_requests.analysis_id'], name='repository_analyses_ibfk_1'),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('idx_repository_url', 'repository_analyses', ['repository_url'], unique=False)
    op.create_index('idx_repo_analysis_id', 'repository_analyses', ['analysis_id'], unique=False)
    op.create_index('idx_commit_hash', 'repository_analyses', ['commit_hash'], unique=False)
    op.create_table('schema_migrations',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
    sa.Column('version', mysql.VARCHAR(length=255), nullable=False),
    sa.Column('description', mysql.TEXT(), nullable=True),
    sa.Column('executed_at', mysql.DATETIME(), server_default=sa.text('current_timestamp()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('version', 'schema_migrations', ['version'], unique=True)
    op.create_index('idx_version', 'schema_migrations', ['version'], unique=False)
    op.create_table('rag_analysis_results',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
    sa.Column('analysis_id', mysql.VARCHAR(length=255), nullable=False),
    sa.Column('git_url', mysql.VARCHAR(length=500), nullable=False),
    sa.Column('analysis_date', mysql.DATETIME(), nullable=False),
    sa.Column('status', mysql.VARCHAR(length=50), nullable=False),
    sa.Column('repository_count', mysql.INTEGER(display_width=11), server_default=sa.text('0'), autoincrement=False, nullable=True),
    sa.Column('total_files', mysql.INTEGER(display_width=11), server_default=sa.text('0'), autoincrement=False, nullable=True),
    sa.Column('total_lines_of_code', mysql.INTEGER(display_width=11), server_default=sa.text('0'), autoincrement=False, nullable=True),
    sa.Column('repositories_data', mysql.MEDIUMTEXT(), nullable=True),
    sa.Column('correlation_data', mysql.MEDIUMTEXT(), nullable=True),
    sa.Column('tech_specs_summary', mysql.MEDIUMTEXT(), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), server_default=sa.text('current_timestamp()'), nullable=True),
    sa.Column('completed_at', mysql.DATETIME(), nullable=True),
    sa.Column('error_message', mysql.TEXT(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('idx_git_url', 'rag_analysis_results', ['git_url'], unique=False)
    op.create_index('idx_analysis_id', 'rag_analysis_results', ['analysis_id'], unique=False)
    op.create_index('analysis_id', 'rag_analysis_results', ['analysis_id'], unique=True)
    # ### end Alembic commands ###
