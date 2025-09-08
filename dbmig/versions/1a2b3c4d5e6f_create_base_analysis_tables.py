"""Create base analysis tables if missing

Revision ID: 1a2b3c4d5e6f
Revises: 9b2d1f7c1a4a
Create Date: 2025-09-08 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "9b2d1f7c1a4a"
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

    # analysis_requests
    if not has_table("analysis_requests"):
        op.create_table(
            "analysis_requests",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("analysis_id", mysql.VARCHAR(length=255), nullable=False),
            sa.Column("status", mysql.VARCHAR(length=50), nullable=False),
            sa.Column("repositories", mysql.LONGTEXT(charset="utf8mb4", collation="utf8mb4_bin"), nullable=True),
            sa.Column("include_ast", mysql.TINYINT(display_width=1), nullable=False),
            sa.Column("include_tech_spec", mysql.TINYINT(display_width=1), nullable=False),
            sa.Column("include_correlation", mysql.TINYINT(display_width=1), nullable=False),
            sa.Column("group_name", mysql.VARCHAR(length=255), nullable=True),
            sa.Column("created_at", mysql.DATETIME(), nullable=False),
            sa.Column("updated_at", mysql.DATETIME(), nullable=False),
            sa.Column("completed_at", mysql.DATETIME(), nullable=True),
            sa.Column("error_message", mysql.TEXT(), nullable=True),
            mysql_collate="utf8mb4_unicode_ci",
            mysql_default_charset="utf8mb4",
            mysql_engine="InnoDB",
        )
        op.create_index("analysis_id", "analysis_requests", ["analysis_id"], unique=True)

    # repository_analyses
    if not has_table("repository_analyses"):
        op.create_table(
            "repository_analyses",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("analysis_id", mysql.VARCHAR(length=36), nullable=False),
            sa.Column("repository_url", mysql.VARCHAR(length=500), nullable=False),
            sa.Column("repository_name", mysql.VARCHAR(length=255), nullable=True),
            sa.Column("branch", mysql.VARCHAR(length=100), server_default=sa.text("'main'"), nullable=True),
            sa.Column("clone_path", mysql.VARCHAR(length=500), nullable=True),
            sa.Column("status", mysql.VARCHAR(length=50), server_default=sa.text("'PENDING'"), nullable=True),
            sa.Column("commit_hash", mysql.VARCHAR(length=40), nullable=True),
            sa.Column("commit_date", mysql.DATETIME(), nullable=True),
            sa.Column("commit_author", mysql.VARCHAR(length=255), nullable=True),
            sa.Column("commit_message", mysql.MEDIUMTEXT(), nullable=True),
            sa.Column("files_count", mysql.INTEGER(display_width=11), server_default=sa.text("0"), nullable=True),
            sa.Column("lines_of_code", mysql.INTEGER(display_width=11), server_default=sa.text("0"), nullable=True),
            sa.Column("languages", mysql.LONGTEXT(charset="utf8mb4", collation="utf8mb4_bin"), nullable=True),
            sa.Column("frameworks", mysql.LONGTEXT(charset="utf8mb4", collation="utf8mb4_bin"), nullable=True),
            sa.Column("dependencies", mysql.LONGTEXT(charset="utf8mb4", collation="utf8mb4_bin"), nullable=True),
            sa.Column("ast_data", mysql.MEDIUMTEXT(), nullable=True),
            sa.Column("tech_specs", mysql.LONGTEXT(charset="utf8mb4", collation="utf8mb4_bin"), nullable=True),
            sa.Column("code_metrics", mysql.LONGTEXT(charset="utf8mb4", collation="utf8mb4_bin"), nullable=True),
            sa.Column("documentation_files", mysql.LONGTEXT(charset="utf8mb4", collation="utf8mb4_bin"), nullable=True),
            sa.Column("config_files", mysql.LONGTEXT(charset="utf8mb4", collation="utf8mb4_bin"), nullable=True),
            sa.Column("created_at", mysql.DATETIME(), server_default=sa.text("current_timestamp()"), nullable=True),
            sa.Column(
                "updated_at",
                mysql.DATETIME(),
                server_default=sa.text("current_timestamp() ON UPDATE current_timestamp()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["analysis_id"], ["analysis_requests.analysis_id"], name="repository_analyses_ibfk_1"),
            mysql_collate="utf8mb4_unicode_ci",
            mysql_default_charset="utf8mb4",
            mysql_engine="InnoDB",
        )
        op.create_index("idx_repository_url", "repository_analyses", ["repository_url"], unique=False)
        op.create_index("idx_repo_analysis_id", "repository_analyses", ["analysis_id"], unique=False)
        op.create_index("idx_commit_hash", "repository_analyses", ["commit_hash"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def has_table(name: str) -> bool:
        try:
            return inspector.has_table(name)
        except Exception:
            return False

    # Drop child first due to FK
    if has_table("repository_analyses"):
        try:
            op.drop_table("repository_analyses")
        except Exception:
            pass
    if has_table("analysis_requests"):
        try:
            op.drop_table("analysis_requests")
        except Exception:
            pass

