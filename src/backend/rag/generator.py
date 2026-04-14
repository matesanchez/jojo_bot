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

# ---------------------------------------------------------------------------
# Module-level singletons — created once, reused across all requests
# ---------------------------------------------------------------------------
_client: anthropic.AsyncAnthropic | None = None
_system_prompt: str | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
    return _client


def load_system_prompt() -> str:
    """Read system prompt from disk (cached after first read)."""
    global _system_prompt
    if _system_prompt is None:
        candidates = [
            Path("prompts/system_prompt.txt"),
            Path("../../prompts/system_prompt.txt"),
            Path(__file__).resolve().parents[3] / "prompts" / "system_prompt.txt",
        ]
        checked = []
        for p in candidates:
            checked.append(str(p))
            if p.exists():
                _system_prompt = p.read_text(encoding="utf-8")
                return _system_prompt
        raise FileNotFoundError(
            f"Could not find prompts/system_prompt.txt. Checked: {', '.join(checked)}"
        )
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


def build_messages(query: str, history: list[dict]) -> list[dict]:
    """Construct the Claude API messages array."""
    messages = []
    for msg in history[-12:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
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


def _collect_text(content_blocks) -> str:
    """Safely collect all text from Claude response content blocks."""
    return "".join(
        block.text for block in content_blocks if hasattr(block, "text")
    )


async def generate(
    query: str,
    chunks: list[dict],
    history: list[dict],
    use_web_search: bool = False,
) -> dict:
    """
    Call Claude API with retrieved context and return a response.

    Returns:
        {"response": str, "citations": list[dict]}
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

    messages = build_messages(query, history)
    client = _get_client()

    kwargs: dict = {
        "model": settings.claude_model,
        "max_tokens": 4096,
        "temperature": 0.3,
        "system": full_system,
        "messages": messages,
    }
    if use_web_search:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

    last_exception: Exception | None = None
    for attempt in range(2):
        try:
            response = await client.messages.create(**kwargs)
            response_text = _collect_text(response.content)

            citations = [
                {
                    "document": chunk.get("doc_title", chunk.get("source_file", "")),
                    "section": chunk.get("section", ""),
                    "page": chunk.get("page"),
                    "excerpt": chunk["text"][:200] + ("..." if len(chunk["text"]) > 200 else ""),
                }
                for chunk in chunks
            ]
            return {"response": response_text, "citations": citations}

        except anthropic.RateLimitError as e:
            last_exception = e
            if attempt == 0:
                logger.warning("Rate limited by Claude API, retrying in 2 seconds...")
                await asyncio.sleep(2)
            # fall through to second attempt; if this was attempt 1, loop exits

        except anthropic.AuthenticationError:
            logger.error("Claude API authentication failed — check ANTHROPIC_API_KEY")
            return {
                "response": "AI service configuration error — please check server settings.",
                "citations": [],
            }

        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {e}", exc_info=True)
            return {
                "response": "Something went wrong generating a response. Please try again.",
                "citations": [],
            }

    # Exhausted retries (rate limit persisted across both attempts)
    logger.warning(f"Claude API still rate-limited after retry: {last_exception}")
    return {
        "response": "Jojo Bot is a bit busy right now — please try again in a moment.",
        "citations": [],
    }


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
        client = _get_client()
        instrument_hint = f" (instrument: {instrument})" if instrument else ""
        prompt = (
            f"Given this Q&A about ÄKTA chromatography{instrument_hint}, "
            "suggest 3 brief follow-up questions the user might ask next. "
            "Return only the questions, one per line, no numbering.\n\n"
            f"Q: {query}\n\nA: {response[:500]}"
        )
        resp = await client.messages.create(
            model=settings.claude_model,
            max_tokens=200,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        # Guard against empty response
        if not resp.content:
            return fallback
        text = resp.content[0].text if hasattr(resp.content[0], "text") else ""
        suggestions = [line.strip() for line in text.strip().splitlines() if line.strip()]
        return suggestions[:3] if suggestions else fallback
    except Exception:
        return fallback
