#!/bin/bash
set -euo pipefail

AUDIT_LOG="/var/log/aios/audit.log"
ENTRIES="${1:-20}"

# Validate ENTRIES is a positive integer
if ! [[ "$ENTRIES" =~ ^[0-9]+$ ]] || [ "$ENTRIES" -eq 0 ]; then
    echo "Usage: $0 [number_of_entries]" >&2
    exit 1
fi

echo "Rolling back last $ENTRIES AIOS actions..."

# Pause agent first
touch /run/aios/paused

# Read last N entries from audit log and reverse renice and cgroup actions
tail -n "$ENTRIES" "$AUDIT_LOG" | while IFS= read -r line; do
    ACTION=$(echo "$line" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read().split(' ', 1)[1])
    print(d.get('action', ''))
except Exception:
    print('')
" 2>/dev/null)

    TARGET=$(echo "$line" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read().split(' ', 1)[1])
    print(d.get('target', ''))
except Exception:
    print('')
" 2>/dev/null)

    case "$ACTION" in
        renice)
            # Validate TARGET is a numeric PID before passing to renice
            if [[ "$TARGET" =~ ^[0-9]+$ ]]; then
                echo "Reversing renice on PID $TARGET"
                renice 0 -p "$TARGET" 2>/dev/null || true
            else
                echo "Skipping renice - invalid target: $TARGET" >&2
            fi
            ;;
        cgroup_cpu_limit)
            # Validate TARGET is numeric before using in cgroup path
            if [[ "$TARGET" =~ ^[0-9]+$ ]]; then
                echo "Removing cgroup limit on PID $TARGET"
                cgdelete -r "cpu:aios/$TARGET" 2>/dev/null || true
            else
                echo "Skipping cgroup - invalid target: $TARGET" >&2
            fi
            ;;
        set_governor)
            echo "Resetting CPU governor to balanced"
            for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
                [ -f "$cpu" ] && echo "balanced" > "$cpu" 2>/dev/null || true
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
