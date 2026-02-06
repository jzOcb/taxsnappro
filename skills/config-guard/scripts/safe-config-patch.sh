#!/usr/bin/env bash
# safe-config-patch.sh — Validate-then-patch wrapper for OpenClaw config
# AGENTS MUST USE THIS instead of direct `gateway config.patch`
#
# Usage:
#   safe-config-patch.sh '{"agents":{"defaults":{"model":"anthropic/claude-opus-4-5"}}}'
#   safe-config-patch.sh --file /path/to/patch.json
#
# Exit codes:
#   0 = success
#   1 = validation failed (patch not applied)
#   2 = gateway didn't recover (rolled back)
#   3 = fatal error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_GUARD="$SCRIPT_DIR/config-guard.sh"
CONFIG_FILE="${OPENCLAW_CONFIG:-$HOME/.openclaw/openclaw.json}"
GATEWAY_URL="${OPENCLAW_GATEWAY_URL:-http://127.0.0.1:18789}"
TEMP_CONFIG="/tmp/openclaw-config-test-$$.json"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[safe-patch]${NC} $*"; }
warn() { echo -e "${YELLOW}[safe-patch]${NC} $*"; }
fail() { echo -e "${RED}[safe-patch]${NC} $*"; exit "${2:-1}"; }

cleanup() {
    rm -f "$TEMP_CONFIG" 2>/dev/null || true
}
trap cleanup EXIT

# ── Parse args ──────────────────────────────────────────────────────
PATCH_JSON=""
if [[ "${1:-}" == "--file" ]]; then
    [[ -f "${2:-}" ]] || fail "Patch file not found: ${2:-}" 3
    PATCH_JSON=$(cat "$2")
elif [[ -n "${1:-}" ]]; then
    PATCH_JSON="$1"
else
    fail "Usage: safe-config-patch.sh '<json>' or --file <path>" 3
fi

# ── Validate JSON syntax ────────────────────────────────────────────
log "Step 1/5: Validating patch JSON syntax..."
if ! echo "$PATCH_JSON" | python3 -m json.tool > /dev/null 2>&1; then
    fail "Invalid JSON syntax in patch"
fi

# ── Simulate the merge ──────────────────────────────────────────────
log "Step 2/5: Simulating merge..."
if [[ ! -f "$CONFIG_FILE" ]]; then
    fail "Config file not found: $CONFIG_FILE" 3
fi

python3 - "$CONFIG_FILE" "$PATCH_JSON" "$TEMP_CONFIG" << 'PYEOF'
import json
import sys
from copy import deepcopy

def deep_merge(base, patch):
    """Recursively merge patch into base."""
    result = deepcopy(base)
    for key, value in patch.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result

with open(sys.argv[1]) as f:
    base = json.load(f)

patch = json.loads(sys.argv[2])
merged = deep_merge(base, patch)

with open(sys.argv[3], 'w') as f:
    json.dump(merged, f, indent=2)

print(f"Merged config written to {sys.argv[3]}")
PYEOF

# ── Run config-guard validation on merged config ────────────────────
log "Step 3/5: Running config-guard validation on merged result..."
if ! bash "$CONFIG_GUARD" check "$TEMP_CONFIG"; then
    fail "Config validation FAILED. Patch NOT applied."
fi

# ── Show what's changing ────────────────────────────────────────────
log "Step 4/5: Changes to be applied:"
echo "$PATCH_JSON" | python3 -m json.tool

# ── Apply via gateway ───────────────────────────────────────────────
log "Step 5/5: Applying patch via gateway..."

# Use curl to call gateway config.patch API
# Note: This assumes gateway REST API is available
# If not, fall back to writing file + sending SIGUSR1

# Check if gateway API is available
if curl -sf "$GATEWAY_URL/api/health" > /dev/null 2>&1; then
    # Gateway API available - but we need to use the gateway tool, not REST
    # For now, just write the merged config and restart
    log "Backing up current config..."
    cp "$CONFIG_FILE" "$CONFIG_FILE.bak.$(date +%Y%m%d-%H%M%S)"
    
    log "Writing merged config..."
    cp "$TEMP_CONFIG" "$CONFIG_FILE"
    
    log "Signaling gateway to reload..."
    pkill -USR1 -f "openclaw\|clawdbot" 2>/dev/null || warn "Could not signal gateway (may need manual restart)"
    
    log "Waiting for gateway..."
    sleep 3
    
    if curl -sf "$GATEWAY_URL/api/health" > /dev/null 2>&1; then
        log "✅ Config patch applied successfully!"
        exit 0
    else
        warn "Gateway not responding, attempting rollback..."
        cp "$CONFIG_FILE.bak."* "$CONFIG_FILE" 2>/dev/null || true
        pkill -USR1 -f "openclaw\|clawdbot" 2>/dev/null || true
        fail "Gateway failed to recover. Rolled back." 2
    fi
else
    warn "Gateway API not available at $GATEWAY_URL"
    warn "Writing config file directly (restart manually if needed)"
    
    log "Backing up current config..."
    cp "$CONFIG_FILE" "$CONFIG_FILE.bak.$(date +%Y%m%d-%H%M%S)"
    
    log "Writing merged config..."
    cp "$TEMP_CONFIG" "$CONFIG_FILE"
    
    log "✅ Config written. Run 'pkill -USR1 -f openclaw' to apply."
    exit 0
fi
