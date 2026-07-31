"""Agent memory (per-game plans/reasoning) and self-built opening book.

Revision ID: 0004_agent_memory
Revises: 0003_pvp_games
Create Date: 2026-07-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_agent_memory"
down_revision: Union[str, None] = "0003_pvp_games"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_memory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("game.id"), nullable=False),
        sa.Column("move_number", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False, server_default=""),
        sa.Column("reasoning", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_agent_memory_game_id", "agent_memory", ["game_id"])

    op.create_table(
        "opening_book",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("position_fen", sa.String(), nullable=False),
        sa.Column("move_san", sa.String(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("position_fen", "move_san", name="uq_book_position_move"),
    )
    op.create_index("ix_opening_book_position_fen", "opening_book", ["position_fen"])


def downgrade() -> None:
    op.drop_index("ix_opening_book_position_fen", table_name="opening_book")
    op.drop_table("opening_book")
    op.drop_index("ix_agent_memory_game_id", table_name="agent_memory")
    op.drop_table("agent_memory")
