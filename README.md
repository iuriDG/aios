# AIOS - AI Operating System Layer

An AI-driven process orchestration layer that sits on top of Linux.
Replaces traditional automation with context-aware decision making.
The kernel is never modified - the AI works entirely in userspace.

## What it does
- Detects what you are doing (gaming, coding, browsing, idle)
- Automatically optimises CPU, RAM, GPU and network for your current task
- Learns your app behaviour over time per binary
- Never touches critical system processes
- Falls back to rule-based decisions if LLM is unavailable
- Fully local - no cloud calls during operation

## Stack
- Agent: Python (prototype) - Rust rewrite planned
- Helper: Rust - privileged, minimal, auditable
- Watchdog: Rust - tamper detection and crash recovery
- LLM: Ollama - phi3:mini or mistral (local, offline)
- DB: SQLite - per-app learned profiles
- OS: Linux Mint 21+ or Ubuntu 24.04

## Requirements
- 8GB RAM minimum
- Linux Mint 21+ or Ubuntu 24.04
- AMD or Nvidia GPU recommended
- 500GB SSD recommended

## Quick install
```bash
git clone https://github.com/iuriDG/aios.git
cd aios
sudo bash scripts/install.sh
```

## Project structure
aios/
agent/
config.py          - all configuration
observer.py        - system snapshot every 5s
context_engine.py  - activity classification
signal_combiner.py - manual vs auto priority
decision_engine.py - action list generation
llm_interface.py   - Ollama bridge
profile_store.py   - SQLite profiles and audit log
ipc.py             - signed socket communication
power_manager.py   - battery and governor management
network_monitor.py - latency monitoring and throttling
gpu_observer.py    - AMD, Nvidia, integrated GPU stats
main.py            - main loop
helper/              - Rust privileged helper
watchdog/            - Rust process monitor
profiles/            - SQLite database (created at runtime)
systemd/             - service unit files
scripts/             - install, update, rollback, uninstall
tests/               - test suite
docs/                - architecture, install, config, troubleshooting

## Build phases
- Phase 1: System observer
- Phase 2: Privileged helper
- Phase 3: Watchdog
- Phase 4: Boot sequence
- Phase 5: First-run quiz
- Phase 6: LLM integration
- Phase 7: Context engine
- Phase 8: Network profiler
- Phase 9: Performance optimiser
- Phase 10: Power management
- Phase 11: Profile learning
- Phase 12: Rust agent rewrite

## Safety
- DRY_RUN = True by default - nothing executes until you enable it
- Protected process list - AI can never touch kernel or system processes
- HMAC signed IPC - requests between agent and helper are verified
- Watchdog monitors binary hashes - tamper detection locks the system
- Audit log is append-only - full history of every action taken
- Panic screen on crash - system restored to safe defaults automatically

## Useful commands
```bash
# Pause AIOS
touch /run/aios/paused

# Resume
rm /run/aios/paused

# Check logs
journalctl -u aios-agent -f

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