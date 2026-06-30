"""add checkpoint columns for HIL

Revision ID: add_checkpoint_hil_columns
Revises: 060a8bfc18a6
Create Date: 2026-06-30 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_checkpoint_hil_columns"
down_revision: Union[str, None] = "060a8bfc18a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "checkpoints",
        sa.Column("auth_decision", sa.JSON(), nullable=True),
    )
    op.add_column(
        "checkpoints",
        sa.Column("subject", sa.JSON(), nullable=True),
    )
    op.add_column(
        "checkpoints",
        sa.Column("confirmation_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("checkpoints", "confirmation_text")
    op.drop_column("checkpoints", "subject")
    op.drop_column("checkpoints", "auth_decision")
