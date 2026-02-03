#!/bin/bash
# run-background-task.sh — Run AI task in background WITHOUT announce
# Uses oracle CLI to run a task and write output to a file
# This avoids the sub-agent announce mechanism entirely
#
# Usage: bash scripts/run-background-task.sh <output_file> <task_description>
#
# The main agent should:
# 1. Call this script via exec (background)
# 2. Poll for output file existence
# 3. Read and deliver results directly
#
# No announce. No queue contention. No unverified output reaching the user.

set -euo pipefail

OUTPUT_FILE="${1:-}"
shift
TASK="${*:-}"

if [[ -z "$OUTPUT_FILE" || -z "$TASK" ]]; then
    echo "Usage: run-background-task.sh <output_file> <task_description>"
    exit 1
fi

# Check if oracle is available
if ! command -v oracle &>/dev/null; then
    echo "ERROR: oracle CLI not found. Install with: npm install -g @anthropic/oracle"
    exit 1
fi

echo "Starting background task..."
echo "Output: $OUTPUT_FILE"
echo "Task: ${TASK:0:100}..."

# Run with oracle, write to output file
oracle --model claude-sonnet-4-20250514 \
    --prompt "$TASK" \
    --output "$OUTPUT_FILE" \
    2>/dev/null

echo "Task complete. Output written to $OUTPUT_FILE"
