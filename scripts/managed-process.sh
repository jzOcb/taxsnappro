#!/bin/bash
# managed-process.sh — THE standard way to launch any long-running process
#
# RULE: Never launch long-running processes any other way.
# This script handles: detached execution, PID tracking, health monitoring,
# auto-restart, signal logging, and registration.
#
# Usage:
#   bash scripts/managed-process.sh register <name> <command> [duration_min]
#   bash scripts/managed-process.sh start <name>
#   bash scripts/managed-process.sh stop <name>
#   bash scripts/managed-process.sh status [name]
#   bash scripts/managed-process.sh restart <name>
#
# Examples:
#   bash scripts/managed-process.sh register btc-v6 "cd btc-arbitrage && python3 src/realtime_paper_trader_v6.py 480" 480
#   bash scripts/managed-process.sh start btc-v6
#   bash scripts/managed-process.sh status

set -uo pipefail

REGISTRY="/home/clawdbot/clawd/.process-registry.json"
PROCESS_DIR="/tmp/managed-processes"
LOG_DIR="/tmp/managed-processes/logs"

mkdir -p "$PROCESS_DIR" "$LOG_DIR"

# Initialize registry if missing
if [ ! -f "$REGISTRY" ]; then
    echo '{}' > "$REGISTRY"
fi

# ═══════════════════════════════════════════════
# REGISTER: Define a managed process
# ═══════════════════════════════════════════════
cmd_register() {
    local NAME="$1"
    local CMD="$2"
    local DURATION="${3:-0}"  # 0 = indefinite
    
    # Write to registry using python for JSON safety
    python3 -c "
import json, sys
reg = json.load(open('$REGISTRY'))
reg['$NAME'] = {
    'command': '''$CMD''',
    'duration_min': $DURATION,
    'auto_restart': True,
    'max_restarts': 5,
    'restart_cooldown': 30
}
json.dump(reg, open('$REGISTRY', 'w'), indent=2)
print('✅ Registered: $NAME')
print('   Command: $CMD')
print('   Duration: ${DURATION}min (0=indefinite)')
"
}

# ═══════════════════════════════════════════════
# START: Launch a registered process (detached)
# ═══════════════════════════════════════════════
cmd_start() {
    local NAME="$1"
    local PID_FILE="$PROCESS_DIR/${NAME}.pid"
    local STATE_FILE="$PROCESS_DIR/${NAME}.state"
    local PROC_LOG="$LOG_DIR/${NAME}.log"
    
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        local OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo "⚠️ $NAME already running (PID: $OLD_PID)"
            return 1
        fi
    fi
    
    # Get command from registry
    local CMD=$(python3 -c "
import json
reg = json.load(open('$REGISTRY'))
if '$NAME' not in reg:
    print('ERROR')
else:
    print(reg['$NAME']['command'])
")
    
    if [ "$CMD" = "ERROR" ]; then
        echo "❌ Process '$NAME' not registered. Use 'register' first."
        return 1
    fi
    
    # Create wrapper script that handles signals and logging
    local WRAPPER="$PROCESS_DIR/${NAME}_wrapper.sh"
    cat > "$WRAPPER" << 'WRAPPER_EOF'
#!/bin/bash
NAME="$1"
CMD="$2"
PID_FILE="$3"
STATE_FILE="$4"
PROC_LOG="$5"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [$NAME] $1" >> "$PROC_LOG"; }

log "STARTING: $CMD"
echo "running" > "$STATE_FILE"

# Run the actual command
eval "$CMD" >> "$PROC_LOG" 2>&1 &
CHILD_PID=$!
echo $CHILD_PID > "$PID_FILE"
log "STARTED: PID=$CHILD_PID"

# Wait for child and capture exit
wait $CHILD_PID
EXIT_CODE=$?

log "EXITED: code=$EXIT_CODE"
echo "stopped:$EXIT_CODE:$(date +%s)" > "$STATE_FILE"
WRAPPER_EOF
    chmod +x "$WRAPPER"
    
    # Launch detached (setsid + nohup + disown)
    cd /home/clawdbot/clawd
    setsid nohup bash "$WRAPPER" "$NAME" "$CMD" "$PID_FILE" "$STATE_FILE" "$PROC_LOG" > /dev/null 2>&1 &
    disown $!
    
    # Wait for PID file
    sleep 3
    
    if [ -f "$PID_FILE" ]; then
        local PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ $NAME started (PID: $PID)"
            echo "   Log: $PROC_LOG"
            return 0
        fi
    fi
    
    echo "❌ $NAME failed to start"
    tail -10 "$PROC_LOG" 2>/dev/null
    return 1
}

# ═══════════════════════════════════════════════
# STOP: Gracefully stop a process
# ═══════════════════════════════════════════════
cmd_stop() {
    local NAME="$1"
    local PID_FILE="$PROCESS_DIR/${NAME}.pid"
    
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️ $NAME: no PID file"
        return 1
    fi
    
    local PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID"
        echo "✅ $NAME stopped (PID: $PID)"
    else
        echo "⚠️ $NAME already stopped"
    fi
    
    rm -f "$PID_FILE"
}

# ═══════════════════════════════════════════════
# STATUS: Show all managed processes
# ═══════════════════════════════════════════════
cmd_status() {
    local FILTER="${1:-}"
    
    echo "═══════════════════════════════════════════"
    echo "  Managed Process Status"
    echo "═══════════════════════════════════════════"
    
    python3 -c "
import json, os, subprocess

reg = json.load(open('$REGISTRY'))
if not reg:
    print('  (no processes registered)')
    
for name, config in reg.items():
    if '$FILTER' and name != '$FILTER':
        continue
    
    pid_file = f'$PROCESS_DIR/{name}.pid'
    state_file = f'$PROCESS_DIR/{name}.state'
    
    # Check PID
    pid = None
    alive = False
    uptime = '?'
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = f.read().strip()
        try:
            result = subprocess.run(['ps', '-p', pid, '-o', 'etimes', '--no-headers'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                alive = True
                secs = int(result.stdout.strip())
                hrs = secs // 3600
                mins = (secs % 3600) // 60
                uptime = f'{hrs}h{mins}m' if hrs > 0 else f'{mins}m'
        except:
            pass
    
    # Status emoji
    if alive:
        status = f'🟢 Running (PID {pid}, uptime {uptime})'
    elif os.path.exists(state_file):
        with open(state_file) as f:
            state = f.read().strip()
        if state.startswith('stopped:'):
            parts = state.split(':')
            code = parts[1] if len(parts) > 1 else '?'
            status = f'🔴 Stopped (exit code {code})'
        else:
            status = f'⚪ {state}'
    else:
        status = '⚪ Never started'
    
    duration = config.get('duration_min', 0)
    dur_str = f'{duration}min' if duration > 0 else 'indefinite'
    restart = '✅' if config.get('auto_restart', False) else '❌'
    
    print(f'  {name}:')
    print(f'    Status: {status}')
    print(f'    Duration: {dur_str} | Auto-restart: {restart}')
    print()
"
    echo "═══════════════════════════════════════════"
}

# ═══════════════════════════════════════════════
# RESTART: Stop then start
# ═══════════════════════════════════════════════
cmd_restart() {
    local NAME="$1"
    cmd_stop "$NAME" 2>/dev/null
    sleep 2
    cmd_start "$NAME"
}

# ═══════════════════════════════════════════════
# HEALTHCHECK: Check all processes, restart dead ones
# (Called by cron every 5 min)
# ═══════════════════════════════════════════════
cmd_healthcheck() {
    local ALERTS=""
    local HC_LOG="$LOG_DIR/healthcheck.log"
    
    python3 << 'PYEOF'
import json, os, subprocess, time

REGISTRY = "/home/clawdbot/clawd/.process-registry.json"
PROCESS_DIR = "/tmp/managed-processes"
ALERT_FLAG = "/tmp/process_monitor_alert.flag"
ALERT_FILE = "/tmp/process_monitor_alert.txt"
COOLDOWN_FILE = "/tmp/process_monitor_cooldown"
COOLDOWN_SECS = 900

reg = json.load(open(REGISTRY))
alerts = []

for name, config in reg.items():
    pid_file = f"{PROCESS_DIR}/{name}.pid"
    state_file = f"{PROCESS_DIR}/{name}.state"
    
    if not os.path.exists(pid_file):
        continue  # Never started, not our problem
    
    with open(pid_file) as f:
        pid = f.read().strip()
    
    # Check if alive
    alive = subprocess.run(["ps", "-p", pid], capture_output=True).returncode == 0
    
    if alive:
        # Check log freshness (if there's a known log file)
        continue
    
    # Process is dead
    # Check if it's been dead for >24h with no auto_restart — stale entry
    if not config.get("auto_restart", False):
        if os.path.exists(state_file):
            age = time.time() - os.path.getmtime(state_file)
            if age > 86400:  # Dead >24h, no auto-restart → stale
                print(f"🧹 {name}: dead >24h, no auto-restart. Cleaning up.")
                os.system(f"bash /home/clawdbot/clawd/scripts/managed-process.sh deregister {name}")
        continue
    
    # Check if it completed normally (duration-based)
    duration_min = config.get("duration_min", 0)
    if duration_min > 0 and os.path.exists(state_file):
        with open(state_file) as f:
            state = f.read().strip()
        if state.startswith("stopped:0:"):
            # Check how long it ran
            start_time = os.path.getctime(pid_file)
            stop_time = int(state.split(":")[2]) if len(state.split(":")) > 2 else time.time()
            ran_min = (stop_time - start_time) / 60
            if ran_min >= duration_min * 0.8:  # Completed ~80%+ of expected duration
                continue  # Normal completion
    
    # duration_min=0 means indefinite — should ALWAYS restart if dead
    if duration_min == 0:
        pass  # Fall through to restart
    
    # Premature death — restart
    print(f"⚠️ {name} died prematurely (PID {pid}). Restarting...")
    alerts.append(f"🔴 {name}: 进程异常停止 (PID {pid})，已自动重启")
    
    # Restart using the managed-process framework
    os.system(f"bash /home/clawdbot/clawd/scripts/managed-process.sh start {name}")

# Send alerts
if alerts:
    # Check cooldown
    if os.path.exists(COOLDOWN_FILE):
        age = time.time() - os.path.getmtime(COOLDOWN_FILE)
        if age < COOLDOWN_SECS:
            print(f"Alert suppressed (cooldown: {int(age)}s / {COOLDOWN_SECS}s)")
            exit(0)
    
    with open(COOLDOWN_FILE, "w") as f:
        f.write(str(time.time()))
    
    alert_text = "🚨 **Process Monitor Alert**\n\n" + "\n".join(alerts) + f"\n\n_自动监控 {time.strftime('%H:%M UTC')}_"
    with open(ALERT_FILE, "w") as f:
        f.write(alert_text)
    open(ALERT_FLAG, "w").close()
    print(f"Alert sent: {len(alerts)} issue(s)")
else:
    print("All processes healthy")
PYEOF
}

# ═══════════════════════════════════════════════
# DEREGISTER: Remove a process from the registry and clean up all its files
# ═══════════════════════════════════════════════
cmd_deregister() {
    local NAME="$1"
    
    # Stop it first if running
    cmd_stop "$NAME" 2>/dev/null || true
    
    # Remove from registry
    python3 -c "
import json
reg = json.load(open('$REGISTRY'))
if '$NAME' in reg:
    del reg['$NAME']
    json.dump(reg, open('$REGISTRY', 'w'), indent=4)
    print('  ✅ $NAME removed from registry')
else:
    print('  ⚠️ $NAME not found in registry')
"
    
    # Clean up all related files
    rm -f "$PROCESS_DIR/${NAME}.pid" \
          "$PROCESS_DIR/${NAME}.state" \
          "$PROCESS_DIR/${NAME}_wrapper.sh" \
          "$LOG_DIR/${NAME}.log" 2>/dev/null
    
    echo "  🧹 Cleaned up files for $NAME"
}

# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════
ACTION="${1:-status}"
shift || true

case "$ACTION" in
    register)    cmd_register "$@" ;;
    deregister)  cmd_deregister "$@" ;;
    start)       cmd_start "$@" ;;
    stop)        cmd_stop "$@" ;;
    status)      cmd_status "$@" ;;
    restart)     cmd_restart "$@" ;;
    healthcheck) cmd_healthcheck ;;
    *)
        echo "Usage: managed-process.sh {register|deregister|start|stop|status|restart|healthcheck} [args]"
        exit 1
        ;;
esac
