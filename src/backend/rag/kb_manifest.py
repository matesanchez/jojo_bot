"""
kb_manifest.py — Lightweight index of all documents ingested into ChromaDB.

Stored at data/kb_manifest.json alongside the chroma_db folder.
Updated atomically on every ingest so reads are always fast — no need to
scan the entire ChromaDB collection to render the Knowledge Base UI.

On first access, if the manifest is missing, it is auto-generated from
the existing ChromaDB metadata (backward-compatible with the initial ingest
that ran before this feature existed).
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_MANIFEST_VERSION = 1


def _manifest_path() -> Path:
    """Resolve the manifest path — sits next to the chroma_db folder."""
    from config import settings
    chroma = Path(settings.chroma_db_path).resolve()
    return chroma.parent / "kb_manifest.json"


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def load_manifest() -> dict:
    """Load the manifest from disk, or return an empty structure."""
    path = _manifest_path()
    if not path.exists():
        return {"version": _MANIFEST_VERSION, "documents": []}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as exc:
        logger.warning("Could not read kb_manifest.json: %s — treating as empty", exc)
        return {"version": _MANIFEST_VERSION, "documents": []}


def _save_manifest(data: dict) -> None:
    path = _manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(path)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise exc


# ---------------------------------------------------------------------------
# Bootstrap from existing ChromaDB (runs once after upgrade)
# ---------------------------------------------------------------------------

def bootstrap_from_chromadb() -> None:
    """
    Scan ChromaDB metadata and generate kb_manifest.json for existing documents.
    Only called when the manifest file is absent (i.e., first run after upgrade).
    """
    import chromadb
    from config import settings

    logger.info("kb_manifest.json not found — bootstrapping from ChromaDB metadata...")
    chroma_path = Path(settings.chroma_db_path).resolve()
    if not chroma_path.exists():
        logger.info("ChromaDB not initialised yet — skipping bootstrap")
        return

    try:
        client = chromadb.PersistentClient(path=str(chroma_path))
        collection = client.get_collection("akta_manuals")
    except Exception:
        logger.info("Collection 'akta_manuals' not found — skipping bootstrap")
        return

    # Fetch all metadata (no embeddings or documents — just the small dicts)
    result = collection.get(include=["metadatas"])
    metadatas = result.get("metadatas") or []

    # Group chunks by source_file
    by_file: dict[str, list[dict]] = defaultdict(list)
    for meta in metadatas:
        sf = meta.get("source_file", "unknown.pdf")
        by_file[sf].append(meta)

    now = datetime.now(timezone.utc).isoformat()
    documents = []
    for source_file, chunks in sorted(by_file.items()):
        instruments = sorted({c.get("instrument", "general") for c in chunks})
        page_nums = [c.get("page_number", 0) for c in chunks]
        doc_title = chunks[0].get("doc_title", source_file.replace("_", " ").replace(".pdf", ""))
        documents.append({
            "source_file": source_file,
            "doc_title": doc_title,
            "instruments": instruments,
            "chunk_count": len(chunks),
            "page_count": max(page_nums) if page_nums else 0,
            "category": "user" if "_user_upload" in source_file else "base",
            "added_at": now,
        })

    manifest = {"version": _MANIFEST_VERSION, "documents": documents}
    _save_manifest(manifest)
    logger.info("Bootstrapped kb_manifest.json with %d documents", len(documents))


# ---------------------------------------------------------------------------
# Public write API — called by ingest endpoints
# ---------------------------------------------------------------------------

def add_documents(new_docs: list[dict]) -> None:
    """
    Append or update document entries in the manifest.
    Each dict should contain: source_file, doc_title, instruments, chunk_count,
    page_count, category, added_at.
    """
    manifest = load_manifest()
    existing = {d["source_file"]: i for i, d in enumerate(manifest["documents"])}

    for doc in new_docs:
        sf = doc["source_file"]
        if sf in existing:
            # Update in place (re-upload replaces old entry)
            manifest["documents"][existing[sf]] = doc
        else:
            manifest["documents"].append(doc)

    _save_manifest(manifest)


def remove_document(source_file: str) -> bool:
    """Remove a document entry. Returns True if found and removed."""
    manifest = load_manifest()
    before = len(manifest["documents"])
    manifest["documents"] = [d for d in manifest["documents"] if d["source_file"] != source_file]
    if len(manifest["documents"]) < before:
        _save_manifest(manifest)
        return True
    return False


# ---------------------------------------------------------------------------
# Public read API
# ---------------------------------------------------------------------------

def get_documents() -> list[dict]:
    """
    Return all documents in the manifest.
    Auto-bootstraps from ChromaDB on first call if the manifest is missing.
    """
    path = _manifest_path()
    if not path.exists():
        bootstrap_from_chromadb()
    return load_manifest().get("documents", [])
