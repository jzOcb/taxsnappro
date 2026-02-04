#!/usr/bin/env bash
# config-guard.sh — Validate and safely apply OpenClaw config changes
# Usage:
#   config-guard.sh check [config-path]     — validate without applying
#   config-guard.sh apply [config-path]      — backup → validate → apply → verify
#   config-guard.sh rollback [config-path]   — restore last backup
#   config-guard.sh diff [config-path]       — show what changed vs backup
#
# Exit codes: 0=ok, 1=validation failed, 2=gateway didn't recover (rolled back), 3=fatal

set -euo pipefail

CONFIG_PATH="${2:-$HOME/.clawdbot/clawdbot.json}"
BACKUP_DIR="$(dirname "$CONFIG_PATH")/.config-backups"
SCHEMA_CACHE="/tmp/openclaw-config-schema.json"
GATEWAY_URL="${OPENCLAW_GATEWAY_URL:-http://127.0.0.1:18789}"
RECOVERY_TIMEOUT="${CONFIG_GUARD_TIMEOUT:-30}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[config-guard]${NC} $*"; }
warn() { echo -e "${YELLOW}[config-guard]${NC} $*"; }
fail() { echo -e "${RED}[config-guard]${NC} $*"; exit "${2:-1}"; }

# ── Backup ──────────────────────────────────────────────────────────
backup() {
    mkdir -p "$BACKUP_DIR"
    local ts
    ts=$(date +%Y%m%d-%H%M%S)
    local backup_file="$BACKUP_DIR/clawdbot-${ts}.json"
    cp "$CONFIG_PATH" "$backup_file"
    # keep symlink to latest
    ln -sf "$backup_file" "$BACKUP_DIR/latest.json"
    log "Backed up to $backup_file"
    echo "$backup_file"
}

# ── Rollback ────────────────────────────────────────────────────────
rollback() {
    local latest="$BACKUP_DIR/latest.json"
    if [[ ! -f "$latest" ]]; then
        fail "No backup found at $latest" 3
    fi
    cp "$latest" "$CONFIG_PATH"
    log "Rolled back config from $latest"
}

# ── Schema validation (uses python3 + jsonschema if available) ──────
validate_schema() {
    local config_file="$1"

    # basic JSON syntax check
    if ! python3 -m json.tool "$config_file" > /dev/null 2>&1; then
        fail "Invalid JSON syntax in $config_file"
    fi

    # validate with inline semantic checks
    python3 - "$config_file" << 'PYEOF'
import json, sys

config_file = sys.argv[1]
with open(config_file) as f:
    config = json.load(f)

errors = []

# Check 1: No unknown top-level keys (common AI mistake)
known_top = {
    "meta", "env", "wizard", "diagnostics", "logging", "update",
    "browser", "ui", "auth", "models", "nodeHost", "agents", "tools",
    "bindings", "broadcast", "audio", "media", "messages", "commands",
    "approvals", "session", "cron", "hooks", "web", "channels",
    "discovery", "canvasHost", "talk", "gateway", "memory", "skills",
    "plugins"
}
unknown = set(config.keys()) - known_top
if unknown:
    errors.append(f"Unknown top-level keys: {unknown}")

# Check 2: Telegram channel not accidentally wiped
channels = config.get("channels", {})
telegram = channels.get("telegram", {})
if channels and "telegram" in channels:
    if not telegram.get("botToken") and not telegram.get("tokenFile"):
        errors.append("WARNING: Telegram channel exists but has no botToken or tokenFile")

# Check 3: Model name format (dots vs hyphens)
def check_model_names(obj, path=""):
    if isinstance(obj, str) and ("claude" in obj or "gpt" in obj or "gemini" in obj):
        # Check for common mistakes
        if "claude-sonnet-4.5" in obj or "claude-opus-4.5" in obj:
            errors.append(f"Model name uses dots instead of hyphens at {path}: '{obj}' → should use '-' not '.'")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            check_model_names(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check_model_names(v, f"{path}[{i}]")

check_model_names(config)

# Check 4: browser.profiles.*.color is required and must be hex
browser = config.get("browser", {})
profiles = browser.get("profiles", {})
for name, prof in profiles.items():
    if "color" not in prof:
        errors.append(f"browser.profiles.{name} missing required 'color' field")
    elif prof["color"] and not all(c in "0123456789abcdefABCDEF#" for c in prof["color"]):
        errors.append(f"browser.profiles.{name}.color must be hex format, got: '{prof['color']}'")

# Check 5: commands.native and commands.nativeSkills required
commands = config.get("commands", {})
if "native" not in commands:
    errors.append("Missing required field: commands.native")
if "nativeSkills" not in commands:
    errors.append("Missing required field: commands.nativeSkills")

# Check 6: No sensitive fields accidentally set to placeholder values
def check_placeholders(obj, path=""):
    if isinstance(obj, str):
        placeholders = ["your-", "xxx", "TODO", "REPLACE", "INSERT", "sk-xxx"]
        for p in placeholders:
            if obj.startswith(p) and ("token" in path.lower() or "key" in path.lower() or "secret" in path.lower()):
                errors.append(f"Placeholder value detected at {path}: '{obj[:20]}...'")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            check_placeholders(v, f"{path}.{k}")

check_placeholders(config)

# Check 7: Critical fields not empty
agents = config.get("agents", {})
defaults = agents.get("defaults", {})
model = defaults.get("model", {})
if model and not model.get("primary"):
    errors.append("agents.defaults.model.primary is empty — no model configured")

# Report
if errors:
    print(f"\n❌ Found {len(errors)} issue(s):\n")
    for e in errors:
        prefix = "⚠️ " if e.startswith("WARNING") else "❌ "
        print(f"  {prefix}{e}")
    # Only fail on non-warnings
    real_errors = [e for e in errors if not e.startswith("WARNING")]
    if real_errors:
        sys.exit(1)
    else:
        print(f"\n⚠️  {len(errors)} warning(s), no blocking errors")
        sys.exit(0)
else:
    print("✅ Config validation passed")
    sys.exit(0)
PYEOF
}

# ── Critical fields diff ────────────────────────────────────────────
check_critical_fields() {
    local new_config="$1"
    local old_config="$BACKUP_DIR/latest.json"

    if [[ ! -f "$old_config" ]]; then
        log "No previous backup to diff against, skipping critical field check"
        return 0
    fi

    python3 - "$old_config" "$new_config" << 'PYEOF'
import json, sys

with open(sys.argv[1]) as f:
    old = json.load(f)
with open(sys.argv[2]) as f:
    new = json.load(f)

warnings = []

# Check if telegram channel was removed
old_tg = old.get("channels", {}).get("telegram", {})
new_tg = new.get("channels", {}).get("telegram", {})
if old_tg and not new_tg:
    warnings.append("Telegram channel config was REMOVED")
if old_tg.get("botToken") and not new_tg.get("botToken"):
    warnings.append("Telegram botToken was REMOVED")

# Check if primary model changed
old_model = old.get("agents", {}).get("defaults", {}).get("model", {}).get("primary", "")
new_model = new.get("agents", {}).get("defaults", {}).get("model", {}).get("primary", "")
if old_model and old_model != new_model:
    warnings.append(f"Primary model changed: {old_model} → {new_model}")

# Check if tools.deny changed (security critical)
old_deny = old.get("tools", {}).get("deny", [])
new_deny = new.get("tools", {}).get("deny", [])
removed = set(old_deny) - set(new_deny)
if removed:
    warnings.append(f"Tools REMOVED from deny list: {removed}")

# Check if gateway auth was removed
old_auth = old.get("gateway", {}).get("auth", {})
new_auth = new.get("gateway", {}).get("auth", {})
if old_auth.get("token") and not new_auth.get("token"):
    warnings.append("Gateway auth token was REMOVED")

if warnings:
    print("\n⚠️  Critical field changes detected:")
    for w in warnings:
        print(f"  ⚠️  {w}")
    print()
    # Don't block, just warn
    sys.exit(0)
else:
    print("✅ No critical field changes")
PYEOF
}

# ── Gateway health check ───────────────────────────────────────────
wait_for_gateway() {
    local timeout="$1"
    local start=$SECONDS

    log "Waiting up to ${timeout}s for gateway to recover..."
    while (( SECONDS - start < timeout )); do
        if curl -sf "$GATEWAY_URL/api/health" > /dev/null 2>&1; then
            log "Gateway is healthy ✅"
            return 0
        fi
        sleep 2
    done

    warn "Gateway did not recover within ${timeout}s"
    return 1
}

# ── Commands ────────────────────────────────────────────────────────
cmd_check() {
    log "Validating $CONFIG_PATH..."
    validate_schema "$CONFIG_PATH"
}

cmd_diff() {
    local latest="$BACKUP_DIR/latest.json"
    if [[ ! -f "$latest" ]]; then
        fail "No backup to diff against" 3
    fi
    diff --color=auto <(python3 -m json.tool "$latest") <(python3 -m json.tool "$CONFIG_PATH") || true
}

cmd_apply() {
    log "=== Config Guard: Safe Apply ==="

    # Step 1: Backup current config
    log "Step 1/4: Backing up current config..."
    local backup_file
    backup_file=$(backup)

    # Step 2: Validate new config
    log "Step 2/4: Validating new config..."
    if ! validate_schema "$CONFIG_PATH"; then
        warn "Validation failed! Rolling back..."
        cp "$backup_file" "$CONFIG_PATH"
        fail "Config validation failed, restored backup"
    fi

    # Step 3: Check critical fields
    log "Step 3/4: Checking critical field changes..."
    check_critical_fields "$CONFIG_PATH"

    # Step 4: Gateway restart will happen externally
    # If called with --restart flag, do it here
    if [[ "${3:-}" == "--restart" ]]; then
        log "Step 4/4: Restarting gateway..."
        kill -USR1 "$(pgrep -f 'clawdbot.*gateway' | head -1)" 2>/dev/null || true

        if ! wait_for_gateway "$RECOVERY_TIMEOUT"; then
            warn "Gateway failed to recover! Rolling back..."
            cp "$backup_file" "$CONFIG_PATH"
            kill -USR1 "$(pgrep -f 'clawdbot.*gateway' | head -1)" 2>/dev/null || true
            sleep 5
            if wait_for_gateway 15; then
                log "Rollback successful, gateway recovered with old config"
            else
                fail "CRITICAL: Gateway not recovering even after rollback!" 3
            fi
            fail "Config change rolled back due to gateway failure" 2
        fi
    else
        log "Step 4/4: Skipped restart (run with --restart to auto-restart)"
    fi

    log "=== Config change applied successfully ✅ ==="
}

cmd_rollback() {
    rollback
    log "Config rolled back. Run 'kill -USR1 \$(pgrep -f clawdbot)' to restart gateway with restored config."
}

# ── Main ────────────────────────────────────────────────────────────
ACTION="${1:-check}"

case "$ACTION" in
    check)    cmd_check ;;
    apply)    cmd_apply ;;
    rollback) cmd_rollback ;;
    diff)     cmd_diff ;;
    *)        fail "Unknown action: $ACTION. Use: check|apply|rollback|diff" 3 ;;
esac
