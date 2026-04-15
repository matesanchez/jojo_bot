"""
session_store.py — CRUD operations for sessions and messages.
"""
import uuid
from datetime import datetime, timezone


def _iso(dt) -> str | None:
    """Safely convert a datetime (or None) to ISO-8601 string."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)  # fallback for unexpected types

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Message, Session


async def create_session(db: AsyncSession, instrument_context: str | None = None) -> str:
    """Create a new session and return its ID."""
    session = Session(
        id=str(uuid.uuid4()),
        instrument_context=instrument_context,
        created_at=datetime.now(timezone.utc),
        last_active=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()
    return session.id


async def get_session(db: AsyncSession, session_id: str) -> dict | None:
    """Return session metadata dict or None if not found."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        return None
    return {
        "id": session.id,
        "title": session.title,
        "instrument_context": session.instrument_context,
        "created_at": _iso(session.created_at),
        "last_active": _iso(session.last_active),
    }


async def list_sessions(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Return a list of recent session summaries."""
    result = await db.execute(
        select(Session).order_by(Session.last_active.desc()).limit(limit)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "title": s.title or "Untitled Chat",
            "instrument_context": s.instrument_context,
            "created_at": _iso(s.created_at),
            "last_active": _iso(s.last_active),
        }
        for s in sessions
    ]


async def delete_session(db: AsyncSession, session_id: str) -> bool:
    """Delete a session and all its messages. Returns True if found."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        return False
    await db.execute(delete(Message).where(Message.session_id == session_id))
    await db.execute(delete(Session).where(Session.id == session_id))
    await db.commit()
    return True


async def add_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    citations: list | None = None,
) -> str:
    """Add a message to a session and update last_active. Returns message ID."""
    msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
        citations=citations,
        created_at=datetime.now(timezone.utc),
    )
    db.add(msg)

    # Update session last_active
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        session.last_active = datetime.now(timezone.utc)

    await db.commit()
    return msg.id


async def get_history(db: AsyncSession, session_id: str, max_turns: int = 6) -> list[dict]:
    """Return the last max_turns*2 messages for a session (for conversation context)."""
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(max_turns * 2)
    )
    messages = list(reversed(result.scalars().all()))
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "citations": m.citations,
            "created_at": _iso(m.created_at),
        }
        for m in messages
    ]


async def get_full_history(db: AsyncSession, session_id: str) -> list[dict]:
    """Return all messages for a session."""
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "citations": m.citations,
            "created_at": _iso(m.created_at),
        }
        for m in messages
    ]


async def update_session_title(db: AsyncSession, session_id: str, first_message: str) -> None:
    """Auto-generate session title from the first user message."""
    stripped = first_message.strip()
    if stripped:
        title = stripped[:50] + ("..." if len(stripped) > 50 else "")
    else:
        # Fallback to timestamp if message is blank
        title = f"Chat {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session and not session.title:
        session.title = title
        await db.commit()
