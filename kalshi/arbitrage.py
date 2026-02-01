exec(open('/tmp/sandbox_bootstrap.py').read())

"""
Kalshi Event Arbitrage Scanner

核心思路: 找到事件已经发生但市场价格没反映的机会。
这不是 junk bonding（赌高概率），这是 arbitrage（赌已确认事实）。

流程:
1. 抓所有即将到期的市场（≤14天）
2. 从市场标题提取关键词
3. 自动搜新闻验证事件是否已发生
4. 对比: 新闻说 YES but 市场 <80% → 🚨 机会
5. 对比: 新闻说 NO but 市场 >20% → 🚨 机会
"""

import requests
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Categories to skip
SKIP_CATS = {"Sports", "Entertainment"}

def api_get(endpoint, params=None):
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=15)
        if resp.status_code == 429:
            time.sleep(3)
            resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except:
        return None

def fetch_expiring_markets(max_days=14):
    """Fetch ALL markets expiring within max_days"""
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=max_days)
    
    all_markets = []
    cursor = None
    
    while True:
        params = {"limit": 200, "status": "open"}
        if cursor:
            params["cursor"] = cursor
        data = api_get("/markets", params)
        if not data:
            break
        
        for m in data.get("markets", []):
            close_str = m.get("close_time", "")
            if not close_str:
                continue
            try:
                close = datetime.fromisoformat(close_str.replace("Z", "+00:00"))
            except:
                continue
            
            days = (close - now).days
            if 0 < days <= max_days:
                m["_days"] = days
                all_markets.append(m)
        
        cursor = data.get("cursor", "")
        if not cursor or len(data.get("markets", [])) < 200:
            break
    
    return all_markets

def fetch_events_map():
    """Build event_ticker -> info map"""
    emap = {}
    cursor = None
    while True:
        params = {"limit": 200, "status": "open"}
        if cursor:
            params["cursor"] = cursor
        data = api_get("/events", params)
        if not data:
            break
        for e in data.get("events", []):
            emap[e["event_ticker"]] = {
                "category": e.get("category", ""),
                "title": e.get("title", ""),
            }
        cursor = data.get("cursor", "")
        if not cursor or len(data.get("events", [])) < 200:
            break
    return emap

def search_news(query, max_results=5):
    """Quick news search via Google News RSS"""
    results = []
    try:
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, headers=HEADERS, timeout=8)
        titles = re.findall(r'<title>(.*?)</title>', r.text)
        dates = re.findall(r'<pubDate>(.*?)</pubDate>', r.text)
        for i, title in enumerate(titles[1:max_results+1]):
            pub_date = dates[i] if i < len(dates) else ""
            results.append({"title": title, "date": pub_date})
    except:
        pass
    return results

def extract_search_query(market):
    """Extract meaningful search terms from market title"""
    title = market.get("title", "")
    yes_sub = market.get("yes_sub_title", "")
    no_sub = market.get("no_sub_title", "")
    
    # Clean up title
    query = title
    # Add subtitles for context
    if yes_sub:
        query += " " + yes_sub
    
    # Remove common filler words
    stop = {"will", "the", "a", "an", "in", "on", "at", "to", "for", "of", "by", 
            "this", "that", "be", "is", "are", "was", "were", "been", "being",
            "how", "many", "much", "what", "which", "who", "whom", "when", "where",
            "before", "after", "more", "than", "least", "above", "below", "between",
            "month", "week", "year", "january", "february", "march", "april", "may",
            "june", "july", "august", "september", "october", "november", "december",
            "or", "and", "not", "no", "yes", "any"}
    
    words = [w for w in query.split() if w.lower() not in stop and len(w) > 2]
    return " ".join(words[:6])

def assess_news_sentiment(news_items, market_title):
    """Simple heuristic: do the news headlines suggest the event happened?
    
    Returns: 
        "confirmed" - strong evidence event occurred
        "likely" - some evidence
        "unclear" - can't determine
        "unlikely" - evidence against
    """
    if not news_items:
        return "unclear", []
    
    # Look for confirmation language in headlines
    confirm_words = ["confirms", "confirmed", "agrees", "agreed", "signed", "signs",
                     "passes", "passed", "approves", "approved", "announces", "announced",
                     "says", "said", "reveals", "happened", "completed", "done", "reached",
                     "met", "meets", "spoke", "speaks", "called", "calls", "talks"]
    deny_words = ["fails", "failed", "rejected", "rejects", "unlikely", "won't", "will not",
                  "delays", "delayed", "postponed", "cancelled", "blocked", "stalled",
                  "denies", "denied", "no sign", "not expected"]
    
    confirm_count = 0
    deny_count = 0
    relevant_headlines = []
    
    for item in news_items:
        headline = item.get("title", "").lower()
        
        # Check if headline is actually about this topic
        title_words = set(market_title.lower().split())
        headline_words = set(headline.split())
        overlap = len(title_words & headline_words)
        if overlap < 2:
            continue
        
        relevant_headlines.append(item["title"])
        
        for w in confirm_words:
            if w in headline:
                confirm_count += 1
                break
        for w in deny_words:
            if w in headline:
                deny_count += 1
                break
    
    if confirm_count >= 2 and deny_count == 0:
        return "confirmed", relevant_headlines
    elif confirm_count > deny_count:
        return "likely", relevant_headlines
    elif deny_count > confirm_count:
        return "unlikely", relevant_headlines
    return "unclear", relevant_headlines

def find_arbitrage(markets, events_map, min_gap=20):
    """
    Find markets where news reality doesn't match market price.
    
    min_gap: minimum gap between expected price and actual price (in cents)
    e.g., news says YES but market is at <(100-min_gap)¢
    """
    opportunities = []
    
    # Filter to political/economics markets
    filtered = []
    for m in markets:
        ev = events_map.get(m.get("event_ticker", ""), {})
        cat = ev.get("category", "")
        if cat in SKIP_CATS:
            continue
        filtered.append(m)
    
    print(f"📡 Checking {len(filtered)} markets for event arbitrage...")
    
    for i, m in enumerate(filtered):
        ticker = m.get("ticker", "")
        title = m.get("title", "")
        price = m.get("last_price", 50)
        days = m.get("_days", 99)
        vol = m.get("volume_24h", 0)
        spread = (m.get("yes_ask", 0) - m.get("yes_bid", 0)) if m.get("yes_ask") else 99
        
        # Only check markets with reasonable spread (tradeable)
        if spread > 20:
            continue
        
        # Only interesting if price is in "uncertain" range or potentially mispriced
        # Skip already near-settled markets (>95 or <5)
        if price > 95 or price < 5:
            continue
        
        # Extract search query and search news
        query = extract_search_query(m)
        if not query or len(query) < 5:
            continue
        
        news = search_news(query, max_results=5)
        if not news:
            continue
        
        sentiment, headlines = assess_news_sentiment(news, title)
        
        # Check for mismatches
        opportunity = None
        
        if sentiment == "confirmed" and price < (100 - min_gap):
            # News says YES but market price is low → buy YES
            profit_pct = ((100 - price) / price) * 100
            opportunity = {
                "type": "EVENT_CONFIRMED_BUT_UNDERPRICED",
                "action": f"BUY YES @ {price}¢",
                "expected_settle": 100,
                "profit_pct": profit_pct,
            }
        elif sentiment == "unlikely" and price > min_gap:
            # News says NO but market price is high → buy NO
            no_cost = 100 - price
            profit_pct = (price / no_cost) * 100 if no_cost > 0 else 0
            opportunity = {
                "type": "EVENT_UNLIKELY_BUT_OVERPRICED",
                "action": f"BUY NO @ {100-price}¢",
                "expected_settle": 0,
                "profit_pct": profit_pct,
            }
        
        if opportunity:
            opportunity.update({
                "ticker": ticker,
                "title": title,
                "sub": m.get("yes_sub_title", "") or m.get("no_sub_title", ""),
                "price": price,
                "days": days,
                "spread": spread,
                "vol24h": vol,
                "sentiment": sentiment,
                "headlines": headlines[:3],
            })
            opportunities.append(opportunity)
        
        # Rate limit: don't hammer Google News
        if (i + 1) % 5 == 0:
            time.sleep(0.5)
    
    # Sort by profit potential
    opportunities.sort(key=lambda x: -x.get("profit_pct", 0))
    return opportunities

def format_report(opportunities):
    lines = []
    now = datetime.now(timezone.utc)
    lines.append("=" * 60)
    lines.append(f"🚨 EVENT ARBITRAGE SCAN — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 60)
    
    if not opportunities:
        lines.append("\n  No arbitrage opportunities found")
        lines.append("  (This is normal — real mispricings are rare)")
        return "\n".join(lines)
    
    lines.append(f"\n🎯 {len(opportunities)} POTENTIAL OPPORTUNITIES")
    lines.append("-" * 50)
    
    for opp in opportunities[:10]:
        emoji = "🚨" if opp["profit_pct"] > 50 else "⚠️"
        lines.append(f"\n{emoji} {opp['type']}")
        lines.append(f"   {opp['title']} — {opp.get('sub', '')}")
        lines.append(f"   💰 {opp['action']} → +{opp['profit_pct']:.0f}% | {opp['days']}d to close")
        lines.append(f"   📊 spread:{opp['spread']} | vol24h:{opp['vol24h']}")
        lines.append(f"   📰 News sentiment: {opp['sentiment'].upper()}")
        for h in opp.get("headlines", []):
            lines.append(f"      • {h}")
        lines.append(f"   [{opp['ticker']}]")
    
    lines.append("\n" + "=" * 60)
    lines.append("⚠️ ALWAYS verify manually before trading!")
    lines.append("   Read the contract rules (PDF) to confirm definitions")
    lines.append("   Cross-check with Polymarket")
    lines.append("=" * 60)
    
    return "\n".join(lines)

def main():
    max_days = 14
    if "--max-days" in sys.argv:
        idx = sys.argv.index("--max-days")
        if idx + 1 < len(sys.argv):
            max_days = int(sys.argv[idx + 1])
    
    min_gap = 20
    if "--min-gap" in sys.argv:
        idx = sys.argv.index("--min-gap")
        if idx + 1 < len(sys.argv):
            min_gap = int(sys.argv[idx + 1])
    
    print("📡 Fetching events...")
    events = fetch_events_map()
    print(f"   {len(events)} events")
    
    print(f"📡 Fetching markets expiring within {max_days} days...")
    markets = fetch_expiring_markets(max_days)
    print(f"   {len(markets)} markets")
    
    opportunities = find_arbitrage(markets, events, min_gap)
    
    report = format_report(opportunities)
    print(report)
    
    # Return data for integration
    return opportunities

if __name__ == "__main__":
    main()
