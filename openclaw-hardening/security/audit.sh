#!/bin/bash
# ============================================
# OpenClaw Server Security Audit
# Run this FIRST to see current exposure
# Usage: bash audit.sh
# ============================================

echo "🔍 OpenClaw Security Audit — $(date -u)"
echo "=========================================="

# 1. Open ports
echo ""
echo "📡 [1/9] Open ports (listening on all interfaces):"
ss -tlnp 2>/dev/null | grep -v "127.0.0.1\|::1" || netstat -tlnp 2>/dev/null | grep -v "127.0.0.1\|::1"
echo ""
echo "⚠️  Any port NOT on 127.0.0.1 is exposed to the internet!"

# 2. SSH config
echo ""
echo "🔑 [2/9] SSH Configuration:"
echo "  Port: $(grep -E "^Port " /etc/ssh/sshd_config 2>/dev/null || echo '22 (default)')"
echo "  PasswordAuth: $(grep -E "^PasswordAuthentication" /etc/ssh/sshd_config 2>/dev/null || echo 'not set (default: yes ⚠️)')"
echo "  PermitRootLogin: $(grep -E "^PermitRootLogin" /etc/ssh/sshd_config 2>/dev/null || echo 'not set (default: yes ⚠️)')"
echo "  PubkeyAuth: $(grep -E "^PubkeyAuthentication" /etc/ssh/sshd_config 2>/dev/null || echo 'not set (default: yes)')"

# 3. Firewall status
echo ""
echo "🧱 [3/9] Firewall:"
if command -v ufw &>/dev/null; then
    sudo ufw status 2>/dev/null || echo "  UFW installed but cannot check status"
else
    echo "  ❌ UFW not installed!"
fi

# 4. Failed login attempts (last 24h)
echo ""
echo "🚨 [4/9] Failed SSH attempts (last 24h):"
# grep -c returns 0 (count) even on no matches, but sudo may output password prompt to stderr
# which contaminates the value. Strip whitespace and default to 0.
FAILED=$(sudo journalctl -u ssh --since "24 hours ago" 2>/dev/null | grep -c "Failed password\|Invalid user" 2>/dev/null || true)
FAILED="${FAILED:-0}"
FAILED=$(echo "$FAILED" | tr -d '[:space:]')
echo "  Failed attempts: $FAILED"
if [ "$FAILED" -gt 100 ] 2>/dev/null; then
    echo "  ⚠️  HIGH! You're being actively scanned/attacked!"
fi

# 5. fail2ban
echo ""
echo "🛡️ [5/9] fail2ban:"
if command -v fail2ban-client &>/dev/null; then
    echo "  ✅ Installed"
    sudo fail2ban-client status sshd 2>/dev/null || echo "  SSH jail not active"
else
    echo "  ❌ Not installed!"
fi

# 6. Gateway config check
echo ""
echo "🤖 [6/9] OpenClaw Gateway:"
if pgrep -f "openclaw\|clawdbot" &>/dev/null; then
    echo "  ✅ Gateway running"
else
    echo "  Gateway process not found (might use different name)"
fi

CONFIG_PATHS=(
    "$HOME/.openclaw/openclaw.json"
    "/opt/clawdbot/openclaw.json"
    "$HOME/.clawdbot/clawdbot.json"
)
for cfg in "${CONFIG_PATHS[@]}"; do
    if [ -f "$cfg" ]; then
        echo "  Config: $cfg"
        if grep -q '"auth"' "$cfg" 2>/dev/null; then
            echo "  ✅ Auth section found in config"
        else
            echo "  ⚠️  No auth section in config!"
        fi
        if grep -q '"loopback"' "$cfg" 2>/dev/null; then
            echo "  ✅ Bound to loopback"
        elif grep -q '"lan"' "$cfg" 2>/dev/null; then
            echo "  ⚠️  Bound to LAN — exposed on network!"
        fi
        break
    fi
done

GW_PORT=$(ss -tlnp 2>/dev/null | grep -E "18789|openclaw|clawdbot" | head -1)
if [ -n "$GW_PORT" ]; then
    echo "  Gateway port: $GW_PORT"
    if echo "$GW_PORT" | grep -q "0.0.0.0\|\*:"; then
        echo "  ⚠️  Gateway listening on ALL interfaces — exposed!"
    fi
fi

# 7. Tailscale
echo ""
echo "🔐 [7/9] Tailscale:"
if command -v tailscale &>/dev/null; then
    echo "  ✅ Installed"
    tailscale status 2>/dev/null | head -5
else
    echo "  ❌ Not installed (recommended for secure remote access)"
fi

# 8. Credential Storage
echo ""
echo "🔑 [8/9] Credential Storage:"
OPENCLAW_JSON="$HOME/.openclaw/openclaw.json"
if [ -f "$OPENCLAW_JSON" ]; then
    if grep -qE '(sk-|key-|token)' "$OPENCLAW_JSON" 2>/dev/null; then
        echo "  ⚠️  Possible API keys in plaintext in openclaw.json"
        echo "     Move secrets to env vars or .env file"
    else
        echo "  ✅ No obvious plaintext keys in config"
    fi
    perms=$(stat -c '%a' "$OPENCLAW_JSON" 2>/dev/null)
    if [ -n "$perms" ] && [ "$perms" != "600" ]; then
        echo "  ⚠️  openclaw.json permissions: $perms (should be 600)"
        echo "     Fix: chmod 600 $OPENCLAW_JSON"
    fi
else
    echo "  (openclaw.json not found at default path)"
fi

SESSIONS_DIR="$HOME/.openclaw/agents/main/sessions"
if [ -d "$SESSIONS_DIR" ]; then
    world_readable=$(find "$SESSIONS_DIR" -perm -o+r 2>/dev/null | head -1)
    if [ -n "$world_readable" ]; then
        echo "  ⚠️  Session logs world-readable! Fix: chmod -R o-rwx $SESSIONS_DIR"
    else
        echo "  ✅ Session logs not world-readable"
    fi
fi

# 9. Browser Control Port
echo ""
echo "🌐 [9/9] Browser Control Port (18791):"
if ss -tlnp 2>/dev/null | grep -q ":18791"; then
    echo "  ⚠️  Browser control port 18791 is LISTENING"
    echo "     This gives full browser access — ensure localhost-only"
else
    echo "  ✅ Browser control port not exposed"
fi

# Summary
echo ""
echo "=========================================="
echo "📋 SUMMARY — Action Items:"
echo "=========================================="
echo ""
if ! command -v ufw &>/dev/null || ! sudo ufw status 2>/dev/null | grep -q "active"; then
    echo "  🔴 CRITICAL: Enable firewall (run harden.sh)"
fi
if grep -q "PasswordAuthentication yes" /etc/ssh/sshd_config 2>/dev/null || ! grep -q "PasswordAuthentication" /etc/ssh/sshd_config 2>/dev/null; then
    echo "  🔴 CRITICAL: Disable SSH password auth"
fi
if ! command -v fail2ban-client &>/dev/null; then
    echo "  🟡 HIGH: Install fail2ban"
fi
if ! command -v tailscale &>/dev/null; then
    echo "  🟡 RECOMMENDED: Install Tailscale"
fi
echo ""
echo "Done. Run 'sudo bash harden.sh' to apply fixes."
