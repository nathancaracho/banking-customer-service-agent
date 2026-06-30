from datetime import datetime, timezone
from hashlib import sha256

from .repository import IdentityRepository
from .schemas import (
    AuthorizationRequest,
    AuthorizationResponse,
    AuthValidationRequest,
    AuthValidationResponse,
    Subject,
)

_AUTHORIZATION_DECISIONS = {
    ("any", True): ("allow", "role_allows_any_resource"),
    ("any", False): ("allow", "role_allows_any_resource"),
    ("own", True): ("allow", "role_allows_own_resource"),
    ("own", False): ("deny", "resource_not_owned"),
    (None, True): ("deny", "no_matching_permission"),
    (None, False): ("deny", "no_matching_permission"),
}

_AUTHORIZATION_EVENTS = {
    "allow": "identity.authorization_allowed",
    "deny": "identity.authorization_denied",
}


def _hash_auth_context(auth_context: str) -> str:
    return sha256(auth_context.encode("utf-8")).hexdigest()


def validate_auth_context(
    repository: IdentityRepository,
    payload: AuthValidationRequest,
) -> AuthValidationResponse:
    policy_version = repository.get_active_policy_version()
    token_hash = _hash_auth_context(payload.auth_context.strip())
    now = datetime.now(timezone.utc)
    auth_session = repository.find_auth_session(token_hash, now)

    if not auth_session or not auth_session.user.is_active:
        response = AuthValidationResponse(
            valid=False,
            subject=None,
            policy_version=policy_version,
            reason="invalid_or_expired_auth_context",
        )
        _record_decision(
            repository,
            decision_type="context_validation",
            event_name="identity.context_rejected",
            decision="deny",
            reason=response.reason,
            policy_version=policy_version,
            user_id=None,
            subject_roles=None,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
            action=None,
            resource_type=None,
            resource_owner_id=None,
            tool_name=None,
            parameters=None,
        )
        return response

    subject = Subject(
        user_id=auth_session.user.user_id,
        roles=sorted(auth_session.user.roles),
    )
    response = AuthValidationResponse(
        valid=True,
        subject=subject,
        policy_version=policy_version,
    )
    _record_decision(
        repository,
        decision_type="context_validation",
        event_name="identity.context_validated",
        decision="allow",
        reason="auth_context_valid",
        policy_version=policy_version,
        user_id=subject.user_id,
        subject_roles=subject.roles,
        request_id=payload.request_id,
        chat_id=payload.chat_id,
        action=None,
        resource_type=None,
        resource_owner_id=None,
        tool_name=None,
        parameters=None,
    )

    return response


def authorize_tool_call(
    repository: IdentityRepository,
    payload: AuthorizationRequest,
) -> AuthorizationResponse:
    policy_version = repository.get_active_policy_version()
    permissions = repository.list_permissions(
        payload.subject.roles,
        payload.action,
        payload.resource.type,
    )
    ownership_scope = next(
        (
            scope
            for scope in ("any", "own")
            if any(permission.ownership_scope == scope for permission in permissions)
        ),
        None,
    )
    owns_resource = payload.resource.owner_id == payload.subject.user_id
    decision, reason = _AUTHORIZATION_DECISIONS[(ownership_scope, owns_resource)]
    response = AuthorizationResponse(
        decision=decision,
        reason=reason,
        policy_version=policy_version,
        subject=payload.subject,
    )
    event_name = _AUTHORIZATION_EVENTS[response.decision]
    _record_decision(
        repository,
        decision_type="authorization",
        event_name=event_name,
        decision=response.decision,
        reason=response.reason,
        policy_version=policy_version,
        user_id=payload.subject.user_id,
        subject_roles=payload.subject.roles,
        request_id=payload.context.request_id,
        chat_id=payload.context.chat_id,
        action=payload.action,
        resource_type=payload.resource.type,
        resource_owner_id=payload.resource.owner_id,
        tool_name=payload.context.tool_name,
        parameters=payload.parameters,
    )

    return response


def _record_decision(
    repository: IdentityRepository,
    *,
    decision_type: str,
    event_name: str,
    decision: str,
    reason: str,
    policy_version: str,
    user_id: str | None,
    subject_roles: list[str] | None,
    request_id: str | None,
    chat_id: str | None,
    action: str | None,
    resource_type: str | None,
    resource_owner_id: str | None,
    tool_name: str | None,
    parameters: dict | None,
) -> None:
    repository.record_decision(
        decision_type=decision_type,
        event_name=event_name,
        decision=decision,
        reason=reason,
        policy_version=policy_version,
        user_id=user_id,
        subject_roles=subject_roles,
        request_id=request_id,
        chat_id=chat_id,
        action=action,
        resource_type=resource_type,
        resource_owner_id=resource_owner_id,
        tool_name=tool_name,
        parameters=parameters,
    )
