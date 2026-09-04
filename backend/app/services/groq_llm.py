from __future__ import annotations

import json
import logging
from typing import Any, Optional

from groq import AsyncGroq

from app.config import get_settings
from app.tools import ToolExecutor, chat_tool_definitions, parse_tool_arguments

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_agent_turn(
    *,
    system_prompt: str,
    history: list[dict[str, Any]],
    user_text: str,
    tools: ToolExecutor,
    max_tool_rounds: int = 4,
) -> str:
    """
    One conversational turn with Groq LLM + tool calling.
    Returns the final spoken reply text.
    """
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    client = AsyncGroq(api_key=settings.groq_api_key)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_text},
    ]

    for _ in range(max_tool_rounds):
        response = await client.chat.completions.create(
            model=settings.groq_llm_model,
            temperature=settings.groq_temperature,
            messages=messages,
            tools=chat_tool_definitions(),
            tool_choice="auto",
        )
        choice = response.choices[0].message
        tool_calls = choice.tool_calls or []

        if not tool_calls:
            reply = (choice.content or "").strip()
            return reply or "Sorry, I didn't catch that. Could you repeat?"

        # Assistant message with tool calls must be appended for Groq/OpenAI protocol
        messages.append(
            {
                "role": "assistant",
                "content": choice.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            name = tc.function.name
            args = parse_tool_arguments(tc.function.arguments)
            logger.info("Tool call %s args=%s", name, args)
            try:
                result = await tools.execute(name, args)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tool failed")
                result = {"error": str(exc)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                }
            )

    # Fallback if tools loop exhausted
    response = await client.chat.completions.create(
        model=settings.groq_llm_model,
        temperature=settings.groq_temperature,
        messages=messages,
    )
    return (response.choices[0].message.content or "").strip() or (
        "Let me check on that and get back to you."
    )
