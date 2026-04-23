#!/bin/bash
set -e

AUDIT_LOG="/var/log/aios/audit.log"
ENTRIES=${1:-20}

echo "Rolling back last $ENTRIES AIOS actions..."

# Pause agent first
touch /run/aios/paused

# Read last N entries from audit log and reverse renice and cgroup actions
tail -n $ENTRIES $AUDIT_LOG | while read line; do
    ACTION=$(echo $line | python3 -c "import sys,json; d=json.loads(sys.stdin.read().split(' ',1)[1]); print(d.get('action',''))" 2>/dev/null)
    TARGET=$(echo $line | python3 -c "import sys,json; d=json.loads(sys.stdin.read().split(' ',1)[1]); print(d.get('target',''))" 2>/dev/null)

    case $ACTION in
        renice)
            echo "Reversing renice on PID $TARGET"
            renice 0 -p $TARGET 2>/dev/null || true
            ;;
        cgroup_cpu_limit)
            echo "Removing cgroup limit on PID $TARGET"
            cgdelete -r cpu:aios/$TARGET 2>/dev/null || true
            ;;
        set_governor)
            echo "Resetting CPU governor to balanced"
            for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
                echo "balanced" > $cpu 2>/dev/null || true
            done
            ;;
        systemctl)
            echo "Skipping systemctl rollback - manual check required for $TARGET"
            ;;
    esac
done

# Resume agent
rm -f /run/aios/paused

echo "Rollback complete"