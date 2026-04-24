# AIOS - AI Operating System Layer

An AI-driven process orchestration layer that sits on top of Linux.
Replaces traditional automation with context-aware decision making.
The kernel is never modified - the AI works entirely in userspace.

## Current status
- Agent running on Linux Mint with Ryzen 5 3500U / Radeon Vega Mobile
- Observer, context engine, decision engine all working
- Rule-based decisions active - LLM fallback when RAM is sufficient
- DRY_RUN = True - decisions logged but not yet executed

## What it does
- Detects what you are doing (gaming, coding, browsing, idle)
- Automatically optimises CPU, RAM, GPU and network for your current task
- Learns your app behaviour over time per binary
- Never touches critical system processes
- Falls back to rule-based decisions if LLM unavailable or RAM insufficient
- Fully local - no cloud calls during operation
- Internet used for model updates only

## Stack
- Agent: Python (prototype) - Rust rewrite planned
- Helper: Rust - privileged, minimal, auditable
- Watchdog: Rust - tamper detection and crash recovery
- LLM: Ollama - phi3:mini (local, offline)
- DB: SQLite - per-app learned profiles
- OS: Linux Mint 21+ or Ubuntu 24.04

## Requirements
- 8GB RAM minimum (6.7GB works with phi3:mini)
- Linux Mint 21+ or Ubuntu 24.04
- AMD or Nvidia GPU recommended
- 500GB SSD recommended

## Quick install
```bash
git clone https://github.com/iuriDG/aios.git
cd aios
cargo build --release -p aios-helper
cargo build --release -p aios-watchdog
sudo bash scripts/install.sh
```

## Project structure
aios/
agent/
config.py          - all configuration - single source of truth
observer.py        - system snapshot every 5s
context_engine.py  - activity classification with scoring
signal_combiner.py - manual vs prompt reply vs auto priority
decision_engine.py - action list generation per mode and gear
llm_interface.py   - Ollama bridge with RAM check and retry
profile_store.py   - SQLite profiles and audit log
ipc.py             - HMAC signed socket communication
power_manager.py   - battery and governor management
network_monitor.py - latency monitoring and throttling
gpu_observer.py    - AMD integrated, Nvidia, ROCm GPU stats
main.py            - main loop
helper/              - Rust privileged helper (root, minimal)
watchdog/            - Rust process monitor and tamper detection
profiles/            - SQLite database (created at runtime)
systemd/             - service unit files
scripts/             - install, update, rollback, uninstall, benchmark
tests/               - test suite
docs/                - architecture, install, config, troubleshooting

## How it works
Every 5-15 seconds the agent takes a system snapshot, classifies
the current activity, and produces a list of OS actions. Actions
are signed with HMAC and sent to a privileged helper process which
executes them after a second safety check. The LLM supplements
rule-based decisions when enough RAM is available.

## Three decision sources
1. Manual mode - user explicitly sets mode, highest priority
2. Prompt reply - user responds to AI question about mode change
3. Auto-detection - context engine classifies from system signals

## Three load gears
- Low  - score below 0.5 - full AI active, 5s loop
- Medium - score 0.5-0.8 - core loop only, 15s loop
- Heavy - score above 0.8 - observer only, 30s loop

## Safety
- DRY_RUN = True by default - nothing executes until you enable it
- Protected process list - AI can never touch kernel or system processes
- HMAC signed IPC - all requests between agent and helper are verified
- Watchdog monitors binary hashes - tamper detection locks the system
- Audit log is append-only - full history of every action taken
- Panic screen on crash - system restored to safe defaults automatically
- LLM RAM check - never attempts inference when system RAM is insufficient

## Configuration
All configuration is in agent/config.py - no hardcoded values anywhere else.
Key settings:
- DRY_RUN - set to False when ready to execute actions
- OLLAMA_MODEL - change model based on available RAM
- LOOP_CADENCE - adjust check frequency per gear
- PROCESS_LIMIT - how many processes to observe
- LLM_RAM_HEADROOM_GB - headroom required above LLM model size

## Useful commands
```bash
# Check all services
systemctl status aios-helper aios-watchdog aios-agent

# Watch live decisions
journalctl -u aios-agent -f

# Pause AIOS
touch /run/aios/paused

# Resume
rm /run/aios/paused

# Rollback last 20 actions
sudo bash scripts/rollback.sh 20

# Update
sudo bash scripts/update.sh

# Uninstall
sudo bash scripts/uninstall.sh
```

## Docs
- docs/architecture.md - full system design
- docs/install.md - step by step install guide
- docs/config.md - all configuration options
- docs/troubleshooting.md - common issues and fixes