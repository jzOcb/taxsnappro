#!/usr/bin/env python3
"""
Kalshi News-Driven Scanner (Strategy A from V2).

Scans recent political/economic news → matches to Kalshi markets → flags mispricings.
Integrates with notify.py for heartbeat scanning.

Usage:
    python3 news_scanner.py              # Full scan
    python3 news_scanner.py --brief      # Quick summary only
"""
import sys
sys.path.insert(0, '/tmp/pip_packages')

import requests
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"

# Key political/economic series to monitor
WATCH_SERIES = {
    'KXGDP': 'GDP Growth',
    'KXCPI': 'CPI Inflation',
    'KXFEDRATE': 'Fed Rate',
    'KXSPENDING': 'Gov Spending/DOGE',
    'KXTRUMP': 'Trump Actions',
    'KXTRUMPMEETING': 'Trump Meetings',
    'KXSCOTUS': 'Supreme Court',
    'KXTARIFF': 'Tariffs',
    'KXDEBT': 'Debt Ceiling',
    'KXUNEMPLOY': 'Unemployment',
}

# News topics to monitor
NEWS_TOPICS = [
    ('government shutdown', '🏛️'),
    ('trump executive order', '📜'),
    ('federal reserve rate', '🏦'),
    ('tariff trade war', '📦'),
    ('supreme court ruling', '⚖️'),
    ('GDP growth estimate', '📈'),
    ('CPI inflation', '📊'),
    ('DOGE spending cuts', '🐕'),
    ('debt ceiling', '💰'),
    ('cabinet confirmation senate', '🏛️'),
]


def get_news(query, days=3, max_results=5):
    """Get recent news headlines from Google News RSS."""
    try:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&when={days}d"
        r = requests.get(url, timeout=10)
        items = re.findall(r'<title>(.*?)</title>', r.text)[2:2+max_results]
        return [re.sub(r'<[^>]+>', '', h).strip() for h in items]
    except:
        return []


def get_series_markets(series_ticker):
    """Get active markets for a series."""
    try:
        r = requests.get(f"{KALSHI_API}/markets", 
                        params={"series_ticker": series_ticker, "limit": 30, "status": "open"},
                        timeout=10)
        return [m for m in r.json().get("markets", []) if (m.get('volume', 0) or 0) > 0]
    except:
        return []


def scan_news():
    """Scan news topics and return headlines."""
    results = {}
    for topic, emoji in NEWS_TOPICS:
        headlines = get_news(topic, days=3, max_results=3)
        if headlines:
            results[topic] = {'emoji': emoji, 'headlines': headlines}
    return results


def scan_markets():
    """Scan watched market series."""
    results = {}
    for series, label in WATCH_SERIES.items():
        markets = get_series_markets(series)
        if markets:
            # Flag non-extreme prices as potential opportunities
            opportunities = []
            for m in markets:
                yes = m.get('yes_ask', 0) or m.get('last_price', 0) or 0
                vol = m.get('volume', 0)
                if 15 < yes < 85 and vol > 100:
                    opportunities.append({
                        'title': m.get('title', ''),
                        'yes': yes,
                        'volume': vol,
                        'close': m.get('close_time', '')[:10],
                        'ticker': m.get('ticker', ''),
                    })
            results[series] = {
                'label': label,
                'total': len(markets),
                'opportunities': opportunities,
            }
    return results


def run_scan(brief=False):
    """Run full news + market scan."""
    now = datetime.now(timezone.utc)
    print(f"📰 News-Driven Scan — {now.strftime('%m/%d %H:%M UTC')}")
    
    # News scan
    news = scan_news()
    if news:
        print(f"\n{'='*60}")
        print("BREAKING NEWS")
        print(f"{'='*60}")
        for topic, data in news.items():
            if not brief:
                print(f"\n{data['emoji']} {topic.upper()}")
                for h in data['headlines']:
                    print(f"  • {h[:75]}")
    
    # Market scan
    markets = scan_markets()
    if markets:
        print(f"\n{'='*60}")
        print("MARKET OPPORTUNITIES")
        print(f"{'='*60}")
        for series, data in markets.items():
            if data['opportunities']:
                print(f"\n📌 {data['label']} ({data['total']} markets)")
                for opp in data['opportunities'][:5]:
                    print(f"  🎯 {opp['yes']:>3}¢ | {opp['title'][:50]:50s} | vol:{opp['volume']:>7}")
    
    # Cross-reference summary
    alerts = []
    
    # Check: shutdown news + any shutdown markets
    if 'government shutdown' in news:
        alerts.append("🚨 ACTIVE SHUTDOWN — check for shutdown duration/resolution markets")
    
    # Check: tariff news + CPI markets
    if 'tariff trade war' in news and 'KXCPI' in markets:
        cpi_opps = markets['KXCPI']['opportunities']
        if cpi_opps:
            alerts.append(f"📦→📊 Tariff escalation could push CPI higher. CPI >0.3% at {cpi_opps[0]['yes']}¢")
    
    # Check: GDP data
    if 'KXGDP' in markets:
        gdp_opps = markets['KXGDP']['opportunities']
        if gdp_opps:
            alerts.append(f"📈 GDP markets active: >4% at {gdp_opps[0]['yes']}¢ (Q3 was 4.4%)")
    
    if alerts:
        print(f"\n{'='*60}")
        print("⚡ ACTION ITEMS")
        print(f"{'='*60}")
        for a in alerts:
            print(f"  {a}")
    
    return {'news': news, 'markets': markets, 'alerts': alerts}


if __name__ == '__main__':
    brief = '--brief' in sys.argv
    run_scan(brief=brief)
