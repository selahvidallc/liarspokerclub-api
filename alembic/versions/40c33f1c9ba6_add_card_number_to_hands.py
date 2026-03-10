"""add card_number to hands

Revision ID: 40c33f1c9ba6
Revises: 1755d243b9b9
Create Date: 2026-03-08 21:42:28.337444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40c33f1c9ba6'
down_revision: Union[str, Sequence[str], None] = '1755d243b9b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "hands",
        sa.Column("card_number", sa.Integer(), nullable=True)
    )

    # Backfill existing rows
    op.execute("UPDATE hands SET card_number = 1")

    op.alter_column(
        "hands",
        "card_number",
        nullable=False
    )


def downgrade():
    op.drop_column("hands", "card_number")
