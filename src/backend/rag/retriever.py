"""
retriever.py — Semantic search over the ChromaDB 'akta_manuals' collection.

Also owns the process-wide ChromaDB client singleton.  Every module that
needs to talk to ChromaDB (main.py health endpoint, ingest, manifest
bootstrap, document deletion) MUST use ``get_shared_client()`` instead of
creating its own ``chromadb.PersistentClient``.

Why: ChromaDB's PersistentClient opens SQLite and HNSW-index files.
On Windows, multiple PersistentClient instances pointed at the same path
compete for file locks, causing silent failures (queries return 0 results)
or outright crashes.  A single shared instance avoids all of this.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import chromadb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings, VALID_INSTRUMENTS

# ---------------------------------------------------------------------------
# Process-wide ChromaDB singleton (thread-safe)
# ---------------------------------------------------------------------------
_client: chromadb.PersistentClient | None = None
_collection = None
_init_lock = threading.Lock()


def get_shared_client() -> chromadb.PersistentClient:
    """Return the shared PersistentClient, creating it on first call.

    Thread-safe — safe to call from the async event loop, from background
    ingest threads, and from the CLI ingest entrypoint.

    NOTE: The double-check locking pattern below is correct. The first
    ``if _client is not None`` (fast path) avoids acquiring the lock on
    every call. If two threads both pass the fast check, one acquires
    ``_init_lock`` and creates the client; the other blocks on the lock,
    then sees the second ``if _client is not None`` is now True and
    returns the already-created instance. This is standard DCLP and has
    been verified safe for CPython's GIL-protected reference assignments.
    """
    global _client
    if _client is not None:              # fast path — no lock needed
        return _client
    with _init_lock:
        if _client is not None:          # re-check after acquiring lock
            return _client
        chroma_path = Path(settings.chroma_db_path).resolve()
        chroma_path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(chroma_path))
        return _client


def _get_collection():
    """Return the cached collection, or look it up from the shared client.

    Raises RuntimeError if the collection has never been created (i.e. the
    ingest pipeline has not been run yet).  This is intentional — callers
    like ``retrieve()`` should surface a clear error rather than silently
    returning zero results.

    The lookup is retried on every call when the collection is not yet
    cached, so it will succeed as soon as a first ingest completes.
    """
    global _collection
    if _collection is not None:
        return _collection
    with _init_lock:
        if _collection is not None:
            return _collection
        client = get_shared_client()
        try:
            _collection = client.get_collection("akta_manuals")
        except Exception:
            raise RuntimeError(
                "ChromaDB collection 'akta_manuals' not found. "
                "Run the ingestion script first:\n"
                "  python -m rag.ingest --input ../../data/manuals/"
            )
        return _collection


def reset_collection_cache() -> None:
    """Clear the cached collection reference.

    Call after operations that may create the collection for the first time
    (e.g. the first-ever document upload) so that subsequent ``retrieve()``
    calls pick it up instead of raising RuntimeError.
    """
    global _collection
    _collection = None


def _title_from_filename(filename: str) -> str:
    """Derive a human-readable title from a PDF filename.

    Kept identical to ingest.get_doc_title() so the retriever can heal
    stored titles without importing the ingest module (which would pull
    PyMuPDF into the request path).
    """
    if not filename:
        return ""
    stem = filename
    if stem.lower().endswith(".pdf"):
        stem = stem[: -len(".pdf")]
    return " ".join(stem.replace("_", " ").split())


def retrieve(
    query: str,
    instrument_filter: str | None = None,
    k: int = 6,
) -> list[dict]:
    """
    Search the ChromaDB 'akta_manuals' collection for chunks relevant to the query.

    Args:
        query: the user's question (must be non-empty)
        instrument_filter: optional instrument name to filter metadata
        k: number of chunks to return

    Returns: list of dicts with keys:
        text, source_file, doc_title, section, page, instrument, distance
    """
    # Validate query
    query = query.strip()
    if not query:
        raise ValueError("Query must be a non-empty string.")

    # Validate instrument_filter against whitelist
    if instrument_filter is not None:
        instrument_filter = instrument_filter.strip()
        if instrument_filter not in VALID_INSTRUMENTS:
            raise ValueError(
                f"Invalid instrument_filter '{instrument_filter}'. "
                f"Must be one of: {sorted(VALID_INSTRUMENTS)}"
            )

    collection = _get_collection()

    where = None
    if instrument_filter and instrument_filter != "general":
        where = {"instrument": {"$eq": instrument_filter}}

    results = collection.query(
        query_texts=[query],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[dict] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for text, meta, dist in zip(documents, metadatas, distances):
        source_file = meta.get("source_file", "") or ""
        # Always derive the display title from the filename. This makes
        # citations resilient to stale or incorrect titles that may be
        # baked into an older chroma_db — the filename is authoritative.
        doc_title = _title_from_filename(source_file) or meta.get("doc_title", "")

        chunks.append(
            {
                "text": text,
                "source_file": source_file,
                "doc_title": doc_title,
                "section": meta.get("section_header", ""),
                "page": meta.get("page_number", 0),
                "instrument": meta.get("instrument", "general"),
                "distance": dist,
            }
        )

    return chunks
