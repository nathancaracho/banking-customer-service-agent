from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    roles: list[str]


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chat_id: str
    role: str
    content: str
    status: str
    created_at: datetime


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class ChatDetailResponse(ChatResponse):
    messages: list[MessageResponse]
