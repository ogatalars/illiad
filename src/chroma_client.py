"""
chroma_client.py

ChromaDB client with two modes:

- "embedded" (default for the Illiad desktop app): an in-process
  chromadb.PersistentClient writing under DATA_DIR/chroma. No container,
  no separate service, no network port.
- "http": the original singleton HTTP client that talks to a standalone
  ChromaDB service. Kept for server/compose deployments.

Mode is selected via CHROMADB_MODE (default "embedded"). Set CHROMADB_MODE=http
(and CHROMADB_HOST / CHROMADB_PORT) to use a standalone service instead.
"""

import os
import socket
import logging

logger = logging.getLogger(__name__)

_client = None

# A short connect probe so an unreachable ChromaDB fails fast instead of
# blocking on the OS connection timeout. Tunable via CHROMADB_CONNECT_TIMEOUT.
_CONNECT_TIMEOUT = float(os.getenv("CHROMADB_CONNECT_TIMEOUT", "2.0"))


def _import_chromadb():
    try:
        import chromadb
        return chromadb
    except ImportError as e:
        raise RuntimeError(
            "ChromaDB integration is not installed. Install it with: "
            "pip install chromadb"
        ) from e


def _embedded_dir() -> str:
    """Persistent, per-user directory for the embedded vector store."""
    try:
        from src.constants import DATA_DIR
    except Exception:
        DATA_DIR = os.getenv("ODYSSEUS_DATA_DIR") or os.path.join(
            os.path.expanduser("~"), ".illiad", "data"
        )
    path = os.path.join(DATA_DIR, "chroma")
    os.makedirs(path, exist_ok=True)
    return path


def _port_open(host: str, port: int, timeout: float = None) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout or _CONNECT_TIMEOUT):
            return True
    except OSError:
        return False


def _get_http_client():
    chromadb = _import_chromadb()
    host = os.getenv("CHROMADB_HOST", "localhost")
    port = int(os.getenv("CHROMADB_PORT", "8100"))

    if not _port_open(host, port):
        raise RuntimeError(
            f"ChromaDB is not reachable at {host}:{port}. Start the ChromaDB "
            f"service or set CHROMADB_HOST / CHROMADB_PORT to point at a "
            f"running instance (or use CHROMADB_MODE=embedded)."
        )

    client = chromadb.HttpClient(host=host, port=port)
    client.heartbeat()  # health check before caching the singleton
    logger.info(f"ChromaDB connected (http): {host}:{port}")
    return client


def _get_embedded_client():
    chromadb = _import_chromadb()
    path = _embedded_dir()
    client = chromadb.PersistentClient(path=path)
    logger.info(f"ChromaDB connected (embedded): {path}")
    return client


def get_chroma_client():
    """Get or create the singleton ChromaDB client for the configured mode."""
    global _client
    if _client is not None:
        return _client

    mode = os.getenv("CHROMADB_MODE", "embedded").strip().lower()
    _client = _get_http_client() if mode == "http" else _get_embedded_client()
    return _client


def reset_client():
    """Reset the singleton (e.g. after a config change)."""
    global _client
    _client = None
