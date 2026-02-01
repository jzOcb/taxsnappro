#!/bin/bash
# ============================================
# Curated Skill Install for OpenClaw
# Installs 15 high-value skills
# Usage: bash install-skills.sh
# ============================================

echo "⚡ Installing curated OpenClaw skills..."
echo ""

# Check clawdhub CLI
if ! command -v clawdhub &>/dev/null; then
    echo "Installing ClawdHub CLI..."
    npm i -g clawdhub
fi

install_skill() {
    echo "  📦 $1..."
    clawdhub install "$1" 2>/dev/null && echo "     ✅ OK" || echo "     ⚠️  Failed (may already be installed)"
}

echo "🛡️ Security"
install_skill "clawdbot-security-suite"

echo ""
echo "🏗️ Infrastructure"
install_skill "digital-ocean"
install_skill "tailscale"

echo ""
echo "💰 Finance"
install_skill "polymarket"
install_skill "ibkr-trader"
install_skill "yahoo-finance-ijybk"

echo ""
echo "🔍 Search & Research"
install_skill "brave-search"
install_skill "tavily"
install_skill "search"
install_skill "last30days"
install_skill "youtube-summarizer"

echo ""
echo "🔧 Tools & Maintenance"
install_skill "duckdb-en"
install_skill "auto-updater"
install_skill "skills-audit"
install_skill "clawddocs"

echo ""
echo "=========================================="
echo "✅ Done! Restart gateway to pick up new skills:"
echo "   clawdbot gateway restart"
echo "=========================================="
