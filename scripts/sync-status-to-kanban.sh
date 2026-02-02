#!/bin/bash
# sync-status-to-kanban.sh — Bidirectional sync between STATUS.md and kanban
# Latest timestamp wins

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
        *进行中*|*运行中*|*"In Progress"*|*Running*) echo "In Progress" ;;
        *暂停*|*Paused*|*卡住*|*Blocked*) echo "Paused" ;;
        *完成*|*Done*|*Completed*) echo "Done" ;;
        *规划中*|*TODO*|*Planning*) echo "TODO" ;;
        *) echo "In Progress" ;;  # Default to In Progress for active projects
    esac
}

# Map English lane to Chinese status
lane_to_status() {
    case "$1" in
        "In Progress") echo "进行中" ;;
        "Paused") echo "暂停" ;;
        "Done") echo "完成" ;;
        "TODO") echo "规划中" ;;
        *) echo "规划中" ;;
    esac
}

# Find kanban card for project
find_kanban_card() {
    local project_name="$1"
    for lane in "${LANES[@]}"; do
        local card="$KANBAN_DIR/$lane/$project_name.md"
        if [ -f "$card" ]; then
            echo "$card"
            return 0
        fi
    done
    return 1
}

# Get file modification time (epoch seconds)
get_mtime() {
    stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null
}

# Update STATUS.md from kanban card
update_status_from_kanban() {
    local status_file="$1"
    local kanban_card="$2"
    local new_lane="$3"
    
    local new_status=$(lane_to_status "$new_lane")
    local timestamp=$(date -u +"%Y-%m-%dT%H:%MZ")
    
    # Update status line
    sed -i "s/^## 当前状态:.*/## 当前状态: $new_status/" "$status_file"
    sed -i "s/^Last updated:.*/Last updated: $timestamp/" "$status_file"
    
    log "↩ Kanban → STATUS: $project_name → $new_status (手动拖拽)"
}

# Update kanban card from STATUS.md
update_kanban_from_status() {
    local project_name="$1"
    local status_file="$2"
    local lane="$3"
    
    # Parse status
    local current_status=$(grep -i "## 当前状态\|## Current Status" "$status_file" | head -1 | sed 's/.*: *//')
    local last_action=$(grep -A1 "## 最后做了什么\|## Last Action" "$status_file" | tail -1 | sed 's/^- //')
    local next_step=$(grep -A1 "## 下一步\|## Next Step" "$status_file" | tail -1 | sed 's/^- //')
    local last_updated=$(grep "Last updated:" "$status_file" | head -1 | sed 's/Last updated: *//')
    
    # Remove from other lanes
    for other_lane in "${LANES[@]}"; do
        if [ "$other_lane" != "$lane" ] && [ -f "$KANBAN_DIR/$other_lane/$project_name.md" ]; then
            rm "$KANBAN_DIR/$other_lane/$project_name.md"
        fi
    done
    
    # Build card content
    local card="# $project_name
**Status:** $current_status
**Updated:** $last_updated

$last_action

**Next:** $next_step"
    
    local card_file="$KANBAN_DIR/$lane/$project_name.md"
    
    # Write if changed
    local new_hash=$(echo "$card" | md5sum | cut -d' ' -f1)
    local old_hash=""
    [ -f "$card_file" ] && old_hash=$(md5sum "$card_file" | cut -d' ' -f1)
    
    if [ "$new_hash" != "$old_hash" ]; then
        echo "$card" > "$card_file"
        log "→ STATUS → Kanban: $project_name → $lane"
        return 0
    fi
    return 1
}

CHANGED=0

# Process each project
for status_file in "$WORKSPACE"/*/STATUS.md; do
    [ -f "$status_file" ] || continue
    
    project_dir="$(dirname "$status_file")"
    project_name="$(basename "$project_dir")"
    
    # Get STATUS.md modification time
    status_mtime=$(get_mtime "$status_file")
    
    # Find existing kanban card (any lane)
    kanban_card=$(find_kanban_card "$project_name")
    
    if [ -n "$kanban_card" ]; then
        # Card exists - check which is newer
        kanban_mtime=$(get_mtime "$kanban_card")
        current_lane=$(basename "$(dirname "$kanban_card")")
        
        # Get expected lane from STATUS.md
        current_status=$(grep -i "## 当前状态\|## Current Status" "$status_file" | head -1 | sed 's/.*: *//')
        expected_lane=$(status_to_lane "$current_status")
        
        # Compare timestamps
        if [ "$kanban_mtime" -gt "$status_mtime" ]; then
            # Kanban is newer - user moved it manually
            if [ "$current_lane" != "$expected_lane" ]; then
                log "🔄 Detected manual move: $project_name ($expected_lane → $current_lane)"
                update_status_from_kanban "$status_file" "$kanban_card" "$current_lane"
                CHANGED=1
            fi
        else
            # STATUS.md is newer - update kanban
            if update_kanban_from_status "$project_name" "$status_file" "$expected_lane"; then
                CHANGED=1
            fi
        fi
    else
        # No card exists - create from STATUS.md
        current_status=$(grep -i "## 当前状态\|## Current Status" "$status_file" | head -1 | sed 's/.*: *//')
        lane=$(status_to_lane "$current_status")
        if update_kanban_from_status "$project_name" "$status_file" "$lane"; then
            CHANGED=1
        fi
    fi
done

if [ "$CHANGED" -eq 1 ]; then
    log "✅ Bidirectional sync complete — changes detected"
else
    log "✅ Bidirectional sync complete — no changes"
fi
