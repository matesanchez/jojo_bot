"""
launcher.py — Jojo Bot Windows launcher.

This is compiled by PyInstaller into "Jojo Bot.exe" so it carries
the custom avatar icon in Windows Explorer, the taskbar, and Start Menu.

What it does:
  1. Starts backend.exe silently in the background (no terminal window)
  2. Waits for the backend to be ready
  3. Starts node.exe server.js silently in the background
  4. Opens the app in its own native window (via Edge WebView2)
     — Fallback: opens http://localhost:3000 in the default browser
       if WebView2 is not available (very old Windows 10 only)
  5. On window close, terminates both background processes cleanly
"""
import os
import subprocess
import sys
import time
from pathlib import Path

# Resolve the directory where this .exe lives (the JojoBot-v1.0 folder)
BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

# Flag: start a Windows subprocess with no visible console window
_HIDDEN = subprocess.CREATE_NO_WINDOW


def wait_for_port(port: int, timeout: int = 30) -> bool:
    """Poll until a local TCP port is listening, or timeout expires."""
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _show_error(msg: str) -> None:
    """Display a Windows error dialog (works without a console)."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, "Jojo Bot \u2014 Error", 0x10)  # type: ignore
    except Exception:
        print(msg, file=sys.stderr)


def main() -> None:
    backend_exe = BASE / "backend" / "backend.exe"
    node_exe    = BASE / "node"    / "node.exe"
    server_js   = BASE / "frontend" / "server.js"

    # Sanity-check required files exist
    missing = [p for p in (backend_exe, node_exe, server_js) if not p.exists()]
    if missing:
        _show_error(
            "Jojo Bot cannot start \u2014 missing files:\n\n"
            + "\n".join(str(p) for p in missing)
            + "\n\nPlease re-extract the package."
        )
        sys.exit(1)

    # Environment for child processes
    env = os.environ.copy()
    env["PORT"]     = "3000"
    env["HOSTNAME"] = "127.0.0.1"

    # ── Start backend silently (no console window) ────────────────────────────
    backend_proc = subprocess.Popen(
        [str(backend_exe)],
        cwd=str(BASE / "backend"),
        env=env,
        creationflags=_HIDDEN,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for backend to be ready (max 30 s)
    if not wait_for_port(8000, timeout=30):
        # Slow to start — the UI will show "cannot reach backend" until it's up
        pass

    # ── Start frontend silently (no console window) ───────────────────────────
    frontend_proc = subprocess.Popen(
        [str(node_exe), str(server_js)],
        cwd=str(BASE / "frontend"),
        env=env,
        creationflags=_HIDDEN,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    wait_for_port(3000, timeout=20)

    # ── Open in a native app window via Edge WebView2 ─────────────────────────
    # pywebview wraps the Edge WebView2 engine built into Windows 10/11.
    # The window title and the process icon (set in launcher.spec) both show
    # the Jojo Bot branding in the taskbar and title bar.
    try:
        import webview  # pywebview

        webview.create_window(
            title="Jojo Bot \u2014 Purification Expert",
            url="http://localhost:3000",
            width=1440,
            height=900,
            resizable=True,
            min_size=(900, 640),
            text_select=True,
        )

        # start() is blocking — returns only when the user closes the window.
        # On Windows 10/11 it automatically uses the EdgeChromium (WebView2) backend.
        webview.start()

    except Exception:
        # Fallback for machines where WebView2 is unavailable (very rare on Win10 21H1+).
        import webbrowser
        webbrowser.open("http://localhost:3000")
        try:
            while True:
                if backend_proc.poll() is not None or frontend_proc.poll() is not None:
                    break
                time.sleep(2)
        except KeyboardInterrupt:
            pass

    finally:
        # Terminate both background processes when the window closes
        for proc in (frontend_proc, backend_proc):
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
