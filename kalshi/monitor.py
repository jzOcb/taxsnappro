exec(open('/tmp/sandbox_bootstrap.py').read())

import requests
import json
import sys
import os
import time
from datetime import datetime, timezone

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
API_DELAY = 0.35
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WATCHLIST_PATH = os.path.join(SCRIPT_DIR, "watchlist.json")
STATE_PATH = os.path.join(SCRIPT_DIR, "state.json")
FALLBACK_DIR = "/tmp"

PRICE_ALERT_THRESHOLD = 3  # cents
EXPIRY_ALERT_DAYS = 2  # alert when market closing within N days
JUNK_BOND_THRESHOLD = 88

def api_get(endpoint, params=None, retries=3):
    url = f"{API_BASE}{endpoint}"
    for attempt in range(retries):
        try:
            time.sleep(API_DELAY)
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                wait = min(10 * (attempt + 1), 60)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return None
    return None

def load_json(path, fallback_path=None):
    for p in [path, fallback_path]:
        if p and os.path.exists(p):
            try:
                with open(p, "r") as f:
                    return json.load(f)
            except:
                pass
    return {}

def save_json(data, path, fallback_path=None):
    for p in [path, fallback_path]:
        if not p:
            continue
        try:
            with open(p, "w") as f:
                json.dump(data, f, indent=2, default=str)
            return p
        except:
            continue
    return None

def load_watchlist():
    wl = load_json(WATCHLIST_PATH, os.path.join(FALLBACK_DIR, "kalshi_watchlist.json"))
    return wl if wl else {"series": [], "tickers": []}

def load_state():
    return load_json(STATE_PATH, os.path.join(FALLBACK_DIR, "kalshi_state.json"))

def save_state(state):
    return save_json(state, STATE_PATH, os.path.join(FALLBACK_DIR, "kalshi_state.json"))

def days_until(close_time_str):
    if not close_time_str:
        return 9999
    try:
        ct = close_time_str.replace("Z", "+00:00")
        ct_dt = datetime.fromisoformat(ct)
        now = datetime.now(timezone.utc)
        delta = ct_dt - now
        return max(0, delta.total_seconds() / 86400)
    except:
        return 9999

def fetch_markets_for_series(series_ticker):
    params = {"limit": 200, "status": "open", "series_ticker": series_ticker}
    data = api_get("/markets", params)
    if data:
        return data.get("markets", [])
    return []

def fetch_markets_for_event(event_ticker):
    params = {"limit": 200, "status": "open", "event_ticker": event_ticker}
    data = api_get("/markets", params)
    if data:
        return data.get("markets", [])
    return []

def fetch_market(ticker):
    data = api_get(f"/markets/{ticker}")
    if data:
        return data.get("market", data)
    return None

def get_price(m):
    return m.get("last_price") or m.get("yes_bid") or 0

def monitor():
    """Run one monitoring cycle."""
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%d %H:%M UTC")

    alerts = []
    new_junk_bonds = []
    expiring = []

    # Load watchlist and state
    watchlist = load_watchlist()
    state = load_state()
    last_prices = state.get("prices", {})
    last_run = state.get("last_run", "never")

    series_list = watchlist.get("series", [])
    ticker_list = watchlist.get("tickers", [])

    print(f"🔄 KALSHI MONITOR — {now_str}")
    print(f"   Last run: {last_run}")
    print(f"   Watching: {len(series_list)} series, {len(ticker_list)} tickers")
    print()

    all_markets = []

    # Fetch markets for watched series
    for series in series_list:
        markets = fetch_markets_for_series(series)
        if not markets:
            # Try as event ticker
            markets = fetch_markets_for_event(series)
        all_markets.extend(markets)

    # Fetch individual tickers
    for ticker in ticker_list:
        m = fetch_market(ticker)
        if m:
            all_markets.append(m)

    # Deduplicate
    seen = set()
    unique_markets = []
    for m in all_markets:
        t = m.get("ticker", "")
        if t and t not in seen:
            seen.add(t)
            unique_markets.append(m)

    print(f"   Fetched {len(unique_markets)} markets\n")

    new_prices = {}

    for m in unique_markets:
        ticker = m.get("ticker", "")
        title = m.get("title", "")
        subtitle = m.get("yes_sub_title", "")
        display = f"{title} ({subtitle})" if subtitle else title
        price = get_price(m)
        dtc = days_until(m.get("close_time", ""))
        spread = 99
        yb = m.get("yes_bid") or 0
        ya = m.get("yes_ask") or 0
        if yb and ya:
            spread = ya - yb

        new_prices[ticker] = price

        # Price move alert
        old_price = last_prices.get(ticker)
        if old_price is not None:
            move = price - old_price
            if abs(move) >= PRICE_ALERT_THRESHOLD:
                direction = "📈" if move > 0 else "📉"
                alerts.append({
                    "type": "price_move",
                    "ticker": ticker,
                    "title": display,
                    "old_price": old_price,
                    "new_price": price,
                    "move": move,
                    "emoji": direction,
                })

        # Junk bond opportunity (new)
        is_junk = (price >= JUNK_BOND_THRESHOLD or (price > 0 and price <= 100 - JUNK_BOND_THRESHOLD))
        was_junk_key = f"junk_{ticker}"
        if is_junk and spread <= 10 and dtc <= 60:
            if not state.get(was_junk_key):
                side = "YES" if price >= JUNK_BOND_THRESHOLD else "NO"
                new_junk_bonds.append({
                    "ticker": ticker,
                    "title": display,
                    "price": price,
                    "side": side,
                    "days": round(dtc, 1),
                    "spread": spread,
                })
            state[was_junk_key] = True
        else:
            state.pop(was_junk_key, None)

        # Expiry alert
        if dtc <= EXPIRY_ALERT_DAYS and dtc > 0:
            expiring.append({
                "ticker": ticker,
                "title": display,
                "price": price,
                "hours": round(dtc * 24, 1),
            })

    # Build output
    output_lines = []
    output_lines.append(f"🔄 *Kalshi Monitor* — {now_str}")
    output_lines.append(f"Tracking {len(unique_markets)} markets\n")

    if alerts:
        output_lines.append("*💥 PRICE ALERTS*")
        for a in sorted(alerts, key=lambda x: abs(x["move"]), reverse=True):
            output_lines.append(
                f'{a["emoji"]} `{a["ticker"]}` {a["old_price"]}→{a["new_price"]}¢ ({a["move"]:+g})'
            )
            output_lines.append(f'   {a["title"]}')
        output_lines.append("")

    if new_junk_bonds:
        output_lines.append("*🎯 NEW JUNK BOND OPPORTUNITIES*")
        for jb in new_junk_bonds:
            output_lines.append(
                f'💰 `{jb["ticker"]}` {jb["price"]}¢ — Buy {jb["side"]} ({jb["days"]}d, spread {jb["spread"]}¢)'
            )
            output_lines.append(f'   {jb["title"]}')
        output_lines.append("")

    if expiring:
        output_lines.append("*⏰ EXPIRING SOON*")
        for ex in expiring:
            output_lines.append(
                f'🕐 `{ex["ticker"]}` @ {ex["price"]}¢ — closes in {ex["hours"]}h'
            )
            output_lines.append(f'   {ex["title"]}')
        output_lines.append("")

    if not alerts and not new_junk_bonds and not expiring:
        output_lines.append("✅ No alerts — all quiet on the market front.")

    # Print output
    for line in output_lines:
        print(line)

    # Update state
    state["prices"] = new_prices
    state["last_run"] = now_str
    state["market_count"] = len(unique_markets)
    saved_to = save_state(state)
    if saved_to:
        print(f"\n💾 State saved to {saved_to}")

    return {
        "alerts": alerts,
        "new_junk_bonds": new_junk_bonds,
        "expiring": expiring,
        "telegram_message": "\n".join(output_lines),
    }

if __name__ == "__main__":
    monitor()
