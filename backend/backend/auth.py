from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt


class AuthenticationError(Exception):
    pass


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    roles: tuple[str, ...]


DEMO_USERS = {
    "customer": CurrentUser(user_id="usr_123", roles=("customer",)),
    "manager": CurrentUser(user_id="usr_manager", roles=("manager",)),
    "admin": CurrentUser(user_id="usr_admin", roles=("admin",)),
}


def decode_access_token(
    token: str,
    secret: str,
    algorithm: str,
) -> CurrentUser:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"require": ["sub"]},
        )
    except jwt.PyJWTError as error:
        raise AuthenticationError("Invalid access token") from error

    user_id = str(payload["sub"]).strip()

    if not user_id:
        raise AuthenticationError("Invalid access token subject")

    roles = tuple(str(role) for role in payload.get("roles", []))
    return CurrentUser(user_id=user_id, roles=roles)


def authenticate_demo_user(
    username: str,
    password: str,
    expected_password: str,
) -> CurrentUser:
    current_user = DEMO_USERS.get(username)

    if current_user is None or password != expected_password:
        raise AuthenticationError("Invalid credentials")

    return current_user


def create_access_token(
    current_user: CurrentUser,
    secret: str,
    algorithm: str,
) -> str:
    return jwt.encode(
        {
            "sub": current_user.user_id,
            "roles": list(current_user.roles),
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        },
        secret,
        algorithm=algorithm,
    )
