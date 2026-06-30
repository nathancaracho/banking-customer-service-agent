from typing import Literal

from pydantic import BaseModel, ConfigDict


class Subject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    roles: list[str]


class AuthValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    auth_context: str
    request_id: str
    chat_id: str


class AuthValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    subject: Subject | None
    policy_version: str
    reason: str | None = None


class AuthorizationResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    owner_id: str | None = None


class AuthorizationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    chat_id: str
    tool_name: str


class AuthorizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: Subject
    action: str
    resource: AuthorizationResource
    parameters: dict | None = None
    context: AuthorizationContext


class AuthorizationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["allow", "deny"]
    reason: str
    policy_version: str
    subject: Subject
