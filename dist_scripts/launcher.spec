# launcher.spec — PyInstaller spec for "Jojo Bot.exe" (the app launcher with custom icon)
#
# Build with (from the dist_scripts directory, with backend venv active):
#   pyinstaller launcher.spec --clean --noconfirm
#
# Output: dist_scripts\dist\Jojo Bot.exe   (single-file executable)
#
# This produces a single .exe that:
#   - Carries the Jojo Bot avatar as its Windows icon
#   - Starts backend.exe + node.exe server.js as hidden background processes
#   - Opens the app in a native Edge WebView2 window (no browser tab)
#   - Cleans up both background processes when the window is closed
# ---------------------------------------------------------------------------

import sys
import os
from pathlib import Path

block_cipher = None

SPEC_DIR = Path(SPECPATH)

# pywebview bundles WebView2Loader.dll — we need to include it so the
# compiled .exe can create a WebView2 window on the target machine.
# It lives inside the venv that was used to run PyInstaller.
VENV_DIR = SPEC_DIR.parent / "src" / "backend" / "venv"
_webview2_dll = VENV_DIR / "Lib" / "site-packages" / "webview" / "lib" / "x64" / "WebView2Loader.dll"

# Build the binaries list — include the DLL if found (it will be on any machine
# that ran `pip install pywebview` in the venv)
_binaries = []
if _webview2_dll.exists():
    # Destination path inside the bundle must mirror what pywebview expects
    _binaries = [(str(_webview2_dll), "webview/lib/x64")]
else:
    print(f"WARNING: WebView2Loader.dll not found at {_webview2_dll}")
    print("         Run: pip install pywebview  (in the backend venv) and rebuild.")
    print("         The .exe will fall back to the default browser if WebView2 is missing.")

# Similarly include the entire webview/lib data folder if present
_webview_lib_dir = VENV_DIR / "Lib" / "site-packages" / "webview" / "lib"
_datas = []
if _webview_lib_dir.exists():
    _datas = [(str(_webview_lib_dir), "webview/lib")]

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=[
        # pywebview core
        'webview',
        'webview.platforms',
        'webview.platforms.edgechromium',
        'webview.event',
        'webview.js',
        'webview.js.css',
        'webview.js.javascript',
        'webview.util',
        'webview.window',
        'webview.menu',
        # ctypes (used by pywebview's Windows backend)
        'ctypes',
        'ctypes.util',
        'ctypes.wintypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'PIL', 'cv2'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Jojo Bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # No blank console window when user double-clicks
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='jojo-avatar.ico', # Custom avatar — shows in Explorer, taskbar, title bar
)
