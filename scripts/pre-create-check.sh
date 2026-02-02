#!/bin/bash
# pre-create-check.sh — Run BEFORE creating any new Python file in a project
# Usage: bash scripts/pre-create-check.sh <project_directory>

set -euo pipefail

PROJECT_DIR="${1:-.}"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Directory not found: $PROJECT_DIR"
    exit 1
fi

echo "╔══════════════════════════════════════════════════╗"
echo "║          PRE-CREATION CHECK                      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. List existing Python modules
echo "📦 Existing Python modules:"
echo "─────────────────────────────"
find "$PROJECT_DIR" -maxdepth 2 -name "*.py" -not -path "*/__pycache__/*" -not -path "*/.git/*" | sort | while read -r f; do
    funcs=$(grep -c "^def " "$f" 2>/dev/null || true)
    funcs=${funcs:-0}
    funcs=$(echo "$funcs" | tr -d '[:space:]')
    echo "  $(basename "$f") ($funcs functions)"
done
echo ""

# 2. List public functions (validation/scoring/analysis)
echo "🔍 Validation / Scoring / Analysis functions:"
echo "─────────────────────────────────────────────"
grep -rn "^def \(validate\|score\|analyze\|check\|verify\|assess\|evaluate\|fetch\|generate_report\)" "$PROJECT_DIR"/*.py 2>/dev/null | \
    sed 's|^.*/||' | while IFS=: read -r file line func; do
    echo "  $file:$line → $func"
done
if ! grep -rq "^def \(validate\|score\|analyze\|check\|verify\|assess\|evaluate\|fetch\|generate_report\)" "$PROJECT_DIR"/*.py 2>/dev/null; then
    echo "  (none found)"
fi
echo ""

# 3. List ALL public functions for import reference
echo "📋 All public functions available for import:"
echo "─────────────────────────────────────────────"
grep -rn "^def [a-z]" "$PROJECT_DIR"/*.py 2>/dev/null | \
    sed 's|^.*/||' | while IFS=: read -r file line func; do
    func_name=$(echo "$func" | sed 's/def \([a-zA-Z_]*\).*/\1/')
    echo "  from $(basename "$file" .py) import $func_name  # $file:$line"
done
echo ""

# 4. Show SKILL.md if it exists
if [ -f "$PROJECT_DIR/SKILL.md" ]; then
    echo "📖 SKILL.md summary:"
    echo "─────────────────────"
    head -40 "$PROJECT_DIR/SKILL.md"
    echo ""
    echo "  ... (read full SKILL.md for details)"
    echo ""
fi

# 5. Show __init__.py registry if it exists
if [ -f "$PROJECT_DIR/__init__.py" ]; then
    echo "📦 Official module registry (__init__.py):"
    echo "─────────────────────────────────────────"
    cat "$PROJECT_DIR/__init__.py"
    echo ""
fi

# 6. Check for known bugs/crashes in STATUS.md
if [ -f "$PROJECT_DIR/STATUS.md" ]; then
    echo "⚠️  Known bugs/crashes from STATUS.md:"
    echo "─────────────────────────────────────"
    grep -E "崩溃|crash|bug|BUG|停止|stopped|failed|FAILED|原因|Root cause|根本原因" "$PROJECT_DIR/STATUS.md" | head -20 || echo "  (no recent crashes documented)"
    echo ""
fi

# 7. Check for recent errors in logs
if [ -d "$PROJECT_DIR/logs" ]; then
    echo "🔥 Recent errors from logs:"
    echo "───────────────────────────"
    find "$PROJECT_DIR/logs" -name "*.log" -mtime -7 -type f -exec grep -l "ERROR\|FATAL\|Exception\|Traceback" {} \; 2>/dev/null | head -5 | while read -r log; do
        echo "  $(basename "$log"):"
        grep -E "ERROR|FATAL|Exception|Traceback" "$log" | tail -3 | sed 's/^/    /'
    done
    echo ""
fi

echo "╔══════════════════════════════════════════════════╗"
echo "║  ⚠️  BEFORE creating new version:                ║"
echo "║  1. Check why previous versions failed           ║"
echo "║  2. Import existing modules, don't rewrite       ║"
echo "║  3. Fix known bugs in the new version            ║"
echo "╚══════════════════════════════════════════════════╝"
