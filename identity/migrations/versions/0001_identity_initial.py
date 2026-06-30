"""identity initial schema

Revision ID: 0001_identity_initial
Revises:
Create Date: 2026-06-29 00:00:00

"""

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0001_identity_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POLICY_VERSION = "2026-06-29"
ROLES = [
    {"id": 1, "name": "customer"},
    {"id": 2, "name": "manager"},
    {"id": 3, "name": "admin"},
]
PERMISSIONS = [
    {
        "id": 1,
        "action": "balance.read",
        "resource_type": "customer_account",
        "ownership_scope": "own",
    },
    {
        "id": 2,
        "action": "card_limit.read",
        "resource_type": "credit_card",
        "ownership_scope": "own",
    },
    {
        "id": 3,
        "action": "card_limit.update",
        "resource_type": "credit_card",
        "ownership_scope": "own",
    },
    {
        "id": 4,
        "action": "pix.transfer",
        "resource_type": "bank_account",
        "ownership_scope": "own",
    },
    {
        "id": 5,
        "action": "customer_profile.read",
        "resource_type": "customer_account",
        "ownership_scope": "any",
    },
    {
        "id": 6,
        "action": "balance.read",
        "resource_type": "customer_account",
        "ownership_scope": "any",
    },
    {
        "id": 7,
        "action": "card_limit.read",
        "resource_type": "credit_card",
        "ownership_scope": "any",
    },
    {
        "id": 8,
        "action": "card_limit.update",
        "resource_type": "credit_card",
        "ownership_scope": "any",
    },
    {
        "id": 9,
        "action": "pix.transfer",
        "resource_type": "bank_account",
        "ownership_scope": "any",
    },
    {
        "id": 10,
        "action": "user.manage",
        "resource_type": "identity",
        "ownership_scope": "any",
    },
    {
        "id": 11,
        "action": "role.manage",
        "resource_type": "identity",
        "ownership_scope": "any",
    },
]
ROLE_PERMISSIONS = [
    {"role_id": 1, "permission_id": 1},
    {"role_id": 1, "permission_id": 2},
    {"role_id": 1, "permission_id": 3},
    {"role_id": 1, "permission_id": 4},
    {"role_id": 2, "permission_id": 5},
    {"role_id": 2, "permission_id": 6},
    {"role_id": 2, "permission_id": 7},
    {"role_id": 3, "permission_id": 5},
    {"role_id": 3, "permission_id": 6},
    {"role_id": 3, "permission_id": 7},
    {"role_id": 3, "permission_id": 8},
    {"role_id": 3, "permission_id": 9},
    {"role_id": 3, "permission_id": 10},
    {"role_id": 3, "permission_id": 11},
]


def _get_schema() -> str:
    return context.config.get_main_option("identity_schema") or "identity"


def upgrade() -> None:
    schema = _get_schema()

    op.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=schema,
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema=schema,
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=128), nullable=False),
        sa.Column("ownership_scope", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "action",
            "resource_type",
            "ownership_scope",
            name="uq_permission_action_resource_scope",
        ),
        schema=schema,
    )
    op.create_table(
        "policy_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version"),
        schema=schema,
    )
    op.create_table(
        "authorization_decisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("decision_type", sa.String(length=64), nullable=False),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("subject_roles", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("chat_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=True),
        sa.Column("resource_type", sa.String(length=128), nullable=True),
        sa.Column("resource_owner_id", sa.String(length=64), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=schema,
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], [f"{schema}.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        schema=schema,
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], [f"{schema}.roles.id"]),
        sa.ForeignKeyConstraint(["user_id"], [f"{schema}.users.id"]),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
        schema=schema,
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], [f"{schema}.permissions.id"]),
        sa.ForeignKeyConstraint(["role_id"], [f"{schema}.roles.id"]),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
        schema=schema,
    )

    role_table = sa.table(
        "roles",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        schema=schema,
    )
    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.Integer()),
        sa.column("action", sa.String()),
        sa.column("resource_type", sa.String()),
        sa.column("ownership_scope", sa.String()),
        schema=schema,
    )
    role_permission_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer()),
        sa.column("permission_id", sa.Integer()),
        schema=schema,
    )
    policy_version_table = sa.table(
        "policy_versions",
        sa.column("id", sa.Integer()),
        sa.column("version", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        schema=schema,
    )

    op.bulk_insert(role_table, ROLES, multiinsert=False)
    op.bulk_insert(permission_table, PERMISSIONS, multiinsert=False)
    op.bulk_insert(role_permission_table, ROLE_PERMISSIONS, multiinsert=False)
    op.bulk_insert(
        policy_version_table,
        [
            {
                "id": 1,
                "version": POLICY_VERSION,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
            }
        ],
        multiinsert=False,
    )


def downgrade() -> None:
    schema = _get_schema()

    op.drop_table("role_permissions", schema=schema)
    op.drop_table("user_roles", schema=schema)
    op.drop_table("auth_sessions", schema=schema)
    op.drop_table("authorization_decisions", schema=schema)
    op.drop_table("policy_versions", schema=schema)
    op.drop_table("permissions", schema=schema)
    op.drop_table("roles", schema=schema)
    op.drop_table("users", schema=schema)
    op.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}"'))
