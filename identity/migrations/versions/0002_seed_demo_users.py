"""Seed demo users for admin UI

Revision ID: 0002_seed_demo_users
Revises: 0001_identity_initial
Create Date: 2026-06-30 00:00:00

"""

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0002_seed_demo_users"
down_revision: Union[str, None] = "0001_identity_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_USERS = [
    {
        "id": "usr_123",
        "display_name": "Cliente Demo",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    },
    {
        "id": "usr_manager",
        "display_name": "Gerente Demo",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    },
    {
        "id": "usr_admin",
        "display_name": "Administrador Demo",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    },
]

USER_ROLES = [
    {"user_id": "usr_123", "role_id": 1},
    {"user_id": "usr_manager", "role_id": 2},
    {"user_id": "usr_admin", "role_id": 3},
]


def _get_schema() -> str:
    return context.config.get_main_option("identity_schema") or "identity"


def upgrade() -> None:
    schema = _get_schema()

    user_table = sa.table(
        "users",
        sa.column("id", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        schema=schema,
    )
    user_role_table = sa.table(
        "user_roles",
        sa.column("user_id", sa.String()),
        sa.column("role_id", sa.Integer()),
        schema=schema,
    )

    op.bulk_insert(user_table, DEMO_USERS, multiinsert=False)
    op.bulk_insert(user_role_table, USER_ROLES, multiinsert=False)


def downgrade() -> None:
    schema = _get_schema()

    user_role_table = sa.table(
        "user_roles",
        sa.column("user_id", sa.String()),
        sa.column("role_id", sa.Integer()),
        schema=schema,
    )
    user_table = sa.table(
        "users",
        sa.column("id", sa.String()),
        schema=schema,
    )

    op.execute(
        user_role_table.delete().where(
            user_role_table.c.user_id.in_(["usr_123", "usr_manager", "usr_admin"])
        )
    )
    op.execute(
        user_table.delete().where(
            user_table.c.id.in_(["usr_123", "usr_manager", "usr_admin"])
        )
    )
