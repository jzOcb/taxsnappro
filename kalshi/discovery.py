#!/usr/bin/env python3
"""Kalshi Market Discovery — Smart series scanner with categorization."""
import sys, os, json, time
sys.path.insert(0, '/tmp/pip_packages')
import requests

API = "https://api.elections.kalshi.com/trade-api/v2"
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
SERIES_CACHE = os.path.join(CACHE_DIR, 'series.json')
CACHE_TTL = 3600 * 6  # 6 hours

# Category keywords for classification
CATEGORIES = {
    'Politics': ['trump', 'biden', 'congress', 'senate', 'house', 'governor', 'election', 'president', 'democrat', 'republican', 'gop', 'nominee', 'cabinet', 'impeach', 'party', 'vote', 'ballot', 'primary'],
    'Economics': ['gdp', 'cpi', 'inflation', 'fed', 'rate', 'recession', 'unemployment', 'jobs', 'debt', 'deficit', 'tariff', 'trade', 'treasury', 'stock', 'sp500', 'nasdaq', 'bitcoin', 'crypto', 'housing', 'oil', 'gas'],
    'Geopolitics': ['ukraine', 'russia', 'china', 'iran', 'israel', 'nato', 'greenland', 'taiwan', 'korea', 'putin', 'xi', 'war', 'peace', 'sanction', 'missile', 'nuclear', 'treaty'],
    'Government': ['shutdown', 'doge', 'spending', 'funding', 'scotus', 'supreme court', 'executive order', 'veto', 'filibuster', 'cr ', 'continuing resolution', 'bill', 'act'],
    'Tech': ['ai ', 'openai', 'anthropic', 'tesla', 'spacex', 'mars', 'moon', 'fusion', 'quantum', 'deepseek', 'ipo', 'fsd'],
    'Culture': ['pope', 'oscar', 'grammy', 'swift', 'musk', 'celebrity', 'movie', 'music', 'book'],
    'Sports': ['nba', 'nfl', 'nhl', 'mlb', 'ncaa', 'epl', 'serie', 'laliga', 'ufc', 'boxing', 'tennis', 'pga', 'nascar', 'f1race', 'wnba', 'mls', 'fifa', 'parlay', 'mvesports'],
}

# Must-watch series
PRIORITY_SERIES = [
    'KXGDP', 'KXCPI', 'KXFED', 'KXGOVSHUTLENGTH', 'KXTRUMPMEETING',
    'KXGREENLAND', 'KXSCOTUS', 'KXRECESSION', 'KXUKRAINE', 'KXIRAN',
    'KXBITCOIN', 'KXSP500', 'KXDOGE', 'KXGOVTCUTS', 'KXGOVTSPEND',
    'KXDEBT', 'KXCR', 'KXSHUTDOWNBY', 'KXTARIFF', 'KXFEDRATE',
    'KXCABINET', 'KXTERMINALRATE', 'KXLOWESTRATE',
]


def fetch_all_series(use_cache=True):
    """Fetch all series from Kalshi API with caching."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    if use_cache and os.path.exists(SERIES_CACHE):
        age = time.time() - os.path.getmtime(SERIES_CACHE)
        if age < CACHE_TTL:
            with open(SERIES_CACHE) as f:
                data = json.load(f)
            print(f"  (cached, {int(age/60)}m old, {len(data)} series)")
            return data
    
    all_series = []
    cursor = None
    for page in range(100):
        params = {'limit': 200}
        if cursor:
            params['cursor'] = cursor
        try:
            r = requests.get(f'{API}/series', params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            batch = data.get('series', [])
            all_series.extend(batch)
            cursor = data.get('cursor')
            if not cursor or not batch:
                break
        except Exception as e:
            print(f"  Error page {page}: {e}")
            break
    
    # Save cache
    try:
        with open(SERIES_CACHE, 'w') as f:
            json.dump(all_series, f)
    except:
        pass
    
    print(f"  Fetched {len(all_series)} series")
    return all_series


def categorize(ticker, title):
    """Categorize a series by keywords."""
    text = f"{ticker} {title}".lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                return cat
    return 'Other'


def fetch_markets_for_series(series_ticker, status='open'):
    """Fetch active markets for a series."""
    try:
        r = requests.get(f'{API}/markets', params={
            'limit': 50, 'status': status, 'series_ticker': series_ticker
        }, timeout=10)
        return r.json().get('markets', [])
    except:
        return []


def scan_priority_series():
    """Scan priority series for tradeable opportunities."""
    results = []
    for s in PRIORITY_SERIES:
        markets = fetch_markets_for_series(s)
        tradeable = [m for m in markets if 5 <= (m.get('yes_ask', 0) or 0) <= 95]
        if tradeable:
            results.append((s, tradeable))
        time.sleep(0.1)  # Rate limit
    return results


def scan_all_categories():
    """Full discovery: categorize all series, find tradeable markets."""
    series_list = fetch_all_series()
    
    # Categorize
    by_cat = {}
    for s in series_list:
        ticker = s.get('ticker', '')
        title = s.get('title', '')
        cat = categorize(ticker, title)
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(s)
    
    return by_cat


def main():
    import datetime
    now = datetime.datetime.utcnow().strftime('%m/%d %H:%M UTC')
    print(f"🔍 Kalshi Market Discovery — {now}")
    
    full_mode = '--full' in sys.argv
    
    # 1. Quick mode: just scan priority series
    print(f"\n{'='*60}")
    print("🎯 PRIORITY SERIES — Tradeable Markets")
    print(f"{'='*60}\n")
    
    results = scan_priority_series()
    
    total_opps = 0
    for series_ticker, markets in results:
        markets.sort(key=lambda m: m.get('volume', 0), reverse=True)
        print(f"📌 {series_ticker} ({len(markets)} tradeable)")
        for m in markets[:5]:
            yes = m.get('yes_ask', 0) or 0
            vol = m.get('volume', 0)
            close = m.get('close_time', '')[:10]
            title = m.get('title', '')[:60]
            flag = '🎯' if 20 <= yes <= 80 else '  '
            print(f"  {flag} {yes:>3}¢ | vol:{vol:>8,} | {close} | {title}")
            total_opps += 1
        print()
    
    print(f"📊 Priority scan: {total_opps} tradeable opportunities")
    
    # 2. Full mode: also scan all series (slow, ~5min)
    if full_mode:
        print(f"\n{'='*60}")
        print("📊 FULL SERIES SCAN (this takes a few minutes...)")
        print(f"{'='*60}\n")
        
        by_cat = scan_all_categories()
        
        print(f"{'Category':<15} {'Count':>6}")
        print("-" * 25)
        for cat in ['Politics', 'Economics', 'Geopolitics', 'Government', 'Tech', 'Culture', 'Sports', 'Other']:
            count = len(by_cat.get(cat, []))
            print(f"  {cat:<13} {count:>6}")
        
        # Find non-priority gems
        priority_set = set(PRIORITY_SERIES)
        gems = []
        
        for cat in ['Politics', 'Economics', 'Geopolitics', 'Government', 'Tech', 'Culture']:
            for s in by_cat.get(cat, [])[:50]:  # Cap per category
                ticker = s.get('ticker', '')
                if ticker in priority_set:
                    continue
                markets = fetch_markets_for_series(ticker)
                tradeable = [m for m in markets if 15 <= (m.get('yes_ask', 0) or 0) <= 85]
                if tradeable:
                    top = max(tradeable, key=lambda m: m.get('volume', 0))
                    if top.get('volume', 0) > 1000:
                        gems.append((cat, ticker, s.get('title', ''), top))
                time.sleep(0.05)
        
        gems.sort(key=lambda x: x[3].get('volume', 0), reverse=True)
        print(f"\n💎 NON-PRIORITY GEMS:")
        for cat, ticker, stitle, m in gems[:20]:
            yes = m.get('yes_ask', 0) or 0
            vol = m.get('volume', 0)
            title = m.get('title', '')[:55]
            print(f"  [{cat[:4]}] {yes:>3}¢ | vol:{vol:>8,} | {ticker:<25} | {title}")
    else:
        print("\n  (Use --full for complete series scan, takes ~5min)")


if __name__ == '__main__':
    main()
