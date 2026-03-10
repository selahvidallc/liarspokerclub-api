"""add game status and finalized_at

Revision ID: a504728d2ac6
Revises: 0fbfbef22c64
Create Date: 2026-03-09 00:51:26.616166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a504728d2ac6'
down_revision: Union[str, Sequence[str], None] = '0fbfbef22c64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("games", sa.Column("status", sa.String(length=20), nullable=True))
    op.add_column("games", sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE games SET status = 'OPEN' WHERE status IS NULL")

    op.alter_column("games", "status", nullable=False)


def downgrade():
    op.drop_column("games", "finalized_at")
    op.drop_column("games", "status")
