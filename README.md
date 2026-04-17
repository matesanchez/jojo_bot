# Jojo Bot 🤖

**AI-powered Q&A assistant for Cytiva ÄKTA chromatography systems, UNICORN software, and Nurix protein purification workflows.**

Jojo Bot lets lab scientists ask natural-language questions about ÄKTA systems and get expert answers grounded in 232 official Cytiva manuals and Nurix SOPs — with citations, web search fallback, and downloadable purification protocols.

---

## What's New — v1.0 (April 2026)

- **Standalone Windows app** — `build-package.bat` compiles Jojo Bot into a fully self-contained `.exe` package with no Python or Node.js installation required for end-users
- **Native app window** — `Jojo Bot.exe` opens in its own dedicated window (Edge WebView2) instead of a browser tab; no terminal windows appear
- **In-app Settings panel** — gear icon (⚙) opens a two-tab modal for API key management and knowledge base browsing
- **API key stored in AppData** — keys are stored in `%APPDATA%\JojoBot\config.json` on each user's machine, never in the package files
- **Live document upload** — users can add their own PDFs to the local knowledge base directly from the UI, with instrument tagging, drag-and-drop, and live progress streaming
- **Knowledge base manifest** — lightweight JSON index for O(1) document listing without querying the full ChromaDB collection
- **Security hardening** — path traversal fixes (Windows-safe `relative_to()` checks), secrets removed from env files, rate limiting tightened

See [CHANGELOG.md](CHANGELOG.md) for the full history.

---

## Features

- **Manual-grounded answers** — RAG pipeline over 232 Cytiva/GE Healthcare PDFs and Nurix SOPs, with citations to document, section, and page number
- **Instrument filtering** — narrow answers to a specific ÄKTA model (pure, go, avant, start, pilot 600, and more)
- **Web search fallback** — automatically searches the web for recent application notes, vendor info, or anything the manuals don't cover
- **Protocol generation** — generate complete, downloadable purification protocols (affinity, IEX, SEC, HIC, multi-step)
- **Conversation memory** — follow-up questions work naturally; full session history is persisted
- **Suggested follow-ups** — auto-generated next questions after every answer
- **User document uploads** — add lab-specific PDFs to the local knowledge base at any time via the Settings panel
- **Standalone distribution** — share the app as a ZIP file; colleagues unzip and double-click to run (no installation)

---

## Tech Stack

| Layer | Choice |
| ----- | ------ |
| AI | Claude API (Sonnet) via Anthropic SDK |
| Backend | FastAPI + Python 3.11 |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Vector DB | ChromaDB (local, no cloud needed) |
| PDF parsing | PyMuPDF |
| Session storage | SQLite via SQLAlchemy async |
| App window | PyWebView (Edge WebView2) |
| Distribution | PyInstaller + portable Node.js |

---

## Project Structure

```
jojobot/
├── .env.example                    # Template for required environment variables
├── start.sh                        # Start both servers with one command (dev)
├── build-package.bat               # Build self-contained Windows distribution
├── DEPLOY.md                       # Step-by-step deployment guide
├── CHANGELOG.md                    # Version history and release notes
├── data/
│   ├── manuals/                    # PDF manuals here (not in Git — 222 MB)
│   └── knowledge_base_index.md     # Human-readable index of all indexed documents
├── dist_scripts/                   # Files that become part of the distributed package
│   ├── launcher.py                 # Source for Jojo Bot.exe (compiled by build-package.bat)
│   ├── launcher.spec               # PyInstaller spec for the launcher
│   ├── jojo-avatar.ico             # App icon (multi-size ICO)
│   ├── Start Jojo Bot.bat          # Fallback launcher script
│   ├── Stop Jojo Bot.bat           # Stop all Jojo Bot processes
│   └── README.txt                  # End-user instructions (included in package)
├── prompts/
│   └── system_prompt.txt           # Jojo Bot persona and instructions
└── src/
    ├── backend/
    │   ├── config.py               # Pydantic settings, env var loading
    │   ├── appdata.py              # API key storage in %APPDATA%\JojoBot\
    │   ├── main.py                 # FastAPI app and all endpoints
    │   ├── backend.spec            # PyInstaller spec for backend.exe
    │   ├── requirements.txt
    │   ├── Dockerfile
    │   ├── test_pipeline.py        # Integration test suite
    │   ├── db/
    │   │   ├── models.py           # Session & Message SQLAlchemy models
    │   │   ├── database.py         # Async engine setup
    │   │   └── session_store.py    # CRUD operations
    │   └── rag/
    │       ├── ingest.py           # PDF → ChromaDB ingestion pipeline
    │       ├── retriever.py        # Semantic search
    │       ├── generator.py        # Claude API integration + web search
    │       ├── kb_manifest.py      # Knowledge base document index
    │       └── protocol_generator.py  # Protocol generation
    └── frontend/
        ├── package.json
        ├── next.config.js
        └── src/
            ├── app/                # Next.js App Router pages
            ├── components/         # Chat UI components (incl. SettingsPanel)
            └── lib/                # API client + TypeScript types
```

---

## Getting Started (Development)

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/settings/keys)
- PDF manuals in `data/manuals/`

### 2. Clone and configure

```bash
git clone https://github.com/matesanchez/jojo_bot.git
cd jojo_bot

cp .env.example .env
# Open .env and add your ANTHROPIC_API_KEY
```

### 3. Set up the backend

```bash
cd src/backend
python3.11 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Ingest the PDF manuals

```bash
python -m rag.ingest --input ../../data/manuals/
```

This takes 5–15 minutes and creates the `data/chroma_db/` vector database. Only needed once (or again with `--reset` if you add new documents in bulk).

### 5. Set up the frontend

```bash
cd src/frontend
npm install
```

### 6. Run locally

From the project root:

```bash
chmod +x start.sh
./start.sh
```

This starts the backend on `http://localhost:8000` and the frontend on `http://localhost:3000`.

---

## Building the Distributable Package (Windows)

To create a self-contained `.zip` that colleagues can unzip and run:

```batch
build-package.bat
```

This will:
1. Compile `backend.exe` with PyInstaller
2. Compile `Jojo Bot.exe` (launcher with Jojo avatar icon) with PyInstaller + pywebview
3. Build the Next.js frontend in standalone mode
4. Download portable Node.js 20
5. Assemble everything into `dist\JojoBot-v1.0\`
6. Create `dist\JojoBot-v1.0.zip`

End-users unzip anywhere and double-click `Jojo Bot.exe`. They enter their own Anthropic API key in the Settings panel (⚙). No installation required.

---

## API Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| `POST` | `/api/chat` | Send a message; returns answer, citations, follow-ups |
| `GET` | `/api/sessions` | List recent chat sessions |
| `GET` | `/api/sessions/{id}` | Get full conversation history |
| `DELETE` | `/api/sessions/{id}` | Delete a session |
| `POST` | `/api/generate-protocol` | Generate a purification protocol |
| `GET` | `/api/health` | Health check + indexed document count |
| `GET` | `/api/settings/api-key` | Get masked API key status |
| `POST` | `/api/settings/api-key` | Save API key to AppData |
| `DELETE` | `/api/settings/api-key` | Remove API key from AppData |
| `GET` | `/api/knowledge-base` | List all indexed documents |
| `POST` | `/api/knowledge-base/upload` | Upload PDFs (SSE progress stream) |
| `DELETE` | `/api/knowledge-base/{source_file}` | Remove a user-uploaded document |

---

## Running Tests

```bash
cd src/backend
source venv/bin/activate
python test_pipeline.py
```

Tests cover the retriever, generator, session store CRUD, and app import.

---

## Security Notes

- The Anthropic API key is stored **only** in `%APPDATA%\JojoBot\config.json` on each user's machine — never in the package files, never in Git, never sent to the frontend
- `.env` and all secrets are in `.gitignore` and will never be committed
- Input messages are limited to 10,000 characters; rate limiting: 30 req/min per session (chat), 10 req/min per IP (settings), 5 req/min per IP (uploads)
- File uploads are restricted to PDF only, max 50 MB per file, with server-side path containment checks using `Path.relative_to()` (Windows-safe)
- The backend binds to `127.0.0.1` in production — not accessible from outside the local machine

---

## Deployment (Cloud)

See [DEPLOY.md](DEPLOY.md) for step-by-step instructions for Railway (backend) and Vercel (frontend).

---

## License

MIT
