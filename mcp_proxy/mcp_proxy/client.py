from decimal import Decimal
from typing import Any

import httpx


class BankingApiError(Exception):
    pass


class BankingApiClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds

    async def get_customer_profile(self, customer_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/v1/customers/{customer_id}/profile",
        )

    async def get_balance(self, customer_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/v1/customers/{customer_id}/balance",
        )

    async def get_card_limit(self, customer_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/v1/customers/{customer_id}/card-limit",
        )

    async def update_card_limit(
        self,
        customer_id: str,
        requested_limit: Decimal,
    ) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/v1/customers/{customer_id}/card-limit",
            json={"requested_limit": str(requested_limit)},
        )

    async def create_pix(
        self,
        request_id: str,
        customer_id: str,
        destination_key: str,
        amount: Decimal,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/pix",
            json={
                "request_id": request_id,
                "customer_id": customer_id,
                "destination_key": destination_key,
                "amount": str(amount),
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
            ) as client:
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as error:
            detail = _get_error_detail(error.response)
            raise BankingApiError(
                f"Banking API returned {error.response.status_code}: {detail}"
            ) from error
        except httpx.HTTPError as error:
            raise BankingApiError("Banking API is unavailable") from error


def _get_error_detail(response: httpx.Response) -> str:
    try:
        return str(response.json().get("detail", "unknown error"))
    except ValueError:
        return "unknown error"
