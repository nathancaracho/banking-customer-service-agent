"""banking api initial schema

Revision ID: 0001_banking_api_initial
Revises:
Create Date: 2026-06-30 00:00:00
"""

from decimal import Decimal
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0001_banking_api_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_schema() -> str:
    return context.config.get_main_option("banking_api_schema") or "banking_api"


def upgrade() -> None:
    schema = _get_schema()

    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("segment", sa.String(length=64), nullable=False),
        sa.Column("credit_score", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=schema,
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=64), nullable=False),
        sa.Column("balance", sa.Numeric(14, 2), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], [f"{schema}.customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id"),
        schema=schema,
    )
    op.create_table(
        "credit_cards",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=64), nullable=False),
        sa.Column("current_limit", sa.Numeric(14, 2), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], [f"{schema}.customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id"),
        schema=schema,
    )
    op.create_table(
        "pix_transfers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=64), nullable=False),
        sa.Column("destination_key", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], [f"{schema}.customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
        schema=schema,
    )

    customer_table = sa.table(
        "customers",
        sa.column("id", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("segment", sa.String()),
        sa.column("credit_score", sa.Integer()),
        schema=schema,
    )
    account_table = sa.table(
        "accounts",
        sa.column("id", sa.String()),
        sa.column("customer_id", sa.String()),
        sa.column("balance", sa.Numeric()),
        schema=schema,
    )
    card_table = sa.table(
        "credit_cards",
        sa.column("id", sa.String()),
        sa.column("customer_id", sa.String()),
        sa.column("current_limit", sa.Numeric()),
        schema=schema,
    )

    op.bulk_insert(
        customer_table,
        [
            {
                "id": "usr_123",
                "display_name": "João Silva",
                "segment": "Personnalité",
                "credit_score": 820,
            }
        ],
    )
    op.bulk_insert(
        account_table,
        [
            {
                "id": "acc_123",
                "customer_id": "usr_123",
                "balance": Decimal("25000.00"),
            }
        ],
    )
    op.bulk_insert(
        card_table,
        [
            {
                "id": "card_123",
                "customer_id": "usr_123",
                "current_limit": Decimal("10000.00"),
            }
        ],
    )


def downgrade() -> None:
    schema = _get_schema()
    op.drop_table("pix_transfers", schema=schema)
    op.drop_table("credit_cards", schema=schema)
    op.drop_table("accounts", schema=schema)
    op.drop_table("customers", schema=schema)
