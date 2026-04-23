#!/bin/bash
# Called by watchdog on unrecoverable crash
# Displays panic screen and restores defaults

ERROR_MSG=${1:-"Unknown error"}
LOG_FILE="/var/log/aios/panic.log"
TIMESTAMP=$(date +"%Y-%m-%dT%H:%M:%S")

# Log it
echo "$TIMESTAMP PANIC: $ERROR_MSG" >> $LOG_FILE

# Restore CPU governor
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "balanced" > $cpu 2>/dev/null
done

# Remove cgroups
cgdelete -r cpu:aios 2>/dev/null

# Remove ready file
rm -f /run/aios/ready

# Clear terminal and show panic screen
clear
echo ""
echo "============================================="
echo "           AIOS - SYSTEM ERROR              "
echo "============================================="
echo ""
echo "  The AI layer has encountered a fatal error"
echo "  and has been safely stopped."
echo ""
echo "  Error: $ERROR_MSG"
echo "  Time:  $TIMESTAMP"
echo "  Log:   $LOG_FILE"
echo ""
echo "  System defaults have been restored."
echo "  Your applications and data are safe."
echo ""
echo "  To restart AIOS:"
echo "    sudo systemctl start aios-helper"
echo "    sudo systemctl start aios-watchdog"
echo "    sudo systemctl start aios-agent"
echo ""
echo "  To boot without AIOS:"
echo "    sudo systemctl disable aios-agent"
echo "    reboot"
echo ""
echo "============================================="
echo ""