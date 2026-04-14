"""
generator.py — Claude API integration for Jojo Bot answer generation.
"""
import asyncio
import logging
import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings

logger = logging.getLogger(__name__)

# Cache system prompt so we only read it once
_system_prompt: str | None = None

MODEL = "claude-sonnet-4-20250514"


def load_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        # Prompt file is at repo-root/prompts/system_prompt.txt
        # When running from src/backend, that's ../../prompts/system_prompt.txt
        candidates = [
            Path("prompts/system_prompt.txt"),
            Path("../../prompts/system_prompt.txt"),
            Path(__file__).resolve().parents[3] / "prompts" / "system_prompt.txt",
        ]
        for p in candidates:
            if p.exists():
                _system_prompt = p.read_text(encoding="utf-8")
                return _system_prompt
        raise FileNotFoundError("Could not find prompts/system_prompt.txt")
    return _system_prompt


def build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks into a readable documentation block."""
    if not chunks:
        return ""
    lines = ["---", "RELEVANT DOCUMENTATION:", ""]
    for i, chunk in enumerate(chunks, start=1):
        title = chunk.get("doc_title", chunk.get("source_file", "Unknown"))
        section = chunk.get("section", "")
        page = chunk.get("page", "")

        header_parts = [title]
        if section:
            header_parts.append(f"Section: {section}")
        if page:
            header_parts.append(f"p. {page}")

        lines.append(f"[{i}] {', '.join(header_parts)}")
        lines.append(f'"{chunk["text"]}"')
        lines.append("")
    lines.append("---")
    return "\n".join(lines)


def build_messages(query: str, context: str, history: list[dict]) -> list[dict]:
    """Construct the Claude API messages array."""
    messages = []

    # Include last 6 turns (12 messages) of history
    for msg in history[-12:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Current user message
    messages.append({"role": "user", "content": query})
    return messages


def should_search_web(query: str, chunks: list[dict]) -> bool:
    """Decide if web search would help answer this query."""
    triggers = [
        any(
            word in query.lower()
            for word in ["latest", "recent", "new", "current", "2024", "2025", "update"]
        ),
        any(
            word in query.lower()
            for word in ["price", "cost", "buy", "vendor", "supplier", "alternative", "competitor"]
        ),
        any(
            phrase in query.lower()
            for phrase in ["application note", "published protocol", "literature", "paper"]
        ),
        all(c.get("distance", 0) > 1.2 for c in chunks) if chunks else True,
        len(chunks) == 0,
    ]
    return any(triggers)


async def generate(
    query: str,
    chunks: list[dict],
    history: list[dict],
    use_web_search: bool = False,
) -> dict:
    """
    Call Claude API with retrieved context and return a response.

    Returns:
        {
            "response": str,
            "citations": list[dict]
        }
    """
    system_prompt = load_system_prompt()
    context_block = build_context_block(chunks)
    full_system = system_prompt
    if context_block:
        full_system += "\n\n" + context_block

    if use_web_search:
        full_system += (
            "\n\nNOTE: Web search results are available for this query. "
            "When using web search information, clearly label it as 'From web search:' "
            "to distinguish it from the official manual documentation. "
            "Manual documentation is always the primary authority."
        )

    messages = build_messages(query, context_block, history)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())

    kwargs: dict = {
        "model": MODEL,
        "max_tokens": 4096,
        "temperature": 0.3,
        "system": full_system,
        "messages": messages,
    }

    if use_web_search:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

    for attempt in range(2):
        try:
            response = await client.messages.create(**kwargs)

            # Collect all text blocks (there may be tool_use blocks interspersed)
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Build citations from retrieved chunks
            citations = []
            for chunk in chunks:
                citations.append(
                    {
                        "document": chunk.get("doc_title", chunk.get("source_file", "")),
                        "section": chunk.get("section", ""),
                        "page": chunk.get("page"),
                        "excerpt": chunk["text"][:200] + ("..." if len(chunk["text"]) > 200 else ""),
                    }
                )

            return {"response": response_text, "citations": citations}

        except anthropic.RateLimitError:
            if attempt == 0:
                logger.warning("Rate limited by Claude API, retrying in 2 seconds...")
                await asyncio.sleep(2)
            else:
                return {
                    "response": "Jojo Bot is a bit busy right now — please try again in a moment.",
                    "citations": [],
                }
        except anthropic.AuthenticationError:
            logger.error("Claude API authentication failed")
            return {
                "response": "AI service configuration error — please check server settings.",
                "citations": [],
            }
        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {e}")
            return {
                "response": "Something went wrong generating a response. Please try again.",
                "citations": [],
            }

    return {"response": "Failed to get a response from the AI service.", "citations": []}


async def suggest_followups(
    query: str, response: str, instrument: str | None
) -> list[str]:
    """Generate 2–3 follow-up question suggestions."""
    fallback = [
        "What is the maintenance schedule for this system?",
        "How do I troubleshoot high backpressure?",
        "How do I create a gradient method in UNICORN?",
    ]
    try:
        client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
        instrument_hint = f" (instrument: {instrument})" if instrument else ""
        prompt = (
            f"Given this Q&A about ÄKTA chromatography{instrument_hint}, "
            "suggest 3 brief follow-up questions the user might ask next. "
            "Return only the questions, one per line, no numbering.\n\n"
            f"Q: {query}\n\nA: {response[:500]}"
        )
        resp = await client.messages.create(
            model=MODEL,
            max_tokens=200,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text if resp.content else ""
        suggestions = [line.strip() for line in text.strip().splitlines() if line.strip()]
        return suggestions[:3] if suggestions else fallback
    except Exception:
        return fallback
