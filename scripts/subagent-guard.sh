#!/bin/bash
# subagent-guard.sh — Enforce sub-agent discipline
# Run after sub-agent completes to validate + deliver results
#
# Usage: bash scripts/subagent-guard.sh <session_key> <output_file>
#
# This script:
# 1. Checks if the output file exists and has content
# 2. Validates no fabricated data patterns
# 3. Returns the content for the main agent to deliver
#
# The main agent should NEVER let announce deliver results.
# Always: spawn → wait → read output file → validate → send content directly.

set -euo pipefail

SESSION_KEY="${1:-}"
OUTPUT_FILE="${2:-}"

if [[ -z "$SESSION_KEY" || -z "$OUTPUT_FILE" ]]; then
    echo "ERROR: Usage: subagent-guard.sh <session_key> <output_file>"
    exit 1
fi

# Check output file exists
if [[ ! -f "$OUTPUT_FILE" ]]; then
    echo "ERROR: Output file not found: $OUTPUT_FILE"
    echo "Sub-agent may not have written output. Check session history."
    exit 2
fi

# Check file has content
FILE_SIZE=$(wc -c < "$OUTPUT_FILE")
if [[ "$FILE_SIZE" -lt 100 ]]; then
    echo "WARNING: Output file suspiciously small ($FILE_SIZE bytes)"
fi

# Scan for fabricated data patterns (numbers that look made up)
FABRICATION_PATTERNS=(
    "收益率[0-9]+\.[0-9]+%"
    "win rate.*[0-9]+\.[0-9]+%"
    "胜率.*[0-9]+\.[0-9]+%"
    "省下.*[0-9]+万"
    "saved.*\\\$[0-9]+,[0-9]+"
    "ROI.*[0-9]+x"
    "准确率.*[0-9]+%"
    "accuracy.*[0-9]+%"
)

echo "=== Fabrication Scan ==="
FOUND_SUSPICIOUS=0
for pattern in "${FABRICATION_PATTERNS[@]}"; do
    matches=$(grep -Pcn "$pattern" "$OUTPUT_FILE" 2>/dev/null || true)
    if [[ "$matches" -gt 0 ]]; then
        echo "⚠️  Pattern found: $pattern ($matches matches)"
        grep -Pn "$pattern" "$OUTPUT_FILE" 2>/dev/null | head -3
        FOUND_SUSPICIOUS=1
    fi
done

if [[ "$FOUND_SUSPICIOUS" -eq 0 ]]; then
    echo "✅ No obvious fabrication patterns detected"
else
    echo ""
    echo "⚠️  REVIEW REQUIRED: Suspicious patterns found. Verify all numbers are real."
fi

# Scan for file path leaks (sub-agent sending paths user can't access)
echo ""
echo "=== Path Leak Scan ==="
PATH_LEAKS=$(grep -Pcn "/home/clawdbot|/workspace|/opt/clawdbot" "$OUTPUT_FILE" 2>/dev/null || true)
if [[ "$PATH_LEAKS" -gt 0 ]]; then
    echo "⚠️  File paths found in output ($PATH_LEAKS occurrences) — DO NOT send raw paths to user"
    grep -Pn "/home/clawdbot|/workspace|/opt/clawdbot" "$OUTPUT_FILE" 2>/dev/null | head -5
else
    echo "✅ No file path leaks detected"
fi

# Summary
echo ""
echo "=== Summary ==="
echo "File: $OUTPUT_FILE"
echo "Size: $FILE_SIZE bytes"
echo "Lines: $(wc -l < "$OUTPUT_FILE")"
echo ""
echo "Ready for main agent to read, verify, and deliver content directly."
