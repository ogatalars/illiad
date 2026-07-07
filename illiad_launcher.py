#!/usr/bin/env python3
# illiad_launcher.py
"""Illiad desktop entrypoint (run-from-source).

Turns the Odysseus web app into a native-window desktop experience:

- Loads .env (respects user config), then fills operational defaults.
- Runs the FastAPI backend (app.app) on a daemon thread, loopback only.
- Waits for the backend port to accept connections.
- Opens a native pywebview window pointing at the local backend (NOT the
  system browser).
- Closing the window tears everything down (os._exit) — no tray, no
  lingering background process.

Run it with:  uv run illiad_launcher.py
"""
import os
import socket
import sys
import threading
import time


def _log(msg: str) -> None:
    # The terminal that launched us doubles as the app's log window.
    print(f"[illiad] {msg}", flush=True)


def _prepare_environment() -> tuple[str, int]:
    """Populate env before importing the app (constants read env at import)."""
    # 1) Respect the user's .env first, so their values win over our defaults.
    try:
        from dotenv import load_dotenv
        load_dotenv(encoding="utf-8-sig")  # utf-8-sig tolerates a Notepad BOM
    except Exception:
        pass

    # 2) Persistent per-user data dir (SQLite, caches, chroma) — independent of
    #    the current working directory. Only set if the user hasn't chosen one.
    if not os.getenv("ODYSSEUS_DATA_DIR"):
        try:
            from platformdirs import user_data_dir
            os.environ["ODYSSEUS_DATA_DIR"] = user_data_dir("illiad")
        except Exception:
            os.environ["ODYSSEUS_DATA_DIR"] = os.path.join(
                os.path.expanduser("~"), ".illiad", "data"
            )

    # 3) ChromaDB in-process (no container). See src/chroma_client.py.
    os.environ.setdefault("CHROMADB_MODE", "embedded")

    # 4) Bind loopback only.
    os.environ.setdefault("APP_BIND", "127.0.0.1")
    os.environ.setdefault("APP_PORT", "7000")

    host = os.environ["APP_BIND"]
    port = _resolve_free_port(host, int(os.environ["APP_PORT"]))
    os.environ["APP_PORT"] = str(port)
    return host, port


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def _resolve_free_port(host: str, preferred: int, span: int = 50) -> int:
    if _port_is_free(host, preferred):
        return preferred
    for candidate in range(preferred + 1, preferred + 1 + span):
        if _port_is_free(host, candidate):
            _log(f"port {preferred} busy; using {candidate} instead.")
            return candidate
    raise RuntimeError(
        f"no free port in range {preferred}-{preferred + span} on {host}."
    )


def _wait_for_port(host: str, port: int, timeout: float = 45.0) -> bool:
    """Block until the backend accepts TCP connections (or timeout)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def _run_backend(host: str, port: int) -> None:
    import uvicorn
    from app import app  # imported here so env is fully prepared first

    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    host, port = _prepare_environment()
    _log(f"data dir: {os.environ['ODYSSEUS_DATA_DIR']}")
    _log(f"starting backend on http://{host}:{port} ...")

    threading.Thread(target=_run_backend, args=(host, port), daemon=True).start()

    if not _wait_for_port(host, port):
        _log("ERROR: backend did not come up in time. Check the log above.")
        os._exit(1)

    url = f"http://{host}:{port}"
    _log(f"opening window: {url}")

    import webview

    # gui backend: auto by default (WebView2 on Windows, WKWebView on macOS,
    # WebKitGTK on Linux). Override with ILLIAD_WEBVIEW_GUI=qt to use Qt.
    gui = os.getenv("ILLIAD_WEBVIEW_GUI") or None

    webview.create_window("Illiad", url, width=1280, height=820, min_size=(900, 600))
    try:
        webview.start(gui=gui)
    except Exception as exc:  # noqa: BLE001
        _log(f"webview failed to start ({exc}).")
        if sys.platform.startswith("linux"):
            _log("On Linux, install the system WebKitGTK runtime — see README.")
        os._exit(1)

    # Window closed → shut everything down (daemon backend thread dies with us).
    _log("window closed, shutting down.")
    os._exit(0)


if __name__ == "__main__":
    main()
