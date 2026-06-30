from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.customer_service import AgentOutcome, create_customer_service_runner
from agents.models import AgentRequest, AuthorizationResponse, KnowledgeHit
from agents.middleware import IdentityDeniedError
from agents.tools import ConfirmationRequiredError


class FakeIdentityClient:
    def __init__(self) -> None:
        self.calls: list[object] = []

    async def authorize(self, payload):
        self.calls.append(payload)
        owner_id = payload.resource.owner_id

        if owner_id and owner_id != payload.subject.user_id:
            return _authorization_response("deny")

        return _authorization_response("allow")


class FakeKnowledgeClient:
    def __init__(self, hits: list[KnowledgeHit] | None = None) -> None:
        self.hits = hits or []
        self.queries: list[str] = []

    async def retrieve(self, query: str) -> list[KnowledgeHit]:
        self.queries.append(query)
        return self.hits


class FakeToolClient:
    def __init__(self) -> None:
        self.profile_calls: list[str] = []
        self.balance_calls: list[str] = []
        self.limit_calls: list[str] = []
        self.limit_updates: list[tuple[str, Decimal]] = []
        self.pix_calls: list[tuple[str, str, str, Decimal]] = []

    async def get_customer_profile(self, customer_id: str):
        self.profile_calls.append(customer_id)
        return {"customer_id": customer_id, "segment": "Personnalite"}

    async def get_balance(self, customer_id: str):
        self.balance_calls.append(customer_id)
        return {"customer_id": customer_id, "balance": "2500.00"}

    async def get_card_limit(self, customer_id: str):
        self.limit_calls.append(customer_id)
        return {"customer_id": customer_id, "current_limit": "10000.00"}

    async def update_card_limit(
        self,
        customer_id: str,
        requested_limit: Decimal,
    ):
        self.limit_updates.append((customer_id, requested_limit))
        return {"customer_id": customer_id, "current_limit": str(requested_limit)}

    async def create_pix(
        self,
        request_id: str,
        customer_id: str,
        destination_key: str,
        amount: Decimal,
    ):
        self.pix_calls.append((request_id, customer_id, destination_key, amount))
        return {
            "id": "pix_12345678",
            "customer_id": customer_id,
            "amount": str(amount),
        }


def _create_fake_llm() -> MagicMock:
    return MagicMock()


class CustomerServiceAgentTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_configures_create_agent_with_domain_tools_and_middlewares(self) -> None:
        agent = create_customer_service_runner(
            FakeIdentityClient(),
            FakeKnowledgeClient(),
            FakeToolClient(),
            llm=_create_fake_llm(),
        )

        mock_result = {"messages": [MagicMock(content="ok")]}

        with unittest.mock.patch("agents.customer_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_agent

            await agent(_build_request("Qual meu saldo?"))

            _, kwargs = mock_create.call_args
            self.assertEqual(
                [tool.name for tool in kwargs["tools"]],
                [
                    "consult_information",
                    "banking_operation",
                    "critical_operation",
                ],
            )
            self.assertIn("middleware", kwargs)
            self.assertNotIn("HumanInTheLoopMiddleware", str(kwargs["middleware"]))

    async def test_sends_chat_memory_to_agent_invocation(self) -> None:
        agent = create_customer_service_runner(
            FakeIdentityClient(),
            FakeKnowledgeClient(),
            FakeToolClient(),
            llm=_create_fake_llm(),
        )

        mock_result = {"messages": [MagicMock(content="ok")]}
        request = _build_request("E aumenta para 10 mil.")
        request.payload.memory.summary = "O cliente perguntou o limite atual."
        request.payload.memory.recent_messages = [
            {"role": "user", "content": "Qual meu limite?"},
            {"role": "assistant", "content": "Seu limite atual e R$ 10.000,00."},
        ]

        with unittest.mock.patch("agents.customer_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_agent

            await agent(request)

            invoke_args, invoke_kwargs = mock_agent.ainvoke.call_args
            messages = invoke_args[0]["messages"]
            self.assertEqual(messages[0].content, "Qual meu limite?")
            self.assertEqual(messages[1].content, "Seu limite atual e R$ 10.000,00.")
            self.assertIn("Conversation summary", messages[2].content)
            self.assertIn("customer_id", messages[2].content)
            self.assertEqual(
                invoke_kwargs["context"].subject.user_id,
                "usr_123",
            )

    async def test_returns_grounded_answer_with_sources(self) -> None:
        agent = create_customer_service_runner(
            FakeIdentityClient(),
            FakeKnowledgeClient(
                [
                    KnowledgeHit(
                        document="A taxa do consignado para aposentados e de 1% ao mes.",
                        metadata={
                            "title": "Tabela de Tarifas 2026",
                            "document_id": "loan-rates-2026",
                            "chunk_index": 0,
                        },
                    )
                ]
            ),
            FakeToolClient(),
            llm=_create_fake_llm(),
        )

        mock_result = {
            "messages": [
                MagicMock(
                    content=(
                        "Encontrei esta orientacao na base de conhecimento:\n\n"
                        "A taxa do consignado para aposentados e de 1% ao mes.\n\n"
                        "Fontes:\n- Tabela de Tarifas 2026 (loan-rates-2026, trecho 0)"
                    )
                )
            ],
        }

        with unittest.mock.patch("agents.customer_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_agent

            outcome = await agent(
                _build_request("Qual a taxa do emprestimo consignado para aposentados?")
            )

            self.assertIn("A taxa do consignado", outcome.content)
            self.assertIn("Fontes:", outcome.content)
            self.assertIn("loan-rates-2026", outcome.content)

    async def test_denies_third_party_balance_access(self) -> None:
        identity_client = FakeIdentityClient()
        tool_client = FakeToolClient()
        agent = create_customer_service_runner(
            identity_client,
            FakeKnowledgeClient(),
            tool_client,
            llm=_create_fake_llm(),
        )

        with unittest.mock.patch("agents.customer_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                side_effect=IdentityDeniedError(
                    "Nao posso executar essa consulta ou operacao com o contexto de acesso atual."
                )
            )
            mock_create.return_value = mock_agent

            outcome = await agent(
                _build_request("Mostre o saldo da conta do Joao Silva")
            )

            self.assertIn("Nao posso executar", outcome.content)
            self.assertEqual(tool_client.balance_calls, [])

    async def test_interrupts_for_credit_limit_update(self) -> None:
        identity_client = FakeIdentityClient()
        tool_client = FakeToolClient()
        agent = create_customer_service_runner(
            identity_client,
            FakeKnowledgeClient(),
            tool_client,
            llm=_create_fake_llm(),
        )

        confirmation_exc = ConfirmationRequiredError(
            "banking_operation",
            {
                "operation": "update_card_limit",
                "customer_id": "usr_123",
                "requested_limit": "15000.00",
            },
        )

        with unittest.mock.patch("agents.customer_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(side_effect=confirmation_exc)
            mock_create.return_value = mock_agent

            outcome = await agent(
                _build_request("Quero aumentar o limite para R$ 15000")
            )

            self.assertTrue(outcome.requires_confirmation)
            self.assertEqual(outcome.tool_name, "banking_operation")
            self.assertIn("aumento", outcome.content.lower())
            self.assertIn("15000", outcome.content)

    async def test_interrupts_for_pix_transfer(self) -> None:
        tool_client = FakeToolClient()
        agent = create_customer_service_runner(
            FakeIdentityClient(),
            FakeKnowledgeClient(),
            tool_client,
            llm=_create_fake_llm(),
        )

        confirmation_exc = ConfirmationRequiredError(
            "critical_operation",
            {
                "operation": "create_pix",
                "customer_id": "usr_123",
                "destination_key": "pix@example.com",
                "amount": "200.00",
            },
        )

        with unittest.mock.patch("agents.customer_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(side_effect=confirmation_exc)
            mock_create.return_value = mock_agent

            outcome = await agent(
                _build_request("Faca um pix de R$ 200 para chave pix@example.com")
            )

            self.assertTrue(outcome.requires_confirmation)
            self.assertEqual(outcome.tool_name, "critical_operation")
            self.assertIn("pix", outcome.content.lower())
            self.assertIn("pix@example.com", outcome.content)

    async def test_handles_empty_message(self) -> None:
        agent = create_customer_service_runner(
            FakeIdentityClient(),
            FakeKnowledgeClient(),
            FakeToolClient(),
            llm=_create_fake_llm(),
        )

        outcome = await agent(_build_request(""))
        self.assertIn("Pode me dizer com mais detalhes", outcome.content)


def _build_request(message: str) -> AgentRequest:
    return AgentRequest.model_validate(
        {
            "request_id": "req_123",
            "chat_id": "chat_123",
            "subject": {
                "user_id": "usr_123",
                "roles": ["customer"],
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "message": {
                    "role": "user",
                    "content": message,
                },
                "memory": {
                    "summary": None,
                    "recent_messages": [],
                },
            },
        }
    )


def _authorization_response(decision: str):
    return AuthorizationResponse.model_validate(
        {
            "decision": decision,
            "reason": "ok" if decision == "allow" else "resource_not_owned",
            "policy_version": "2026-06-29",
            "subject": {
                "user_id": "usr_123",
                "roles": ["customer"],
            },
        }
    )


if __name__ == "__main__":
    unittest.main()
