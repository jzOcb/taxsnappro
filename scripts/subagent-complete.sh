#!/bin/bash
# subagent-complete.sh — Mark sub-agent as done in tracker
# Called by main agent AFTER reading and delivering sub-agent output
#
# Usage: bash scripts/subagent-complete.sh <session_key>

set -euo pipefail

SESSION_KEY="${1:-}"
STATE_FILE="/home/clawdbot/clawd/memory/subagent-tracker.json"

if [[ -z "$SESSION_KEY" ]]; then
    echo "ERROR: session_key required"
    exit 1
fi

if [[ ! -f "$STATE_FILE" ]]; then
    echo "No tracker state found"
    exit 0
fi

python3 -c "
import json
state = json.load(open('$STATE_FILE'))
if '$SESSION_KEY' in state:
    state['$SESSION_KEY']['status'] = 'done'
    state['$SESSION_KEY']['completed_at'] = $(date +%s)
    json.dump(state, open('$STATE_FILE', 'w'), indent=2)
    print(f'Marked done: {state[\"$SESSION_KEY\"][\"label\"]}')
else:
    print(f'Session not found in tracker: $SESSION_KEY')
"
