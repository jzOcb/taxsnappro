#!/bin/bash
# run_full_scan.sh — Execute all Kalshi scanning strategies
#
# Runs: parity + endgame + cross-platform + NO farming
# Output: combined report + individual JSON files
#
# Usage:
#   bash scripts/run_full_scan.sh           # Full scan (all strategies)
#   bash scripts/run_full_scan.sh --quick   # Skip slow strategies (parity full scan)
#   bash scripts/run_full_scan.sh --json    # JSON output only
#   bash scripts/run_full_scan.sh --individual  # Run each scanner separately

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
KALSHI_DIR="$PROJECT_DIR/kalshi"
LOG_DIR="$KALSHI_DIR/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date -u +"%Y-%m-%d_%H%M")
LOG_FILE="$LOG_DIR/scan-${TIMESTAMP}.log"

echo "╔══════════════════════════════════════════════╗"
echo "║  🎯 KALSHI FULL STRATEGY SCAN               ║"
echo "║  $(date -u +'%Y-%m-%d %H:%M UTC')                        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Check if running individual or unified
if [[ "${1:-}" == "--individual" ]]; then
    echo "🔍 Running scanners individually..."
    echo ""
    
    echo "━━━ 1/4: Parity Arbitrage ━━━"
    python3 "$KALSHI_DIR/parity_scanner.py" 2>&1 | tee -a "$LOG_FILE"
    echo ""
    
    echo "━━━ 2/4: Endgame Strategy ━━━"
    python3 "$KALSHI_DIR/endgame_scanner.py" 2>&1 | tee -a "$LOG_FILE"
    echo ""
    
    echo "━━━ 3/4: Cross-Platform Monitor ━━━"
    python3 "$KALSHI_DIR/cross_platform_monitor.py" --auto 2>&1 | tee -a "$LOG_FILE"
    echo ""
    
    echo "━━━ 4/4: NO Farming (Decision Engine) ━━━"
    python3 "$KALSHI_DIR/report_v2.py" 2>&1 | tee -a "$LOG_FILE"
    
else
    echo "🔍 Running unified scanner..."
    echo ""
    python3 "$KALSHI_DIR/unified_scanner.py" "$@" 2>&1 | tee -a "$LOG_FILE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📄 Log saved to: $LOG_FILE"
echo "📊 Results:"
echo "   • $KALSHI_DIR/parity-scan-results.json"
echo "   • $KALSHI_DIR/endgame-scan-results.json"
echo "   • $KALSHI_DIR/cross-platform-results.json"
echo "   • $KALSHI_DIR/unified-scan-results.json"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
