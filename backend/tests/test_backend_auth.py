import unittest

import jwt

from backend.auth import (
    AuthenticationError,
    authenticate_demo_user,
    decode_access_token,
)


class BackendAuthTestCase(unittest.TestCase):
    secret = "test-secret-with-at-least-32-bytes"

    def test_rejects_invalid_token(self) -> None:
        with self.assertRaises(AuthenticationError):
            decode_access_token(
                "invalid-token",
                secret=self.secret,
                algorithm="HS256",
            )

    def test_returns_subject_from_valid_token(self) -> None:
        token = jwt.encode(
            {"sub": "usr_123"},
            self.secret,
            algorithm="HS256",
        )

        current_user = decode_access_token(
            token,
            secret=self.secret,
            algorithm="HS256",
        )

        self.assertEqual(current_user.user_id, "usr_123")

    def test_rejects_invalid_demo_credentials(self) -> None:
        with self.assertRaises(AuthenticationError):
            authenticate_demo_user("customer", "wrong", "demo")

    def test_authenticates_demo_customer(self) -> None:
        current_user = authenticate_demo_user("customer", "demo", "demo")

        self.assertEqual(current_user.user_id, "usr_123")
        self.assertEqual(current_user.roles, ("customer",))
