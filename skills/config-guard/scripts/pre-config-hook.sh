#!/usr/bin/env bash
# pre-config-hook.sh — Git pre-commit hook for openclaw config changes
# Install: cp this to .git/hooks/pre-commit or chain it in existing hook
# Triggers when clawdbot.json / openclaw.json is staged for commit

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_GUARD="${SCRIPT_DIR}/config-guard.sh"

# Find config file in staged changes
CONFIG_FILES=$(git diff --cached --name-only | grep -E '(clawdbot|openclaw)\.json$' || true)

if [[ -z "$CONFIG_FILES" ]]; then
    exit 0  # no config changes, pass through
fi

echo "🔒 [config-guard] Detected config change in: $CONFIG_FILES"

for f in $CONFIG_FILES; do
    if [[ -f "$f" ]]; then
        echo "🔒 [config-guard] Validating $f..."
        if ! bash "$CONFIG_GUARD" check "$f"; then
            echo ""
            echo "❌ Config validation failed for $f"
            echo "   Fix the issues above, then try again."
            echo "   To bypass: git commit --no-verify"
            echo ""
            exit 1
        fi
    fi
done

echo "✅ [config-guard] Config validation passed"
