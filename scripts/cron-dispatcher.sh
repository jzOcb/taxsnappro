#!/bin/bash
# cron-dispatcher.sh — System crontab replacement for broken OpenClaw cron
# Runs jobs directly, sends output via Telegram Bot API
# Independent of OpenClaw — works even if gateway is down
#
# Usage: cron-dispatcher.sh <job-name>
# Jobs: btc-30min, kalshi-hourly, market-alert, market-report,
#        x-auto-poster, x-engagement, session-scanner, daily-x-content

set -uo pipefail

JOB="${1:-}"
LOG_DIR="/home/clawdbot/clawd/logs/cron-dispatch"
mkdir -p "$LOG_DIR"

# Kalshi API credentials (needed by position_monitor.py, portfolio_analysis.py)
export KALSHI_API_KEY="${KALSHI_API_KEY:-e23e4c65-cc51-45f0-9120-65dd5b3bda79}"
export KALSHI_PRIVATE_KEY_PATH="${KALSHI_PRIVATE_KEY_PATH:-/opt/kalshi_private_key.pem}"

# Telegram config (read from OpenClaw config, fallback to hardcoded)
BOT_TOKEN=$(python3 -c "
import json
try:
    with open('/home/clawdbot/.openclaw/clawdbot.json') as f:
        print(json.load(f)['channels']['telegram']['botToken'])
except:
    print('7391346583:AAHoXuebz21gds-FqZAlQh5kbSHFcXHaN5w')
" 2>/dev/null)
CHAT_ID="6978208486"

log() {
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [$JOB] $1" >> "$LOG_DIR/dispatch.log"
}

# Trim dispatch log
if [ -f "$LOG_DIR/dispatch.log" ] && [ "$(wc -l < "$LOG_DIR/dispatch.log" 2>/dev/null)" -gt 2000 ]; then
    tail -1000 "$LOG_DIR/dispatch.log" > "$LOG_DIR/dispatch.log.tmp" && mv "$LOG_DIR/dispatch.log.tmp" "$LOG_DIR/dispatch.log"
fi

send_telegram() {
    local msg="$1"
    local parse_mode="${2:-HTML}"
    # Telegram has 4096 char limit per message
    local len=${#msg}
    if [ "$len" -gt 4000 ]; then
        # Split into chunks
        local chunk_size=3900
        local offset=0
        local part=1
        while [ "$offset" -lt "$len" ]; do
            local chunk="${msg:$offset:$chunk_size}"
            if [ "$part" -gt 1 ]; then
                chunk="(续${part}) ${chunk}"
            fi
            curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
                -d "chat_id=${CHAT_ID}" \
                --data-urlencode "text=${chunk}" \
                -d "parse_mode=${parse_mode}" > /dev/null 2>&1
            offset=$((offset + chunk_size))
            part=$((part + 1))
            sleep 1
        done
    else
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d "chat_id=${CHAT_ID}" \
            --data-urlencode "text=${msg}" \
            -d "parse_mode=${parse_mode}" > /dev/null 2>&1
    fi
}

# ═══════════════════════════════════════════════
# BTC 30-min Paper Trading Update
# ═══════════════════════════════════════════════
job_btc_30min() {
    log "START"
    local output
    output=$(python3 << 'PYEOF'
import json, os, re, time, subprocess, glob

def load_state(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def parse_log_summary(log_path):
    """Parse last P&L status line from log. Format: P&L: $+0.15 (55, 52.7% WR, 32 flash)"""
    try:
        with open(log_path, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 8192))
            tail = f.read().decode('utf-8', errors='ignore')
        lines = tail.strip().split('\n')
        for line in reversed(lines):
            m = re.search(r'P&L: \$([+-]?\d+\.\d+) \((\d+), ([\d.]+)% WR, (\d+) flash\)', line)
            if m:
                return {
                    'pnl': float(m.group(1)),
                    'trades': int(m.group(2)),
                    'wr': float(m.group(3)),
                    'flash': int(m.group(4))
                }
    except:
        pass
    return None

def aggregate_crypto_sessions(vnum):
    """Aggregate ALL today's session files for a crypto version (survives restarts)."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime('%Y%m%d')
    pattern = f"{base}/data/rt_v{vnum}_{today}*.json"
    files = sorted(glob.glob(pattern))
    total_trades = 0
    total_pnl = 0.0
    wins = 0
    flash = 0
    for f in files:
        try:
            d = json.load(open(f))
            trades = d.get('trades', [])
            total_trades += len(trades)
            total_pnl += d.get('pnl', 0)
            wins += sum(1 for t in trades if t.get('pnl', 0) > 0)
            flash += d.get('flash_filtered', 0)
        except:
            pass
    # Also check persistent state file
    state_path = f"{base}/data/rt_v{vnum}_state.json"
    try:
        sd = json.load(open(state_path))
        # Only add if state has trades not in session files
        st = sd.get('trades', [])
        if st and total_trades == 0:
            total_trades = len(st)
            total_pnl = sd.get('pnl', 0)
            wins = sum(1 for t in st if t.get('pnl', 0) > 0)
    except:
        pass
    if total_trades == 0:
        return None
    wr = (wins / total_trades * 100) if total_trades > 0 else 0
    return {'pnl': total_pnl, 'trades': total_trades, 'wr': wr, 'flash': flash}

def fmt_pnl(v):
    return f"+${v:.2f}" if v >= 0 else f"-${abs(v):.2f}"

base = "/home/clawdbot/clawd/btc-arbitrage"

# ═══════════════════════════════════════════════
# DYNAMIC: Only show RUNNING crypto versions (skip dead/killed ones)
# ═══════════════════════════════════════════════
procs = subprocess.run(["pgrep", "-af", "realtime_paper_trader"], capture_output=True, text=True)
proc_lines = procs.stdout.strip().split('\n') if procs.stdout.strip() else []

running_versions = {}
for line in proc_lines:
    m = re.search(r'paper_trader_v(\d+)\.py', line)
    if m:
        vnum = m.group(1)
        running_versions[f"V{vnum}"] = True

lines = ["📊 Trading Fleet 30min Update\n"]

# --- Crypto Section ---
if running_versions:
    lines.append("💰 Crypto:")
    for vname in sorted(running_versions.keys(), key=lambda x: int(x[1:])):
        vnum = vname[1:]
        # Aggregate ALL today's sessions (survives restarts)
        agg = aggregate_crypto_sessions(vnum)
        if agg:
            restarts = len(glob.glob(f"{base}/data/rt_v{vnum}_{__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y%m%d')}*.json"))
            restart_note = f" 🔄×{restarts}" if restarts > 1 else ""
            lines.append(f"  ✅ {vname}: {fmt_pnl(agg['pnl'])} | {agg['trades']}笔 | WR {agg['wr']:.0f}% | Flash:{agg['flash']}{restart_note}")
        else:
            # Fallback to log parsing for current session
            log_path = f"{base}/logs/rt_v{vnum}_live.log"
            log_data = parse_log_summary(log_path)
            if log_data:
                lines.append(f"  ✅ {vname}: {fmt_pnl(log_data['pnl'])} | {log_data['trades']}笔 | WR {log_data['wr']:.0f}% | Flash:{log_data['flash']}")
            else:
                lines.append(f"  ✅ {vname}: 启动中...")
else:
    lines.append("💰 Crypto: 无运行中")

# --- Weather Section ---
# Weather: prefer V2 state, fallback to V1
w_alive = bool(subprocess.run(["pgrep", "-f", "weather_paper_trader"], capture_output=True, text=True).stdout.strip())
w_v2_path = f"{base}/weather_trader_v2_state.json"
w_v1_path = f"{base}/weather_trader_state.json"
ws_path = w_v2_path if os.path.exists(w_v2_path) else w_v1_path
if os.path.exists(ws_path):
    ws = load_state(ws_path)
    w_status = "✅" if w_alive else "💀"
    w_trades = ws.get("total_trades", 0)
    w_pnl = ws.get("total_pnl", 0)
    w_wins = ws.get("wins", 0)
    w_losses = ws.get("losses", 0)
    w_positions = len(ws.get("positions", []))
    ver = "V2" if "v2" in ws_path else "V1⚠️"
    lines.append(f"\n🌡️ Weather ({ver}):")
    lines.append(f"  {w_status} {w_trades}笔 | P&L: {fmt_pnl(w_pnl)} | W/L: {w_wins}/{w_losses} | Open: {w_positions}")

# --- Mention Section ---
mention_state = f"{base}/mention_trader_state.json"
m_alive = bool(subprocess.run(["pgrep", "-f", "mention_paper_trader"], capture_output=True, text=True).stdout.strip())
if os.path.exists(mention_state):
    ms = load_state(mention_state)
    m_status = "✅" if m_alive else "💀"
    m_trades = ms.get("total_trades", 0)
    m_pnl = ms.get("total_pnl", 0)
    m_wins = ms.get("wins", 0)
    m_losses = ms.get("losses", 0)
    m_open = len(ms.get("positions", []))
    lines.append(f"\n🗣️ Mention:")
    lines.append(f"  {m_status} {m_trades}笔 | P&L: {fmt_pnl(m_pnl)} | W/L: {m_wins}/{m_losses} | Open: {m_open}")

# --- NBA Section ---
nba_state = f"{base}/nba_trader_state.json"
n_alive = bool(subprocess.run(["pgrep", "-f", "nba_paper_trader"], capture_output=True, text=True).stdout.strip())
if os.path.exists(nba_state):
    ns = load_state(nba_state)
    n_status = "✅" if n_alive else "💀"
    n_trades = ns.get("total_trades", 0)
    n_pnl = ns.get("total_pnl", 0)
    n_wins = ns.get("wins", 0)
    n_losses = ns.get("losses", 0)
    n_open = len(ns.get("positions", []))
    lines.append(f"\n🏀 NBA:")
    lines.append(f"  {n_status} {n_trades}笔 | P&L: {fmt_pnl(n_pnl)} | W/L: {n_wins}/{n_losses} | Open: {n_open}")

# --- Cross-Platform Section ---
cp_state = f"{base}/crossplatform_trader_state.json"
cp_alive = bool(subprocess.run(["pgrep", "-f", "crossplatform_paper_trader"], capture_output=True, text=True).stdout.strip())
if os.path.exists(cp_state):
    cs = load_state(cp_state)
    cp_status = "✅" if cp_alive else "💀"
    pt = cs.get("paper_trading", {})
    cp_trades = pt.get("total_trades", cs.get("total_trades", 0))
    cp_pnl = pt.get("total_pnl", cs.get("total_pnl", 0))
    cp_open = pt.get("open_trades", 0)
    cp_pairs = len(cs.get("active_pairs", cs.get("tracked_pairs", cs.get("pairs", {}))))
    data_pts = 0
    try:
        with open(f"{base}/data/cross_platform_prices.jsonl") as f:
            data_pts = sum(1 for _ in f)
    except: pass
    lines.append(f"\n📊 Cross-Platform:")
    lines.append(f"  {cp_status} {cp_trades}笔(open:{cp_open}) | P&L: {fmt_pnl(cp_pnl)} | Pairs: {cp_pairs} | Data: {data_pts}条")

lines.append("")

# Market prices
try:
    import urllib.request
    btc_data = json.loads(urllib.request.urlopen("https://api.binance.us/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=5).read())
    eth_data = json.loads(urllib.request.urlopen("https://api.binance.us/api/v3/ticker/24hr?symbol=ETHUSDT", timeout=5).read())
    lines.append(f"BTC ${float(btc_data['lastPrice']):,.0f} ({float(btc_data['priceChangePercent']):+.1f}%) | ETH ${float(eth_data['lastPrice']):,.0f} ({float(eth_data['priceChangePercent']):+.1f}%)")
except:
    lines.append("Market data unavailable")

lines.append(f"\n⏰ {time.strftime('%H:%M UTC')}")
print("\n".join(lines))
PYEOF
    )

    if [ -n "$output" ]; then
        send_telegram "$output" ""
        log "SENT: $(echo "$output" | wc -c) bytes"
    else
        log "ERROR: no output"
    fi
}

# ═══════════════════════════════════════════════
# Kalshi Hourly Report
# ═══════════════════════════════════════════════
job_kalshi_hourly() {
    log "START"

    # Step 1: Position monitor (fast, ~5s)
    local positions
    positions=$(cd /home/clawdbot/clawd/kalshi && timeout 30 python3 position_monitor.py 2>&1) || positions="持仓数据获取失败"

    # Step 2: Market scan (slow, ~120s, scans 500+ markets)
    # stderr has progress bars, only capture stdout for the report
    local scan
    scan=$(cd /home/clawdbot/clawd/kalshi && timeout 150 python3 -c "
from report_v2 import scan_and_decide
result = scan_and_decide()
print(result)
" 2>/dev/null) || scan="市场扫描超时"

    # Step 3: Portfolio analysis (sizing, risk, recommendations)
    local analysis
    analysis=$(cd /home/clawdbot/clawd/kalshi && timeout 30 python3 portfolio_analysis.py 2>&1) || analysis=""

    # Combine
    local output="📈 Kalshi Hourly Report

${positions:-无持仓数据}

${analysis}
${scan:-无新机会}

⏰ $(date -u +%H:%M\ UTC)"

    send_telegram "$output" ""
    log "SENT"
}

# ═══════════════════════════════════════════════
# Market Alert Monitor (4h)
# ═══════════════════════════════════════════════
job_market_alert() {
    log "START"
    local alert
    alert=$(cd /home/clawdbot/clawd/market-report && python3 market_report.py --alert-only 2>&1) || true

    if [ -n "$alert" ] && [ "$alert" != "" ]; then
        # Has alert — get full report
        local report
        report=$(cd /home/clawdbot/clawd/market-report && python3 market_report.py 2>&1) || true
        if [ -n "$report" ]; then
            send_telegram "📊 市场异动报告

${report}

⏰ $(date -u +%H:%M\ UTC)" ""
            log "SENT: alert + full report"
        fi
    else
        log "NO ALERT"
    fi
}

# ═══════════════════════════════════════════════
# Market Report (premarket/midday/close)
# ═══════════════════════════════════════════════
job_market_report() {
    log "START"
    local report
    report=$(cd /home/clawdbot/clawd/market-report && python3 market_report.py 2>&1) || true

    if [ -n "$report" ]; then
        local label="${2:-}"
        send_telegram "📊 ${label:-Market Report}

${report}

⏰ $(date -u +%H:%M\ UTC)" ""
        log "SENT: ${label}"
    else
        log "ERROR: no output"
    fi
}

# ═══════════════════════════════════════════════
# X Auto-Poster (10min)
# ═══════════════════════════════════════════════
job_x_auto_poster() {
    log "START"
    local output
    output=$(cd /home/clawdbot/clawd && python3 scripts/x-queue-post.py 2>&1) || true
    
    if echo "$output" | grep -qi "posted\|success\|url"; then
        log "POSTED: $output"
    else
        log "QUEUE EMPTY or ERROR: ${output:0:100}"
    fi
}

# ═══════════════════════════════════════════════
# MAIN DISPATCHER
# ═══════════════════════════════════════════════
case "$JOB" in
    btc-30min)
        job_btc_30min
        ;;
    kalshi-hourly)
        job_kalshi_hourly
        ;;
    market-alert)
        job_market_alert
        ;;
    market-report-premarket)
        job_market_report "$@" "美股盘前报告"
        ;;
    market-report-midday)
        job_market_report "$@" "美股午间报告"
        ;;
    market-report-close)
        job_market_report "$@" "美股收盘报告"
        ;;
    x-auto-poster)
        job_x_auto_poster
        ;;
    test)
        send_telegram "🧪 Cron dispatcher test — $(date -u +%H:%M:%S\ UTC)" ""
        log "TEST sent"
        ;;
    *)
        echo "Usage: cron-dispatcher.sh {btc-30min|kalshi-hourly|market-alert|market-report-premarket|market-report-midday|market-report-close|x-auto-poster|test}"
        exit 1
        ;;
esac
