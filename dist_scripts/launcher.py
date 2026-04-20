"""
launcher.py — Jojo Bot Windows launcher.

This is compiled by PyInstaller into "Jojo Bot.exe" so it carries
the custom avatar icon in Windows Explorer, the taskbar, and Start Menu.

What it does:
  1. Verifies required files exist and that ports 8000 / 3000 are free
  2. Starts backend.exe silently, capturing stdout+stderr to logs/backend.log
  3. Polls /api/health until the backend is actually READY to serve
     (not just until its TCP socket binds — Chroma loads a few seconds later)
  4. Starts node.exe server.js silently, capturing logs to logs/frontend.log
  5. Opens the app in its own native window via Edge WebView2
     — Fallback: opens http://localhost:3000 in the default browser
       if WebView2 is not available (very old Windows 10 only)
  6. On window close, terminates both background processes cleanly

Logs are kept across two runs (backend.log + backend.log.prev) so a crash
from the previous session is still available when the user reopens the app.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Resolve the directory where this .exe lives (the JojoBot-v1.0 folder)
BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

# Flag: start a Windows subprocess with no visible console window
_HIDDEN = subprocess.CREATE_NO_WINDOW

# Logs are written next to the .exe so users can attach them when reporting bugs.
LOG_DIR = BASE / "logs"

BACKEND_PORT = 8000
FRONTEND_PORT = 3000
BACKEND_HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/api/health"


# ── Port helpers ─────────────────────────────────────────────────────────────

def _is_port_in_use(port: int) -> bool:
    """Return True if something is already listening on 127.0.0.1:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False


def wait_for_port(port: int, timeout: int = 30) -> bool:
    """Poll until a local TCP port is listening, or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def wait_for_health(url: str, timeout: int = 60) -> bool:
    """Poll an HTTP health endpoint until it returns 200, or timeout expires.

    Port-open is not enough: Chroma takes a few seconds to load its collection
    after the socket binds. /api/health only returns 200 when the backend is
    actually ready to serve requests.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


# ── UI helpers (MessageBox without a console) ────────────────────────────────

def _show_error(msg: str) -> None:
    """Display a Windows error dialog (works without a console)."""
    try:
        import ctypes
        # MB_ICONERROR (0x10)
        ctypes.windll.user32.MessageBoxW(0, msg, "Jojo Bot \u2014 Error", 0x10)  # type: ignore
    except Exception:
        print(msg, file=sys.stderr)


def _show_yes_no(msg: str, title: str = "Jojo Bot") -> bool:
    """Yes/No confirmation dialog. Returns True for Yes, False otherwise."""
    try:
        import ctypes
        # MB_YESNO (0x04) | MB_ICONWARNING (0x30)
        result = ctypes.windll.user32.MessageBoxW(0, msg, title, 0x04 | 0x30)  # type: ignore
        return result == 6  # IDYES
    except Exception:
        return False


# ── Log rotation ─────────────────────────────────────────────────────────────

def _open_log(name: str):
    """Open a log file for this run; keep the prior run's log as .prev.

    Returns a file object on success, or subprocess.DEVNULL as a safe fallback
    if the filesystem refuses (e.g. read-only install dir).
    """
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / name
        prev = log_path.with_suffix(log_path.suffix + ".prev")
        if log_path.exists():
            try:
                if prev.exists():
                    prev.unlink()
                log_path.rename(prev)
            except Exception:
                # Rotation failure is non-fatal — we'll just overwrite.
                pass
        return open(log_path, "w", buffering=1, encoding="utf-8", errors="replace")
    except Exception:
        return subprocess.DEVNULL


def _safe_close(handle) -> None:
    """Close a log file handle if it's a real file (not subprocess.DEVNULL)."""
    if hasattr(handle, "close"):
        try:
            handle.close()
        except Exception:
            pass


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    backend_exe = BASE / "backend" / "backend.exe"
    node_exe    = BASE / "node"    / "node.exe"
    server_js   = BASE / "frontend" / "server.js"

    # ── Sanity-check required files exist ────────────────────────────────────
    missing = [p for p in (backend_exe, node_exe, server_js) if not p.exists()]
    if missing:
        _show_error(
            "Jojo Bot cannot start \u2014 missing files:\n\n"
            + "\n".join(str(p) for p in missing)
            + "\n\nPlease re-extract the package."
        )
        sys.exit(1)

    # ── Pre-check: are the ports free? ───────────────────────────────────────
    # If 8000 or 3000 is already in use, our child processes will fail to bind
    # and wait_for_port / wait_for_health would still succeed (talking to the
    # wrong server). Fail fast and tell the user what to do.
    busy = [p for p in (BACKEND_PORT, FRONTEND_PORT) if _is_port_in_use(p)]
    if busy:
        ports = ", ".join(str(p) for p in busy)
        _show_error(
            f"Jojo Bot cannot start \u2014 port(s) {ports} are already in use.\n\n"
            "Another instance of Jojo Bot may be running, or another app is\n"
            "holding the port.\n\n"
            "Open Task Manager, end any existing Jojo Bot / backend.exe /\n"
            "node.exe processes, then try again."
        )
        sys.exit(1)

    # ── Environment for child processes ──────────────────────────────────────
    env = os.environ.copy()
    env["PORT"]     = str(FRONTEND_PORT)
    env["HOSTNAME"] = "127.0.0.1"

    backend_log = None
    frontend_log = None
    backend_proc = None
    frontend_proc = None

    try:
        # ── Start backend silently, capture stdout+stderr to backend.log ─────
        backend_log = _open_log("backend.log")
        backend_proc = subprocess.Popen(
            [str(backend_exe)],
            cwd=str(BASE / "backend"),
            env=env,
            creationflags=_HIDDEN,
            stdout=backend_log,
            stderr=subprocess.STDOUT,
        )

        # Wait for backend to actually be READY (HTTP 200 from /api/health),
        # not just for the TCP socket to bind. 60s covers cold-start on
        # slower machines where Windows Defender scans the freshly-unpacked
        # PyInstaller directory.
        if not wait_for_health(BACKEND_HEALTH_URL, timeout=60):
            # Did the backend crash outright?
            if backend_proc.poll() is not None:
                _show_error(
                    "Jojo Bot backend failed to start.\n\n"
                    f"See the log file for details:\n{LOG_DIR / 'backend.log'}"
                )
                sys.exit(1)

            # Still running but slow. Let the user choose.
            keep_going = _show_yes_no(
                "The backend is taking longer than expected to start.\n\n"
                "This can happen on the first run after install, while\n"
                "Windows Defender scans the unpacked files.\n\n"
                "Continue waiting and open the app anyway?",
                title="Jojo Bot \u2014 slow start",
            )
            if not keep_going:
                try:
                    backend_proc.terminate()
                except Exception:
                    pass
                sys.exit(1)

        # ── Start frontend silently, capture logs to frontend.log ────────────
        frontend_log = _open_log("frontend.log")
        frontend_proc = subprocess.Popen(
            [str(node_exe), str(server_js)],
            cwd=str(BASE / "frontend"),
            env=env,
            creationflags=_HIDDEN,
            stdout=frontend_log,
            stderr=subprocess.STDOUT,
        )

        # TCP port check is fine for Next.js standalone — it's ready when it binds.
        if not wait_for_port(FRONTEND_PORT, timeout=20):
            if frontend_proc.poll() is not None:
                _show_error(
                    "Jojo Bot frontend failed to start.\n\n"
                    f"See the log file for details:\n{LOG_DIR / 'frontend.log'}"
                )
                sys.exit(1)
            # Slow but still running — proceed; the window will just show a loader.

        # ── Open in a native app window via Edge WebView2 ────────────────────
        try:
            import webview  # pywebview

            webview.create_window(
                title="Jojo Bot \u2014 Purification Expert",
                url=f"http://127.0.0.1:{FRONTEND_PORT}",
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
            webbrowser.open(f"http://127.0.0.1:{FRONTEND_PORT}")
            try:
                while True:
                    if (backend_proc and backend_proc.poll() is not None) or \
                       (frontend_proc and frontend_proc.poll() is not None):
                        break
                    time.sleep(2)
            except KeyboardInterrupt:
                pass

    finally:
        # Terminate both background processes when the window closes.
        for proc in (frontend_proc, backend_proc):
            if proc is None:
                continue
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        # Flush and close log handles.
        _safe_close(backend_log)
        _safe_close(frontend_log)


if __name__ == "__main__":
    main()
