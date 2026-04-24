#!/bin/bash
set -euo pipefail

echo "Updating AIOS..."

# Stop services
systemctl stop aios-agent
systemctl stop aios-watchdog

# Pull latest code
cd /opt/aios
git pull origin main

# Rebuild Rust binaries - subshells keep cwd safe if a build fails
(cd helper && cargo build --release)
(cd watchdog && cargo build --release)

# Install new binaries
cp helper/target/release/aios-helper /usr/local/bin/
cp watchdog/target/release/aios-watchdog /usr/local/bin/

# Update panic script
cp scripts/panic.sh /usr/local/bin/aios-panic.sh
chmod +x /usr/local/bin/aios-panic.sh

# Reload systemd in case service files changed
cp systemd/*.service /etc/systemd/system/
systemctl daemon-reload

# Restart services
systemctl start aios-watchdog
systemctl start aios-agent

echo "Update complete"
