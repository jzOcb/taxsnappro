exec(open('/tmp/sandbox_bootstrap.py').read())

"""
Kalshi Scanner → Telegram-friendly report
Outputs a clean, concise summary for messaging.

⚠️ CRITICAL: This scanner only does PRICE-LEVEL analysis.
Every recommendation MUST go through deep research (news, data sources,
procedural constraints) before being sent to Jason.
See kalshi/README.md for the mandatory research checklist.
"""

import requests
import json
import os
import sys
from datetime import datetime, timezone, timedelta

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

POLITICAL_SERIES = [
    # ---- HIGH PRIORITY (from discovery.py priority list) ----
    "KXGDP", "KXCPI", "KXFED", "KXGOVSHUTLENGTH",
    "KXTRUMPMEETING", "KXGREENLAND", "KXSCOTUS", "KXRECESSION",
    "KXUKRAINE", "KXIRAN", "KXBITCOIN", "KXSP500", "KXDOGE",
    "KXGOVTCUTS", "KXGOVTSPEND", "KXDEBT", "KXCR",
    "KXSHUTDOWNBY", "KXTARIFF", "KXFEDRATE",
    "KXCABINET", "KXTERMINALRATE", "KXLOWESTRATE",
    
    # ---- Trump / White House ----
    "KXTRUMPSAYNICKNAME", "KXTRUMPRESIGN", "KXTRUMPREMOVE",
    "KXTRUMPPARDONFAMILY", "KXTRUMPAGCOUNT", "KXEOTRUMPTERM",
    "KXTRUMPAPPROVALYEAR", "KXTRUMPPRES", "KXTRUMPRUN",
    "KXIMPEACH", "KXMARTIAL", "KXNEXTPRESSEC", "KXNEXTDHSSEC",
    
    # ---- Congress / Legislation ----
    "KXDEBTGROWTH", "KXACAREPEAL", "KXFREEIVF", "KXTAFTHARTLEY",
    "KXBALANCEPOWERCOMBO", "KXCAPCONTROL", "KXDOED",
    
    # ---- SCOTUS / Legal ----
    "KXSCOTUSPOWER", "KXJAN6CASES", "KXOBERGEFELL",
    
    # ---- Economy ----
    "KXUSDEBT", "KXLCPIMAXYOY",
    "KXFEDCHAIRNOM", "KXFEDEMPLOYEES", "KXTRILLIONAIRE",
    
    # ---- Foreign Policy / Geopolitics ----
    "KXKHAMENEIOUT", "KXGREENTERRITORY", "KXGREENLANDPRICE",
    "KXCANAL", "KXNEWPOPE", "KXFULLTERMSKPRES",
    "KXNEXTIRANLEADER", "KXPUTINDJTLOCATION",
    "KXWITHDRAW", "KXUSAKIM", "KXRECOGSOMALI",
    "KXFTA", "KXDJTVOSTARIFFS", "KXZELENSKYPUTIN",
    
    # ---- Elections ----
    "KXPRESNOMD", "KXVPRESNOMD", "KXPRESPARTY",
    "KXHOUSERACE", "KXMUSKPRIMARY", "KXAOCSENATE",
    "CONTROLH", "POWER",
    
    # ---- IPOs / Markets ----
    "KXIPOSPACEX", "KXIPOFANNIE", "KXSPACEXBANKPUBLIC",
    
    # ---- Tariffs (deduped) ----
    "KXTARIFFS",
    
    # ---- Bills ----
    "KXBILLSIGNED", "KXTRUMPBILLSSIGNED",
]

def api_get(endpoint, params=None):
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except:
        return None

def scan():
    now = datetime.now(timezone.utc)
    
    # Load previous state for comparison
    state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
    prev_state = {}
    for sp in [state_path, "/tmp/kalshi_state.json"]:
        try:
            with open(sp) as f:
                prev_state = json.load(f)
            break
        except:
            pass
    prev_prices = prev_state.get("prices", {})
    
    # Fetch markets
    all_markets = []
    for series in POLITICAL_SERIES:
        data = api_get("/markets", {"limit": 50, "status": "open", "series_ticker": series})
        if data:
            all_markets.extend(data.get("markets", []))
    
    # Analyze
    junk_bonds = []
    alerts = []
    movers = []
    current_prices = {}
    
    for m in all_markets:
        close_str = m.get("close_time", "")
        if not close_str:
            continue
        try:
            close = datetime.fromisoformat(close_str.replace("Z", "+00:00"))
        except:
            continue
        days = (close - now).days
        if days <= 0:
            continue
        
        ticker = m.get("ticker", "")
        price = m.get("last_price", 50)
        prev = m.get("previous_price", price)
        vol = m.get("volume_24h", 0)
        spread = (m.get("yes_ask", 0) - m.get("yes_bid", 0)) if m.get("yes_ask") else 99
        title = m.get("title", "")
        sub = m.get("yes_sub_title", "") or m.get("no_sub_title", "")
        
        current_prices[ticker] = price
        
        # Short name
        name = sub if sub else title
        if len(name) > 50:
            name = name[:47] + "..."
        
        # Junk bond (60 day horizon)
        if (price >= 85 or price <= 12) and days <= 60 and spread <= 15:
            side = "YES" if price >= 85 else "NO"
            cost = price if price >= 85 else (100 - price)
            ret = ((100 - cost) / cost) * 100 if cost > 0 else 0
            ann = (ret / max(days, 1)) * 365
            if ret >= 3:  # at least 3% return
                junk_bonds.append({
                    "name": name, "side": side, "cost": cost,
                    "ret": ret, "ann": ann, "days": days,
                    "spread": spread, "vol": vol, "ticker": ticker,
                })
        
        # Price movement alert (vs last scan)
        last_price = prev_prices.get(ticker)
        if last_price is not None:
            delta = abs(price - last_price)
            if delta >= 5:
                d = "📈" if price > last_price else "📉"
                alerts.append({
                    "name": name, "old": last_price, "new": price,
                    "delta": delta, "icon": d, "vol": vol,
                    "days": days, "ticker": ticker,
                })
        
        # 24h movers
        if abs(price - prev) >= 5 and vol >= 10:
            d = "📈" if price > prev else "📉"
            movers.append({
                "name": name, "old": prev, "new": price,
                "delta": abs(price - prev), "icon": d,
                "vol": vol, "days": days, "ticker": ticker,
            })
    
    # Sort
    junk_bonds.sort(key=lambda x: -x["ann"])
    alerts.sort(key=lambda x: -x["delta"])
    movers.sort(key=lambda x: -x["delta"])
    
    # Format Telegram message
    lines = []
    lines.append(f"⚡ Kalshi Scan — {now.strftime('%m/%d %H:%M UTC')}")
    lines.append(f"Markets: {len(all_markets)}")
    lines.append("")
    
    # Alerts (price changes since last scan)
    if alerts:
        lines.append("🚨 SINCE LAST SCAN")
        for a in alerts[:5]:
            lines.append(f"{a['icon']} {a['name']}")
            lines.append(f"   {a['old']}¢→{a['new']}¢ (Δ{a['delta']}¢) vol:{a['vol']}")
        lines.append("")
    
    # Top junk bonds
    if junk_bonds:
        lines.append(f"🎯 JUNK BONDS ({len(junk_bonds)})")
        for jb in junk_bonds[:8]:
            emoji = "🔥" if jb["ann"] >= 100 else "✅"
            lines.append(f"{emoji} {jb['side']}@{jb['cost']}¢ +{jb['ret']:.0f}% / {jb['days']}d ({jb['ann']:.0f}%ann)")
            lines.append(f"   {jb['name']}")
            lines.append(f"   sp:{jb['spread']} vol:{jb['vol']}")
        lines.append("")
    
    # 24h movers
    if movers:
        lines.append(f"🔥 24H MOVERS ({len(movers)})")
        for mv in movers[:5]:
            lines.append(f"{mv['icon']} {mv['name']}")
            lines.append(f"   {mv['old']}¢→{mv['new']}¢ (Δ{mv['delta']}¢) vol:{mv['vol']}")
        lines.append("")
    
    if not junk_bonds and not alerts and not movers:
        lines.append("😴 Nothing notable right now")
    
    report = "\n".join(lines)
    
    # Save state (try multiple paths for sandbox compatibility)
    new_state = {
        "last_scan": now.isoformat(),
        "prices": current_prices,
        "markets_count": len(all_markets),
        "junk_bonds_count": len(junk_bonds),
    }
    for sp in [state_path, "/tmp/kalshi_state.json"]:
        try:
            with open(sp, "w") as f:
                json.dump(new_state, f, indent=2)
            break
        except:
            pass
    
    return report, len(alerts), len(junk_bonds), junk_bonds, movers

if __name__ == "__main__":
    report, n_alerts, n_jb, jb_list, movers_list = scan()
    print(report)
    
    # If --research flag, auto-research top opportunities
    if "--research" in sys.argv and jb_list:
        from research import research_market
        print("\n" + "=" * 60)
        print("🔍 AUTO-RESEARCH: Top Junk Bonds")
        print("=" * 60)
        for jb in jb_list[:3]:
            ticker = jb["ticker"]
            name = jb["name"]
            try:
                r = research_market(ticker, name)
                print(f"\n{r}")
            except Exception as e:
                print(f"\n⚠️ Research failed for {ticker}: {e}")
            print("-" * 60)
