"""
ingest.py — PDF → ChromaDB ingestion pipeline for Jojo Bot.

Usage:
    python -m rag.ingest --input ../../data/manuals/
    python -m rag.ingest --input ../../data/manuals/ --reset
"""
import argparse
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import chromadb
import fitz  # PyMuPDF

# Allow running as a module from src/backend
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings

# ---------------------------------------------------------------------------
# Document title derivation
# ---------------------------------------------------------------------------
# Titles are derived from the PDF filename so they always match what the
# user actually uploaded. A prior version of this module carried a hand-
# maintained DOCUMENT_TITLES dict which had drifted out of sync with the
# source files and ended up mapping filenames to unrelated titles — that
# mapping has been removed. `get_doc_title()` below is now the single
# source of truth.

# Instrument keyword mapping
INSTRUMENT_KEYWORDS: dict[str, list[str]] = {
    "pure": ["äkta pure", "akta pure"],
    "go": ["äkta go", "akta go"],
    "avant": ["äkta avant", "akta avant"],
    "start": ["äkta start", "akta start"],
    "pilot_600": ["äkta pilot 600", "pilot 600"],
    "basic": ["äkta basic", "akta basic"],
    "prime": ["äktaprime", "aktaprime", "äkta prime"],
    "process": ["äktaprocess", "aktaprocess"],
    "fplc": ["aktafplc", "akta fplc", "fplc"],
    "explorer": ["äktaexplorer", "aktaexplorer"],
    "purifier": ["äktapurifier", "aktapurifier"],
    "unicorn": ["unicorn"],
}


def get_doc_title(filename: str) -> str:
    """Return a clean, human-readable document title derived from the filename.

    The filename is the authoritative source — we intentionally do NOT look
    up a hand-maintained table, because such tables drift out of sync as
    manuals are added/renamed.
    """
    stem = filename
    # Case-insensitive ".pdf" strip
    if stem.lower().endswith(".pdf"):
        stem = stem[: -len(".pdf")]
    # Underscores → spaces, collapse whitespace
    return " ".join(stem.replace("_", " ").split())


def detect_instrument(text: str) -> str:
    """Detect which ÄKTA instrument a chunk is about using keyword matching."""
    lower = text.lower()
    for instrument, keywords in INSTRUMENT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return instrument
    return "general"


def looks_like_heading(line: str) -> bool:
    """Heuristic: line is short, no period at end, possibly numbered."""
    line = line.strip()
    if not line:
        return False
    if len(line) > 120:
        return False
    if re.match(r"^\d+(\.\d+)*\s+\w", line):
        return True
    if line.isupper() and len(line) > 3:
        return True
    return False


def recursive_split(text: str, max_chars: int = 2000, overlap_chars: int = 200) -> list[str]:
    """
    Split text into chunks of at most max_chars with overlap_chars overlap.
    Tries to split on: double newline > single newline > period > hard cut.
    """
    if len(text) <= max_chars:
        return [text] if text.strip() else []

    separators = ["\n\n", "\n", ". ", " "]
    for sep in separators:
        idx = text.rfind(sep, 0, max_chars)
        if idx != -1:
            split_at = idx + len(sep)
            first = text[:split_at].strip()
            rest = text[max(0, split_at - overlap_chars):].strip()
            return [first] + recursive_split(rest, max_chars, overlap_chars)

    # Hard cut
    first = text[:max_chars].strip()
    rest = text[max(0, max_chars - overlap_chars):].strip()
    return [first] + recursive_split(rest, max_chars, overlap_chars)


def extract_chunks_from_pdf(pdf_path: Path) -> list[dict]:
    """Extract text chunks from a PDF, returning a list of chunk dicts."""
    doc = fitz.open(str(pdf_path))
    filename = pdf_path.name
    doc_title = get_doc_title(filename)
    chunks = []
    chunk_index = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if not text.strip():
            continue

        page_chunks = recursive_split(text, max_chars=2000, overlap_chars=200)
        for chunk_text in page_chunks:
            if not chunk_text.strip():
                continue

            # Detect section header
            first_line = chunk_text.split("\n")[0].strip()
            section_header = first_line if looks_like_heading(first_line) else ""

            # Detect instrument
            instrument = detect_instrument(chunk_text)

            chunks.append({
                "text": chunk_text,
                "source_file": filename,
                "doc_title": doc_title,
                "section_header": section_header,
                "page_number": page_num + 1,
                "chunk_index": chunk_index,
                "instrument": instrument,
            })
            chunk_index += 1

    doc.close()
    return chunks


def ingest(input_dir: str, reset: bool = False) -> None:
    """Main ingestion entry point."""
    input_path = Path(input_dir).resolve()
    if not input_path.exists():
        print(f"ERROR: Input directory not found: {input_path}")
        sys.exit(1)

    pdf_files = sorted(input_path.glob("*.pdf"))
    if not pdf_files:
        print(f"ERROR: No PDF files found in {input_path}")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF files in {input_path}")

    # Connect to ChromaDB
    chroma_path = Path(settings.chroma_db_path).resolve()
    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))

    if reset:
        try:
            client.delete_collection("akta_manuals")
            print("Existing collection deleted.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name="akta_manuals",
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0

    for i, pdf_path in enumerate(pdf_files, start=1):
        print(f"\nProcessing {i}/{len(pdf_files)}: {pdf_path.name}")
        try:
            chunks = extract_chunks_from_pdf(pdf_path)
            if not chunks:
                print(f"  → No text extracted (possibly scanned/image PDF) — skipping")
                continue

            # Batch-add to ChromaDB
            ids = [str(uuid.uuid4()) for _ in chunks]
            documents = [c["text"] for c in chunks]
            metadatas = [
                {
                    "source_file": c["source_file"],
                    "doc_title": c["doc_title"],
                    "section_header": c["section_header"],
                    "page_number": c["page_number"],
                    "chunk_index": c["chunk_index"],
                    "instrument": c["instrument"],
                }
                for c in chunks
            ]

            # Add in batches of 100 to avoid memory issues
            batch_size = 100
            for b in range(0, len(chunks), batch_size):
                collection.add(
                    ids=ids[b : b + batch_size],
                    documents=documents[b : b + batch_size],
                    metadatas=metadatas[b : b + batch_size],
                )

            pages = max(c["page_number"] for c in chunks)
            # Summarise all detected instruments for this document
            instruments = sorted({c["instrument"] for c in chunks})
            print(f"  → {pages} pages, {len(chunks)} chunks created")
            print(f"  → Instruments detected: {', '.join(instruments)}")
            total_chunks += len(chunks)

        except Exception as e:
            import traceback
            print(f"  → ERROR processing {pdf_path.name}: {type(e).__name__}: {e} — skipping")
            traceback.print_exc()

    # --- Write the knowledge base manifest so the UI can list documents ---
    from rag.kb_manifest import add_documents

    now = datetime.now(timezone.utc).isoformat()
    manifest_docs = []
    # Re-scan what we just ingested to build accurate manifest entries
    for pdf_path in pdf_files:
        filename = pdf_path.name
        try:
            chunks = extract_chunks_from_pdf(pdf_path)
            if not chunks:
                continue
            instruments = sorted({c["instrument"] for c in chunks})
            page_count = max(c["page_number"] for c in chunks)
            manifest_docs.append({
                "source_file": filename,
                "doc_title": get_doc_title(filename),
                "instruments": instruments,
                "chunk_count": len(chunks),
                "page_count": page_count,
                "category": "base",
                "added_at": now,
            })
        except Exception:
            pass  # already logged above

    if manifest_docs:
        add_documents(manifest_docs)
        print(f"Updated kb_manifest.json with {len(manifest_docs)} documents.")

    print(f"\nIngestion complete. {len(pdf_files)} documents, ~{total_chunks} chunks indexed.")


def ingest_files(
    file_paths: list[Path],
    instrument_override: str = "auto",
    progress_callback=None,
) -> dict:
    """
    Incrementally ingest a list of PDF files into an existing ChromaDB collection.

    Uses deterministic chunk IDs (filename::chunk_index) so re-uploading the same
    file is safe — existing chunks are replaced (upsert) rather than duplicated.

    Args:
        file_paths:          List of absolute Path objects pointing to PDFs.
        instrument_override: If not "auto", force all chunks to this instrument tag.
        progress_callback:   Optional callable(current, total, filename, chunks_added).

    Returns:
        {"files_processed": int, "chunks_added": int, "errors": list[str]}
    """
    chroma_path = Path(settings.chroma_db_path).resolve()
    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(
        name="akta_manuals",
        metadata={"hnsw:space": "cosine"},
    )

    total = len(file_paths)
    total_chunks = 0
    errors: list[str] = []

    for i, pdf_path in enumerate(file_paths, start=1):
        filename = pdf_path.name
        try:
            chunks = extract_chunks_from_pdf(pdf_path)

            # Apply instrument override (user picked from dropdown in UI)
            if instrument_override and instrument_override != "auto":
                for c in chunks:
                    c["instrument"] = instrument_override

            if not chunks:
                msg = f"{filename}: No text extracted (possibly a scanned/image-only PDF)"
                errors.append(msg)
                if progress_callback:
                    progress_callback(i, total, filename, 0)
                continue

            # Deterministic IDs → re-ingesting same file replaces old chunks cleanly
            ids = [f"{filename}::{c['chunk_index']}" for c in chunks]
            documents = [c["text"] for c in chunks]
            metadatas = [
                {
                    "source_file": c["source_file"],
                    "doc_title": c["doc_title"],
                    "section_header": c["section_header"],
                    "page_number": c["page_number"],
                    "chunk_index": c["chunk_index"],
                    "instrument": c["instrument"],
                }
                for c in chunks
            ]

            # Upsert in batches of 100
            batch_size = 100
            for b in range(0, len(chunks), batch_size):
                collection.upsert(
                    ids=ids[b: b + batch_size],
                    documents=documents[b: b + batch_size],
                    metadatas=metadatas[b: b + batch_size],
                )

            total_chunks += len(chunks)
            if progress_callback:
                progress_callback(i, total, filename, len(chunks))

        except Exception as exc:
            import traceback
            msg = f"{filename}: {type(exc).__name__}: {exc}"
            errors.append(msg)
            traceback.print_exc()
            if progress_callback:
                progress_callback(i, total, filename, 0)

    return {
        "files_processed": total,
        "chunks_added": total_chunks,
        "errors": errors,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest ÄKTA manuals into ChromaDB")
    parser.add_argument("--input", required=True, help="Directory containing PDF manuals")
    parser.add_argument("--reset", action="store_true", help="Clear the existing vector DB before ingesting")
    args = parser.parse_args()
    ingest(args.input, reset=args.reset)
