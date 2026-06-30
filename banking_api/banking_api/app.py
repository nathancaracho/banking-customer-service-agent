from collections.abc import Generator
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings, load_settings
from .database import create_session_factory
from .models import Account, CreditCard, Customer, PixTransfer
from .schemas import (
    BalanceResponse,
    BalanceUpdate,
    CardLimitResponse,
    CardLimitUpdate,
    CustomerCreate,
    CustomerProfileResponse,
    CustomerProfileUpdate,
    PixCreate,
    PixResponse,
)


def _get_session(request: Request) -> Generator[Session, None, None]:
    with request.app.state.session_factory() as session:
        yield session


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    engine, session_factory = create_session_factory(
        resolved_settings.database_url,
        resolved_settings.database_schema,
    )

    app = FastAPI(title="Banking API")
    app.state.engine = engine
    app.state.session_factory = session_factory

    @app.get("/health")
    def _health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/v1/customers",
        response_model=CustomerProfileResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def _create_customer(
        payload: CustomerCreate,
        session: Session = Depends(_get_session),
    ) -> CustomerProfileResponse:
        if session.get(Customer, payload.id) is not None:
            raise HTTPException(status_code=409, detail="Customer already exists")

        customer = Customer(
            id=payload.id,
            display_name=payload.display_name,
            segment=payload.segment,
            credit_score=payload.credit_score,
        )
        customer.account = Account(
            id=str(uuid4()),
            balance=payload.initial_balance,
        )
        customer.credit_card = CreditCard(
            id=str(uuid4()),
            current_limit=payload.initial_card_limit,
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)
        return CustomerProfileResponse.model_validate(customer)

    @app.get(
        "/v1/customers/{customer_id}/profile",
        response_model=CustomerProfileResponse,
    )
    def _get_customer_profile(
        customer_id: str,
        session: Session = Depends(_get_session),
    ) -> CustomerProfileResponse:
        customer = session.get(Customer, customer_id)

        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        return CustomerProfileResponse.model_validate(customer)

    @app.put(
        "/v1/customers/{customer_id}/profile",
        response_model=CustomerProfileResponse,
    )
    def _update_customer_profile(
        customer_id: str,
        payload: CustomerProfileUpdate,
        session: Session = Depends(_get_session),
    ) -> CustomerProfileResponse:
        customer = session.get(Customer, customer_id)

        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        customer.display_name = payload.display_name
        customer.segment = payload.segment
        customer.credit_score = payload.credit_score
        session.commit()
        return CustomerProfileResponse.model_validate(customer)

    @app.get(
        "/v1/customers/{customer_id}/balance",
        response_model=BalanceResponse,
    )
    def _get_balance(
        customer_id: str,
        session: Session = Depends(_get_session),
    ) -> BalanceResponse:
        account = session.scalar(
            select(Account).where(Account.customer_id == customer_id)
        )

        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")

        return BalanceResponse(
            customer_id=customer_id,
            account_id=account.id,
            balance=account.balance,
        )

    @app.put(
        "/v1/customers/{customer_id}/balance",
        response_model=BalanceResponse,
    )
    def _update_balance(
        customer_id: str,
        payload: BalanceUpdate,
        session: Session = Depends(_get_session),
    ) -> BalanceResponse:
        account = session.scalar(
            select(Account).where(Account.customer_id == customer_id)
        )

        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")

        account.balance = payload.balance
        session.commit()

        return BalanceResponse(
            customer_id=customer_id,
            account_id=account.id,
            balance=account.balance,
        )

    @app.get(
        "/v1/customers/{customer_id}/card-limit",
        response_model=CardLimitResponse,
    )
    def _get_card_limit(
        customer_id: str,
        session: Session = Depends(_get_session),
    ) -> CardLimitResponse:
        card = session.scalar(
            select(CreditCard).where(CreditCard.customer_id == customer_id)
        )

        if card is None:
            raise HTTPException(status_code=404, detail="Credit card not found")

        return CardLimitResponse(
            customer_id=customer_id,
            card_id=card.id,
            current_limit=card.current_limit,
        )

    @app.put(
        "/v1/customers/{customer_id}/card-limit",
        response_model=CardLimitResponse,
    )
    def _update_card_limit(
        customer_id: str,
        payload: CardLimitUpdate,
        session: Session = Depends(_get_session),
    ) -> CardLimitResponse:
        card = session.scalar(
            select(CreditCard).where(CreditCard.customer_id == customer_id)
        )

        if card is None:
            raise HTTPException(status_code=404, detail="Credit card not found")

        card.current_limit = payload.requested_limit
        session.commit()

        return CardLimitResponse(
            customer_id=customer_id,
            card_id=card.id,
            current_limit=card.current_limit,
        )

    @app.post(
        "/v1/pix",
        response_model=PixResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def _create_pix(
        payload: PixCreate,
        session: Session = Depends(_get_session),
    ) -> PixResponse:
        existing_transfer = session.scalar(
            select(PixTransfer).where(
                PixTransfer.request_id == payload.request_id
            )
        )

        if existing_transfer is not None:
            return PixResponse.model_validate(existing_transfer)

        account = session.scalar(
            select(Account).where(Account.customer_id == payload.customer_id)
        )

        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")

        if account.balance < payload.amount:
            raise HTTPException(
                status_code=409,
                detail="Insufficient balance",
            )

        account.balance -= payload.amount
        transfer = PixTransfer(
            id=str(uuid4()),
            request_id=payload.request_id,
            customer_id=payload.customer_id,
            destination_key=payload.destination_key,
            amount=payload.amount,
            status="completed",
        )
        session.add(transfer)
        session.commit()
        session.refresh(transfer)
        return PixResponse.model_validate(transfer)

    return app
