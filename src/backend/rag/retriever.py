"""
retriever.py — Semantic search over the ChromaDB 'akta_manuals' collection.
"""
import asyncio
import sys
from pathlib import Path

import chromadb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings, VALID_INSTRUMENTS

# ---------------------------------------------------------------------------
# Thread-safe singleton for the ChromaDB collection
# ---------------------------------------------------------------------------
_client: chromadb.PersistentClient | None = None
_collection = None
_lock = asyncio.Lock()


async def _get_collection_async():
    """Async-safe collection accessor — initialises once, reuses thereafter."""
    global _client, _collection
    if _collection is not None:
        return _collection
    async with _lock:
        # Double-check after acquiring lock
        if _collection is not None:
            return _collection
        chroma_path = Path(settings.chroma_db_path).resolve()
        _client = chromadb.PersistentClient(path=str(chroma_path))
        try:
            _collection = _client.get_collection("akta_manuals")
        except Exception:
            raise RuntimeError(
                "ChromaDB collection 'akta_manuals' not found. "
                "Run the ingestion script first:\n"
                "  python -m rag.ingest --input ../../data/manuals/"
            )
    return _collection


def _get_collection_sync():
    """Sync accessor for non-async callers (e.g. health endpoint)."""
    global _client, _collection
    if _collection is None:
        chroma_path = Path(settings.chroma_db_path).resolve()
        _client = chromadb.PersistentClient(path=str(chroma_path))
        try:
            _collection = _client.get_collection("akta_manuals")
        except Exception:
            raise RuntimeError(
                "ChromaDB collection 'akta_manuals' not found. "
                "Run: python -m rag.ingest --input ../../data/manuals/"
            )
    return _collection


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

    collection = _get_collection_sync()

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
        chunks.append(
            {
                "text": text,
                "source_file": meta.get("source_file", ""),
                "doc_title": meta.get("doc_title", ""),
                "section": meta.get("section_header", ""),
                "page": meta.get("page_number", 0),
                "instrument": meta.get("instrument", "general"),
                "distance": dist,
            }
        )

    return chunks
