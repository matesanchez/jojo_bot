"""
session_store.py — CRUD operations for sessions and messages.
"""
import uuid
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Message, Session


async def create_session(db: AsyncSession, instrument_context: str | None = None) -> str:
    """Create a new session and return its ID."""
    session = Session(
        id=str(uuid.uuid4()),
        instrument_context=instrument_context,
        created_at=datetime.utcnow(),
        last_active=datetime.utcnow(),
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
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_active": session.last_active.isoformat() if session.last_active else None,
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
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "last_active": s.last_active.isoformat() if s.last_active else None,
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
        created_at=datetime.utcnow(),
    )
    db.add(msg)

    # Update session last_active
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        session.last_active = datetime.utcnow()

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
            "created_at": m.created_at.isoformat() if m.created_at else None,
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
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


async def update_session_title(db: AsyncSession, session_id: str, first_message: str) -> None:
    """Auto-generate session title from the first user message."""
    title = first_message[:50].strip()
    if len(first_message) > 50:
        title += "..."
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session and not session.title:
        session.title = title
        await db.commit()
