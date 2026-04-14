"""
retriever.py — Semantic search over the ChromaDB 'akta_manuals' collection.
"""
import sys
from pathlib import Path

import chromadb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings

# Module-level cached client & collection
_client: chromadb.PersistentClient | None = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
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


def retrieve(
    query: str,
    instrument_filter: str | None = None,
    k: int = 6,
) -> list[dict]:
    """
    Search the ChromaDB 'akta_manuals' collection for chunks relevant to the query.

    Args:
        query: the user's question
        instrument_filter: optional instrument name (e.g. "pure") to filter metadata
        k: number of chunks to return

    Returns: list of dicts with keys:
        text, source_file, doc_title, section, page, instrument, distance
    """
    collection = _get_collection()

    where = None
    if instrument_filter:
        where = {"instrument": {"$eq": instrument_filter}}

    results = collection.query(
        query_texts=[query],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
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
