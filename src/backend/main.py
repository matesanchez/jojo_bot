"""
main.py — FastAPI application for Jojo Bot.
"""
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager

import chromadb
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.database import get_db, init_db
from db.session_store import (
    add_message,
    create_session,
    delete_session,
    get_full_history,
    get_history,
    get_session,
    list_sessions,
    update_session_title,
)
from rag.generator import generate, should_search_web, suggest_followups
from rag.retriever import retrieve

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per session_id)
# ---------------------------------------------------------------------------
_rate_limit: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_MAX = 30  # requests
RATE_LIMIT_WINDOW = 60  # seconds


def check_rate_limit(session_id: str) -> None:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    _rate_limit[session_id] = [t for t in _rate_limit[session_id] if t > window_start]
    if len(_rate_limit[session_id]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    _rate_limit[session_id].append(now)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Jojo Bot backend started. Database initialized.")
    yield


app = FastAPI(title="Jojo Bot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    instrument_filter: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    citations: list[dict]
    follow_up_suggestions: list[str]
    instrument_detected: str | None = None


class ProtocolRequest(BaseModel):
    target_protein: str
    purification_type: str
    instrument: str = "pure"
    column: str | None = None
    sample_volume: str | None = None
    additional_notes: str | None = None
    session_id: str | None = None


class ProtocolResponse(BaseModel):
    protocol_markdown: str
    protocol_title: str
    warnings: list[str]
    session_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Input validation
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(req.message) > 10_000:
        raise HTTPException(status_code=400, detail="Message too long (max 10,000 characters).")

    try:
        # Create or validate session
        if req.session_id:
            session = await get_session(db, req.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail="Session not found.")
            session_id = req.session_id
        else:
            session_id = await create_session(db, instrument_context=req.instrument_filter)

        check_rate_limit(session_id)

        # Retrieve relevant chunks
        try:
            chunks = retrieve(query=req.message, instrument_filter=req.instrument_filter, k=6)
        except RuntimeError as e:
            raise HTTPException(
                status_code=503,
                detail="Knowledge base not initialized. Run the ingestion script first.",
            )

        # Get conversation history
        history = await get_history(db, session_id, max_turns=6)

        # Generate response
        use_web = should_search_web(req.message, chunks)
        result = await generate(
            query=req.message,
            chunks=chunks,
            history=history,
            use_web_search=use_web,
        )

        # Follow-up suggestions
        instrument_detected = chunks[0]["instrument"] if chunks else None
        followups = await suggest_followups(req.message, result["response"], instrument_detected)

        # Persist messages
        await add_message(db, session_id, "user", req.message)
        await add_message(db, session_id, "assistant", result["response"], result["citations"])

        # Auto-title from first message
        history_count = len(history)
        if history_count == 0:
            await update_session_title(db, session_id, req.message)

        return ChatResponse(
            session_id=session_id,
            response=result["response"],
            citations=result["citations"],
            follow_up_suggestions=followups,
            instrument_detected=instrument_detected,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /api/chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


@app.get("/api/sessions")
async def get_sessions(db: AsyncSession = Depends(get_db)):
    try:
        return await list_sessions(db, limit=20)
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve sessions.")


@app.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    messages = await get_full_history(db, session_id)
    return {"session_id": session_id, "session": session, "messages": messages}


@app.delete("/api/sessions/{session_id}")
async def remove_session(session_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"status": "deleted", "session_id": session_id}


@app.get("/api/health")
async def health():
    try:
        from pathlib import Path
        chroma_path = Path(settings.chroma_db_path).resolve()
        client = chromadb.PersistentClient(path=str(chroma_path))
        try:
            collection = client.get_collection("akta_manuals")
            doc_count = collection.count()
        except Exception:
            doc_count = 0
    except Exception:
        doc_count = 0

    return {"status": "ok", "version": "1.0.0", "documents_indexed": doc_count}


@app.post("/api/generate-protocol", response_model=ProtocolResponse)
async def generate_protocol_endpoint(req: ProtocolRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Create or validate session
        if req.session_id:
            session = await get_session(db, req.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail="Session not found.")
            session_id = req.session_id
        else:
            session_id = await create_session(db, instrument_context=req.instrument)

        history = await get_history(db, session_id, max_turns=6)

        from rag.protocol_generator import generate_protocol
        result = await generate_protocol(
            target_protein=req.target_protein,
            purification_type=req.purification_type,
            instrument=req.instrument,
            column=req.column,
            sample_volume=req.sample_volume,
            additional_notes=req.additional_notes,
            history=history,
        )

        return ProtocolResponse(
            protocol_markdown=result["protocol_markdown"],
            protocol_title=result["protocol_title"],
            warnings=result["warnings"],
            session_id=session_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating protocol: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not generate protocol.")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
