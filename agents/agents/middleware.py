from dataclasses import dataclass
import time
from typing import Any

from langchain.agents.middleware import ToolCallRequest, wrap_tool_call
from langchain_core.messages import ToolMessage
from observability import record_llm_call

from .clients.identity_client import IdentityClientError, build_authorization_request
from .models import Subject


class IdentityDeniedError(RuntimeError):
    pass


@dataclass(frozen=True)
class CustomerServiceContext:
    identity_client: object
    subject: Subject
    request_id: str
    chat_id: str


PROTECTED_TOOLS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "consult_information": {
        "*": [("knowledge.read", "knowledge_base")],
    },
    "banking_operation": {
        "get_customer_profile": [("profile.read", "customer_profile")],
        "get_balance": [("balance.read", "customer_account")],
        "get_card_limit": [("card_limit.read", "credit_card")],
        "update_card_limit": [
            ("card_limit.read", "credit_card"),
            ("card_limit.update", "credit_card"),
        ],
    },
    "critical_operation": {
        "create_pix": [
            ("balance.read", "customer_account"),
            ("pix.transfer", "bank_account"),
        ],
    },
}


@wrap_tool_call
async def identity_middleware(request: ToolCallRequest, handler) -> ToolMessage:
    ctx: CustomerServiceContext = request.runtime.context
    tool_name = request.tool_call.get("name", "")
    args = request.tool_call.get("args", {})
    rules = _resolve_tool_rules(tool_name, args)

    if rules is None:
        return await handler(request)

    for action, resource_type in rules:
        payload = build_authorization_request(
            subject=ctx.subject,
            action=action,
            resource_type=resource_type,
            owner_id=ctx.subject.user_id,
            request_id=ctx.request_id,
            chat_id=ctx.chat_id,
            tool_name=tool_name,
            parameters=args,
        )

        try:
            response = await ctx.identity_client.authorize(payload)
        except IdentityClientError:
            raise IdentityDeniedError(
                "Nao posso executar essa consulta ou operacao com o contexto de acesso atual."
            )

        if response.decision != "allow":
            raise IdentityDeniedError(
                "Nao posso executar essa consulta ou operacao com o contexto de acesso atual."
            )

    return await handler(request)


@wrap_tool_call
async def observability_middleware(request: ToolCallRequest, handler) -> ToolMessage:
    started_at = time.perf_counter()
    tool_name = request.tool_call.get("name", "unknown")

    try:
        result = await handler(request)
    except Exception as exc:
        duration_ms = (time.perf_counter() - started_at) * 1000
        record_llm_call(
            model="tool",
            operation="tool_call",
            prompt=tool_name,
            duration_ms=duration_ms,
            error=str(exc),
        )
        raise

    duration_ms = (time.perf_counter() - started_at) * 1000
    content = result.content if isinstance(result, ToolMessage) else str(result)
    record_llm_call(
        model="tool",
        operation="tool_call",
        prompt=tool_name,
        response=content[:500] if content else "",
        duration_ms=duration_ms,
    )
    return result


def _resolve_tool_rules(
    tool_name: str,
    args: dict[str, Any],
) -> list[tuple[str, str]] | None:
    tool_rules = PROTECTED_TOOLS.get(tool_name)

    if tool_rules is None:
        return None

    operation = str(args.get("operation") or "*").strip().lower()
    return tool_rules.get(operation) or tool_rules.get("*")
