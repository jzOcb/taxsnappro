#!/usr/bin/env python3
"""
Cross-Platform Price Comparison: Kalshi vs Polymarket.

Two modes:
1. Manual pairs — known equivalent markets
2. Auto-discovery — fuzzy match (Jaccard+Levenshtein, 60/40 weighted)

Run: python3 crossplatform.py          # Manual pairs only
     python3 crossplatform.py --auto   # + auto-discovery
"""
import sys
sys.path.insert(0, '/tmp/pip_packages')
import requests, json, re
from datetime import datetime, timezone

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
POLY_API = "https://gamma-api.polymarket.com"


# ─── Fuzzy Matching (from prediction-market-arbitrage-bot) ───

def tokenize(text):
    """Tokenize text for Jaccard similarity."""
    text = re.sub(r'[^a-z0-9\s]', '', text.lower())
    return set(text.split())

def jaccard(a, b):
    """Jaccard similarity between two strings."""
    sa, sb = tokenize(a), tokenize(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

def levenshtein_ratio(a, b):
    """Normalized Levenshtein similarity (1.0 = identical)."""
    a, b = a.lower(), b.lower()
    if not a or not b:
        return 0.0
    n, m = len(a), len(b)
    if n > m:
        a, b, n, m = b, a, m, n
    prev = list(range(n + 1))
    for j in range(1, m + 1):
        curr = [j] + [0] * n
        for i in range(1, n + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            curr[i] = min(curr[i-1] + 1, prev[i] + 1, prev[i-1] + cost)
        prev = curr
    dist = prev[n]
    return 1.0 - dist / max(n, m)

def similarity(text_a, text_b):
    """Weighted similarity: 60% Jaccard + 40% Levenshtein."""
    return 0.6 * jaccard(text_a, text_b) + 0.4 * levenshtein_ratio(text_a, text_b)


def auto_match_markets(kalshi_markets, poly_events, threshold=0.45):
    """Auto-match Kalshi markets to Polymarket events using fuzzy matching."""
    matches = []
    for km in kalshi_markets:
        k_title = km.get('title', '')
        best_score = 0
        best_match = None
        for pe in poly_events:
            for pm in pe.get('markets', []):
                p_title = pm.get('question', '') or pe.get('title', '')
                score = similarity(k_title, p_title)
                if score > best_score:
                    best_score = score
                    best_match = (pe, pm)
        
        if best_score >= threshold and best_match:
            matches.append({
                'kalshi': km,
                'poly_event': best_match[0],
                'poly_market': best_match[1],
                'score': best_score,
            })
    
    return sorted(matches, key=lambda x: x['score'], reverse=True)

# Manually paired markets (Kalshi series → Polymarket event slug)
# Updated: 2026-02-01
PAIRS = [
    {
        'name': '📈 GDP Q4 2025',
        'kalshi_series': 'KXGDP',
        'kalshi_filter': lambda t: 'q4' in t.lower() or '2025' in t.lower(),
        'poly_slug': 'us-gdp-q4-2025',
        'notes': 'GDPNow tracking 4.2%. Key thresholds: >3%, >3.5%, >4%',
    },
    {
        'name': '📊 CPI January 2026',
        'kalshi_series': 'KXCPI',
        'kalshi_filter': lambda t: 'january' in t.lower() or 'jan' in t.lower(),
        'poly_slug': 'cpi-monthly-january-2026',
        'notes': 'Feb 11 data release. Tariffs could push higher.',
    },
    {
        'name': '🏦 Fed Rate 2026',
        'kalshi_series': 'KXFED',
        'kalshi_filter': lambda t: any(x in t.lower() for x in ['march', 'june', 'jan']),
        'poly_slug': 'fed-decision-in-march',
        'notes': 'Compare rate cut/hold probabilities',
    },
    {
        'name': '🏛️ Gov Shutdown Duration',
        'kalshi_series': 'KXGOVSHUTLENGTH',
        'kalshi_filter': None,
        'poly_slug': 'us-government-shutdown-saturday',
        'notes': 'Shutdown active. Length markets on Kalshi.',
    },
    {
        'name': '🐕 DOGE Spending Cuts',
        'kalshi_series': 'KXGOVTCUTS',
        'kalshi_filter': None,
        'poly_slug': 'doge-spending-cuts',
        'notes': 'Will govt spending decrease by $X billion?',
    },
    {
        'name': '🇮🇷 US Strikes Iran',
        'kalshi_series': 'KXIRAN',
        'kalshi_filter': None,
        'poly_slug': 'us-strikes-iran-by',
        'notes': 'Time-bound markets on both platforms',
    },
    {
        'name': '🟢 Greenland Acquisition',
        'kalshi_series': 'KXGREENLAND',
        'kalshi_filter': None,
        'poly_slug': 'trump-greenland',
        'notes': 'Trump acquire Greenland before 2027',
    },
]


def get_kalshi_markets(series=None, search=None):
    """Get Kalshi markets by series or search."""
    markets = []
    if series:
        try:
            r = requests.get(f"{KALSHI_API}/markets", 
                           params={"series_ticker": series, "limit": 30, "status": "open"}, timeout=10)
            markets = [m for m in r.json().get("markets", []) if (m.get('volume', 0) or 0) > 0]
        except:
            pass
    return markets


def get_poly_event(slug):
    """Get Polymarket event markets."""
    try:
        r = requests.get(f"{POLY_API}/events", params={"slug": slug, "closed": "false"}, timeout=10)
        events = r.json()
        if events:
            return events[0] if isinstance(events, list) else events
    except:
        pass
    return None


def compare():
    """Run cross-platform comparison."""
    now = datetime.now(timezone.utc)
    print(f"🔄 Cross-Platform Scan — {now.strftime('%m/%d %H:%M UTC')}")
    
    for pair in PAIRS:
        print(f"\n{'='*50}")
        print(f"{pair['name']}")
        print(f"{'='*50}")
        
        # Kalshi side
        k_markets = get_kalshi_markets(series=pair.get('kalshi_series'))
        if pair.get('kalshi_filter'):
            k_markets = [m for m in k_markets if pair['kalshi_filter'](m.get('title', ''))]
        
        if k_markets:
            print(f"  KALSHI:")
            for m in k_markets[:5]:
                yes = m.get('yes_ask', 0) or m.get('last_price', 0) or 0
                print(f"    {yes:>3}¢ | {m.get('title', '')[:50]} | vol:{m.get('volume', 0)}")
        else:
            print(f"  KALSHI: No matching markets found")
        
        # Polymarket side
        poly_event = get_poly_event(pair.get('poly_slug', ''))
        if poly_event:
            poly_markets = poly_event.get('markets', [])
            if poly_markets:
                print(f"  POLYMARKET:")
                for m in poly_markets[:5]:
                    prices = m.get('outcomePrices', '')
                    if isinstance(prices, str):
                        try: prices = json.loads(prices)
                        except: prices = []
                    yes = float(prices[0])*100 if isinstance(prices, list) and prices else None
                    q = m.get('question', '')
                    vol = float(m.get('volume', 0) or 0)
                    if yes is not None:
                        print(f"    {yes:>5.1f}¢ | {q[:50]} | vol:${vol/1e6:.1f}M")
        else:
            print(f"  POLYMARKET: No matching event")
        
        if pair.get('notes'):
            print(f"  📝 {pair['notes']}")


def auto_discover():
    """Auto-discover cross-platform matches."""
    print(f"\n{'='*60}")
    print("🤖 AUTO-DISCOVERY (Fuzzy Matching)")
    print(f"{'='*60}\n")
    
    # Get top Polymarket events
    try:
        r = requests.get(f"{POLY_API}/events", params={
            'limit': 50, 'active': 'true', 'closed': 'false',
            'order': 'volume24hr', 'ascending': 'false'
        }, timeout=15)
        poly_events = r.json()
    except Exception as e:
        print(f"  Error fetching Polymarket: {e}")
        return
    
    # Filter out sports
    sports_kw = ['nba', 'nfl', 'nhl', 'mlb', 'epl', 'serie', 'ufc', 'lol:', 'ncaa']
    poly_events = [e for e in poly_events 
                   if not any(kw in e.get('title', '').lower() for kw in sports_kw)]
    
    # Get Kalshi political/econ markets
    kalshi_markets = []
    for series in ['KXGDP', 'KXCPI', 'KXFED', 'KXGOVSHUTLENGTH', 'KXTRUMPMEETING',
                   'KXGREENLAND', 'KXTARIFF', 'KXRECESSION', 'KXGOVTCUTS']:
        try:
            r = requests.get(f"{KALSHI_API}/markets", params={
                'series_ticker': series, 'limit': 10, 'status': 'open'
            }, timeout=10)
            markets = r.json().get('markets', [])
            # Only mid-priced with volume
            for m in markets:
                yes = m.get('yes_ask', 0) or 0
                if 10 <= yes <= 90 and m.get('volume', 0) > 500:
                    kalshi_markets.append(m)
        except:
            pass
    
    print(f"  Kalshi markets: {len(kalshi_markets)} | Polymarket events: {len(poly_events)}")
    print(f"  Matching...")
    
    matches = auto_match_markets(kalshi_markets, poly_events)
    
    if matches:
        print(f"\n  Found {len(matches)} potential matches:\n")
        for m in matches[:15]:
            km = m['kalshi']
            pm = m['poly_market']
            k_yes = km.get('yes_ask', 0) or 0
            
            # Parse Polymarket price
            prices = pm.get('outcomePrices', '')
            if isinstance(prices, str):
                try: prices = json.loads(prices)
                except: prices = []
            p_yes = float(prices[0]) * 100 if isinstance(prices, list) and prices else 0
            
            spread = abs(k_yes - p_yes)
            flag = '🚨' if spread > 5 else '  '
            
            print(f"  {flag} [{m['score']:.2f}] Kalshi {k_yes:>3.0f}¢ vs Poly {p_yes:>5.1f}¢ (spread: {spread:.1f}¢)")
            print(f"     K: {km.get('title','')[:55]}")
            print(f"     P: {pm.get('question', m['poly_event'].get('title',''))[:55]}")
            print()
    else:
        print("  No matches above threshold")


if __name__ == '__main__':
    compare()
    if '--auto' in sys.argv:
        auto_discover()
