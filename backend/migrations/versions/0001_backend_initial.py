"""backend initial schema

Revision ID: 0001_backend_initial
Revises:
Create Date: 2026-06-30 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0001_backend_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_schema() -> str:
    return context.config.get_main_option("backend_schema") or "backend"


def upgrade() -> None:
    schema = _get_schema()

    op.create_table(
        "chats",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=schema,
    )
    op.create_index(
        "ix_chats_user_id",
        "chats",
        ["user_id"],
        schema=schema,
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("chat_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["chat_id"],
            [f"{schema}.chats.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=schema,
    )
    op.create_index(
        "ix_messages_chat_id",
        "messages",
        ["chat_id"],
        schema=schema,
    )
    op.create_table(
        "chat_summaries",
        sa.Column("chat_id", sa.String(length=36), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("covered_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["chat_id"],
            [f"{schema}.chats.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("chat_id"),
        schema=schema,
    )


def downgrade() -> None:
    schema = _get_schema()

    op.drop_table("chat_summaries", schema=schema)
    op.drop_index("ix_messages_chat_id", table_name="messages", schema=schema)
    op.drop_table("messages", schema=schema)
    op.drop_index("ix_chats_user_id", table_name="chats", schema=schema)
    op.drop_table("chats", schema=schema)
