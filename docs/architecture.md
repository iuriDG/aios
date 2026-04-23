# AIOS Architecture

## Overview
AI-driven process orchestration layer that sits on top of Linux.
Replaces traditional automation with context-aware decision making.
The kernel is never modified - the AI works entirely in userspace.

## Boot order
1. Linux kernel
2. aios-helper (privileged)
3. aios-watchdog
4. aios-agent (unprivileged)
5. Display manager and desktop

## Layers top to bottom

### User control
- Manual mode selector - user picks mode explicitly
- Autonomy level - suggest / auto-tune / full control
- Per-app overrides - locked rules per binary, survive reboots

### Local AI core
- Context engine - classifies activity from system signals
- Signal combiner - manual wins, then prompt reply, then auto
- Profile store - per-binary per-mode learned patterns in SQLite
- Local LLM - Ollama running phi3:mini or mistral
- Decision engine - produces action list per mode and gear
- Mismatch detector - asks user when manual mode disagrees with observed activity
- Load arbiter - three gears based on bottleneck score across CPU RAM GPU

### Safety guard
- Protected process list - hardcoded, never touched
- Audit log - append-only, every action timestamped
- Block and re-plan - unsafe actions rejected before execution

### App profile layer
- Per-binary not per-type - Chrome and Firefox are separate
- Mode-aware - same app has different profile per mode
- Bootstrap defaults on first run, refined every session
- User overrides lock a signal permanently

### Action executor
- cgroups - CPU and RAM limits per process
- nice / ionice - scheduling priority
- systemd - start stop suspend services
- cpuset - pin processes to cores
- tc - network traffic shaping
- set_governor - CPU and AMD GPU power profile

### Resource pools
- CPU - 1 core pinned to AI loop, rest for user apps
- RAM - user apps first, LLM 4-8GB, agent under 200MB
- GPU - exclusive to user during use, AI only when idle

## Security model
- Agent runs as unprivileged user aios
- Helper runs as root with minimal Linux capabilities
- HMAC signed requests between agent and helper
- Watchdog checks binary hashes at startup
- Tamper detection shuts down and restores defaults
- Secret stored at /etc/aios/ipc.secret mode 600

## Key design decisions
- No cloud calls during operation - internet for model updates only
- DRY_RUN = True until manually verified on Linux
- Stability check - 3 consecutive matching snapshots before acting
- Transition drain - 3 cycles to gracefully switch between modes
- Hold last decision on gear spike - no thrashing