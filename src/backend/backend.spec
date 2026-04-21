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
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all source files (excluding venv)
src_dir = Path(SPECPATH)

# ---------------------------------------------------------------------------
# Auto-collect submodules and data files for packages with complex internals.
#
# ChromaDB has dozens of internal submodules (embedding functions, segment
# managers, DB backends, etc.) that it imports dynamically.  Rather than
# maintaining a fragile hand-written list, let PyInstaller discover them all.
# This is what fixed the "ONNXMiniLM_L6_V2 is not defined" crash.
#
# onnxruntime ships native .dll/.so inference engines and provider libs.
# tokenizers is a Rust-compiled package with native extensions.
# Both are required by ChromaDB's default embedding function at runtime.
# ---------------------------------------------------------------------------
chromadb_imports  = collect_submodules("chromadb")
chromadb_datas    = collect_data_files("chromadb")

onnx_imports      = collect_submodules("onnxruntime")
onnx_datas        = collect_data_files("onnxruntime")

tokenizers_datas  = collect_data_files("tokenizers")

# Pydantic v2 uses compiled Rust core — collect its native libs
pydantic_datas    = collect_data_files("pydantic")

# anthropic SDK has internal sub-packages (types, resources) that are
# discovered at import time
anthropic_imports = collect_submodules("anthropic")

a = Analysis(
    [str(src_dir / "main.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[
        # Include prompts folder
        (str(src_dir.parent.parent / "prompts"), "prompts"),
    ] + chromadb_datas + onnx_datas + tokenizers_datas + pydantic_datas,
    hiddenimports=chromadb_imports + onnx_imports + anthropic_imports + [
        # FastAPI / Starlette
        "fastapi",
        "fastapi.middleware.cors",
        "fastapi.responses",
        "starlette.middleware.cors",
        "starlette.responses",
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
        "pydantic_core",
        # Database
        "sqlalchemy",
        "sqlalchemy.ext.asyncio",
        "aiosqlite",
        # ChromaDB runtime dependencies that live outside the chromadb package
        "tokenizers",
        "tenacity",
        "tqdm",
        "hnswlib",
        # Anthropic SDK transitive dependencies
        "httpx",
        "httpcore",
        "anyio",
        "anyio._backends._asyncio",
        "sniffio",
        "certifi",
        "h11",
        "idna",
        # PyMuPDF (C extension for PDF parsing)
        "fitz",
        # dotenv
        "dotenv",
        # numpy (required by chromadb — see NOTE in excludes)
        "numpy",
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
        # NOTE: numpy is NOT excluded — chromadb/api/types.py imports it,
        # so removing it makes backend.exe fail on first import.
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
