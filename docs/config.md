# AIOS Configuration Reference

All configuration is in `agent/config.py`.
Edit this file to change behaviour.
Restart the agent after any change:
`sudo systemctl restart aios-agent`

## Paths
| Key | Default | Description |
|---|---|---|
| BASE_DIR | agent/ | Base directory of agent |
| PROFILES_DIR | profiles/ | SQLite database location |
| DB_PATH | profiles/aios.db | Full database path |
| LOG_PATH | /var/log/aios/agent.log | Agent log file |
| SOCKET_PATH | /run/aios/helper.sock | IPC socket path |
| READY_FILE | /run/aios/ready | Written when agent is ready |
| TAMPER_LOG | /var/log/aios/tamper.log | Tamper detection log |

## LLM
| Key | Default | Description |
|---|---|---|
| OLLAMA_URL | http://localhost:11434/api/generate | Ollama API endpoint |
| OLLAMA_MODEL | phi3:mini | Model to use for decisions |

Change model to mistral if you have 16GB+ RAM for better decisions.

## Loop cadence
| Key | Default | Description |
|---|---|---|
| LOOP_CADENCE low | 5s | Check interval when system is idle |
| LOOP_CADENCE medium | 15s | Check interval under moderate load |
| LOOP_CADENCE heavy | 30s | Check interval under heavy load |

## Load arbiter thresholds
| Key | Default | Description |
|---|---|---|
| GEAR_MEDIUM_THRESHOLD | 0.5 | Score above this = medium gear |
| GEAR_HEAVY_THRESHOLD | 0.8 | Score above this = heavy gear |

## Mode detection
| Key | Default | Description |
|---|---|---|
| CONFIDENCE_THRESHOLD | 50 | Minimum score before acting |
| MANUAL_MODE_EXPIRY_MINUTES | 120 | How long manual mode stays active |
| SUPPRESS_PROMPT_MINUTES | 30 | How long to suppress prompt after dismiss |
| IDLE_THRESHOLD_MINUTES | 5 | Minutes of no input before idle mode |

## Safety
| Key | Default | Description |
|---|---|---|
| DRY_RUN | True | If True log actions but never execute |
| PROTECTED_PROCESSES | see config | Processes the AI can never touch |

## CPU nice levels
| Key | Value | Description |
|---|---|---|
| NICE_REALTIME | -20 | Highest priority - games |
| NICE_HIGH | -10 | High priority - compilers |
| NICE_NORMAL | 0 | Default priority |
| NICE_LOW | 10 | Low priority - background |
| NICE_BACKGROUND | 19 | Lowest priority - noise |

## Hardware weights
Set automatically by benchmark.py at first run.
| Key | Description |
|---|---|
| hw_weight_cpu | CPU bottleneck weight |
| hw_weight_ram | RAM bottleneck weight |
| hw_weight_gpu | GPU bottleneck weight |
| hw_cpu_inference_secs | CPU inference benchmark result |
| hw_gpu_inference_secs | GPU inference benchmark result |

## Known process categories
All lists are in config.py and can be extended.
| Key | Description |
|---|---|
| KNOWN_GAMES | Process names classified as gaming |
| KNOWN_DEV | Process names classified as development |
| KNOWN_BROWSER | Process names classified as browsing |
| COMPILERS | Process names that trigger dev mode |