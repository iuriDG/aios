#!/bin/bash
set -euo pipefail

echo "Uninstalling AIOS..."

# Pause first
touch /run/aios/paused 2>/dev/null || true

# Stop and disable services
systemctl stop aios-agent 2>/dev/null || true
systemctl stop aios-watchdog 2>/dev/null || true
systemctl stop aios-helper 2>/dev/null || true
systemctl disable aios-agent 2>/dev/null || true
systemctl disable aios-watchdog 2>/dev/null || true
systemctl disable aios-helper 2>/dev/null || true

# Remove service files
rm -f /etc/systemd/system/aios-agent.service
rm -f /etc/systemd/system/aios-watchdog.service
rm -f /etc/systemd/system/aios-helper.service
systemctl daemon-reload

# Remove binaries
rm -f /usr/local/bin/aios-helper
rm -f /usr/local/bin/aios-watchdog
rm -f /usr/local/bin/aios-panic.sh

# Remove agent
rm -rf /opt/aios-agent

# Remove runtime files
rm -rf /run/aios

# Remove secret
rm -f /etc/aios/ipc.secret
rmdir /etc/aios 2>/dev/null || true

# Restore system defaults - guard against missing cpufreq paths (e.g. no scaling driver)
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [ -f "$cpu" ] && echo "balanced" > "$cpu" 2>/dev/null || true
done
cgdelete -r cpu:aios 2>/dev/null || true

# Quote the command substitution to handle interface names safely;
# skip tc entirely if we can't determine the interface
DEFAULT_IFACE=$(ip route show default 2>/dev/null | awk '/dev/ {print $5; exit}')
if [ -n "$DEFAULT_IFACE" ]; then
    tc qdisc del dev "$DEFAULT_IFACE" root 2>/dev/null || true
fi

# Remove aios user
userdel aios 2>/dev/null || true

# Ask about logs and profiles
read -p "Remove logs and profiles? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /var/log/aios
    echo "Logs removed"
else
    echo "Logs kept at /var/log/aios"
fi

echo "AIOS uninstalled - system restored to defaults"
