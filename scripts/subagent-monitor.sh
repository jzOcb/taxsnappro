#!/bin/bash
# subagent-monitor.sh — Track sub-agent health
# Checks all active sub-agents, flags stuck/slow ones
# Called by heartbeat or cron every 5 minutes
#
# Output: writes alert to /tmp/subagent_stuck_alert.flag if any sub-agent is stuck
# "Stuck" = running for >5 minutes with 0 tokens (never started)
#         = running for >15 minutes total (taking too long)

set -euo pipefail

ALERT_FILE="/tmp/subagent_stuck_alert.flag"
ALERT_TEXT="/tmp/subagent_stuck_alert.txt"
STATE_FILE="/home/clawdbot/clawd/memory/subagent-tracker.json"

# Get current timestamp in seconds
NOW=$(date +%s)

# Query active sessions via clawdbot CLI or API
# We check for subagent sessions that are still active
SESSIONS_DIR="/home/clawdbot/.clawdbot/sessions"

# Find active sub-agent transcript files modified in last 30 minutes
ACTIVE_SUBAGENTS=()
if [[ -d "$SESSIONS_DIR" ]]; then
    while IFS= read -r -d '' file; do
        ACTIVE_SUBAGENTS+=("$file")
    done < <(find "$SESSIONS_DIR" -name "*.jsonl" -mmin -30 -print0 2>/dev/null)
fi

# Track spawn times in state file
if [[ ! -f "$STATE_FILE" ]]; then
    echo '{}' > "$STATE_FILE"
fi

# Check for sub-agents that were spawned but have no activity
# This is detected by: session exists, but totalTokens = 0 after >5 min
# We write spawn times when we spawn, and check elapsed time here

# Read tracker state
SPAWNED=$(cat "$STATE_FILE" 2>/dev/null || echo '{}')

STUCK_COUNT=0
STUCK_DETAILS=""

# Check each tracked sub-agent
for key in $(echo "$SPAWNED" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(k) for k in d]" 2>/dev/null); do
    SPAWN_TIME=$(echo "$SPAWNED" | python3 -c "import sys,json; print(json.load(sys.stdin).get('$key',{}).get('spawn_time',0))" 2>/dev/null)
    LABEL=$(echo "$SPAWNED" | python3 -c "import sys,json; print(json.load(sys.stdin).get('$key',{}).get('label','unknown'))" 2>/dev/null)
    STATUS=$(echo "$SPAWNED" | python3 -c "import sys,json; print(json.load(sys.stdin).get('$key',{}).get('status','running'))" 2>/dev/null)
    
    # Skip already completed ones
    if [[ "$STATUS" == "done" || "$STATUS" == "alerted" ]]; then
        continue
    fi
    
    ELAPSED=$((NOW - SPAWN_TIME))
    
    # Stuck: >5 min with no output file, or >15 min total
    if [[ "$ELAPSED" -gt 300 ]]; then
        OUTPUT_FILE=$(echo "$SPAWNED" | python3 -c "import sys,json; print(json.load(sys.stdin).get('$key',{}).get('output_file',''))" 2>/dev/null)
        
        if [[ -n "$OUTPUT_FILE" && ! -f "$OUTPUT_FILE" && "$ELAPSED" -gt 300 ]]; then
            STUCK_COUNT=$((STUCK_COUNT + 1))
            STUCK_DETAILS+="⚠️ Sub-agent '$LABEL' ($key): ${ELAPSED}秒无输出文件\n"
        elif [[ "$ELAPSED" -gt 900 ]]; then
            STUCK_COUNT=$((STUCK_COUNT + 1))
            STUCK_DETAILS+="⚠️ Sub-agent '$LABEL' ($key): 已运行${ELAPSED}秒（>15分钟）\n"
        fi
    fi
done

# Write alert if stuck
if [[ "$STUCK_COUNT" -gt 0 ]]; then
    echo -e "🚨 Sub-agent 卡住警报\n\n${STUCK_DETAILS}\n建议：检查session状态，考虑kill并重试" > "$ALERT_TEXT"
    touch "$ALERT_FILE"
    echo "ALERT: $STUCK_COUNT sub-agent(s) stuck"
    exit 1
else
    # Clean up old alerts
    rm -f "$ALERT_FILE" "$ALERT_TEXT" 2>/dev/null
    echo "OK: No stuck sub-agents"
    exit 0
fi
