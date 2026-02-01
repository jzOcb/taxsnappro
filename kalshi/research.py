exec(open('/tmp/sandbox_bootstrap.py').read())

"""
Kalshi Deep Research Tool
Fetches news, data sources, and procedural constraints for a market.

⚠️ This is MANDATORY before any trading recommendation.
See README.md for the full research checklist.
"""

import requests
import json
import re
import sys
from datetime import datetime, timezone

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def search_news(query, max_results=8):
    """Search Google News RSS for recent articles"""
    results = []
    try:
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, headers=HEADERS, timeout=10)
        titles = re.findall(r'<title>(.*?)</title>', r.text)
        dates = re.findall(r'<pubDate>(.*?)</pubDate>', r.text)
        links = re.findall(r'<link/>(.*?)<', r.text)
        
        for i, title in enumerate(titles[1:max_results+1]):  # skip feed title
            results.append({
                "title": title,
                "date": dates[i] if i < len(dates) else "",
                "url": links[i].strip() if i < len(links) else "",
            })
    except Exception as e:
        results.append({"error": str(e)})
    return results

def search_multiple(queries):
    """Search multiple queries and deduplicate"""
    all_results = []
    seen_titles = set()
    for q in queries:
        for r in search_news(q):
            if r.get("title") and r["title"] not in seen_titles:
                seen_titles.add(r["title"])
                all_results.append(r)
    return all_results

def check_congress(query=""):
    """Check Congress.gov for legislation status"""
    results = []
    try:
        url = f"https://www.congress.gov/search?q=%7B%22source%22%3A%22legislation%22%2C%22search%22%3A%22{query}%22%7D"
        r = requests.get(url, headers=HEADERS, timeout=10)
        # Extract bill titles
        titles = re.findall(r'<span class="result-title">(.*?)</span>', r.text)
        for t in titles[:5]:
            clean = re.sub(r'<.*?>', '', t).strip()
            if clean:
                results.append(clean)
    except:
        pass
    return results

def check_fed_data():
    """Check key economic indicators"""
    data = {}
    
    # Atlanta Fed GDPNow
    try:
        r = requests.get("https://www.atlantafed.org/cqer/research/gdpnow", 
                         headers=HEADERS, timeout=10)
        gdp_match = re.search(r'GDPNow.*?(\d+\.\d+)\s*percent', r.text)
        if gdp_match:
            data["gdpnow"] = float(gdp_match.group(1))
    except:
        pass
    
    # Try Fred API for key indicators (no key needed for some)
    indicators = {
        "fed_funds": "https://api.stlouisfed.org/fred/series/observations?series_id=FEDFUNDS&limit=1&sort_order=desc&file_type=json",
        "cpi": "https://api.stlouisfed.org/fred/series/observations?series_id=CPIAUCSL&limit=1&sort_order=desc&file_type=json",
    }
    
    return data

def check_scotus_calendar():
    """Check Supreme Court schedule"""
    results = []
    try:
        r = requests.get("https://www.supremecourt.gov/oral_arguments/calendars.aspx",
                         headers=HEADERS, timeout=10)
        # Extract upcoming dates
        dates = re.findall(r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,\s+\d{4})', r.text)
        results = dates[:10]
    except:
        pass
    return results

def check_polymarket(query):
    """Check Polymarket for cross-reference pricing"""
    results = []
    # Try multiple search variations
    queries_to_try = [query]
    # Simplify: take key nouns
    words = query.split()
    if len(words) > 3:
        queries_to_try.append(" ".join(words[:3]))
    
    seen = set()
    for q in queries_to_try:
        try:
            r = requests.get(f"https://gamma-api.polymarket.com/markets?closed=false&limit=5&_q={q}",
                             headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for m in data:
                    qtext = m.get("question", "")
                    if qtext in seen:
                        continue
                    seen.add(qtext)
                    results.append({
                        "question": qtext,
                        "price": m.get("outcomePrices", ""),
                        "volume": m.get("volume", 0),
                        "url": f"https://polymarket.com/event/{m.get('slug', '')}",
                    })
        except:
            pass
    return results[:5]

def research_market(ticker, title, category=""):
    """Full research pipeline for a specific market"""
    report = []
    report.append(f"🔍 DEEP RESEARCH: {title}")
    report.append(f"   Ticker: {ticker}")
    report.append(f"   Category: {category}")
    report.append(f"   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    report.append("=" * 60)
    
    # 1. Extract search keywords from title
    # Remove common words
    stop_words = {"will", "the", "a", "an", "in", "on", "at", "to", "for", "of", "by", "before", "after", "more", "than", "least"}
    keywords = [w for w in title.split() if w.lower() not in stop_words and len(w) > 2]
    search_query = " ".join(keywords[:5])
    
    # 2. News search
    report.append("\n📰 LATEST NEWS")
    report.append("-" * 40)
    news_queries = [search_query]
    
    # Add category-specific queries
    if "GDP" in ticker.upper() or "gdp" in title.lower():
        news_queries.extend(["US GDP estimate 2026", "GDP growth forecast", "Atlanta Fed GDPNow"])
    elif "TRUMP" in ticker.upper():
        news_queries.extend(["Trump " + " ".join(keywords[:3])])
    elif "SCOTUS" in ticker.upper() or "supreme court" in title.lower():
        news_queries.extend(["Supreme Court ruling 2026", "SCOTUS calendar"])
    elif any(w in ticker.upper() for w in ["GOVT", "SPEND", "DEBT", "CUTS"]):
        news_queries.extend(["Congress budget 2026", "government spending bill"])
    elif "TARIFF" in ticker.upper() or "tariff" in title.lower():
        news_queries.extend(["Trump tariffs 2026", "US trade tariffs"])
    elif "IRAN" in ticker.upper() or "KHAMENEI" in ticker.upper():
        news_queries.extend(["Iran leadership 2026", "Khamenei"])
    elif "GREENLAND" in ticker.upper():
        news_queries.extend(["Trump Greenland purchase 2026"])
    
    news = search_multiple(news_queries)
    if news:
        for n in news[:8]:
            if "error" in n:
                report.append(f"  ⚠️ Search error: {n['error']}")
            else:
                report.append(f"  📰 {n['title']}")
                if n.get('date'):
                    report.append(f"     {n['date'][:25]}")
    else:
        report.append("  ⚠️ No recent news found")
    
    # 3. Category-specific data
    if "GDP" in ticker.upper() or "gdp" in title.lower():
        report.append("\n📊 ECONOMIC DATA")
        report.append("-" * 40)
        fed_data = check_fed_data()
        if fed_data.get("gdpnow"):
            report.append(f"  Atlanta Fed GDPNow: {fed_data['gdpnow']}%")
        else:
            report.append("  ⚠️ GDPNow data not fetched - check manually")
            report.append("  🔗 https://www.atlantafed.org/cqer/research/gdpnow")
    
    if "SCOTUS" in ticker.upper() or "supreme court" in title.lower():
        report.append("\n⚖️ SCOTUS CALENDAR")
        report.append("-" * 40)
        cal = check_scotus_calendar()
        if cal:
            for d in cal[:5]:
                report.append(f"  📅 {d}")
        else:
            report.append("  ⚠️ Could not fetch calendar")
            report.append("  🔗 https://www.supremecourt.gov/oral_arguments/calendars.aspx")
    
    if any(w in ticker.upper() for w in ["GOVT", "SPEND", "CUTS", "ACA", "TAFT", "DOED"]):
        report.append("\n🏛️ CONGRESS")
        report.append("-" * 40)
        bills = check_congress(search_query)
        if bills:
            for b in bills:
                report.append(f"  📋 {b}")
        else:
            report.append("  ⚠️ Check manually: https://www.congress.gov")
    
    # 4. Cross-reference with Polymarket
    report.append("\n🔄 POLYMARKET CROSS-CHECK")
    report.append("-" * 40)
    poly = check_polymarket(search_query)
    if poly:
        for p in poly[:3]:
            report.append(f"  💰 {p['question']}")
            vol = p.get('volume', 0)
            try:
                vol = float(vol)
                vol_str = f"${vol:,.0f}"
            except:
                vol_str = str(vol)
            report.append(f"     Price: {p['price']} | Vol: {vol_str}")
    else:
        report.append("  No matching Polymarket markets found")
    
    # 5. Risk assessment template
    report.append("\n⚠️ RISK ASSESSMENT (FILL IN)")
    report.append("-" * 40)
    report.append("  [ ] Data release date confirmed?")
    report.append("  [ ] Procedural constraints verified?")
    report.append("  [ ] News consistent with position?")
    report.append("  [ ] Polymarket aligned?")
    report.append("  [ ] Correlated positions checked?")
    report.append("  [ ] Downside scenario considered?")
    
    return "\n".join(report)


def main():
    if len(sys.argv) < 2:
        print("Usage: python research.py <ticker> [title]")
        print("  or:  python research.py --scan  (research top junk bonds from scanner)")
        sys.exit(1)
    
    if sys.argv[1] == "--scan":
        # Import scanner and research top opportunities
        from scanner import fetch_all_markets, fetch_events_map, analyze_markets
        print("📡 Fetching markets...")
        events = fetch_events_map()
        markets = fetch_all_markets()
        jb, _, _ = analyze_markets(markets, events)
        
        print(f"\n🔍 Researching top {min(5, len(jb))} junk bonds...\n")
        for bond in jb[:5]:
            report = research_market(bond["ticker"], bond["title"], bond.get("category", ""))
            print(report)
            print("\n" + "=" * 60 + "\n")
    else:
        ticker = sys.argv[1]
        title = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ticker
        
        # Fetch market info from API
        from scanner import api_get
        data = api_get(f"/markets/{ticker}")
        if data and data.get("market"):
            m = data["market"]
            title = m.get("title", title)
            cat = m.get("category", "")
            print(f"Market: {title}")
            print(f"Price: {m.get('last_price', '?')}¢ | Close: {m.get('close_time', '?')[:10]}")
            print()
        
        report = research_market(ticker, title)
        print(report)


if __name__ == "__main__":
    main()
