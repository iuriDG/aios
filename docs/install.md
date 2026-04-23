# AIOS Installation Guide

## Requirements
- Linux Mint 21+ or Ubuntu 24.04
- 8GB RAM minimum
- AMD or Nvidia GPU recommended
- 500GB SSD recommended
- Internet connection for initial setup

## Step 1 - Clone the repo
```bash
git clone https://github.com/yourusername/aios.git
cd aios
```

## Step 2 - Install system dependencies
```bash
sudo apt update && sudo apt install -y \
  build-essential git curl python3 python3-pip \
  pkg-config libssl-dev htop sysstat \
  lm-sensors cgroup-tools \
  linux-tools-generic notify-send
```

## Step 3 - Install Rust
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

## Step 4 - Install Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3:mini
```

## Step 5 - Install AMD GPU tools (AMD only)
```bash
sudo apt install rocm-smi
```

## Step 6 - Run installer
```bash
sudo bash scripts/install.sh
```

## Step 7 - Verify installation
```bash
systemctl status aios-helper
systemctl status aios-watchdog
systemctl status aios-agent
```

## Step 8 - Check logs
```bash
journalctl -u aios-agent -f
```

## Step 9 - Test dry run
```bash
# DRY_RUN is True by default
# Check logs to verify decisions look sane
tail -f /var/log/aios/audit.log
```

## Step 10 - Enable execution
Once decisions look correct open agent/config.py and set:
```python
DRY_RUN = False
```
Then restart the agent:
```bash
sudo systemctl restart aios-agent
```

## Verify hardware benchmark ran
```bash
python3 scripts/benchmark.py
```

## Verify network profile
```bash
python3 scripts/network_profile.py
```

## Useful commands
```bash
# Pause AIOS without stopping
touch /run/aios/paused

# Resume
rm /run/aios/paused

# Rollback last 20 actions
sudo bash scripts/rollback.sh 20

# Update AIOS
sudo bash scripts/update.sh

# Uninstall
sudo bash scripts/uninstall.sh
```