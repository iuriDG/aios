import os

# Base paths
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR    = os.environ.get("AIOS_PROFILES_DIR", os.path.join(BASE_DIR, "..", "profiles"))
DB_PATH         = os.path.join(PROFILES_DIR, "aios.db")
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