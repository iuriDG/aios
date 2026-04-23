#!/bin/bash
set -e

echo "Installing AIOS..."

# Create aios user for agent - no root needed
useradd -r -s /bin/false aios 2>/dev/null || true

# Create directories
mkdir -p /run/aios
mkdir -p /var/log/aios
mkdir -p /etc/aios
chown aios:aios /run/aios
chown aios:aios /var/log/aios

# Build Rust binaries
echo "Building helper and watchdog..."
cd helper && cargo build --release && cd ..
cd watchdog && cargo build --release && cd ..

# Install binaries
cp helper/target/release/aios-helper /usr/local/bin/
cp watchdog/target/release/aios-watchdog /usr/local/bin/
chmod 755 /usr/local/bin/aios-helper
chmod 755 /usr/local/bin/aios-watchdog

# Install Python agent
pip3 install psutil requests --break-system-packages
cp -r agent /opt/aios-agent
chmod +x /opt/aios-agent/main.py

# Install systemd units
cp systemd/*.service /etc/systemd/system/
systemctl daemon-reload

# Enable services in correct order
systemctl enable aios-helper
systemctl enable aios-watchdog
systemctl enable aios-agent

# Run first-run setup if no profile exists
if [ ! -f /opt/aios-agent/profiles/aios.db ]; then
    echo "Running first-run setup..."
    python3 scripts/first_run.py
fi

echo "AIOS installed - reboot to start"