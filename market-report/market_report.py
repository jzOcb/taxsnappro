#!/usr/bin/env python3
"""
US Stock Market Report Generator

Generates comprehensive market reports covering:
- Major indices (S&P 500, Nasdaq, Dow, Russell 2000)
- Sector performance (XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLU, XLRE, XLB, XLC)
- Top movers in major stocks
- Market breadth indicators
- Key macro signals (VIX, DXY, Gold, Oil, 10Y yield)

Usage:
    python3 market_report.py                    # Full report to stdout
    python3 market_report.py --output /tmp/report.txt  # Save to file
    python3 market_report.py --alert-only       # Only output if significant moves detected
    python3 market_report.py --json             # JSON output for programmatic use
"""

import yfinance as yf
import json
import sys
import os
from datetime import datetime, timedelta
import argparse

# === Configuration ===

INDICES = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "^DJI": "Dow Jones",
    "^RUT": "Russell 2000",
}

SECTORS = {
    "XLK": "科技",
    "XLF": "金融",
    "XLE": "能源",
    "XLV": "医疗",
    "XLY": "消费可选",
    "XLP": "消费必需",
    "XLI": "工业",
    "XLU": "公用事业",
    "XLRE": "房地产",
    "XLB": "材料",
    "XLC": "通信",
}

MACRO = {
    "^VIX": "VIX恐慌指数",
    "GC=F": "黄金",
    "CL=F": "原油WTI",
    "^TNX": "10Y国债",
    "DX-Y.NYB": "美元指数",
    "BTC-USD": "比特币",
}

# Mag7 + key stocks to track
WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",  # Mag7
    "PLTR", "CRM", "NOW", "WDAY",  # Software/AI
    "JPM", "GS", "WFC",  # Banks
    "WMT", "COST",  # Retail
    "NVO", "LLY", "MRK",  # Pharma
    "COIN", "MSTR",  # Crypto-adjacent
]

# Alert thresholds
ALERT_THRESHOLDS = {
    "index_move_pct": 1.5,      # Index moves > 1.5%
    "vix_level": 25,            # VIX above 25
    "vix_spike_pct": 15,        # VIX daily spike > 15%
    "stock_move_pct": 8,        # Individual stock > 8%
    "sector_move_pct": 3,       # Sector ETF > 3%
}


def get_quote_data(tickers_list):
    """Fetch current quotes for a list of tickers."""
    results = {}
    try:
        tickers_str = " ".join(tickers_list)
        tickers = yf.Tickers(tickers_str)
        for symbol in tickers_list:
            try:
                t = tickers.tickers[symbol]
                info = t.fast_info
                price = getattr(info, 'last_price', None)
                prev_close = getattr(info, 'previous_close', None)
                
                if price and prev_close and prev_close > 0:
                    change_pct = ((price - prev_close) / prev_close) * 100
                else:
                    # Fallback to history
                    hist = t.history(period="2d")
                    if len(hist) >= 2:
                        price = hist['Close'].iloc[-1]
                        prev_close = hist['Close'].iloc[-2]
                        change_pct = ((price - prev_close) / prev_close) * 100
                    elif len(hist) == 1:
                        price = hist['Close'].iloc[-1]
                        change_pct = 0
                    else:
                        continue
                
                results[symbol] = {
                    "price": round(float(price), 2),
                    "prev_close": round(float(prev_close), 2) if prev_close else None,
                    "change_pct": round(float(change_pct), 2),
                }
            except Exception as e:
                pass  # Skip failed tickers silently
    except Exception as e:
        print(f"Error fetching batch: {e}", file=sys.stderr)
    
    return results


def check_alerts(indices_data, sectors_data, macro_data, watchlist_data):
    """Check for significant market events that warrant an alert."""
    alerts = []
    
    # Check index moves
    for symbol, data in indices_data.items():
        name = INDICES.get(symbol, symbol)
        if abs(data["change_pct"]) >= ALERT_THRESHOLDS["index_move_pct"]:
            direction = "暴涨" if data["change_pct"] > 0 else "暴跌"
            alerts.append(f"🚨 {name} {direction} {data['change_pct']:+.1f}%")
    
    # Check VIX
    if "^VIX" in macro_data:
        vix = macro_data["^VIX"]
        if vix["price"] >= ALERT_THRESHOLDS["vix_level"]:
            alerts.append(f"🚨 VIX 恐慌指数飙升至 {vix['price']:.1f}")
        if abs(vix["change_pct"]) >= ALERT_THRESHOLDS["vix_spike_pct"]:
            alerts.append(f"🚨 VIX 日内变动 {vix['change_pct']:+.1f}%")
    
    # Check sector moves
    for symbol, data in sectors_data.items():
        name = SECTORS.get(symbol, symbol)
        if abs(data["change_pct"]) >= ALERT_THRESHOLDS["sector_move_pct"]:
            direction = "大涨" if data["change_pct"] > 0 else "大跌"
            alerts.append(f"⚠️ {name}板块 {direction} {data['change_pct']:+.1f}%")
    
    # Check individual stock moves
    for symbol, data in watchlist_data.items():
        if abs(data["change_pct"]) >= ALERT_THRESHOLDS["stock_move_pct"]:
            direction = "飙升" if data["change_pct"] > 0 else "暴跌"
            alerts.append(f"⚠️ {symbol} {direction} {data['change_pct']:+.1f}% (${data['price']})")
    
    return alerts


def format_report(indices_data, sectors_data, macro_data, watchlist_data, alerts):
    """Format the market report as a readable text."""
    now = datetime.utcnow()
    lines = []
    
    # Header
    if alerts:
        lines.append("🚨 美股市场警报 🚨")
        for a in alerts:
            lines.append(a)
        lines.append("")
    
    lines.append(f"📊 美股市场报告 — {now.strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")
    
    # Indices
    lines.append("📈 主要指数")
    for symbol, name in INDICES.items():
        if symbol in indices_data:
            d = indices_data[symbol]
            emoji = "🟢" if d["change_pct"] >= 0 else "🔴"
            lines.append(f"  {emoji} {name}: {d['price']:,.1f} ({d['change_pct']:+.1f}%)")
    lines.append("")
    
    # Macro
    lines.append("🌍 宏观信号")
    for symbol, name in MACRO.items():
        if symbol in macro_data:
            d = macro_data[symbol]
            emoji = "🟢" if d["change_pct"] >= 0 else "🔴"
            if symbol == "^TNX":
                lines.append(f"  {emoji} {name}: {d['price']:.2f}% ({d['change_pct']:+.1f}%)")
            else:
                lines.append(f"  {emoji} {name}: ${d['price']:,.1f} ({d['change_pct']:+.1f}%)")
    lines.append("")
    
    # Sectors - sorted by change
    lines.append("🏭 板块表现（涨跌排序）")
    sorted_sectors = sorted(
        [(s, SECTORS[s], sectors_data[s]) for s in SECTORS if s in sectors_data],
        key=lambda x: x[2]["change_pct"],
        reverse=True
    )
    for symbol, name, d in sorted_sectors:
        emoji = "🟢" if d["change_pct"] >= 0 else "🔴"
        bar_len = min(int(abs(d["change_pct"]) * 5), 20)
        bar = "█" * bar_len if bar_len > 0 else "▏"
        lines.append(f"  {emoji} {name:6s} {d['change_pct']:+5.1f}% {bar}")
    lines.append("")
    
    # Top movers in watchlist
    if watchlist_data:
        sorted_watch = sorted(
            [(s, watchlist_data[s]) for s in watchlist_data],
            key=lambda x: x[1]["change_pct"],
            reverse=True
        )
        
        # Top gainers
        gainers = [(s, d) for s, d in sorted_watch if d["change_pct"] > 0][:5]
        losers = [(s, d) for s, d in sorted_watch if d["change_pct"] < 0][-5:]
        losers.reverse()
        
        if gainers:
            lines.append("🚀 今日领涨")
            for s, d in gainers:
                lines.append(f"  🟢 {s:6s} ${d['price']:>8.1f}  {d['change_pct']:+.1f}%")
        
        if losers:
            lines.append("💀 今日领跌")
            for s, d in losers:
                lines.append(f"  🔴 {s:6s} ${d['price']:>8.1f}  {d['change_pct']:+.1f}%")
    
    return "\n".join(lines)


def generate_report(alert_only=False, output_json=False):
    """Main report generation function."""
    # Fetch all data
    all_tickers = list(INDICES.keys()) + list(SECTORS.keys()) + list(MACRO.keys()) + WATCHLIST
    all_data = get_quote_data(all_tickers)
    
    # Split into categories
    indices_data = {k: all_data[k] for k in INDICES if k in all_data}
    sectors_data = {k: all_data[k] for k in SECTORS if k in all_data}
    macro_data = {k: all_data[k] for k in MACRO if k in all_data}
    watchlist_data = {k: all_data[k] for k in WATCHLIST if k in all_data}
    
    # Check alerts
    alerts = check_alerts(indices_data, sectors_data, macro_data, watchlist_data)
    
    if alert_only and not alerts:
        return None
    
    if output_json:
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "alerts": alerts,
            "indices": indices_data,
            "sectors": sectors_data,
            "macro": macro_data,
            "watchlist": watchlist_data,
        }, indent=2, ensure_ascii=False)
    
    return format_report(indices_data, sectors_data, macro_data, watchlist_data, alerts)


def main():
    parser = argparse.ArgumentParser(description="US Stock Market Report Generator")
    parser.add_argument("--output", help="Save report to file")
    parser.add_argument("--alert-only", action="store_true", help="Only output if alerts triggered")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    report = generate_report(alert_only=args.alert_only, output_json=args.json)
    
    if report is None:
        sys.exit(0)  # No alerts, silent exit
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
