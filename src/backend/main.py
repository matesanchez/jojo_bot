"""
main.py — FastAPI application for Jojo Bot.
"""
from __future__ import annotations

import asyncio
import json
import logging
import queue as thread_queue
import shutil
import tempfile
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_api_key, settings
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
from rag.generator import generate, reset_client, should_search_web, suggest_followups
from rag.retriever import get_shared_client, reset_collection_cache, retrieve

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiting (in-memory per session_id — for production use Redis)
# ---------------------------------------------------------------------------
_rate_limit: dict[str, list[float]] = defaultdict(list)

# Safety cap — an abusive client rotating IPs/session-ids could otherwise
# balloon this dict and leak memory over time. We keep at most this many
# distinct keys; once full, stale-window keys are purged and, if that is
# not enough, the oldest keys are evicted.
_RATE_LIMIT_MAX_KEYS = 10_000
# The longest sliding window across any rate-limiter — used to decide when a
# key is "stale" and safe to drop.
_RATE_LIMIT_MAX_WINDOW_SECONDS = 60


def _purge_stale_rate_limit_keys(now: float) -> None:
    """Drop keys whose most-recent request is outside the longest window.

    Also enforces the _RATE_LIMIT_MAX_KEYS cap by evicting the oldest
    remaining keys (by their last-seen timestamp) if the dict is still
    over capacity after the stale sweep.
    """
    cutoff = now - _RATE_LIMIT_MAX_WINDOW_SECONDS
    stale = [k for k, ts in _rate_limit.items() if not ts or ts[-1] <= cutoff]
    for k in stale:
        _rate_limit.pop(k, None)

    if len(_rate_limit) > _RATE_LIMIT_MAX_KEYS:
        # Sort by last-seen ascending, evict oldest down to 90 % of the cap
        target = int(_RATE_LIMIT_MAX_KEYS * 0.9)
        to_evict = sorted(_rate_limit.items(), key=lambda kv: kv[1][-1] if kv[1] else 0)
        for k, _ts in to_evict[: len(_rate_limit) - target]:
            _rate_limit.pop(k, None)


def _check_rate(key: str, max_requests: int, window_seconds: int) -> None:
    now = time.time()
    window_start = now - window_seconds
    _rate_limit[key] = [t for t in _rate_limit[key] if t > window_start]
    if len(_rate_limit[key]) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    _rate_limit[key].append(now)
    # Opportunistic cleanup — bounds memory growth without needing a timer.
    if len(_rate_limit) > _RATE_LIMIT_MAX_KEYS:
        _purge_stale_rate_limit_keys(now)


def check_rate_limit(session_id: str) -> None:
    """Chat endpoint: 30 requests / 60 s per session."""
    _check_rate(f"chat:{session_id}", max_requests=30, window_seconds=60)


def check_settings_rate_limit(request: Request) -> None:
    """Settings/upload endpoints: 10 requests / 60 s per IP."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate(f"settings:{client_ip}", max_requests=10, window_seconds=60)


def check_upload_rate_limit(request: Request) -> None:
    """Upload endpoint: 5 requests / 60 s per IP (ingest is expensive)."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate(f"upload:{client_ip}", max_requests=5, window_seconds=60)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Jojo Bot backend started. Database initialised.")

    # Ensure user_documents folder exists
    user_docs_path = Path(settings.user_documents_dir).resolve()
    user_docs_path.mkdir(parents=True, exist_ok=True)

    # Warm-up: initialise the shared ChromaDB client and verify the collection
    # is accessible.  Using get_shared_client() ensures a single PersistentClient
    # for the entire process — creating duplicates causes SQLite lock conflicts
    # on Windows that silently return 0 documents.
    try:
        client = get_shared_client()
        client.get_collection("akta_manuals")
        logger.info("ChromaDB collection 'akta_manuals' is ready.")
    except Exception:
        logger.warning(
            "ChromaDB collection 'akta_manuals' not found. "
            "Run: python -m rag.ingest --input ../../data/manuals/"
        )

    # Log API key status (never log the key itself)
    if get_api_key():
        logger.info("Anthropic API key is configured.")
    else:
        logger.warning(
            "No Anthropic API key found. "
            "Set it via the Settings panel (⚙) in the UI, or add ANTHROPIC_API_KEY to .env"
        )

    yield


app = FastAPI(title="Jojo Bot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
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


class ApiKeyRequest(BaseModel):
    api_key: str


# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(req.message) > 10_000:
        raise HTTPException(status_code=400, detail="Message too long (max 10,000 characters).")

    try:
        if req.session_id:
            session = await get_session(db, req.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail="Session not found.")
            session_id = req.session_id
        else:
            session_id = await create_session(db, instrument_context=req.instrument_filter)

        check_rate_limit(session_id)

        try:
            chunks = retrieve(
                query=req.message,
                instrument_filter=req.instrument_filter or None,
                k=6,
            )
        except RuntimeError:
            raise HTTPException(
                status_code=503,
                detail="Knowledge base not initialised. Run the ingestion script first.",
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        history = await get_history(db, session_id, max_turns=6)
        use_web = should_search_web(req.message, chunks)
        result = await generate(
            query=req.message,
            chunks=chunks,
            history=history,
            use_web_search=use_web,
        )

        instrument_detected = chunks[0]["instrument"] if chunks else None
        followups = await suggest_followups(req.message, result["response"], instrument_detected)

        await add_message(db, session_id, "user", req.message)
        await add_message(db, session_id, "assistant", result["response"], result["citations"])

        if not history:
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
    doc_count = 0
    try:
        client = get_shared_client()
        collection = client.get_collection("akta_manuals")
        doc_count = collection.count()
    except Exception as exc:
        # Log the real reason so it shows up in backend.log — a silent
        # "pass" here was the main reason "0 documents" was hard to debug.
        logger.debug("Health check could not read ChromaDB: %s", exc)
    return {
        "status": "ok",
        "version": "1.0.0",
        "documents_indexed": doc_count,
        "api_key_configured": get_api_key() is not None,
    }


@app.post("/api/generate-protocol", response_model=ProtocolResponse)
async def generate_protocol_endpoint(req: ProtocolRequest, db: AsyncSession = Depends(get_db)):
    try:
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating protocol: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not generate protocol.")


# ---------------------------------------------------------------------------
# Settings endpoints
# ---------------------------------------------------------------------------

@app.get("/api/settings/api-key")
async def get_api_key_status(request: Request):
    """Return whether an API key is configured and a masked preview."""
    check_settings_rate_limit(request)
    from appdata import get_masked_key
    key = get_api_key()
    return {
        "configured": key is not None,
        "masked_key": get_masked_key() if key else None,
    }


@app.post("/api/settings/api-key")
async def set_api_key(req: ApiKeyRequest, request: Request):
    """Save the API key to the user's local AppData config and reset the Anthropic client."""
    check_settings_rate_limit(request)
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    if not key.startswith("sk-ant-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid key format. Anthropic API keys start with 'sk-ant-'.",
        )
    try:
        from appdata import save_api_key
        save_api_key(key)
        # Reset the cached Anthropic client so it picks up the new key
        reset_client()
        logger.info("API key updated via Settings panel")
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Failed to save API key: {e}")
        raise HTTPException(status_code=500, detail="Could not save API key.")


@app.delete("/api/settings/api-key")
async def delete_api_key_endpoint(request: Request):
    """Remove the stored API key."""
    check_settings_rate_limit(request)
    from appdata import delete_api_key
    delete_api_key()
    reset_client()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Knowledge base endpoints
# ---------------------------------------------------------------------------

@app.get("/api/knowledge-base")
async def get_knowledge_base():
    """Return the list of all ingested documents."""
    try:
        from rag.kb_manifest import get_documents
        docs = get_documents()
        return {"documents": docs, "total": len(docs)}
    except Exception as e:
        logger.error(f"Error fetching knowledge base: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not load knowledge base.")


@app.post("/api/knowledge-base/upload")
async def upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    instrument: str = Form("general"),
):
    """
    Accept PDF uploads, save them to user_documents/, and ingest them into ChromaDB.
    Returns a Server-Sent Events stream so the UI can show live progress.
    """
    check_upload_rate_limit(request)

    # Validate instrument tag
    from config import VALID_INSTRUMENTS
    if instrument not in VALID_INSTRUMENTS and instrument != "auto":
        raise HTTPException(
            status_code=400,
            detail=f"Invalid instrument '{instrument}'. Must be one of: {sorted(VALID_INSTRUMENTS)}",
        )

    # Validate that all uploads are PDFs (basic check)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file
    MAX_FILES = 20

    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Too many files. Maximum {MAX_FILES} per upload.")

    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are accepted. Got: {f.filename}",
            )

    def _safe_filename(raw: str) -> str:
        """
        Strip all path components and dangerous characters from an uploaded filename.
        Only keeps alphanumerics, hyphens, underscores, dots, and spaces.
        Ensures the result ends with .pdf and is non-empty.
        """
        import re
        # Strip any path prefix (handles both / and \ separators)
        name = Path(raw).name
        # Remove any remaining path traversal characters
        name = re.sub(r"[^\w\s\-.]", "_", name)
        # Collapse multiple underscores/spaces
        name = re.sub(r"[_\s]{2,}", "_", name).strip("_. ")
        # Ensure it ends with .pdf (case-insensitive)
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        return name or "upload.pdf"

    # Save uploaded files to a temp directory first
    user_docs_path = Path(settings.user_documents_dir).resolve()
    user_docs_path.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    file_sizes: list[int] = []
    for upload in files:
        safe_name = _safe_filename(upload.filename or "upload.pdf")
        dest = (user_docs_path / safe_name).resolve()

        # Path containment check — destination must be inside user_documents_dir
        # Use relative_to() instead of startswith() to be correct on both Windows (\) and Unix (/)
        try:
            dest.relative_to(user_docs_path)
        except ValueError:
            logger.warning(f"Blocked path traversal attempt in upload filename: {upload.filename!r}")
            raise HTTPException(status_code=400, detail=f"Invalid filename: {upload.filename}")

        content = await upload.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File '{safe_name}' is too large (max 50 MB).",
            )
        dest.write_bytes(content)
        saved_paths.append(dest)
        file_sizes.append(len(content))
        logger.info(f"Saved uploaded file: {dest.name} ({len(content):,} bytes)")

    # Run ingest in a background thread, stream progress via SSE
    progress_q: thread_queue.Queue = thread_queue.Queue()

    def _progress_cb(current: int, total: int, filename: str, chunks: int) -> None:
        progress_q.put({
            "type": "progress",
            "current": current,
            "total": total,
            "filename": filename,
            "chunks_added": chunks,
        })

    def _run_ingest() -> None:
        from rag.ingest import ingest_files
        from rag.kb_manifest import add_documents
        from collections import defaultdict

        result = ingest_files(saved_paths, instrument_override=instrument, progress_callback=_progress_cb)

        # Update the KB manifest with newly added docs
        now = datetime.now(timezone.utc).isoformat()
        new_entries = []
        for path in saved_paths:
            # Quick re-scan to get page count (already read above, reuse from ChromaDB)
            new_entries.append({
                "source_file": path.name,
                "doc_title": path.stem.replace("_", " "),
                "instruments": [instrument] if instrument != "auto" else ["general"],
                "chunk_count": 0,  # Will be updated from result below
                "page_count": 0,
                "category": "user",
                "added_at": now,
            })
        # Patch chunk counts from result summary (approximate — best effort)
        if result["chunks_added"] > 0 and new_entries:
            per_file = result["chunks_added"] // len(new_entries)
            for e in new_entries:
                e["chunk_count"] = per_file
        add_documents(new_entries)

        # Clear the retriever's cached collection reference so it picks up
        # newly-created collections (matters on first-ever upload when the
        # collection didn't exist at server startup).
        reset_collection_cache()

        progress_q.put({
            "type": "done",
            "chunks_added": result["chunks_added"],
            "files_processed": result["files_processed"],
            "errors": result["errors"],
        })

    ingest_thread = threading.Thread(target=_run_ingest, daemon=True)

    async def _event_stream():
        yield f"data: {json.dumps({'type': 'start', 'total': len(saved_paths)})}\n\n"

        ingest_thread.start()
        loop = asyncio.get_event_loop()

        while True:
            try:
                # Poll the thread-safe queue (run in executor to avoid blocking event loop)
                item = await loop.run_in_executor(
                    None, lambda: progress_q.get(timeout=120)
                )
                yield f"data: {json.dumps(item)}\n\n"
                if item["type"] in ("done", "error"):
                    break
            except thread_queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Ingest timed out'})}\n\n"
                break
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
                break

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if proxied
        },
    )


@app.delete("/api/knowledge-base/{source_file:path}")
async def delete_document(source_file: str):
    """
    Remove a user-uploaded document from ChromaDB and the manifest.
    Base documents (from data/manuals/) cannot be deleted via the API.
    """
    from rag.kb_manifest import get_documents, remove_document as manifest_remove

    # Reject any path traversal attempts immediately — source_file must be a bare filename
    if "/" in source_file or "\\" in source_file or ".." in source_file:
        raise HTTPException(status_code=400, detail="Invalid document name.")
    # Strip to just the filename component as a final safety net
    source_file = Path(source_file).name
    if not source_file:
        raise HTTPException(status_code=400, detail="Invalid document name.")

    # Safety: only allow deletion of user-uploaded docs
    docs = get_documents()
    doc = next((d for d in docs if d["source_file"] == source_file), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.get("category") == "base":
        raise HTTPException(
            status_code=403,
            detail="Base documents cannot be deleted via the API.",
        )

    # Remove from ChromaDB (uses the shared client — never create a new one)
    try:
        client = get_shared_client()
        collection = client.get_collection("akta_manuals")
        existing = collection.get(where={"source_file": {"$eq": source_file}}, include=[])
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception as e:
        logger.error(f"Error deleting from ChromaDB: {e}")

    # Remove physical file — with path containment check
    user_docs_path = Path(settings.user_documents_dir).resolve()
    file_path = (user_docs_path / source_file).resolve()
    # Path containment check — use relative_to() to be correct on Windows (\) and Unix (/)
    try:
        file_path.relative_to(user_docs_path)
    except ValueError:
        logger.warning(f"Blocked path traversal attempt in delete: {source_file!r}")
        raise HTTPException(status_code=400, detail="Invalid document name.")
    if file_path.exists():
        file_path.unlink()

    # Remove from manifest
    manifest_remove(source_file)

    return {"status": "deleted", "source_file": source_file}


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os as _os
    import uvicorn
    # Jojo Bot is a local desktop tool — the backend must never be reachable
    # from the LAN by default, whether running packaged or in dev mode.
    # A developer who explicitly wants to hit the backend from another device
    # (e.g. a phone on the same Wi-Fi) can opt in with JOJO_DEV_LAN=1.
    _dev_lan = _os.environ.get("JOJO_DEV_LAN", "").strip().lower() in {"1", "true", "yes"}
    host = "0.0.0.0" if (_dev_lan and not settings.is_production) else "127.0.0.1"
    uvicorn.run(
        "main:app",
        host=host,
        port=8000,
        reload=not settings.is_production,
    )
