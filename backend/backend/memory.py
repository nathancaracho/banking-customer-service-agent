import time
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from observability import record_llm_call
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .models import Chat, ChatSummary, Message
from .repository import get_chat


class MemoryCompressor:
    def __init__(self, settings: Settings) -> None:
        self._llm = ChatOpenAI(
            model=settings.litellm_model,
            base_url=settings.litellm_url,
            api_key=settings.litellm_api_key,
            temperature=0.0,
        )
        self._model = settings.litellm_model

    async def compress_if_needed(
        self,
        session: AsyncSession,
        chat: Chat,
        limit: int,
    ) -> None:
        # Load all messages to check if we exceed the limit significantly
        messages = sorted(chat.messages, key=lambda m: m.created_at)
        
        # Determine how many messages are covered by the current summary
        covered_count = 0
        if chat.summary:
            covered_count = sum(
                1 for m in messages if m.created_at <= chat.summary.covered_until
            )
        
        uncovered_messages = messages[covered_count:]
        
        # If the number of uncovered messages is within limit, do nothing
        if len(uncovered_messages) <= limit:
            return

        # We compress everything except the last few messages (e.g. keep last `limit // 2` intact)
        keep_recent = limit // 2
        to_compress = uncovered_messages[:-keep_recent]
        last_to_compress = to_compress[-1]

        system_prompt = (
            "You are a helpful assistant. Summarize the following conversation. "
            "Keep important context like account numbers, intents, and user preferences. "
            "If there is an existing summary, update it with the new messages."
        )

        history = [SystemMessage(content=system_prompt)]
        if chat.summary:
            history.append(SystemMessage(content=f"Current summary:\n{chat.summary.content}"))

        for m in to_compress:
            if m.role == "user":
                history.append(HumanMessage(content=m.content))
            else:
                history.append(AIMessage(content=m.content))

        prompt_text = "\n".join(str(m.content) for m in history)

        started_at = time.perf_counter()
        error: str | None = None
        try:
            response = await self._llm.ainvoke(history)
            new_summary_content = str(response.content)
            usage = response.usage_metadata
            prompt_tokens = usage.get("input_tokens") if usage else None
            completion_tokens = usage.get("output_tokens") if usage else None
            total_tokens = usage.get("total_tokens") if usage else None
        except Exception as exc:
            new_summary_content = ""
            prompt_tokens = completion_tokens = total_tokens = None
            error = str(exc)
            raise
        finally:
            duration_ms = (time.perf_counter() - started_at) * 1000
            record_llm_call(
                model=self._model,
                operation="chat",
                prompt=prompt_text,
                response=new_summary_content if not error else None,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                duration_ms=duration_ms,
                error=error,
            )

        if chat.summary:
            chat.summary.content = new_summary_content
            chat.summary.covered_until = last_to_compress.created_at
        else:
            summary = ChatSummary(
                chat_id=chat.id,
                content=new_summary_content,
                covered_until=last_to_compress.created_at,
            )
            session.add(summary)
        
        await session.commit()
