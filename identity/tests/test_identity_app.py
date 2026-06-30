from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from identity.app import create_app
from identity.config import Settings


def _hash_auth_context(auth_context: str) -> str:
    return sha256(auth_context.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FakeUser:
    user_id: str
    roles: list[str]
    is_active: bool = True


@dataclass(frozen=True)
class FakeAuthSession:
    user: FakeUser
    expires_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class FakePermission:
    action: str
    resource_type: str
    ownership_scope: str


class FakeIdentityRepository:
    def __init__(self) -> None:
        self.policy_version = "2026-06-29"
        self.auth_sessions: dict[str, FakeAuthSession] = {}
        self.permissions: dict[tuple[str, str, str], list[FakePermission]] = {
            ("customer", "card_limit.update", "credit_card"): [
                FakePermission(
                    action="card_limit.update",
                    resource_type="credit_card",
                    ownership_scope="own",
                )
            ]
        }
        self.decisions: list[dict] = []

    def get_active_policy_version(self) -> str:
        return self.policy_version

    def find_auth_session(self, token_hash: str, now: datetime) -> FakeAuthSession | None:
        auth_session = self.auth_sessions.get(token_hash)

        if auth_session is None:
            return None

        if auth_session.revoked_at is not None:
            return None

        if auth_session.expires_at <= now:
            return None

        return auth_session

    def list_permissions(
        self,
        roles: list[str],
        action: str,
        resource_type: str,
    ) -> list[FakePermission]:
        permissions: list[FakePermission] = []

        for role in roles:
            permissions.extend(
                self.permissions.get((role, action, resource_type), [])
            )

        return permissions

    def record_decision(self, **decision: object) -> None:
        self.decisions.append(decision)


class IdentityAppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeIdentityRepository()
        self.repository.auth_sessions[_hash_auth_context("token-customer")] = FakeAuthSession(
            user=FakeUser(
                user_id="usr_123",
                roles=["customer"],
            ),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        settings = Settings(
            database_url="postgresql+psycopg2://test:test@localhost:5432/test",
            database_schema="identity",
        )
        fake_session = MagicMock(name="session")
        fake_session_context = MagicMock(name="session_context")
        fake_session_context.__enter__.return_value = fake_session
        fake_session_context.__exit__.return_value = False
        fake_session_factory = MagicMock(
            name="session_factory",
            return_value=fake_session_context,
        )
        repository_patcher = patch(
            "identity.app.SqlAlchemyIdentityRepository",
            return_value=self.repository,
        )
        repository_patcher.start()
        self.addCleanup(repository_patcher.stop)

        with (
            patch("identity.app.create_session_factory") as create_session_factory_mock,
        ):
            create_session_factory_mock.return_value = (
                MagicMock(name="engine"),
                fake_session_factory,
            )
            self.app = create_app(settings=settings)

        self.client = TestClient(self.app)

    def test_rejects_invalid_auth_context(self) -> None:
        response = self.client.post(
            "/v1/auth/validate",
            json={
                "auth_context": "invalid-token",
                "request_id": "req_123",
                "chat_id": "chat_123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "valid": False,
                "subject": None,
                "policy_version": "2026-06-29",
                "reason": "invalid_or_expired_auth_context",
            },
        )

    def test_denies_third_party_resource_for_customer(self) -> None:
        response = self.client.post(
            "/v1/authorization/check",
            json={
                "subject": {
                    "user_id": "usr_123",
                    "roles": ["customer"],
                },
                "action": "card_limit.update",
                "resource": {
                    "type": "credit_card",
                    "owner_id": "usr_999",
                },
                "parameters": {
                    "requested_limit": 15000,
                },
                "context": {
                    "request_id": "req_123",
                    "chat_id": "chat_123",
                    "tool_name": "update_card_limit",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "decision": "deny",
                "reason": "resource_not_owned",
                "policy_version": "2026-06-29",
                "subject": {
                    "user_id": "usr_123",
                    "roles": ["customer"],
                },
            },
        )

    def test_validates_auth_context_and_returns_subject_roles(self) -> None:
        response = self.client.post(
            "/v1/auth/validate",
            json={
                "auth_context": "token-customer",
                "request_id": "req_123",
                "chat_id": "chat_123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "valid": True,
                "subject": {
                    "user_id": "usr_123",
                    "roles": ["customer"],
                },
                "policy_version": "2026-06-29",
                "reason": None,
            },
        )

    def test_authorizes_customer_on_own_credit_card_operation(self) -> None:
        response = self.client.post(
            "/v1/authorization/check",
            json={
                "subject": {
                    "user_id": "usr_123",
                    "roles": ["customer"],
                },
                "action": "card_limit.update",
                "resource": {
                    "type": "credit_card",
                    "owner_id": "usr_123",
                },
                "parameters": {
                    "requested_limit": 15000,
                },
                "context": {
                    "request_id": "req_123",
                    "chat_id": "chat_123",
                    "tool_name": "update_card_limit",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "decision": "allow",
                "reason": "role_allows_own_resource",
                "policy_version": "2026-06-29",
                "subject": {
                    "user_id": "usr_123",
                    "roles": ["customer"],
                },
            },
        )

    def test_records_authorization_audit_entry(self) -> None:
        self.client.post(
            "/v1/authorization/check",
            json={
                "subject": {
                    "user_id": "usr_123",
                    "roles": ["customer"],
                },
                "action": "card_limit.update",
                "resource": {
                    "type": "credit_card",
                    "owner_id": "usr_123",
                },
                "parameters": {
                    "requested_limit": 15000,
                },
                "context": {
                    "request_id": "req_123",
                    "chat_id": "chat_123",
                    "tool_name": "update_card_limit",
                },
            },
        )

        self.assertEqual(len(self.repository.decisions), 1)
        self.assertEqual(
            self.repository.decisions[0]["event_name"],
            "identity.authorization_allowed",
        )
        self.assertEqual(self.repository.decisions[0]["decision"], "allow")


if __name__ == "__main__":
    unittest.main()
