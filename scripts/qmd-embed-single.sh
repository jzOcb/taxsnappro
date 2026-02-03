#!/bin/bash
# qmd single-file embedding for CPU-only VPS
# Workaround for batch embedding crashes

set -e
export PATH="$HOME/.bun/bin:$PATH"

FILE="$1"
COLLECTION="$2"

if [ -z "$FILE" ] || [ -z "$COLLECTION" ]; then
    echo "Usage: $0 <file> <collection-name>"
    exit 1
fi

if [ ! -f "$FILE" ]; then
    echo "File not found: $FILE"
    exit 1
fi

BASENAME=$(basename "$FILE")
TEMP_DIR="/tmp/qmd-single-$$"
mkdir -p "$TEMP_DIR"
cp "$FILE" "$TEMP_DIR/"

echo "Embedding: $BASENAME → $COLLECTION"

# Index
qmd collection add "$TEMP_DIR" --name "$COLLECTION" --mask "*.md" 2>&1 | grep -E "(Creating|Indexed|✓)" || true

# Embed with timeout
timeout 60 qmd embed -c "$COLLECTION" 2>&1 | grep -E "(Embedding|Done|✓)" || {
    echo "⚠️  Timeout/crash on $BASENAME"
    rm -rf "$TEMP_DIR"
    exit 1
}

rm -rf "$TEMP_DIR"
echo "✅ $BASENAME"
