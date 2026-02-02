#!/bin/bash
# Curated skill install — run on host (not sandbox)
# Usage: bash ~/clawd/setup/install-skills.sh

set -e
echo "⚡ Installing curated skills..."

# Core
clawdhub install polymarket
clawdhub install digital-ocean
clawdhub install tailscale
clawdhub install clawdbot-security-suite
clawdhub install auto-updater
clawdhub install search

# Finance
clawdhub install ibkr-trader
clawdhub install yahoo-finance-ijybk

# Research
clawdhub install brave-search
clawdhub install tavily
clawdhub install last30days
clawdhub install youtube-summarizer

# Tools
clawdhub install duckdb-en
clawdhub install skills-audit
clawdhub install clawddocs

echo ""
echo "✅ Done! Restart gateway to pick up new skills:"
echo "   clawdbot gateway restart"
