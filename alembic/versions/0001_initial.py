"""Initial schema: game, move and log tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def upgrade() -> None:
    op.create_table(
        "game",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("result", sa.String(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_fen", sa.String(), nullable=False, server_default=STARTING_FEN),
        sa.Column("pgn", sa.String(), nullable=False, server_default=""),
    )
    op.create_index("ix_game_is_completed", "game", ["is_completed"])

    op.create_table(
        "move",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("game.id"), nullable=False),
        sa.Column("move_number", sa.Integer(), nullable=False),
        sa.Column("from_square", sa.String(), nullable=False),
        sa.Column("to_square", sa.String(), nullable=False),
        sa.Column("move_san", sa.String(), nullable=False),
    )
    op.create_index("ix_move_game_id", "move", ["game_id"])

    op.create_table(
        "log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("game.id"), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
    )
    op.create_index("ix_log_game_id", "log", ["game_id"])
    op.create_index("ix_log_action_type", "log", ["action_type"])


def downgrade() -> None:
    op.drop_index("ix_log_action_type", table_name="log")
    op.drop_index("ix_log_game_id", table_name="log")
    op.drop_table("log")
    op.drop_index("ix_move_game_id", table_name="move")
    op.drop_table("move")
    op.drop_index("ix_game_is_completed", table_name="game")
    op.drop_table("game")
