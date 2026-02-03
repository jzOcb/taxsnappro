#!/bin/bash
# collect-daily-work.sh — Aggregate ALL work sources into one summary
# Called by daily X content cron BEFORE writing posts.
# Collects from: git commits, work log, session histories
# Outputs to stdout (or file if arg given)
#
# Usage: bash scripts/collect-daily-work.sh [output_file]

set -euo pipefail

TODAY=$(date -u +%Y-%m-%d)
YESTERDAY=$(date -u -d "yesterday" +%Y-%m-%d 2>/dev/null || date -u -v-1d +%Y-%m-%d)
OUTPUT="${1:-/tmp/daily-work-summary-${TODAY}.md}"
WORKSPACE="/home/clawdbot/clawd"

cat > "$OUTPUT" << EOF
# Daily Work Summary — ${TODAY}
# Auto-collected by collect-daily-work.sh
# Sources: git commits, work log, memory files

EOF

# ═══════════════════════════════════════
# SOURCE 1: Git commits (last 24h, all repos)
# ═══════════════════════════════════════
echo "## Git Commits (last 24h)" >> "$OUTPUT"
echo "" >> "$OUTPUT"

for dir in "$WORKSPACE" "$WORKSPACE"/openclaw-hardening "$WORKSPACE"/kalshi "$WORKSPACE"/process-guardian "$WORKSPACE"/skills/agent-guardrails; do
    if [[ -d "$dir/.git" ]]; then
        REPO_NAME=$(basename "$dir")
        [[ "$dir" == "$WORKSPACE" ]] && REPO_NAME="main-workspace"
        COMMITS=$(cd "$dir" && git log --oneline --since="24 hours ago" --format="  - %h %s" 2>/dev/null)
        if [[ -n "$COMMITS" ]]; then
            echo "### $REPO_NAME" >> "$OUTPUT"
            echo "$COMMITS" >> "$OUTPUT"
            echo "" >> "$OUTPUT"
        fi
    fi
done

# ═══════════════════════════════════════
# SOURCE 2: Work log (mechanical entries from sessions)
# ═══════════════════════════════════════
echo "## Work Log Entries" >> "$OUTPUT"
echo "" >> "$OUTPUT"

WORK_LOG="$WORKSPACE/memory/work-log-${TODAY}.md"
WORK_LOG_YESTERDAY="$WORKSPACE/memory/work-log-${YESTERDAY}.md"

if [[ -f "$WORK_LOG" ]]; then
    grep "^- \[" "$WORK_LOG" >> "$OUTPUT" 2>/dev/null || echo "  (no entries today)" >> "$OUTPUT"
else
    echo "  ⚠️ NO WORK LOG FOR TODAY — sessions may not be logging" >> "$OUTPUT"
fi
echo "" >> "$OUTPUT"

# Also check yesterday (for work done after last content review)
if [[ -f "$WORK_LOG_YESTERDAY" ]]; then
    echo "### Yesterday (since last review)" >> "$OUTPUT"
    grep "^- \[" "$WORK_LOG_YESTERDAY" >> "$OUTPUT" 2>/dev/null || true
    echo "" >> "$OUTPUT"
fi

# ═══════════════════════════════════════
# SOURCE 3: Memory files
# ═══════════════════════════════════════
echo "## Memory File Entries" >> "$OUTPUT"
echo "" >> "$OUTPUT"

MEMORY_TODAY="$WORKSPACE/memory/${TODAY}.md"
if [[ -f "$MEMORY_TODAY" ]]; then
    # Extract section headers as summary
    grep "^##" "$MEMORY_TODAY" >> "$OUTPUT" 2>/dev/null || echo "  (no sections)" >> "$OUTPUT"
else
    echo "  (no memory file for today)" >> "$OUTPUT"
fi
echo "" >> "$OUTPUT"

# ═══════════════════════════════════════
# SOURCE 4: STATUS.md changes
# ═══════════════════════════════════════
echo "## Project Status Changes" >> "$OUTPUT"
echo "" >> "$OUTPUT"

for status_file in "$WORKSPACE"/*/STATUS.md; do
    if [[ -f "$status_file" ]]; then
        PROJECT=$(basename "$(dirname "$status_file")")
        # Check if modified in last 24h
        if find "$status_file" -mmin -1440 -print 2>/dev/null | grep -q .; then
            LAST_UPDATED=$(grep "Last updated" "$status_file" 2>/dev/null | head -1)
            CURRENT_STATUS=$(grep "当前状态\|Current Status" "$status_file" 2>/dev/null | head -1)
            echo "### $PROJECT" >> "$OUTPUT"
            echo "  $LAST_UPDATED" >> "$OUTPUT"
            echo "  $CURRENT_STATUS" >> "$OUTPUT"
            echo "" >> "$OUTPUT"
        fi
    fi
done

# ═══════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════
echo "## Collection Stats" >> "$OUTPUT"
COMMIT_COUNT=$(grep -c "^  - [0-9a-f]" "$OUTPUT" 2>/dev/null || echo 0)
LOG_COUNT=$(grep -c "^\- \[" "$OUTPUT" 2>/dev/null || echo 0)
echo "- Git commits found: $COMMIT_COUNT" >> "$OUTPUT"
echo "- Work log entries: $LOG_COUNT" >> "$OUTPUT"

if [[ "$LOG_COUNT" -eq 0 ]]; then
    echo "- ⚠️ WARNING: Zero work log entries. Sessions may not be calling log-work.sh" >> "$OUTPUT"
fi

echo "" >> "$OUTPUT"
echo "--- End of collection ---" >> "$OUTPUT"

echo "✅ Collected to: $OUTPUT"
echo "   Commits: $COMMIT_COUNT | Log entries: $LOG_COUNT"
