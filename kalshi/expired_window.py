#!/usr/bin/env python3
"""
Kalshi Expired Window Scanner — Strategy B from V2.

Finds markets where the time window has already passed but price hasn't adjusted.
This is how the Putin phone call opportunity was found — "January" market still 
trading in February with event already confirmed.

Logic:
1. Find all markets with time-bound titles (January, February, Q1, before X date)
2. Check if current date is past the window
3. Search news to verify if event occurred within window
4. If event happened but price < 90¢ (YES) or > 10¢ (NO) → ALERT
"""

import sys
sys.path.insert(0, '/tmp/pip_packages')

import requests
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote

# Kalshi API
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"

# Time-related patterns in market titles
MONTH_PATTERNS = {
    'january': (1, 31), 'february': (2, 28), 'march': (3, 31),
    'april': (4, 30), 'may': (5, 31), 'june': (6, 30),
    'july': (7, 31), 'august': (8, 31), 'september': (9, 30),
    'october': (10, 31), 'november': (11, 30), 'december': (12, 31),
    'jan': (1, 31), 'feb': (2, 28), 'mar': (3, 31),
    'apr': (4, 30), 'jun': (6, 30), 'jul': (7, 31),
    'aug': (8, 31), 'sep': (9, 30), 'oct': (10, 31),
    'nov': (11, 30), 'dec': (12, 31),
}

QUARTER_PATTERNS = {
    'q1': (3, 31), 'q2': (6, 30), 'q3': (9, 30), 'q4': (12, 31),
    'first quarter': (3, 31), 'second quarter': (6, 30),
    'third quarter': (9, 30), 'fourth quarter': (12, 31),
}

BEFORE_PATTERN = re.compile(
    r'before\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})',
    re.IGNORECASE
)


def get_all_markets():
    """Fetch all active Kalshi markets."""
    markets = []
    cursor = None
    while True:
        params = {"limit": 200, "status": "open"}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(f"{KALSHI_API}/markets", params=params, timeout=15)
        if r.status_code != 200:
            break
        data = r.json()
        batch = data.get("markets", [])
        if not batch:
            break
        markets.extend(batch)
        cursor = data.get("cursor")
        if not cursor:
            break
    return markets


def extract_time_window(title, subtitle=""):
    """Extract time window end date from market title/subtitle."""
    text = f"{title} {subtitle}".lower()
    now = datetime.now(timezone.utc)
    year = now.year
    
    # Check "before DATE" pattern
    match = BEFORE_PATTERN.search(text)
    if match:
        month_name = match.group(1).lower()
        day = int(match.group(2))
        month_num = MONTH_PATTERNS.get(month_name, (0, 0))[0]
        if month_num:
            try:
                deadline = datetime(year, month_num, day, tzinfo=timezone.utc)
                # If deadline is far in the past, try next year
                if (now - deadline).days > 180:
                    deadline = datetime(year + 1, month_num, day, tzinfo=timezone.utc)
                return deadline, f"before {match.group(1)} {day}"
            except ValueError:
                pass
    
    # Check "in MONTH" pattern
    for month_name, (month_num, last_day) in MONTH_PATTERNS.items():
        # Match "in january", "january 2026", or title containing month as time window
        patterns = [
            f'in {month_name}',
            f'{month_name} 20',
            f'by {month_name}',
            f'during {month_name}',
        ]
        for pat in patterns:
            if pat in text:
                try:
                    deadline = datetime(year, month_num, last_day, tzinfo=timezone.utc)
                    if (now - deadline).days > 180:
                        deadline = datetime(year + 1, month_num, last_day, tzinfo=timezone.utc)
                    return deadline, f"{month_name} window"
                except ValueError:
                    pass
    
    # Check quarter patterns
    for q_name, (month_num, last_day) in QUARTER_PATTERNS.items():
        if q_name in text:
            try:
                deadline = datetime(year, month_num, last_day, tzinfo=timezone.utc)
                if (now - deadline).days > 180:
                    deadline = datetime(year + 1, month_num, last_day, tzinfo=timezone.utc)
                return deadline, f"{q_name} window"
            except ValueError:
                pass
    
    return None, None


def search_news(query, max_results=5):
    """Search Google News for verification."""
    try:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        
        # Parse RSS
        items = re.findall(r'<item>.*?<title>(.*?)</title>.*?<pubDate>(.*?)</pubDate>.*?</item>', 
                          r.text, re.DOTALL)
        results = []
        for title, date in items[:max_results]:
            title = re.sub(r'<[^>]+>', '', title)  # Strip HTML
            results.append({'title': title, 'date': date})
        return results
    except:
        return []


def check_market_mispricing(market):
    """Check if a time-bound market is mispriced."""
    title = market.get('title', '')
    subtitle = market.get('subtitle', '')
    yes_price = market.get('yes_ask', market.get('last_price', 50))
    no_price = 100 - yes_price if yes_price else 50
    ticker = market.get('ticker', '')
    volume = market.get('volume', 0)
    
    deadline, window_type = extract_time_window(title, subtitle)
    if not deadline:
        return None
    
    now = datetime.now(timezone.utc)
    days_past = (now - deadline).days
    
    # Only interested in windows that have passed (or about to)
    if days_past < -3:  # More than 3 days before deadline
        return None
    
    # Build search query from title
    # Remove common words
    search_terms = re.sub(r'\b(will|the|a|an|in|on|by|before|during|at|of|to|and|or)\b', '', 
                          title, flags=re.IGNORECASE)
    search_terms = ' '.join(search_terms.split()[:6])
    
    news = search_news(search_terms)
    
    result = {
        'ticker': ticker,
        'title': title,
        'subtitle': subtitle,
        'yes_price': yes_price,
        'no_price': no_price,
        'volume': volume,
        'window_type': window_type,
        'deadline': deadline.isoformat(),
        'days_past': days_past,
        'news': news[:3],
        'potential': None,
    }
    
    # Flag potential mispricings
    if days_past > 0:  # Window has passed
        if yes_price and yes_price < 85:
            result['potential'] = 'YES_UNDERPRICED'
            result['signal'] = f"Window expired {days_past}d ago, YES only {yes_price}¢"
        elif yes_price and yes_price > 15:
            result['potential'] = 'NEEDS_VERIFICATION'
            result['signal'] = f"Window expired {days_past}d ago, verify if event occurred"
    elif days_past >= -3:  # About to expire
        result['potential'] = 'EXPIRING_SOON'
        result['signal'] = f"Window expires in {-days_past}d, price at {yes_price}¢"
    
    return result


def scan():
    """Main scan: find all expired window opportunities."""
    print(f"⏰ Expired Window Scanner — {datetime.now(timezone.utc).strftime('%m/%d %H:%M UTC')}")
    
    markets = get_all_markets()
    print(f"Total markets: {len(markets)}")
    
    opportunities = []
    expiring = []
    
    for market in markets:
        result = check_market_mispricing(market)
        if result:
            if result['potential'] == 'YES_UNDERPRICED':
                opportunities.append(result)
            elif result['potential'] == 'NEEDS_VERIFICATION':
                opportunities.append(result)
            elif result['potential'] == 'EXPIRING_SOON':
                expiring.append(result)
    
    # Print results
    if opportunities:
        print(f"\n🚨 EXPIRED WINDOW ALERTS ({len(opportunities)})")
        for opp in sorted(opportunities, key=lambda x: x.get('yes_price', 50)):
            print(f"\n  🎯 {opp['title']}")
            print(f"     {opp['signal']}")
            print(f"     Ticker: {opp['ticker']} | Vol: {opp['volume']}")
            if opp['news']:
                print(f"     📰 News:")
                for n in opp['news'][:2]:
                    print(f"        - {n['title'][:70]}")
    else:
        print("\n✅ No expired window opportunities found")
    
    if expiring:
        print(f"\n⏳ EXPIRING SOON ({len(expiring)})")
        for exp in sorted(expiring, key=lambda x: x.get('days_past', 0), reverse=True):
            print(f"  ⌛ {exp['title']}")
            print(f"     {exp['signal']} | Vol: {exp['volume']}")
    
    return opportunities, expiring


if __name__ == '__main__':
    opps, exp = scan()
    
    # Save results
    with open('/tmp/expired_window_results.json', 'w') as f:
        json.dump({'opportunities': opps, 'expiring': exp}, f, indent=2)
