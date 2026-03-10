"""add game ladder and settlement mode

Revision ID: 1755d243b9b9
Revises: ac01299981d3
Create Date: 2026-03-06 12:46:20.707112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1755d243b9b9'
down_revision: Union[str, Sequence[str], None] = 'ac01299981d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    op.add_column("games", sa.Column("cards_per_hand", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("games", sa.Column("bet_ladder", sa.JSON(), nullable=True))
    op.add_column("games", sa.Column("settlement_mode", sa.String(length=32), nullable=False, server_default="PER_HAND"))


def downgrade():
    op.drop_column("games", "settlement_mode")
    op.drop_column("games", "bet_ladder")
    op.drop_column("games", "cards_per_hand")
