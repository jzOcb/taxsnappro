#!/bin/bash
# memory-cleanup.sh — Weekly memory maintenance
# Archives old daily logs, keeps memory lean
#
# Run weekly via cron or manually: bash scripts/memory-cleanup.sh
#
# What it does:
# 1. Moves daily logs older than 7 days to memory/archive/
# 2. Reports current memory size
# 3. Flags if MEMORY.md is getting too large (>20KB)

set -euo pipefail

MEMORY_DIR="/home/clawdbot/clawd/memory"
ARCHIVE_DIR="$MEMORY_DIR/archive"
MEMORY_MD="/home/clawdbot/clawd/MEMORY.md"
MAX_MEMORY_KB=20

mkdir -p "$ARCHIVE_DIR"

echo "=== Memory Cleanup $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# Archive daily logs older than 7 days
ARCHIVED=0
find "$MEMORY_DIR" -maxdepth 1 -name "2026-*.md" -mtime +7 -print0 | while IFS= read -r -d '' file; do
    basename=$(basename "$file")
    mv "$file" "$ARCHIVE_DIR/$basename"
    echo "Archived: $basename"
    ARCHIVED=$((ARCHIVED + 1))
done

# Also archive research files older than 14 days
find "$MEMORY_DIR" -maxdepth 1 -name "research-*.md" -mtime +14 -print0 | while IFS= read -r -d '' file; do
    basename=$(basename "$file")
    mv "$file" "$ARCHIVE_DIR/$basename"
    echo "Archived research: $basename"
done
find "$MEMORY_DIR" -maxdepth 1 -name "kalshi-*.md" -mtime +14 -print0 | while IFS= read -r -d '' file; do
    basename=$(basename "$file")
    mv "$file" "$ARCHIVE_DIR/$basename"
    echo "Archived kalshi: $basename"
done

# Report sizes
echo ""
echo "=== Current State ==="
ACTIVE_SIZE=$(du -sh "$MEMORY_DIR" --exclude=archive 2>/dev/null | cut -f1)
ARCHIVE_SIZE=$(du -sh "$ARCHIVE_DIR" 2>/dev/null | cut -f1)
ACTIVE_FILES=$(find "$MEMORY_DIR" -maxdepth 1 -name "*.md" | wc -l)
ARCHIVE_FILES=$(find "$ARCHIVE_DIR" -name "*.md" 2>/dev/null | wc -l)

echo "Active: $ACTIVE_SIZE ($ACTIVE_FILES files)"
echo "Archive: $ARCHIVE_SIZE ($ARCHIVE_FILES files)"

# Check MEMORY.md size
if [[ -f "$MEMORY_MD" ]]; then
    MEMORY_SIZE_KB=$(du -k "$MEMORY_MD" | cut -f1)
    echo "MEMORY.md: ${MEMORY_SIZE_KB}KB"
    if [[ "$MEMORY_SIZE_KB" -gt "$MAX_MEMORY_KB" ]]; then
        echo "⚠️ MEMORY.md is large (${MEMORY_SIZE_KB}KB > ${MAX_MEMORY_KB}KB) — consider distilling"
    fi
fi

echo ""
echo "Done."
