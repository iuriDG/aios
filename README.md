cat > README.md << EOF
# AIOS - AI Operating System Layer

An AI-driven process orchestration layer that sits on top of Linux,
replacing traditional automation with context-aware decision making.

## Architecture
- agent/ - AI agent (Python prototype, Rust target)
- helper/ - Privileged helper process (Rust)
- watchdog/ - Process monitor and crash recovery (Rust)
- profiles/ - Per-app learned behaviour (SQLite)
- systemd/ - Service unit files
- scripts/ - Install and first-run setup

## Stack
- Agent: Python → Rust
- Helper: Rust
- Watchdog: Rust
- LLM: Ollama (phi3:mini / mistral)
- DB: SQLite

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
EOF