from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from langchain_core.tools import tool

from .knowledge import KnowledgeBaseUnavailableError
from .models import KnowledgeHit


@dataclass(frozen=True)
class ToolContext:
    tool_client: object
    knowledge_client: object


class ConfirmationRequiredError(RuntimeError):
    def __init__(self, tool_name: str, parameters: dict) -> None:
        super().__init__(tool_name)
        self.tool_name = tool_name
        self.parameters = parameters


def create_tools(ctx: ToolContext) -> list:
    @tool
    async def consult_information(query: str) -> str:
        """Consult the knowledge base and answer only with grounded information.

        Args:
            query: The user's informational question
        """
        try:
            hits = await ctx.knowledge_client.retrieve(query)
        except KnowledgeBaseUnavailableError:
            return (
                "A base de conhecimento esta temporariamente indisponivel. "
                "Tente novamente em instantes."
            )

        grounded_hits = [hit for hit in hits if hit.document.strip()]

        if not grounded_hits:
            return (
                "Nao encontrei evidencia suficiente na base de conhecimento "
                "para responder com seguranca."
            )

        return _build_grounded_answer(grounded_hits)

    @tool
    async def banking_operation(
        operation: str,
        customer_id: str,
        requested_limit: float | None = None,
    ) -> str:
        """Handle standard banking operations for the authenticated customer.

        Args:
            operation: Supported values are get_customer_profile, get_balance,
                get_card_limit, and update_card_limit
            customer_id: The customer's unique identifier
            requested_limit: The requested new credit card limit when applicable
        """
        normalized_operation = operation.strip().lower()
        handlers = {
            "get_customer_profile": _handle_profile_lookup,
            "get_balance": _handle_balance_lookup,
            "get_card_limit": _handle_card_limit_lookup,
            "update_card_limit": _handle_card_limit_update,
        }
        handler = handlers.get(normalized_operation)

        if handler is None:
            return "Nao reconheci a operacao bancaria solicitada."

        return await handler(
            ctx=ctx,
            customer_id=customer_id,
            requested_limit=requested_limit,
        )

    @tool
    async def critical_operation(
        operation: str,
        customer_id: str,
        destination_key: str | None = None,
        amount: float | None = None,
    ) -> str:
        """Handle critical banking operations that require extra confirmation.

        Args:
            operation: Supported values are create_pix
            customer_id: The customer's unique identifier
            destination_key: The PIX destination key when applicable
            amount: Transfer amount in BRL when applicable
        """
        normalized_operation = operation.strip().lower()

        if normalized_operation != "create_pix":
            return "Nao reconheci a operacao critica solicitada."

        return await _handle_pix_execution(
            ctx=ctx,
            customer_id=customer_id,
            destination_key=destination_key,
            amount=amount,
        )

    return [consult_information, banking_operation, critical_operation]


async def _handle_profile_lookup(
    *,
    ctx: ToolContext,
    customer_id: str,
    requested_limit: float | None = None,
) -> str:
    try:
        profile = await ctx.tool_client.get_customer_profile(customer_id)
    except Exception:
        return "Houve uma indisponibilidade temporaria ao tentar consultar o perfil."

    segment = str(profile.get("segment") or "nao informado")
    return f"Seu perfil bancario atual esta no segmento {segment}."


async def _handle_balance_lookup(
    *,
    ctx: ToolContext,
    customer_id: str,
    requested_limit: float | None = None,
) -> str:
    try:
        balance = await ctx.tool_client.get_balance(customer_id)
    except Exception:
        return "Houve uma indisponibilidade temporaria ao tentar consultar o saldo."

    formatted = _format_currency(balance.get("balance"))
    return f"Seu saldo atual e {formatted}."


async def _handle_card_limit_lookup(
    *,
    ctx: ToolContext,
    customer_id: str,
    requested_limit: float | None = None,
) -> str:
    try:
        card_limit = await ctx.tool_client.get_card_limit(customer_id)
    except Exception:
        return "Houve uma indisponibilidade temporaria ao tentar consultar o limite do cartao."

    formatted = _format_currency(card_limit.get("current_limit"))
    return f"Seu limite atual do cartao e {formatted}."


async def _handle_card_limit_update(
    *,
    ctx: ToolContext,
    customer_id: str,
    requested_limit: float | None = None,
) -> str:
    if requested_limit is None:
        return "Me diga qual valor de limite voce deseja solicitar."

    requested = _to_decimal(requested_limit)

    try:
        card_limit = await ctx.tool_client.get_card_limit(customer_id)
    except Exception:
        return "Houve uma indisponibilidade temporaria ao tentar consultar o limite do cartao."

    current_limit = _to_decimal(card_limit.get("current_limit"))
    max_eligible = (current_limit * Decimal("1.5")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if requested <= current_limit:
        return (
            "Esse valor nao representa aumento. "
            "Me diga um valor acima do seu limite atual."
        )

    if requested > max_eligible:
        return (
            "No momento eu so posso propor aumento ate "
            f"{_format_currency(max_eligible)} com base na elegibilidade atual."
        )

    raise ConfirmationRequiredError(
        "banking_operation",
        {
            "operation": "update_card_limit",
            "customer_id": customer_id,
            "requested_limit": str(requested),
            "current_limit": str(current_limit),
            "max_eligible_limit": str(max_eligible),
        },
    )


async def _handle_pix_execution(
    *,
    ctx: ToolContext,
    customer_id: str,
    destination_key: str | None,
    amount: float | None,
) -> str:
    if destination_key is None or not destination_key.strip():
        return "Me diga a chave PIX de destino para eu seguir."

    if amount is None:
        return "Me diga o valor do PIX para eu seguir."

    transfer_amount = _to_decimal(amount)

    if transfer_amount <= Decimal("0.00"):
        return "O valor do PIX precisa ser maior que zero."

    try:
        balance = await ctx.tool_client.get_balance(customer_id)
    except Exception:
        return "Houve uma indisponibilidade temporaria ao tentar consultar o saldo."

    current_balance = _to_decimal(balance.get("balance"))

    if current_balance < transfer_amount:
        return "Nao consigo seguir com esse PIX porque o saldo disponivel e insuficiente."

    raise ConfirmationRequiredError(
        "critical_operation",
        {
            "operation": "create_pix",
            "customer_id": customer_id,
            "destination_key": destination_key,
            "amount": str(transfer_amount),
            "current_balance": str(current_balance),
        },
    )


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if value is None:
        return Decimal("0.00")

    normalized = str(value).strip()

    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")

    try:
        return Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return Decimal("0.00")


def _format_currency(value) -> str:
    amount = _to_decimal(value)
    integer_part, decimal_part = f"{amount:.2f}".split(".")
    groups: list[str] = []

    while integer_part:
        groups.insert(0, integer_part[-3:])
        integer_part = integer_part[:-3]

    return f"R$ {'.'.join(groups)},{decimal_part}"


def _build_grounded_answer(hits: Iterable[KnowledgeHit]) -> str:
    selected_hits = list(hits)[:2]
    primary_hit = selected_hits[0]
    excerpt = primary_hit.document.strip()

    if len(excerpt) > 360:
        excerpt = excerpt[:357].rstrip() + "..."

    source_lines = []

    for hit in selected_hits:
        title = str(hit.metadata.get("title") or "Documento sem titulo")
        document_id = str(hit.metadata.get("document_id") or "desconhecido")
        chunk_index = hit.metadata.get("chunk_index")
        chunk_suffix = f", trecho {chunk_index}" if isinstance(chunk_index, int) else ""
        source_lines.append(f"- {title} ({document_id}{chunk_suffix})")

    return (
        "Encontrei esta orientacao na base de conhecimento:\n\n"
        f"{excerpt}\n\n"
        "Fontes:\n" + "\n".join(source_lines)
    )
