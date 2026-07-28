"""Add game.user_color (which side the human plays).

Revision ID: 0002_user_color
Revises: 0001_initial
Create Date: 2026-07-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_color"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game",
        sa.Column("user_color", sa.String(), nullable=False, server_default="white"),
    )


def downgrade() -> None:
    op.drop_column("game", "user_color")
