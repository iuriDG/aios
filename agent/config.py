import os
import psutil

TOTAL_RAM_GB = round(psutil.virtual_memory().total / 1e9, 1)
LLM_RESERVED_GB = float(os.environ.get("AIOS_LLM_RESERVED_GB", round(TOTAL_RAM_GB * 0.4, 1)))


# Base paths
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR    = os.environ.get("AIOS_PROFILES_DIR", os.path.join(BASE_DIR, "profiles"))
DB_PATH = os.path.join(PROFILES_DIR, "aios.db")
LOG_PATH        = os.environ.get("AIOS_LOG_PATH", "/var/log/aios/agent.log")
SOCKET_PATH     = os.environ.get("AIOS_SOCKET_PATH", "/run/aios/helper.sock")
READY_FILE      = "/run/aios/ready"
TAMPER_LOG      = "/var/log/aios/tamper.log"

# LLM
OLLAMA_URL      = os.environ.get("AIOS_OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL    = os.environ.get("AIOS_MODEL", "phi3:mini")

# Loop cadence seconds per gear
LOOP_CADENCE = {
    "low":    5,
    "medium": 15,
    "heavy":  30
}

# Load arbiter thresholds
GEAR_MEDIUM_THRESHOLD = 0.5
GEAR_HEAVY_THRESHOLD  = 0.8

# Mode detection
CONFIDENCE_THRESHOLD        = 50
MANUAL_MODE_EXPIRY_MINUTES  = 120
SUPPRESS_PROMPT_MINUTES     = 30
IDLE_THRESHOLD_MINUTES      = 5

# Safety
PROTECTED_PROCESSES = [
    "systemd", "init", "sshd", "networkmanager",
    "dbus", "kworker", "aios-agent", "aios-helper",
    "aios-watchdog", "kernel", "migration", "rcu"
]

# Dry run - set to False when ready to execute
DRY_RUN = True

# Protected processes
PROTECTED_PROCESSES = [
    "systemd", "init", "sshd", "networkmanager",
    "dbus", "kworker", "aios-agent", "aios-helper",
    "aios-watchdog", "kernel", "migration", "rcu"
]

# CPU nice levels
NICE_REALTIME   = -20
NICE_HIGH       = -10
NICE_NORMAL     =   0
NICE_LOW        =  10
NICE_BACKGROUND =  19

# Known process categories
KNOWN_GAMES = [
    "steam", "steamwebhelper", "gameoverlayui",
    "wine", "proton", "lutris", "heroic"
]

KNOWN_DEV = [
    "code", "vscodium", "nvim", "vim", "emacs",
    "gcc", "g++", "clang", "cargo", "rustc",
    "make", "cmake", "python3", "node", "docker",
    "java", "gradle", "maven"
]

KNOWN_BROWSER = [
    "firefox", "chrome", "chromium", "brave",
    "opera", "vivaldi", "edge"
]

COMPILERS = [
    "gcc", "g++", "clang", "rustc", "cargo",
    "make", "cmake", "gradle", "maven", "go"
]

# Paths
IPC_SECRET_PATH     = "/etc/aios/ipc.secret"
OBSERVER_LOG        = "/var/log/aios/observer.log"
PAUSED_FILE         = "/run/aios/paused"
PROMPT_FILE         = "/run/aios/prompt.txt"
PROMPT_REPLY_FILE   = "/run/aios/prompt_reply.txt"

# Process observer
PROCESS_PID_FILTER  = 10
PROCESS_LIMIT       = 20

# LLM
LLM_RAM_HEADROOM_GB = 0.5
LLM_MAX_RETRIES     = 3
LLM_MAX_TOKENS      = 512
LLM_TEMPERATURE     = 0.1

# Network monitor
NETWORK_PING_INTERVAL_SECS = 30
NETWORK_PING_COUNT         = 5

# Profile store
AUDIT_LOG_RETENTION_DAYS = 30

# Signal combiner
PROMPT_REPLY_EXPIRY_HOURS = 4

# Watchdog
WATCHDOG_CHECK_INTERVAL_SECS = 5
WATCHDOG_LOG_TAIL_LINES      = 500

NOISE_PROCESSES = ["update", "sync", "backup", "index", "tracker"]