exec(open('/tmp/sandbox_bootstrap.py').read())

"""
Kalshi Decision Engine
Analyzes markets, fetches rules, validates with research, outputs BUY/WAIT/SKIP.

SCORING CRITERIA:
- Recent news (7d): +30
- Official data source: +30
- No procedural risk: +20
- Annualized yield per 100%: +10
- Spread <=3¢: +10, <=5¢: +5
- >= 70: BUY | 50-69: WAIT | <50: SKIP
"""

import requests
import json
import re
from datetime import datetime, timezone, timedelta

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

def api_get(endpoint, params=None):
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None

def fetch_market_details(ticker):
    """Fetch full market details including rules"""
    data = api_get(f"/markets/{ticker}")
    if not data:
        return None
    return data.get("market", {})

def analyze_rules(rules_text, title):
    """Parse resolution rules and identify key factors"""
    analysis = {
        "official_source": None,
        "procedural_risk": False,
        "time_window": None,
        "ambiguity": False,
    }
    
    if not rules_text:
        analysis["ambiguity"] = True
        return analysis
    
    text_lower = rules_text.lower()
    
    # Identify official data sources
    sources = {
        "BEA": ["bureau of economic analysis", "bea.gov", "gdp release"],
        "BLS": ["bureau of labor statistics", "bls.gov", "cpi", "unemployment"],
        "Fed": ["federal reserve", "fomc", "fed.gov", "interest rate"],
        "Congress": ["congress.gov", "congressional", "legislative"],
        "White House": ["whitehouse.gov", "executive order", "presidential"],
        "Treasury": ["treasury.gov", "treasury department"],
    }
    
    for source, keywords in sources.items():
        if any(kw in text_lower for kw in keywords):
            analysis["official_source"] = source
            break
    
    # Check for procedural complexity
    procedural_keywords = [
        "pass both", "senate and house", "signed into law",
        "confirmed by", "ratified", "approved by congress",
        "two-thirds", "supermajority", "veto override"
    ]
    if any(kw in text_lower for kw in procedural_keywords):
        analysis["procedural_risk"] = True
    
    # Extract time window
    date_pattern = r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}'
    dates = re.findall(date_pattern, text_lower)
    if dates:
        analysis["time_window"] = dates[0]
    
    # Check for ambiguous terms
    ambiguous_terms = ["may", "could", "might", "approximately", "around", "substantial"]
    if any(term in text_lower for term in ambiguous_terms):
        analysis["ambiguity"] = True
    
    return analysis

def score_market(market, research_result=None):
    """
    Score a market opportunity
    
    Returns: {
        "score": int,
        "decision": "BUY" | "WAIT" | "SKIP",
        "reasons": [str],
        "position_size": int (dollars),
        "confidence": "HIGH" | "MEDIUM" | "LOW"
    }
    """
    score = 0
    reasons = []
    
    ticker = market.get("ticker", "")
    title = market.get("title", "")
    rules = market.get("rules", "")
    
    # Basic market data
    price = market.get("last_price", 50)
    spread = (market.get("yes_ask", 0) - market.get("yes_bid", 0)) if market.get("yes_ask") else 99
    vol = market.get("volume_24h", 0)
    
    close_str = market.get("close_time", "")
    if not close_str:
        return {"score": 0, "decision": "SKIP", "reasons": ["No close time"], "position_size": 0, "confidence": "LOW"}
    
    try:
        close = datetime.fromisoformat(close_str.replace("Z", "+00:00"))
        days = (close - datetime.now(timezone.utc)).days
    except:
        return {"score": 0, "decision": "SKIP", "reasons": ["Invalid close time"], "position_size": 0, "confidence": "LOW"}
    
    if days <= 0:
        return {"score": 0, "decision": "SKIP", "reasons": ["Market expired"], "position_size": 0, "confidence": "LOW"}
    
    # Calculate returns
    side = "YES" if price >= 85 else "NO"
    cost = price if price >= 85 else (100 - price)
    ret = ((100 - cost) / cost) * 100 if cost > 0 else 0
    ann_yield = (ret / max(days, 1)) * 365
    
    # --- SCORING ---
    
    # 1. Yield (base requirement)
    if ann_yield < 100:
        return {"score": 0, "decision": "SKIP", "reasons": ["Annualized yield too low (<100%)"], "position_size": 0, "confidence": "LOW"}
    
    score += int(ann_yield / 100) * 10
    reasons.append(f"年化收益 {ann_yield:.0f}%")
    
    # 2. Spread
    if spread <= 3:
        score += 10
        reasons.append(f"流动性好 (spread {spread}¢)")
    elif spread <= 5:
        score += 5
        reasons.append(f"流动性尚可 (spread {spread}¢)")
    else:
        reasons.append(f"⚠️ 流动性差 (spread {spread}¢)")
    
    # 3. Analyze rules
    rule_analysis = analyze_rules(rules, title)
    
    if rule_analysis["official_source"]:
        score += 30
        reasons.append(f"✅ 官方数据源: {rule_analysis['official_source']}")
    else:
        reasons.append("⚠️ 无明确官方数据源")
    
    if not rule_analysis["procedural_risk"]:
        score += 20
        reasons.append("✅ 无程序性风险")
    else:
        reasons.append("⚠️ 有程序性障碍（需多方批准）")
    
    if rule_analysis["ambiguity"]:
        reasons.append("⚠️ 规则存在模糊表述")
        score -= 10
    
    # 4. Research validation (if provided)
    if research_result:
        news_count = len(research_result.get("news", []))
        if news_count >= 3:
            score += 30
            reasons.append(f"✅ 有 {news_count} 条相关新闻")
        elif news_count > 0:
            score += 15
            reasons.append(f"⚠️ 仅 {news_count} 条新闻")
        else:
            reasons.append("❌ 无相关新闻验证")
    
    # --- DECISION ---
    if score >= 70:
        decision = "BUY"
        confidence = "HIGH"
        position_size = 200 if score >= 85 else 100
    elif score >= 50:
        decision = "WAIT"
        confidence = "MEDIUM"
        position_size = 50
        reasons.append("需要更多验证")
    else:
        decision = "SKIP"
        confidence = "LOW"
        position_size = 0
    
    return {
        "score": score,
        "decision": decision,
        "reasons": reasons,
        "position_size": position_size,
        "confidence": confidence,
        "side": side,
        "cost": cost,
        "ann_yield": ann_yield,
        "days": days,
        "rule_analysis": rule_analysis,
    }

def decide(ticker):
    """Full decision pipeline for a single market"""
    market = fetch_market_details(ticker)
    if not market:
        return {"error": "Failed to fetch market details"}
    
    # TODO: integrate research.py here
    research_result = None
    
    decision = score_market(market, research_result)
    decision["ticker"] = ticker
    decision["title"] = market.get("title", "")
    decision["rules"] = market.get("rules", "")
    
    return decision

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python decision.py <TICKER>")
        sys.exit(1)
    
    result = decide(sys.argv[1])
    
    if "error" in result:
        print(f"❌ {result['error']}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"📊 {result['title']}")
    print(f"🎯 {result['ticker']}")
    print(f"{'='*60}\n")
    
    print(f"决策: {result['decision']} ({result['confidence']} confidence)")
    print(f"评分: {result['score']}/100")
    print(f"推荐: {result['side']} @ {result['cost']:.0f}¢")
    print(f"回报: +{result['ann_yield']:.0f}% 年化 ({result['days']}天)")
    print(f"仓位: ${result['position_size']}\n")
    
    print("理由:")
    for r in result['reasons']:
        print(f"  • {r}")
    
    print(f"\n规则摘要:")
    print(f"  数据源: {result['rule_analysis']['official_source'] or '未指定'}")
    print(f"  程序性风险: {'是' if result['rule_analysis']['procedural_risk'] else '否'}")
    print(f"  时间窗口: {result['rule_analysis']['time_window'] or '未指定'}")
    print(f"  规则模糊: {'是' if result['rule_analysis']['ambiguity'] else '否'}")
    
    print(f"\n完整规则:")
    print(f"  {result['rules'][:500]}...")
