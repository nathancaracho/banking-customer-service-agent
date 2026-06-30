from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=255)
    segment: str = Field(min_length=1, max_length=64)
    credit_score: int = Field(ge=0, le=1000)
    initial_balance: Decimal = Field(
        ge=0,
        le=Decimal("999999999999.99"),
        max_digits=14,
        decimal_places=2,
    )
    initial_card_limit: Decimal = Field(
        ge=0,
        le=Decimal("999999999999.99"),
        max_digits=14,
        decimal_places=2,
    )


class CustomerProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    segment: str = Field(min_length=1, max_length=64)
    credit_score: int = Field(ge=0, le=1000)


class CustomerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    segment: str
    credit_score: int


class BalanceResponse(BaseModel):
    customer_id: str
    account_id: str
    balance: Decimal
    currency: str = "BRL"


class BalanceUpdate(BaseModel):
    balance: Decimal = Field(
        ge=0,
        le=Decimal("999999999999.99"),
        max_digits=14,
        decimal_places=2,
    )


class CardLimitResponse(BaseModel):
    customer_id: str
    card_id: str
    current_limit: Decimal
    currency: str = "BRL"


class CardLimitUpdate(BaseModel):
    requested_limit: Decimal = Field(
        ge=0,
        le=Decimal("999999999999.99"),
        max_digits=14,
        decimal_places=2,
    )


class PixCreate(BaseModel):
    request_id: str = Field(min_length=1, max_length=64)
    customer_id: str = Field(min_length=1, max_length=64)
    destination_key: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class PixResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    customer_id: str
    destination_key: str
    amount: Decimal
    status: str
    created_at: datetime
