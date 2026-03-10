"""add bet ladder to presets

Revision ID: ac01299981d3
Revises: db4e93559a06
Create Date: 2026-03-06 12:14:35.058660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac01299981d3'
down_revision: Union[str, Sequence[str], None] = 'db4e93559a06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "game_presets",
        sa.Column("bet_ladder", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("game_presets", "bet_ladder")