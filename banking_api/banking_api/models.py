from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255))
    segment: Mapped[str] = mapped_column(String(64))
    credit_score: Mapped[int]

    account: Mapped["Account"] = relationship(back_populates="customer")
    credit_card: Mapped["CreditCard"] = relationship(back_populates="customer")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id"),
        unique=True,
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    customer: Mapped[Customer] = relationship(back_populates="account")


class CreditCard(Base):
    __tablename__ = "credit_cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id"),
        unique=True,
    )
    current_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    customer: Mapped[Customer] = relationship(back_populates="credit_card")


class PixTransfer(Base):
    __tablename__ = "pix_transfers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    destination_key: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )
