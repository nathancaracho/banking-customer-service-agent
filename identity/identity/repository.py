from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import (
    AuthSession,
    AuthorizationDecision,
    Permission,
    PolicyVersion,
    Role,
    User,
)


@dataclass(frozen=True)
class RepositoryUser:
    user_id: str
    roles: list[str]
    is_active: bool


@dataclass(frozen=True)
class RepositoryAuthSession:
    user: RepositoryUser
    expires_at: datetime
    revoked_at: datetime | None


@dataclass(frozen=True)
class RepositoryPermission:
    action: str
    resource_type: str
    ownership_scope: str


class IdentityRepository(Protocol):
    def get_active_policy_version(self) -> str: ...

    def find_auth_session(
        self,
        token_hash: str,
        now: datetime,
    ) -> RepositoryAuthSession | None: ...

    def list_permissions(
        self,
        roles: list[str],
        action: str,
        resource_type: str,
    ) -> list[RepositoryPermission]: ...

    def record_decision(self, **decision: object) -> None: ...


class SqlAlchemyIdentityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_policy_version(self) -> str:
        active_policy = self.session.scalar(
            select(PolicyVersion).where(PolicyVersion.is_active.is_(True))
        )

        if active_policy is None:
            raise RuntimeError("Missing active policy version in identity database")

        return active_policy.version

    def find_auth_session(
        self,
        token_hash: str,
        now: datetime,
    ) -> RepositoryAuthSession | None:
        auth_session = self.session.scalar(
            select(AuthSession)
            .options(selectinload(AuthSession.user).selectinload(User.roles))
            .where(AuthSession.token_hash == token_hash)
            .where(AuthSession.revoked_at.is_(None))
            .where(AuthSession.expires_at > now)
        )

        if auth_session is None:
            return None

        return RepositoryAuthSession(
            user=RepositoryUser(
                user_id=auth_session.user.id,
                roles=sorted(role.name for role in auth_session.user.roles),
                is_active=auth_session.user.is_active,
            ),
            expires_at=auth_session.expires_at,
            revoked_at=auth_session.revoked_at,
        )

    def list_permissions(
        self,
        roles: list[str],
        action: str,
        resource_type: str,
    ) -> list[RepositoryPermission]:
        permissions = self.session.scalars(
            select(Permission)
            .join(Permission.roles)
            .where(Role.name.in_(roles))
            .where(Permission.action == action)
            .where(Permission.resource_type == resource_type)
        ).all()

        return [
            RepositoryPermission(
                action=permission.action,
                resource_type=permission.resource_type,
                ownership_scope=permission.ownership_scope,
            )
            for permission in permissions
        ]

    def record_decision(self, **decision: object) -> None:
        self.session.add(AuthorizationDecision(**decision))
        self.session.commit()
