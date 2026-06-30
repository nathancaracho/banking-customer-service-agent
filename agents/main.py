import asyncio

from observability import setup_telemetry

from agents.config import load_settings
from agents.customer_service import create_customer_service_runner
from agents.database import create_session_factory
from agents.clients.identity_client import IdentityClient
from agents.knowledge import KnowledgeRetriever
from agents.clients.mcp_client import McpToolClient
from agents.worker import AgentWorker


def main() -> None:
    settings = load_settings()
    _engine, session_factory = create_session_factory(
        settings.database_url,
        settings.database_schema,
    )
    setup_telemetry("agents", sqlalchemy_engines=[_engine])
    
    authorization_client = IdentityClient(
        settings.identity_base_url,
        settings.identity_timeout_seconds,
    )
    knowledge_client = KnowledgeRetriever(settings)
    tool_client = McpToolClient(
        settings.mcp_url,
        settings.mcp_timeout_seconds,
    )
    agent = create_customer_service_runner(
        authorization_client,
        knowledge_client,
        tool_client,
        settings,
    )
    worker = AgentWorker(settings, agent, session_factory)
    asyncio.run(worker.serve_forever())


if __name__ == "__main__":
    main()
