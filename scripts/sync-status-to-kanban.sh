#!/bin/bash
# sync-status-to-kanban.sh — Sync STATUS.md from project dirs to kanban board
# Scans all project directories for STATUS.md, creates/updates kanban task cards

set -uo pipefail

# Auto-detect workspace
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(dirname "$SCRIPT_DIR")"
KANBAN_DIR="$WORKSPACE/kanban-tasks"
LOG_FILE="$WORKSPACE/memory/kanban-sync.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" >> "$LOG_FILE"
}

# Lane names (English)
LANES=("TODO" "In Progress" "Paused" "Done")

# Ensure lane dirs exist
for lane in "${LANES[@]}"; do
    mkdir -p "$KANBAN_DIR/$lane"
done

# Map Chinese status to English lane
status_to_lane() {
    case "$1" in
        *进行中*|*"In Progress"*) echo "In Progress" ;;
        *暂停*|*Paused*|*卡住*|*Blocked*) echo "Paused" ;;
        *完成*|*Done*|*Completed*) echo "Done" ;;
        *规划中*|*TODO*|*Planning*) echo "TODO" ;;
        *) echo "TODO" ;;
    esac
}

CHANGED=0

# Scan project dirs for STATUS.md
for status_file in "$WORKSPACE"/*/STATUS.md; do
    [ -f "$status_file" ] || continue
    
    project_dir="$(dirname "$status_file")"
    project_name="$(basename "$project_dir")"
    
    # Parse status
    current_status=$(grep -i "## 当前状态\|## Current Status" "$status_file" | head -1 | sed 's/.*: *//')
    last_action=$(grep -A1 "## 最后做了什么\|## Last Action" "$status_file" | tail -1 | sed 's/^- //')
    next_step=$(grep -A1 "## 下一步\|## Next Step" "$status_file" | tail -1 | sed 's/^- //')
    last_updated=$(grep "Last updated:" "$status_file" | head -1 | sed 's/Last updated: *//')
    
    lane=$(status_to_lane "$current_status")
    
    # Remove from other lanes
    for other_lane in "${LANES[@]}"; do
        if [ "$other_lane" != "$lane" ] && [ -f "$KANBAN_DIR/$other_lane/$project_name.md" ]; then
            rm "$KANBAN_DIR/$other_lane/$project_name.md"
            CHANGED=1
        fi
    done
    
    # Build card content
    card="# $project_name
**Status:** $current_status
**Updated:** $last_updated

$last_action

**Next:** $next_step"
    
    card_file="$KANBAN_DIR/$lane/$project_name.md"
    
    # Only write if changed (use checksum to handle multiline)
    new_hash=$(echo "$card" | md5sum | cut -d' ' -f1)
    old_hash=""
    [ -f "$card_file" ] && old_hash=$(md5sum "$card_file" | cut -d' ' -f1)
    if [ "$new_hash" != "$old_hash" ]; then
        echo "$card" > "$card_file"
        CHANGED=1
        log "Updated: $project_name → $lane"
    fi
done

if [ "$CHANGED" -eq 1 ]; then
    log "Sync complete — changes made"
else
    log "Sync complete — no changes"
fi
