# AIOS Troubleshooting

## Agent won't start

**Check service status**
```bash
systemctl status aios-agent
journalctl -u aios-agent -n 50
```

**Check helper is running first**
```bash
systemctl status aios-helper
```
Agent depends on helper - if helper is down agent won't start.

**Check socket exists**
```bash
ls -la /run/aios/helper.sock
```

**Check ready file**
```bash
cat /run/aios/ready
```

---

## Tamper detection triggered

System will lock and require manual restart.

**Check tamper log**
```bash
cat /var/log/aios/tamper.log
```

**Restart manually after verifying binaries**
```bash
sudo systemctl start aios-helper
sudo systemctl start aios-watchdog
sudo systemctl start aios-agent
```

---

## LLM not working

**Check Ollama is running**
```bash
systemctl status ollama
```

**Check model is pulled**
```bash
ollama list
```

**Pull model if missing**
```bash
ollama pull phi3:mini
```

Agent falls back to rule-based decisions if Ollama is unavailable.
System still works without LLM.

---

## Wrong mode detected

**Set manual mode**
```bash
# Write to user profile directly
python3 -c "
import sys; sys.path.append('agent')
from profile_store import set_user_pref
from datetime import datetime
set_user_pref('manual_mode', 'gaming')
set_user_pref('manual_mode_set_at', datetime.now().isoformat())
"
```

**Check context engine scores**
```bash
python3 -c "
import sys; sys.path.append('agent')
from observer import observe
from context_engine import classify
print(classify(observe()))
"
```

---

## System feels slow after AIOS installed

**Check AI is not using too many resources**
```bash
htop
```
Look for aios-agent process - should be under 5% CPU.

**Check gear**
```bash
tail -f /var/log/aios/audit.log
```
If always in heavy gear the thresholds may need tuning in config.py.

**Pause AIOS temporarily**
```bash
touch /run/aios/paused
```

---

## Actions not executing

**Check DRY_RUN is False**
```bash
grep DRY_RUN agent/config.py
```

**Check helper permissions**
```bash
ls -la /usr/local/bin/aios-helper
```
Should be owned by root.

**Test helper manually**
```bash
echo '{"action":"renice","pid":$$,"priority":0,"signature":"test"}' | \
  socat - UNIX-CONNECT:/run/aios/helper.sock
```

---

## GPU not detected

**AMD - check ROCm**
```bash
rocm-smi
```

**Check sysfs fallback**
```bash
cat /sys/class/drm/card0/device/gpu_busy_percent
```

**If no GPU detected**
AI falls back to CPU-only mode automatically.
Set hw_weight_gpu to 0 in profile store:
```bash
python3 -c "
import sys; sys.path.append('agent')
from profile_store import set_user_pref
set_user_pref('hw_weight_gpu', '0')
"
```

---

## Rollback needed

```bash
sudo bash scripts/rollback.sh 20
```

---

## Full reset

```bash
# Pause
touch /run/aios/paused

# Reset CPU governor
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "balanced" | sudo tee $cpu
done

# Remove cgroups
sudo cgdelete -r cpu:aios

# Clear profile database
rm profiles/aios.db

# Resume
rm /run/aios/paused
sudo systemctl restart aios-agent
```

---

## Uninstall completely

```bash
sudo bash scripts/uninstall.sh
```