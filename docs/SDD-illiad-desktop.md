# SDD / Implementation Spec — Illiad (Odysseus como app desktop)

> **v0.2 — formato executável por agente.** Este documento é a fonte de verdade
> para uma sessão do **Claude Code (modo agente)**. Ele descreve o que já foi
> feito, o mapa do código real, e as tarefas restantes com critério de aceite.
>
> **Como usar:** aponte o agente para este arquivo, execute as tarefas da §5 em
> ordem, e rode o smoke test da §6 depois de **cada** tarefa. Respeite os
> guardrails da §3 — eles não são negociáveis.

---

## 1. Objetivo (uma frase)

Transformar o [Odysseus](https://github.com/pewdiepie-archdaemon/odysseus)
(FastAPI + UI web servida em `localhost:7000`, deploy via docker-compose) numa
**experiência de app desktop nativo**, cross-platform, **sem Docker** e **sem
instalador**: o usuário roda `uv run illiad_launcher.py` e uma janela nativa
abre. Fechar a janela encerra tudo.

O modelo de distribuição é **run-from-source** (não há binário assinado), o que
elimina por design o problema de code signing (SmartScreen/Gatekeeper). Ver §8.

## 2. Contexto para o agente

- Este repositório é um **fork do Odysseus**. A maior parte do código é do
  upstream; nós fazemos um conjunto pequeno e cirúrgico de mudanças.
- O app tem **layout flat**: `app.py`, `src/`, `core/`, `routes/`, `services/`
  ficam na raiz. **Não** é um pacote build-able — por isso `[tool.uv] package =
  false` e o comando é `uv run illiad_launcher.py` (não um console-script).
- O ASGI app é `app.app` (em `app.py`, raiz).
- Toda persistência é centralizada em `DATA_DIR` (ver §4). Não invente caminhos
  novos: importe de `src/constants.py`.

## 3. Guardrails (NÃO faça)

1. **Não** reintroduza Docker nem exija qualquer container/serviço externo
   (ChromaDB, SearXNG, ntfy). Tudo roda in-process ou degrada.
2. Backend **sempre em loopback** (`127.0.0.1`). Nunca `0.0.0.0`.
3. **Não** transforme o app em pacote instalável nem mexa no layout flat. Mantenha
   `[tool.uv] package = false`.
4. **Não** remova o modo `http` de `src/chroma_client.py` — só o modo `embedded`
   é o default; o `http` fica para compatibilidade com deploy de servidor.
5. **Não** adicione PyInstaller, code signing, instaladores, nem matrix de build
   no CI. Está fora de escopo (§7).
6. Preserve **AGPL-3.0-or-later**. Registre as modificações. Não feche o código.
7. **Nunca** logue nem coloque em URL chaves de API, tokens ou o conteúdo de
   `.env`.
8. Faça mudanças **pequenas e verificáveis**. Rode o smoke test (§6) após cada
   tarefa. Se uma mudança quebrar o boot, reverta antes de seguir.

## 4. Mapa do código real (onde mexer)

| Arquivo | Papel | Relevância |
|--------|-------|-----------|
| `app.py` (raiz) | Orquestrador; expõe `app` (ASGI). Faz `load_dotenv`. | Não precisa mudar. |
| `launcher.py` (raiz) | Launcher **antigo** (frozen: browser + tray). | **Deletar** (substituído). |
| `illiad_launcher.py` (raiz) | **Novo** entrypoint desktop (pywebview + uvicorn sidecar). | Entregue. |
| `pyproject.toml` (raiz) | `[project]` + deps + `[tool.uv] package=false`. | Entregue (fonte de verdade das deps). |
| `.env.example` (raiz) | Config desktop (loopback, auth off, embedded chroma, keys opcionais). | Entregue. |
| `src/runtime_paths.py` | `get_app_root()`, `get_default_data_dir()`. | Base do DATA_DIR. |
| `src/constants.py` | `DATA_DIR = os.getenv("ODYSSEUS_DATA_DIR", get_default_data_dir())`; todos os paths persistidos derivam daqui. | Importar daqui. |
| `src/chroma_client.py` | Cliente Chroma com modos `embedded`/`http`. | Entregue (modificado). |
| `src/memory_vector.py` | RAG / memória semântica; usa Chroma via `data_dir`. | Verificar (T1). |
| `src/api_key_manager.py` | `ApiKeyManager(data_dir)` — guarda chaves de API. | T5. |
| `src/service_health.py` | Health checks; referencia searxng. | Neutralizar removidos (T4). |
| `services/search/providers.py` | Providers: searxng, brave, **duckduckgo (sem chave)**, google pse, tavily, serper. `_get_search_settings()`, `_get_provider_key()`. | T3. |
| `services/search/service.py`, `services/search/__init__.py` | Camada de busca. | T3. |
| `services/research/*` | Deep research; usa provider de busca + endpoint de LLM. | T3 (indireto). |
| `core/database.py` | `DATABASE_URL` normalizado contra `DATA_DIR`/`get_app_root`. | Verificar (T2). |
| `docker-compose*.yml`, `Dockerfile`, `Odysseus.spec`, `build-*.{sh,ps1}`, `launch-windows.ps1`, `install-service.sh`, `odysseus-ui.service`, `config/searxng/` | Artefatos de container/packaging do upstream. | Fora de escopo; deixar quieto (T8 opcional). |

## 5. Estado atual — o que o bundle já entregou

O `illiad-starter.zip` já aplicou:

- `illiad_launcher.py` — carrega `.env`, resolve DATA_DIR por-usuário via
  `platformdirs`, sobe uvicorn em daemon thread, espera a porta, abre janela
  `pywebview`, `os._exit` ao fechar. Sem tray, sem browser.
- `src/chroma_client.py` — modo `embedded` (default) com `PersistentClient` em
  `DATA_DIR/chroma`; modo `http` preservado.
- `pyproject.toml` — `chromadb` (no lugar de `chromadb-client`), `+pywebview`,
  `+platformdirs`, `[tool.uv] package=false`, pytest preservado.
- `.env.example`, `README.md`.

Ainda **não** feito → tarefas abaixo.

## 6. Tarefas para o agente (em ordem)

### T0 — Aplicar o starter e validar o boot
- **Ação:** garantir que os arquivos do bundle estão no lugar; **deletar
  `launcher.py`** (antigo). Rodar o smoke test §7.
- **Aceite:** `uv run illiad_launcher.py` sobe o backend e abre uma janela nativa
  sem traceback; fechar a janela encerra o processo (sem processo órfão).

### T1 — ChromaDB embedded ponta a ponta
- **Ação:** garantir que todo caminho de RAG/memória obtém o client via
  `src/chroma_client.py:get_chroma_client()` e funciona com `PersistentClient`.
  Inspecionar `src/memory_vector.py` e qualquer uso de `HttpClient`/`chromadb.`
  fora do `chroma_client.py`; redirecionar para o singleton.
- **Aceite:** com `CHROMADB_MODE=embedded` e **sem** container, criar/indexar um
  documento (RAG) e recuperá-lo funciona; nenhum erro "ChromaDB is not reachable".

### T2 — Integridade do diretório de dados
- **Ação:** confirmar que **todos** os arquivos persistidos (SQLite, json de
  settings/auth, uploads, chroma) caem sob `ODYSSEUS_DATA_DIR`. Procurar
  gravações relativas a `./data` ou a `__file__` fora de `src/constants.py`.
- **Aceite:** rodar `uv run illiad_launcher.py` a partir de um **cwd diferente**
  (ex.: `/tmp`) e confirmar que o `app.db` e o `chroma/` aparecem no dir do
  `platformdirs`, não no cwd.

### T3 — Busca zero-config (sem SearXNG)
- **Ação:** garantir que a ausência de `SEARXNG_URL` não quebra busca/research.
  Se nenhum provider estiver configurado nas settings, usar **duckduckgo** como
  default (sem chave). Não remover os outros providers.
- **Aceite:** com `.env` mínimo (sem nenhuma key de busca), uma busca web e um
  deep research retornam resultados; nenhuma menção a SearXNG no fluxo.

### T4 — Neutralizar health check dos serviços removidos
- **Ação:** em `src/service_health.py`, no modo desktop, reportar Chroma
  **embedded** como saudável (checar o `PersistentClient`, não uma porta) e
  **não** reportar SearXNG/ntfy como erro (marcar como "não aplicável" / oculto).
- **Aceite:** a tela/endpoint de status não mostra Chroma/SearXNG/ntfy como
  falha quando rodando desktop.

### T5 — Chaves de API por Settings (MVP)
- **Ação:** confirmar que a tela de **Settings** existente + `ApiKeyManager`
  cobrem definir provider e chave de modelo (OpenAI/Anthropic/Ollama). Documentar
  o fluxo no README se faltar. **Não** construir tela nova agora — só garantir
  que o caminho existente funciona no app desktop.
- **Aceite:** colar uma chave em Settings (ou `.env`) e rodar um agente/chat
  usando essa chave funciona; a chave persiste entre execuções.

### T6 — Polimento de primeiro uso
- **Ação:** título da janela "Illiad", `min_size` sensato (já no launcher),
  ícone se trivial, e uma linha clara no log/README: *"mantenha esta janela de
  terminal aberta enquanto usa o app"*.
- **Aceite:** primeira execução é auto-explicativa; nada de tela branca sem
  feedback enquanto o backend sobe.

### T7 — Licença e atribuição
- **Ação:** manter `LICENSE` (AGPL) do upstream; adicionar um `NOTICE` curto
  listando as modificações do Illiad; conferir `ACKNOWLEDGMENTS.md`.
- **Aceite:** `LICENSE` presente e correta; README §License bate com a realidade.

### T8 — (Opcional) Parquear artefatos de container/packaging
- **Ação:** mover `docker-compose*.yml`, `Dockerfile`, `Odysseus.spec`,
  `build-*.{sh,ps1}`, `install-service.sh`, `odysseus-ui.service`,
  `config/searxng/` para uma pasta `legacy/` (ou deletar), pois não são usados
  no modelo desktop. **Só faça se explicitamente pedido** — são inofensivos.
- **Aceite:** boot continua funcionando; nada no caminho desktop referencia esses
  arquivos.

## 7. Smoke test (rodar após cada tarefa)

```bash
# Linux only, uma vez: sudo apt install gir1.2-webkit2-4.1 libgirepository1.0-dev
uv run illiad_launcher.py
# Espera-se no log: "starting backend..." -> "opening window: http://127.0.0.1:7000"
# Uma janela nativa abre com a UI. Criar um chat simples deve responder
# (com uma key de modelo configurada). Fechar a janela -> processo encerra.
```

Checklist mínimo verde:
- [ ] Janela abre sem traceback.
- [ ] `app.db` e `chroma/` sob o DATA_DIR do `platformdirs`.
- [ ] Busca web responde sem nenhuma API key (duckduckgo).
- [ ] Fechar a janela mata o processo (sem órfão em `ps`).

## 8. Por que run-from-source (contexto de decisão, para humanos)

Code signing não tem "atalho grátis" em 2026: o `--no-quarantine` do Homebrew
foi descontinuado (casks não assinados saem do tap em set/2026), Apple Silicon
exige assinatura para executar arm64, o macOS 15 removeu o "botão direito →
Abrir", o EV do Windows deixou de pular o SmartScreen (2024), e o Azure Artifact
Signing barato (~US$9,99/mês) só aceita pessoa física em EUA/Canadá. Para um
projeto open-source não-monetizado, assinar não se paga. **Rodar a partir do
código-fonte contorna o problema por design** — não há binário para assinar.

## 9. Fora de escopo (não fazer nesta sessão)

Instaladores por SO, PyInstaller/Tauri/Electron, code signing/notarização, CI
matrix de build, auto-update, tray/rodar em background, bundle de servidor de
modelo local, e uma tela de settings dedicada só para chaves (a existente basta
no MVP — T5).

## 10. Apêndice — arquitetura (referência)

```
┌─────────────────────────────────────────────┐
│  Processo único  (uv run illiad_launcher.py)  │
│                                               │
│   pywebview  ──HTTP 127.0.0.1:7000──▶ FastAPI │
│   (janela        (thread principal)   (uvicorn│
│    nativa)                             daemon) │
│                                               │
│   In-process: ChromaDB (PersistentClient)     │
│   Externo/opcional: Ollama, APIs de modelo    │
└─────────────────────────────────────────────┘
```

- UI (JS/HTML/CSS do upstream) roda no webview do SO, não no navegador.
- Backend na mesma "casa" (daemon thread), só loopback.
- O terminal é o processo do app: fechou o terminal, fechou o app.
- Dependência de sistema só no Linux (WebKitGTK); Mac/Windows já têm o webview.
