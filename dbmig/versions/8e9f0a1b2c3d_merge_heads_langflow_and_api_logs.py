"""Merge heads: langflow tables and api_logs

Revision ID: 8e9f0a1b2c3d
Revises: 3a4b5c6d7e80, 7f8e9d0c1b2a
Create Date: 2025-09-11 07:10:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "8e9f0a1b2c3d"
down_revision: Union[str, None] = ("3a4b5c6d7e80", "7f8e9d0c1b2a")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge point; no schema changes required.
    pass


def downgrade() -> None:
    # Merge points typically have no automatic downgrade.
    pass

