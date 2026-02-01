"""
Kalshi Enhanced Report with Decision Engine
Scans markets → Analyzes rules → Makes BUY/WAIT/SKIP recommendations
"""

try:
    import requests
except ImportError:
    import urllib.request
    import urllib.parse
    import json as _json
    print("⚠️ requests not available, using urllib fallback")
    
    class _Response:
        def __init__(self, status, body):
            self.status_code = status
            self._body = body
        def json(self):
            return _json.loads(self._body.decode('utf-8'))
        def raise_for_status(self):
            if not (200 <= self.status_code < 300):
                raise Exception(f"HTTP {self.status_code}")
    
    class requests:
        @staticmethod
        def get(url, params=None, timeout=15):
            if params:
                url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read()
                return _Response(response.status, body)
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

POLITICAL_SERIES = [
    "KXGDP", "KXCPI", "KXFED", "KXGOVSHUTLENGTH",
    "KXTRUMPMEETING", "KXGREENLAND", "KXSCOTUS", "KXRECESSION",
    "KXUKRAINE", "KXIRAN", "KXBITCOIN", "KXSP500", "KXDOGE",
    "KXGOVTCUTS", "KXGOVTSPEND", "KXDEBT", "KXCR",
    "KXSHUTDOWNBY", "KXTARIFF", "KXFEDRATE",
    "KXCABINET", "KXTERMINALRATE", "KXLOWESTRATE",
    "KXTRUMPSAYNICKNAME", "KXTRUMPRESIGN", "KXTRUMPREMOVE",
    "KXTRUMPPARDONFAMILY", "KXTRUMPAGCOUNT", "KXEOTRUMPTERM",
    "KXTRUMPAPPROVALYEAR", "KXTRUMPPRES", "KXTRUMPRUN",
    "KXIMPEACH", "KXMARTIAL", "KXNEXTPRESSEC", "KXNEXTDHSSEC",
    "KXDEBTGROWTH", "KXACAREPEAL", "KXFREEIVF", "KXTAFTHARTLEY",
    "KXBALANCEPOWERCOMBO", "KXCAPCONTROL", "KXDOED",
    "KXSCOTUSPOWER", "KXJAN6CASES", "KXOBERGEFELL",
    "KXUSDEBT", "KXLCPIMAXYOY",
    "KXFEDCHAIRNOM", "KXFEDEMPLOYEES", "KXTRILLIONAIRE",
    "KXKHAMENEIOUT", "KXGREENTERRITORY", "KXGREENLANDPRICE",
    "KXCANAL", "KXNEWPOPE", "KXFULLTERMSKPRES",
    "KXNEXTIRANLEADER", "KXPUTINDJTLOCATION",
    "KXWITHDRAW", "KXUSAKIM", "KXRECOGSOMALI",
    "KXFTA", "KXDJTVOSTARIFFS", "KXZELENSKYPUTIN",
    "KXPRESNOMD", "KXVPRESNOMD", "KXPRESPARTY",
    "KXHOUSERACE", "KXMUSKPRIMARY", "KXAOCSENATE",
    "CONTROLH", "POWER",
    "KXIPOSPACEX", "KXIPOFANNIE", "KXSPACEXBANKPUBLIC",
    "KXTARIFFS",
    "KXBILLSIGNED", "KXTRUMPBILLSSIGNED",
]

def api_get(endpoint, params=None):
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"API error on {endpoint}: {e}")
        return None

def kalshi_url(ticker):
    return f"https://kalshi.com/markets/{ticker.lower()}"

def format_vol(v):
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    elif v >= 1_000:
        return f"{v/1_000:.0f}K"
    return str(v)

def analyze_rules(rules_text):
    """Parse resolution rules"""
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
    
    # Official data sources
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
    
    # Procedural complexity
    procedural_keywords = [
        "pass both", "senate and house", "signed into law",
        "confirmed by", "ratified", "approved by congress",
    ]
    if any(kw in text_lower for kw in procedural_keywords):
        analysis["procedural_risk"] = True
    
    # Ambiguous terms
    ambiguous_terms = ["may", "could", "might", "approximately", "around"]
    if any(term in text_lower for term in ambiguous_terms):
        analysis["ambiguity"] = True
    
    return analysis

def score_market(m):
    """Score and decide on a market"""
    score = 0
    reasons = []
    
    price = m.get("last_price", 50)
    spread = (m.get("yes_ask", 0) - m.get("yes_bid", 0)) if m.get("yes_ask") else 99
    rules = m.get("rules", "")
    
    close_str = m.get("close_time", "")
    if not close_str:
        return None
    
    try:
        close = datetime.fromisoformat(close_str.replace("Z", "+00:00"))
        days = (close - datetime.now(timezone.utc)).days
    except:
        return None
    
    if days <= 0:
        return None
    
    side = "YES" if price >= 85 else "NO"
    cost = price if price >= 85 else (100 - price)
    ret = ((100 - cost) / cost) * 100 if cost > 0 else 0
    ann_yield = (ret / max(days, 1)) * 365
    
    if ann_yield < 100:
        return None
    
    score += int(ann_yield / 100) * 10
    reasons.append(f"年化 {ann_yield:.0f}%")
    
    if spread <= 3:
        score += 10
        reasons.append("流动性好")
    elif spread <= 5:
        score += 5
        reasons.append("流动性尚可")
    
    rule_analysis = analyze_rules(rules)
    
    if rule_analysis["official_source"]:
        score += 30
        reasons.append(f"✅ {rule_analysis['official_source']} 数据源")
    else:
        reasons.append("⚠️ 无官方数据源")
    
    if not rule_analysis["procedural_risk"]:
        score += 20
        reasons.append("✅ 无程序性风险")
    else:
        reasons.append("⚠️ 有程序性障碍")
    
    if rule_analysis["ambiguity"]:
        score -= 10
        reasons.append("⚠️ 规则模糊")
    
    # Decision
    if score >= 70:
        decision = "🟢 BUY"
        confidence = "HIGH"
        position = 200 if score >= 85 else 100
    elif score >= 50:
        decision = "🟡 WAIT"
        confidence = "MEDIUM"
        position = 50
    else:
        decision = "🔴 SKIP"
        confidence = "LOW"
        position = 0
    
    return {
        "decision": decision,
        "score": score,
        "confidence": confidence,
        "position": position,
        "side": side,
        "cost": cost,
        "ann_yield": ann_yield,
        "days": days,
        "reasons": reasons,
        "spread": spread,
        "vol": m.get("volume_24h", 0),
        "ticker": m.get("ticker", ""),
        "title": m.get("title", ""),
        "sub": m.get("yes_sub_title", "") or m.get("no_sub_title", ""),
    }

def scan_and_decide():
    now = datetime.now(timezone.utc)
    
    # Fetch all political markets (with rate limiting)
    all_markets = []
    for i, series in enumerate(POLITICAL_SERIES):
        data = api_get("/markets", {"limit": 50, "status": "open", "series_ticker": series})
        if data:
            all_markets.extend(data.get("markets", []))
        # Rate limit: 1 req/sec (Kalshi limit is ~10/sec but be conservative)
        if i < len(POLITICAL_SERIES) - 1:
            time.sleep(0.2)
    
    # Score each junk bond candidate
    opportunities = []
    for m in all_markets:
        price = m.get("last_price", 50)
        if (price >= 85 or price <= 12):
            result = score_market(m)
            if result:
                opportunities.append(result)
    
    # Sort by score
    opportunities.sort(key=lambda x: -x["score"])
    
    # Format report
    lines = []
    lines.append(f"⚡ Kalshi Decision Report — {now.strftime('%m/%d %H:%M UTC')}")
    lines.append(f"扫描了 {len(all_markets)} 个市场，找到 {len(opportunities)} 个高确定性机会\n")
    
    if not opportunities:
        lines.append("😴 暂无符合标准的机会")
        return "\n".join(lines)
    
    # Categorize
    buys = [o for o in opportunities if "BUY" in o["decision"]]
    waits = [o for o in opportunities if "WAIT" in o["decision"]]
    skips = [o for o in opportunities if "SKIP" in o["decision"]]
    
    # BUY recommendations
    if buys:
        lines.append(f"🟢 推荐买入 ({len(buys)})\n")
        for i, o in enumerate(buys[:5], 1):
            full_name = f"{o['title']} → {o['sub']}" if o['sub'] else o['title']
            lines.append(f"#{i} {o['decision']} — 评分 {o['score']}/100")
            lines.append(f"   {full_name}")
            lines.append(f"   👉 {o['side']} @ {o['cost']:.0f}¢ | 仓位 ${o['position']}")
            lines.append(f"   📊 {o['ann_yield']:.0f}% 年化 ({o['days']}天) | spread {o['spread']}¢ | 量 {format_vol(o['vol'])}")
            lines.append(f"   💡 {' | '.join(o['reasons'])}")
            lines.append(f"   🔗 {kalshi_url(o['ticker'])}\n")
    
    # WAIT candidates
    if waits:
        lines.append(f"🟡 观望中 ({len(waits)})\n")
        for o in waits[:3]:
            full_name = f"{o['title']} → {o['sub']}" if o['sub'] else o['title']
            lines.append(f"   {o['decision']} ({o['score']}/100) — {full_name}")
            lines.append(f"   {o['side']} @ {o['cost']:.0f}¢ | {o['ann_yield']:.0f}% ann")
            lines.append(f"   💡 {' | '.join(o['reasons'])}")
            lines.append(f"   {kalshi_url(o['ticker'])}\n")
    
    # SKIP (show why they were rejected)
    if skips and not buys and not waits:
        lines.append(f"🔴 已拒绝 ({len(skips)}) — 高收益但风险不可控\n")
        for o in skips[:3]:
            full_name = f"{o['title']} → {o['sub']}" if o['sub'] else o['title']
            lines.append(f"   SKIP ({o['score']}/100) — {full_name}")
            lines.append(f"   {o['side']} @ {o['cost']:.0f}¢ | {o['ann_yield']:.0f}% ann")
            lines.append(f"   ❌ 拒绝原因: {' | '.join(o['reasons'])}")
            lines.append(f"   {kalshi_url(o['ticker'])}\n")
    
    if not buys and not waits:
        lines.append("\n⚠️ 本轮扫描无推荐标的 — 所有高收益机会都因规则/数据源问题被拒绝")
    
    return "\n".join(lines)

if __name__ == "__main__":
    report = scan_and_decide()
    print(report)
