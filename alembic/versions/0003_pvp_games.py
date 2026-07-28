"""Two-player games: mode, player names and per-seat tokens.

Revision ID: 0003_pvp_games
Revises: 0002_user_color
Create Date: 2026-07-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_pvp_games"
down_revision: Union[str, None] = "0002_user_color"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game", sa.Column("mode", sa.String(), nullable=False, server_default="agent")
    )
    op.create_index("ix_game_mode", "game", ["mode"])
    op.add_column("game", sa.Column("white_name", sa.String(), nullable=True))
    op.add_column("game", sa.Column("black_name", sa.String(), nullable=True))
    op.add_column("game", sa.Column("white_token", sa.String(), nullable=True))
    op.add_column("game", sa.Column("black_token", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("game", "black_token")
    op.drop_column("game", "white_token")
    op.drop_column("game", "black_name")
    op.drop_column("game", "white_name")
    op.drop_index("ix_game_mode", table_name="game")
    op.drop_column("game", "mode")
