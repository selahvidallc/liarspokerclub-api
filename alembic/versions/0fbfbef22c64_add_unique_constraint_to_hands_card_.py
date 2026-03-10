"""add unique constraint to hands card settlements

Revision ID: 0fbfbef22c64
Revises: 40c33f1c9ba6
Create Date: 2026-03-09 00:29:51.930502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fbfbef22c64'
down_revision: Union[str, Sequence[str], None] = '40c33f1c9ba6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_unique_constraint(
        "uq_hands_card_pair",
        "hands",
        ["game_id", "hand_number", "card_number", "winner_user_id", "loser_user_id"],
    )

    op.create_index(
        "ix_hands_game_hand_card",
        "hands",
        ["game_id", "hand_number", "card_number"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_hands_game_hand_card", table_name="hands")
    op.drop_constraint("uq_hands_card_pair", "hands", type_="unique")
