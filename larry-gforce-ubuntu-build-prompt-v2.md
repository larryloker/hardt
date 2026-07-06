# LARRY G-FORCE — UBUNTU 26 REBUILD PROMPT (v2, file-grounded)

**Source of truth:** the uploaded files from the Windows canonical tree (`C:\Users\LocalLarry\Documents\LocalLarry\GITHUB`), captured 2026-07-03 in `VERSION_STATE.json`.
**Target root:** `/home/locallarry/Documents/GITHUB-AGENT-main` — referred to below as `$ROOT`.
**Rig:** same hardware (Ryzen 5 7500F, RTX 4060 8GB, 64GB DDR5). Only the OS changed: Windows 10 → Ubuntu 26.04 LTS, native (NO WSL anywhere).

---

## 1. RULESET (non-negotiable — violations = shutdown)

1. **The uploaded files are ground truth.** Never contradict them from memory. When this prompt and a real file disagree, the file wins — say so and ask.
2. **Never fabricate** model tags, package names, config keys, paths, or tool output. Unverified = say "unverified".
3. **Ask, don't guess.** Missing file/token/decision → STOP and request it from the operator (FXJEFE). He has the full old tree and all secrets.
4. **Evidence with every claim.** "Done/working" must be accompanied by the actual command + real output. No evidence = treated as fabrication.
5. **Real tool calls only.** Never narrate a tool call as if it ran.
6. **One canonical file per name.** No `_v2`, `_final`, `(1)` copies (the old `agent_v2222.py` chaos is over). Git for history.
7. **Minimal diffs** when patching ported code — never regenerate whole files.

---

## 2. WHAT EXISTS (inventory from VERSION_STATE.json + configs)

Two config generations live side by side — **port both, unify nothing without approval**:

| Generation | File | Consumers |
|---|---|---|
| v2.0.0 legacy | `larry_config.json` | `agent_v2.py`, `src/` modules, telegram bot, dashboard |
| v3.0.0 restructured | `config.json` | `main.py`, `subagents/`, `tools/`, `utils/` |

Two MCP registries with **different formats** — both are real, do not merge:

| Registry | Format | Content |
|---|---|---|
| `$ROOT/mcp.json` | `{"servers": [ ... ]}` **list**, native/stdio/http transports | 12 servers: fxjefe-local (disabled — script deleted), filesystem, time, memory, sqlite, brave-search, playwright, context7, n8n, podman, github, desktop-commander |
| `$ROOT/mcp/mcp.json` | `{"mcpServers": { name: {command,args} }}` **dict** (see `mcp_json.example`) | stdio/docker spec registry |

Identify which loader reads which registry before touching either. If only one is actually consumed in the current code, report the evidence and ask before deleting the other.

Known ports: Ollama `11434`, dashboard `3777`, HTTP API `7333`, n8n `5678`. Document all in `$ROOT/config/PORTS.md`.

---

## 3. TARGET LAYOUT ON UBUNTU (state_locations → Linux)

Direct translation of `VERSION_STATE.json` — keep the same relative structure so the portable-mode path logic (`larry_paths.BASE_DIR`, `working_directory: null`) keeps working:

```
$ROOT/
├── .venv/                        # REGENERATED on Linux — never copied (old venv scripts
│                                 #   have hardcoded Windows shebangs, e.g. jsondiff)
├── .env                          # recreated; secrets supplied by operator
├── larry_config.json             # v2 config (edits in §5)
├── config.json                   # v3 config (edits in §5)
├── mcp.json                      # list-format registry (edits in §6)
├── mcp/
│   ├── mcp.json                  # dict-format registry (from mcp_json.example)
│   └── fxjefe-local-mcp/         # README only — server script deleted, stays disabled
├── prompts/LARRY_SYSTEM_PROMPT.md  # Linux revision (§8)
├── src/                          # agent_v2.py, model_router.py, kali_tools.py, ...
├── main.py, subagents/, tools/, utils/   # v3 layout, if present in old tree
├── memory/                       # chroma_db/, tasks.db, skills.db, sessions.db
├── data/                         # unified_context.db, conversation_history.json, larry_memory.json
├── memory.json                   # knowledge-graph store (MemoryServer)
├── db/                           # dashboard_auth.json, saved_db
├── logs/                         # larry.log, agent_status.json, agent_startup_error.log
├── sandbox/
└── scripts/                      # NEW: setup.sh, launch_*.sh + systemd user units
```

Data files (`Larry_memory.json`, `conversation_history.json`, `memory.json`, `*.db`) are **copied as data**, with CRLF→LF normalization applied only to code/config, never to binary DBs.

**ChromaDB is NOT copied.** Wipe and re-index on Linux (old index was built with a different environment; history shows it previously corrupted with embed-model mismatch errors). Fresh `memory/chroma_db` + re-run indexing.

---

## 4. PYTHON ENVIRONMENT

1. `python3 -m venv $ROOT/.venv` — venv at repo root (matches VERSION_STATE interpreter location).
2. Install `requirements.txt` as-is. It is already Linux-clean: `pyreadline3` has `sys_platform == 'win32'` marker and will auto-skip.
3. **CUDA torch gate (known past failure):** `python -c "import torch; print(torch.cuda.is_available())"` must print `True`. If `False`, reinstall from the CUDA wheel index before proceeding. The reranker config (`BAAI/bge-reranker-v2-m3` on `cuda:0`) depends on this.
4. Playwright on Linux needs both: `playwright install chromium` **and** `sudo playwright install-deps` (system libraries).
5. `jsondiff` is a console script from the `jsonpatch` package — pip regenerates it with a correct Linux shebang. Do not port the old file.

---

## 5. CONFIG EDITS (exact, per file)

### larry_config.json
- No path edits needed — all paths are already relative (`./memory/chroma_db`, `./data/...`, `./mcp.json`) and `working_directory: null` = portable mode. Verify `larry_paths.BASE_DIR` resolves correctly on Linux.
- `hardware.gpu_persistence_mode: true` → on Linux this maps to `nvidia-smi -pm 1`; `gpu_power_limit_w: 100` → `nvidia-smi -pl 100`. Put both in a launcher/systemd `ExecStartPre`, ask operator before applying (needs root).
- `gpu_gaming` block (gaming_mode true, gaming_num_gpu 16) — semantics unchanged, port verbatim.

### config.json
- Paths already relative — no edits.
- `api.host: "0.0.0.0"` conflicts with the system prompt's own rule ("everything important binds to 127.0.0.1"). **Recommend `127.0.0.1`; flag as operator decision D5.**
- `api.token: null` → env `LARRY_API_TOKEN` in `.env`.

### .env (recreate; request every value from operator)
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOW_ALL` (was temporarily `true` — ask if it should stay), `BRAVE_API_KEY`, `GITHUB_TOKEN`, `N8N_API_KEY`, `LARRY_API_TOKEN`. Never invent placeholder values that look real.

---

## 6. mcp.json — PER-SERVER LINUX EDITS (list-format registry)

| Server | Edit |
|---|---|
| `fxjefe-local` | Keep `"enabled": false`. Script was deleted; README survives. Re-enable only after operator restores `fxjefe_local_mcp_server.py` (decision D6). |
| `filesystem` | `allowed_paths`: `["C:\\Users\\LocalLarry\\Documents\\LocalLarry\\GITHUB"]` → `["/home/locallarry/Documents/GITHUB-AGENT-main"]` |
| `time`, `memory`, `sqlite`, `context7` | Relative paths already portable — no edits. |
| `brave-search`, `github`, `n8n` | Key-env indirection unchanged; keys go in `.env`. n8n only works if n8n runs on :5678 — verify or leave enabled-but-degraded, report which. |
| `playwright` | Config unchanged; depends on §4 step 4. |
| `podman` | `socket_path: null` → on Ubuntu requires `podman` installed (apt) and user socket enabled (`systemctl --user enable --now podman.socket`). Ask operator whether podman is wanted on this box (D7). |
| `desktop-commander` | `allowed_apps: ["notepad","calculator","explorer"]` are Windows apps. Propose Linux equivalents (`gedit`/`gnome-text-editor`, `gnome-calculator`, `nautilus`) or disable — operator decision D8. |

For `mcp/mcp.json` (dict registry): translate the example's Windows paths the same way; `docker`-command entries require Docker or podman-docker shim — same D7 decision.

---

## 7. WINDOWS-SPECIFIC CODE REWORK (search-and-fix list)

Run these greps over the ported tree; every hit is work:

```bash
grep -rn 'C:\\\\\|C:/'            src/ *.py        # hardcoded Windows paths
grep -rn 'wsl -d kali-linux\|wsl ' src/ *.py       # WSL dispatch
grep -rn 'winget\|choco'           src/ *.py       # Windows package managers
grep -rIl $'\r'                    --include='*.py' --include='*.json' --include='*.md' .
```

1. **`kali_tools.py`:** remove the WSL layer entirely. `wsl -d kali-linux -- <cmd>` → direct native `subprocess` (Kali's tools are now installed natively on Ubuntu or skipped). Keep the `TOOLS` registry, `list_tools`, `run_tool`, `parse_args_with_preset` signatures identical so `agent_v2.py` imports unchanged. Keep the module-level environment-probe caching pattern.
2. **`security_tools_installer.py`:** winget/choco → `apt-get install -y` for nmap, nikto, gobuster, sqlmap, etc. Same public function names. Tools missing from Ubuntu's repos: report and ask, never fake an install.
3. **`persistence_logger.log_wsl_kali_usage`:** keep the name (compatibility), log native execution internally; note the rename as future cleanup.
4. **`agent_v2.py`:** apply both patches from `agent_v2_PATCH.md` verbatim — (a) hardened sibling-import guard with framed FATAL + `logs/agent_startup_error.log`, (b) `print("= * 40")` → `print("=" * 40)` in the /voice handler. The patch doc's guard is OS-agnostic — port as written.
5. **`model_router.py`:** keep the "nuclear-defensive" `get_router()` (never returns `None`, emergency fallback router) and the gaming/production GPU clamping driven by `gpu_gaming`.
6. **`production_rag.py`:** keep the exclusion list + 1800-char per-call cap + 450/650 chunk sizes. Extend exclusions with Linux venv paths (`.venv/lib`, `site-packages` resolve differently than on Windows).
7. **Launchers:** every `.ps1`/`.bat` and the `& .venv\Scripts\python.exe ...` invocations → `scripts/launch_*.sh` using `$ROOT/.venv/bin/python`, plus systemd **user** units for long-running services (telegram bot, dashboard, API). `Start_Agent_LarryV2.py` remains the blessed Python entry point if that's what the old tree used — verify, don't assume.
8. **CRLF→LF** across all text files (several uploads, including `Larry_memory.json`, carry `\r\n`); `chmod +x` + correct shebangs on scripts.

---

## 8. SYSTEM PROMPT REVISION (`prompts/LARRY_SYSTEM_PROMPT.md`)

Produce a Linux edition preserving identity, startup ritual, Radical Honesty, risk philosophy, sub-agent inheritance rules, 70% resource guard, and memory-chunking rules **unchanged**. Edit only environment claims:
- "Windows (with WSL Kali)" framing → native Ubuntu; all `wsl -d kali-linux --` instructions removed.
- "Full access ... host device and inside the Kali WSL terminal" → "on the Ubuntu host".
- winget/choco references → apt.
Show the operator a diff of the prompt before installing it.

---

## 9. OLLAMA ON LINUX

1. Native install; configure via `systemctl edit ollama` override — env vars go here, not in shell profiles. Bring over the calibrated set unless operator says otherwise: `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`. Note `keep_alive` is also set per-request from configs (`30m` / `-1` history) — config value wins; don't double-manage.
2. **Stock models to pull first** (the fallback chain in `config.json` + embedder): `qwen3-coder:30b-a3b-q4_K_M`, `qwen3:8b`, `dolphin3:8b`, `nomic-embed-text:latest`. Then `llama3.1:8b` (ULTRA_CONTEXT — its absence caused live 404 errors in `Larry_memory.json`) and `llama3.2:3b`. The remaining tier1/tier2 list (dolphin-mixtral:8x7b, phi4:14b, etc.) is pulled on demand — confirm disk budget with operator first.
3. **Custom models** `LocalLarry-15b`, `LocalLarry-Fast`, `LocalLarry-Uncensored` cannot be pulled — they are built from Modelfiles. **Request the Modelfiles from the operator (D1).** Until they exist, the configs' fallback mapping covers operation; verify the fallback path actually triggers.
4. Calibration constants: `num_thread 6` (physical cores); `num_gpu 99` for 8B-class; MoE 30B coder starts at `num_gpu 12–14`, tuned against live `nvidia-smi` — never guessed.

---

## 10. OPERATOR DECISIONS REQUIRED (ask before building the affected part)

- **D1:** Modelfiles for the three `LocalLarry-*` customs (§9.3).
- **D2:** ChromaDB embedder conflict — configs say `nomic-embed-text`, `production_rag.py` history says `mxbai-embed-large` (chunk caps were sized for it). Which embedder is canonical for the fresh Linux index?
- **D3:** Two chroma paths on record — `$ROOT/chroma_db` (VERSION_STATE) vs `./memory/chroma_db` (both configs). Pick one; recommend `memory/chroma_db`.
- **D4:** Dual memory stores (`memory.json` + `data/larry_memory.json`) — keep both as-is, or is one dead?
- **D5:** API bind `0.0.0.0` vs `127.0.0.1` (§5).
- **D6:** Restore `fxjefe_local_mcp_server.py` or keep server disabled?
- **D7:** Container runtime on Ubuntu: podman, Docker, or neither?
- **D8:** desktop-commander Linux app list or disable?
- **D9:** Default model mismatch — VERSION_STATE captured `dolphin3:8b` as live default; configs say `LocalLarry-15b`. Which reflects intent for the rebuild?

---

## 11. BUILD ORDER WITH GATES (evidence at every gate)

| Phase | Work | Gate (show command + output) |
|---|---|---|
| 1 | apt update, NVIDIA driver, git, python3-venv, build deps; repo at `$ROOT` | `nvidia-smi` shows RTX 4060 |
| 2 | venv + requirements + playwright deps | `torch.cuda.is_available()` → `True`; `pip check` clean |
| 3 | Ollama + systemd env + §9.2 pulls (+ D1 Modelfiles) | env visible in `systemctl show ollama`; test generation; `ollama list` matches plan |
| 4 | Port tree; §7 rework; §5 config edits; `.env` from operator | all four greps in §7 return zero hits; `python -m compileall` clean |
| 5 | model_router + gaming clamp | router never-None test; `nvidia-smi` confirms clamped VRAM in gaming_mode |
| 6 | MCP: both registries, per-server §6 edits | tool listing succeeds; one real round-trip per enabled server, output shown |
| 7 | RAG: fresh chroma (D2/D3), production_rag guards | index run completes with zero context-length errors; insert→query round-trip |
| 8 | agent_v2 patches + CLI boot | framed-FATAL test (hide one sibling module) passes; clean boot with all siblings |
| 9 | Telegram bot, dashboard (:3777), API (:7333) as systemd user units | services survive `systemctl --user restart`; `/fast` + `/tools` echo test in Telegram |
| 10 | End-to-end: full agent task exercising a real MCP tool | transcript with genuine structured tool round-trip |

## 12. REPORTING FORMAT (every work unit)

1. **Done:** files touched, commands run.
2. **Evidence:** verbatim output (truncated, never paraphrased into success claims).
3. **Questions:** open D-numbers or new blockers.
4. **Next.**
