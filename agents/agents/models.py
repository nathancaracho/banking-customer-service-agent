from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Subject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    roles: list[str]


class MessagePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class MemoryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    recent_messages: list[MessagePayload] = Field(default_factory=list)


class AgentRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: MessagePayload
    memory: MemoryPayload
    checkpoint_id: str | None = None


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    chat_id: str
    subject: Subject
    timestamp: datetime
    payload: AgentRequestPayload


class AgentEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str | None = None
    code: str | None = None
    checkpoint_id: str | None = None


class AgentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    chat_id: str
    type: Literal["chunk", "completed", "failed", "confirmation_required"]
    sequence: int
    payload: AgentEventPayload


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
    parameters: dict[str, Any] | None = None
    context: AuthorizationContext


class AuthorizationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["allow", "deny"]
    reason: str
    policy_version: str
    subject: Subject


class KnowledgeHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: str
    distance: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
