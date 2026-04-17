# backend.spec — PyInstaller spec for Jojo Bot backend
#
# Build with:
#   cd src\backend
#   pyinstaller backend.spec
#
# Output: src\backend\dist\backend\backend.exe
# ---------------------------------------------------------------------------

import sys
from pathlib import Path

block_cipher = None

# Collect all source files (excluding venv)
src_dir = Path(SPECPATH)

a = Analysis(
    [str(src_dir / "main.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[
        # Include prompts folder
        (str(src_dir.parent.parent / "prompts"), "prompts"),
        # ChromaDB needs its migrations folder
        ("venv/Lib/site-packages/chromadb/migrations", "chromadb/migrations"),
    ],
    hiddenimports=[
        # FastAPI / Starlette
        "fastapi",
        "fastapi.middleware.cors",
        "starlette.middleware.cors",
        "starlette.routing",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # Pydantic
        "pydantic",
        "pydantic_settings",
        "pydantic.v1",
        # Database
        "sqlalchemy",
        "sqlalchemy.ext.asyncio",
        "aiosqlite",
        # ChromaDB
        "chromadb",
        "chromadb.api",
        "chromadb.api.client",
        "chromadb.config",
        "chromadb.db",
        "chromadb.db.impl",
        "chromadb.db.impl.sqlite",
        "chromadb.segment",
        "chromadb.segment.impl",
        "chromadb.segment.impl.manager",
        "chromadb.segment.impl.manager.local",
        "chromadb.segment.impl.metadata",
        "chromadb.segment.impl.metadata.sqlite",
        "chromadb.segment.impl.vector",
        "chromadb.segment.impl.vector.local_hnsw",
        "chromadb.telemetry",
        "chromadb.telemetry.product",
        "chromadb.telemetry.product.events",
        "hnswlib",
        # Anthropic SDK
        "anthropic",
        "httpx",
        "httpcore",
        "anyio",
        "anyio._backends._asyncio",
        # PyMuPDF
        "fitz",
        # dotenv
        "dotenv",
        # Our modules
        "appdata",
        "config",
        "db.database",
        "db.models",
        "db.session_store",
        "rag.generator",
        "rag.ingest",
        "rag.kb_manifest",
        "rag.protocol_generator",
        "rag.retriever",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "cv2",
        "torch",
        "tensorflow",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console window so users can see startup logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(src_dir.parent.parent / "jojo-avatar.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="backend",
)
