exec(open('/tmp/sandbox_bootstrap.py').read())

"""
Kalshi ↔ Polymarket Cross-Platform Arbitrage Scanner

核心策略: 对比 Kalshi 和 Polymarket 的定价差异。
Polymarket 流动性更大、玩家更专业 → 如果价差 >15¢，Kalshi 可能定价错误。

流程:
1. 拉 Kalshi 所有政治/经济市场
2. 对每个市场，在 Polymarket 搜索相似问题
3. 模糊匹配标题 → 对比价格
4. 标记价差 >15¢ 的市场
"""

import requests
import json
import re
import sys
import time
from datetime import datetime, timezone

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# All known political series
POLITICAL_SERIES = [
    "KXTRUMPSAYNICKNAME", "KXTRUMPRESIGN", "KXTRUMPREMOVE",
    "KXTRUMPPARDONFAMILY", "KXTRUMPAGCOUNT", "KXEOTRUMPTERM",
    "KXTRUMPAPPROVALYEAR", "KXTRUMPPRES", "KXTRUMPRUN",
    "KXIMPEACH", "KXMARTIAL", "KXNEXTPRESSEC", "KXNEXTDHSSEC",
    "KXGOVTCUTS", "KXGOVTSPEND", "KXDEBTGROWTH",
    "KXACAREPEAL", "KXFREEIVF", "KXTAFTHARTLEY",
    "KXBALANCEPOWERCOMBO", "KXCAPCONTROL", "KXDOED",
    "KXSCOTUSPOWER", "KXJAN6CASES", "KXOBERGEFELL",
    "KXGDP", "KXUSDEBT", "KXLCPIMAXYOY",
    "KXFEDCHAIRNOM", "KXFEDEMPLOYEES", "KXTRILLIONAIRE",
    "KXKHAMENEIOUT", "KXGREENTERRITORY", "KXGREENLANDPRICE",
    "KXCANAL", "KXNEWPOPE", "KXFULLTERMSKPRES",
    "KXNEXTIRANLEADER", "KXPUTINDJTLOCATION",
    "KXWITHDRAW", "KXUSAKIM", "KXRECOGSOMALI",
    "KXFTA", "KXDJTVOSTARIFFS",
    "KXPRESNOMD", "KXVPRESNOMD", "KXPRESPARTY",
    "KXHOUSERACE", "KXMUSKPRIMARY", "KXAOCSENATE",
    "CONTROLH", "POWER",
    "KXIPOSPACEX", "KXIPOFANNIE", "KXSPACEXBANKPUBLIC",
    "KXTRUMPMEETING", "KXZELENSKYPUTIN",
    "KXBILLSIGNED", "KXTRUMPBILLSSIGNED",
    "KXTARIFF", "KXTARIFFS",
    "KXFED",
]

def get_kalshi_markets():
    """Get all political markets from Kalshi"""
    now = datetime.now(timezone.utc)
    markets = []
    
    for series in POLITICAL_SERIES:
        try:
            data = requests.get(f"{API_BASE}/markets",
                              params={"limit": 50, "status": "open", "series_ticker": series},
                              timeout=10).json()
            for m in data.get("markets", []):
                price = m.get("last_price", 50)
                close = m.get("close_time", "")
                days = 999
                try:
                    ct = datetime.fromisoformat(close.replace("Z", "+00:00"))
                    days = (ct - now).days
                except:
                    pass
                
                if days <= 0:
                    continue
                
                markets.append({
                    "ticker": m["ticker"],
                    "series": series,
                    "title": m.get("title", ""),
                    "sub": m.get("yes_sub_title", "") or m.get("no_sub_title", ""),
                    "price": price,
                    "days": days,
                    "vol24h": m.get("volume_24h", 0),
                    "spread": (m.get("yes_ask", 0) - m.get("yes_bid", 0)) if m.get("yes_ask") else 99,
                })
        except:
            pass
    
    return markets

def search_polymarket(query, limit=5):
    """Search Polymarket for matching markets"""
    results = []
    try:
        r = requests.get(f"https://gamma-api.polymarket.com/markets?closed=false&limit={limit}&_q={query}",
                        headers=HEADERS, timeout=10)
        for m in r.json():
            prices = m.get("outcomePrices", "")
            if isinstance(prices, str):
                try:
                    prices = json.loads(prices)
                except:
                    prices = []
            
            yes_price = 50
            if prices and len(prices) >= 1:
                try:
                    yes_price = round(float(prices[0]) * 100)
                except:
                    pass
            
            vol = 0
            try:
                vol = float(m.get("volume", 0) or 0)
            except:
                pass
            
            results.append({
                "question": m.get("question", ""),
                "yes_price": yes_price,
                "volume": vol,
                "slug": m.get("slug", ""),
            })
    except:
        pass
    return results

def extract_keywords(title, sub=""):
    """Extract meaningful search keywords"""
    text = f"{title} {sub}"
    # Remove markdown
    text = re.sub(r'\*\*|__|~~', '', text)
    # Remove common filler
    stop = {"will", "the", "a", "an", "in", "on", "at", "to", "for", "of", "by",
            "this", "that", "be", "is", "are", "how", "many", "much", "what",
            "before", "after", "more", "than", "above", "below", "or", "and",
            "not", "no", "yes", "any", "least", "between", "increase", "decrease"}
    words = [w for w in text.split() if w.lower() not in stop and len(w) > 2]
    return " ".join(words[:5])

def fuzzy_match_score(kalshi_title, poly_question):
    """Simple word overlap score between two market titles"""
    k_words = set(kalshi_title.lower().split())
    p_words = set(poly_question.lower().split())
    # Remove common words
    stop = {"will", "the", "a", "an", "in", "on", "at", "to", "for", "of", "by", "?", "before", "after"}
    k_words -= stop
    p_words -= stop
    
    if not k_words or not p_words:
        return 0
    
    overlap = len(k_words & p_words)
    return overlap / min(len(k_words), len(p_words))

def find_cross_platform_gaps(kalshi_markets, min_gap=15, min_match=0.3):
    """
    For each Kalshi market, find matching Polymarket and compare prices.
    
    min_gap: minimum price difference in cents to flag
    min_match: minimum fuzzy match score (0-1)
    """
    opportunities = []
    checked = 0
    
    for km in kalshi_markets:
        keywords = extract_keywords(km["title"], km["sub"])
        if len(keywords) < 5:
            continue
        
        poly_results = search_polymarket(keywords)
        checked += 1
        
        for pm in poly_results:
            match_score = fuzzy_match_score(
                km["title"] + " " + km["sub"],
                pm["question"]
            )
            
            if match_score < min_match:
                continue
            
            # Compare prices
            k_price = km["price"]
            p_price = pm["yes_price"]
            gap = abs(k_price - p_price)
            
            if gap >= min_gap:
                # Determine direction
                if p_price > k_price:
                    signal = f"Kalshi {k_price}¢ vs Poly {p_price}¢ → Kalshi UNDERPRICED (buy YES)"
                else:
                    signal = f"Kalshi {k_price}¢ vs Poly {p_price}¢ → Kalshi OVERPRICED (buy NO)"
                
                opportunities.append({
                    "kalshi_ticker": km["ticker"],
                    "kalshi_title": km["title"],
                    "kalshi_sub": km["sub"],
                    "kalshi_price": k_price,
                    "kalshi_days": km["days"],
                    "kalshi_spread": km["spread"],
                    "kalshi_vol": km["vol24h"],
                    "poly_question": pm["question"],
                    "poly_price": p_price,
                    "poly_volume": pm["volume"],
                    "gap": gap,
                    "match_score": match_score,
                    "signal": signal,
                })
        
        # Rate limit
        if checked % 3 == 0:
            time.sleep(0.3)
    
    opportunities.sort(key=lambda x: -x["gap"])
    return opportunities, checked

def format_report(opportunities, checked):
    lines = []
    now = datetime.now(timezone.utc)
    lines.append("=" * 60)
    lines.append(f"🔄 CROSS-PLATFORM SCAN — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"   Checked {checked} Kalshi markets against Polymarket")
    lines.append("=" * 60)
    
    if not opportunities:
        lines.append("\n  No significant price gaps found")
        return "\n".join(lines)
    
    lines.append(f"\n🚨 {len(opportunities)} PRICE DISCREPANCIES (≥15¢ gap)")
    lines.append("-" * 50)
    
    for opp in opportunities[:15]:
        emoji = "🚨" if opp["gap"] >= 25 else "⚠️"
        lines.append(f"\n{emoji} GAP: {opp['gap']}¢ | Match: {opp['match_score']:.0%}")
        lines.append(f"   Kalshi: {opp['kalshi_title'][:45]} — {opp['kalshi_sub'][:20]}")
        lines.append(f"   Poly:   {opp['poly_question'][:65]}")
        lines.append(f"   💰 {opp['signal']}")
        lines.append(f"   Kalshi: {opp['kalshi_price']}¢ (sp:{opp['kalshi_spread']}, {opp['kalshi_days']}d)")
        lines.append(f"   Poly:   {opp['poly_price']}¢ (vol: ${opp['poly_volume']:,.0f})")
        lines.append(f"   [{opp['kalshi_ticker']}]")
    
    lines.append("\n" + "=" * 60)
    lines.append("⚠️ VERIFY: Check contract definitions match before trading!")
    lines.append("   Different platforms may define resolution differently")
    lines.append("=" * 60)
    
    return "\n".join(lines)

def main():
    min_gap = 15
    if "--min-gap" in sys.argv:
        idx = sys.argv.index("--min-gap")
        if idx + 1 < len(sys.argv):
            min_gap = int(sys.argv[idx + 1])
    
    print("📡 Fetching Kalshi political markets...")
    kalshi = get_kalshi_markets()
    print(f"   {len(kalshi)} markets")
    
    print("🔄 Cross-checking with Polymarket...")
    opps, checked = find_cross_platform_gaps(kalshi, min_gap=min_gap)
    
    report = format_report(opps, checked)
    print(report)
    
    return opps

if __name__ == "__main__":
    main()
