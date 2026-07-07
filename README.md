# Illiad

A native-window desktop build of [Odysseus](https://github.com/pewdiepie-archdaemon/odysseus) —
a self-hosted AI workspace. Illiad runs the same app in its **own window**
(not a browser tab), with **no Docker** and **no installer**: you run one
command and the app opens.

> Companion to Odysseus (the *Odyssey*); this is the *Iliad*.

## What's different from Odysseus

- Opens in a **native window** (pywebview) instead of your browser.
- **No containers**: ChromaDB runs in-process; no SearXNG/ntfy services.
- Web search works out of the box via **DuckDuckGo** (no API key needed).
- Configure model/agent API keys in **Settings**, or in a `.env` file.

## Install & run

You need [**uv**](https://docs.astral.sh/uv/) (installs Python + dependencies
for you — one command, listed on the uv site).

```bash
git clone https://github.com/ogatalars/illiad.git
cd illiad
uv run illiad_launcher.py
```

That's it. `uv` creates an isolated environment, installs everything, launches
the backend, and opens the window.

### Linux: one extra system package

pywebview needs the system **WebKitGTK** runtime (it is not a pip package).
Install it once for your distro, e.g. on Debian/Ubuntu:

```bash
sudo apt install gir1.2-webkit2-4.1 libgirepository1.0-dev
```

Fedora: `sudo dnf install webkit2gtk4.1`. Arch: `sudo pacman -S webkit2gtk-4.1`.

> Prefer no system dependency? Set `ILLIAD_WEBVIEW_GUI=qt` and install PySide6
> (`uv pip install pyside6`) to use the Qt webview instead — heavier, but
> self-contained.

macOS and Windows need nothing extra — the webview ships with the OS.

## How it behaves

- The terminal you launched from **is** the app process and shows its log.
  **Keep that window open** while you use Illiad.
- **Closing the app window quits everything** — backend included. No tray icon,
  no background process left running.
- Your data (SQLite, caches, vector store) lives in a per-user folder and
  persists across runs. Override it with `ODYSSEUS_DATA_DIR`.

## Configuration

Everything has a default, so the app runs with no config. To customize, copy
`.env.example` to `.env` and edit. Common cases:

- **Use a hosted model**: set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` (or set
  the key in Settings inside the app).
- **Use a local model**: run [Ollama](https://ollama.com) and set
  `OLLAMA_BASE_URL` — no key needed.
- **Better web search**: add a provider key (Brave/Tavily/Serper/Google PSE)
  in `.env` or under Settings → Search. DuckDuckGo is the keyless default.

## License

Illiad is a derivative of Odysseus and is distributed under **AGPL-3.0-or-later**.
If you distribute a modified version, you must publish your source under the
same license. See `LICENSE` and `ACKNOWLEDGMENTS.md`.

## Design

See [`docs/SDD-illiad-desktop.md`](docs/SDD-illiad-desktop.md) for the full
design document (architecture, decisions, and what was intentionally left out).
