from typing import Any

import httpx

from ..models import AuthorizationRequest, AuthorizationResponse


class IdentityClientError(RuntimeError):
    pass


class IdentityClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds

    async def authorize(self, payload: AuthorizationRequest) -> AuthorizationResponse:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
            ) as client:
                response = await client.post(
                    "/v1/authorization/check",
                    json=payload.model_dump(mode="json"),
                )
                response.raise_for_status()
        except httpx.HTTPError as error:
            raise IdentityClientError("Identity service is unavailable") from error

        return AuthorizationResponse.model_validate(response.json())


def build_authorization_request(
    *,
    subject: Any,
    action: str,
    resource_type: str,
    owner_id: str | None,
    request_id: str,
    chat_id: str,
    tool_name: str,
    parameters: dict[str, Any] | None = None,
) -> AuthorizationRequest:
    return AuthorizationRequest(
        subject=subject,
        action=action,
        resource={
            "type": resource_type,
            "owner_id": owner_id,
        },
        parameters=parameters,
        context={
            "request_id": request_id,
            "chat_id": chat_id,
            "tool_name": tool_name,
        },
    )
