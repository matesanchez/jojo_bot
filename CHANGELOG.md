# Changelog

All notable changes to Jojo Bot are documented here.

---

## v1.0.0 — April 2026

### Overview

v1.0 transforms Jojo Bot from a developer-run local server into a polished, self-contained Windows desktop application that any Nurix colleague can unzip and run — without installing Python, Node.js, or any other software.

### New Features

#### Standalone Windows Distribution
- `build-package.bat` compiles and assembles a fully self-contained distribution package
- Output: `dist\JojoBot-v1.0\` folder and `dist\JojoBot-v1.0.zip` — share the ZIP with colleagues
- Includes: compiled `backend.exe` (PyInstaller), compiled `Jojo Bot.exe` (launcher), portable Node.js 20, pre-vectorized knowledge base

#### Native App Window (`Jojo Bot.exe`)
- `Jojo Bot.exe` opens Jojo Bot in its own dedicated window using Edge WebView2 (built into Windows 10/11)
- No browser tab opens; no terminal windows appear — everything runs silently in the background
- The Jojo Bot avatar icon appears in Windows Explorer, the taskbar, and the window title bar
- Closing the window automatically shuts down both background server processes

#### In-App Settings Panel
- Gear icon (⚙) in the top-right corner opens a two-tab settings modal
- **API Key tab**: enter, mask/reveal, save, or delete your Anthropic API key; shows a "configured ✓" chip when a key is saved; displays a red notification dot on the gear icon when no key is set
- **Knowledge Base tab**: browse all indexed documents (base manuals + user uploads), upload new PDFs with instrument tagging, drag-and-drop support, live progress bar, and per-file chunk counts; delete user-uploaded documents

#### AppData API Key Storage
- API keys are stored in `%APPDATA%\JojoBot\config.json` on each user's machine
- Keys are never included in the package files, never committed to Git, and never sent to the frontend
- The backend starts successfully without a key (graceful degradation) and re-initialises the Anthropic client automatically when a key is saved — no server restart needed

#### Live Document Upload (SSE Streaming)
- Upload your own PDFs from the Settings panel → Knowledge Base tab
- Ingestion progress is streamed in real-time via Server-Sent Events (SSE): per-file progress, chunk counts, success/error results
- Uses deterministic chunk IDs (`filename::chunk_index`) with `upsert()` — re-uploading the same file is safe and idempotent
- New documents are immediately queryable without restarting the server

#### Knowledge Base Manifest
- `data/kb_manifest.json` tracks all indexed documents with metadata: title, instrument tags, chunk count, page count, category, and upload timestamp
- Provides O(1) document listing without scanning the entire ChromaDB collection
- Auto-bootstraps from existing ChromaDB on first run (backward compatible with v1.0 knowledge base)

### Security Improvements

- **Path traversal fix (Windows)** — replaced `startswith()` path containment checks with `Path.relative_to()`, which is correct on both Windows (`\`) and Unix (`/`). Previous check could be bypassed on Windows.
- **API key removed from `.env`** — `src/backend/.env` no longer contains a plaintext API key; confirmed not in git history
- **Belt-and-suspenders `.gitignore`** — root and backend-level gitignore files explicitly exclude `.env`, `*.db`, `venv/`, `data/manuals/`, `data/chroma_db/`, all build artefacts
- **Production host binding** — backend binds to `127.0.0.1` in production (not `0.0.0.0`), preventing any external network access
- **Separate rate limits** — chat (30/min/session), settings (10/min/IP), uploads (5/min/IP)
- **File type enforcement** — uploads restricted to PDF only, max 50 MB per file

### Bug Fixes

- **`TypeError` in `retriever.py`** — `chromadb.PersistentClient` is a factory function (not a class) in chromadb 0.5.23; `PersistentClient | None` union syntax failed at module load. Fixed with `from __future__ import annotations` to defer annotation evaluation.
- **`datetime.utcnow()` deprecated** — replaced all `datetime.utcnow()` calls in `session_store.py` with `datetime.now(timezone.utc)` for timezone-aware datetimes
- **Null guard in `build_messages()`** — added validation that each history entry has a valid `role` (`user`/`assistant`) and non-None `content` before including it in the Claude API request

### Other Changes

- `next.config.js` — Next.js `output: "standalone"` mode is now opt-in via `BUILD_STANDALONE=true` environment variable (not the default for development)
- `src/backend/appdata.py` — new module for cross-platform AppData config storage (Windows/macOS/Linux)
- `src/backend/rag/kb_manifest.py` — new module for knowledge base document manifest management
- Updated `data/knowledge_base_index.md` to reflect expanded knowledge base (232 documents)
- `CHANGELOG.md` — this file, new

---

## v0.1.0 — 2025 (internal development build)

### Initial Release

- RAG pipeline over 43 Cytiva/GE Healthcare ÄKTA manuals
- FastAPI backend + Next.js 14 frontend
- ChromaDB vector search with instrument filtering
- Claude API integration with web search fallback
- Purification protocol generation (affinity, IEX, SEC, HIC, multi-step)
- Session persistence via SQLite
- Suggested follow-up questions
- Railway + Vercel deployment support
