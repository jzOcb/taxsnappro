#!/bin/bash
# subagent-spawn-wrapper.sh — Register sub-agent spawn for tracking
# Called by main agent BEFORE spawning a sub-agent
# Records spawn time, label, expected output file in tracker state
#
# Usage: bash scripts/subagent-spawn-wrapper.sh <session_key> <label> <output_file>

set -euo pipefail

SESSION_KEY="${1:-}"
LABEL="${2:-unknown}"
OUTPUT_FILE="${3:-}"

STATE_FILE="/home/clawdbot/clawd/memory/subagent-tracker.json"
NOW=$(date +%s)

if [[ -z "$SESSION_KEY" ]]; then
    echo "ERROR: session_key required"
    exit 1
fi

# Initialize state file if needed
if [[ ! -f "$STATE_FILE" ]]; then
    echo '{}' > "$STATE_FILE"
fi

# Add entry
python3 -c "
import json, sys
state = json.load(open('$STATE_FILE'))
state['$SESSION_KEY'] = {
    'label': '$LABEL',
    'spawn_time': $NOW,
    'output_file': '$OUTPUT_FILE',
    'status': 'running'
}
json.dump(state, open('$STATE_FILE', 'w'), indent=2)
print(f'Registered: $LABEL ($SESSION_KEY) at {$NOW}')
print(f'Expected output: $OUTPUT_FILE')
print(f'Will alert if stuck >5min (no output) or >15min (total)')
"
