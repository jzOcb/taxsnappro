exec(open('/tmp/sandbox_bootstrap.py').read())

"""
Kalshi Portfolio Tracker
Track positions, P&L, and exposure.

Usage:
  python portfolio.py                    # Show current portfolio
  python portfolio.py add <ticker> <side> <qty> <price>  # Add position
  python portfolio.py close <ticker>     # Close position (settled at 100)
  python portfolio.py loss <ticker>      # Close position (settled at 0)
  python portfolio.py history            # Show trade history
"""

import json
import sys
import os
from datetime import datetime, timezone

WATCHLIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")
# Fallback for sandbox
WATCHLIST_FALLBACK = "/tmp/kalshi_watchlist.json"

def load_data():
    for path in [WATCHLIST_PATH, WATCHLIST_FALLBACK]:
        try:
            with open(path) as f:
                return json.load(f)
        except:
            pass
    return {"positions": [], "watching": [], "history": []}

def save_data(data):
    for path in [WATCHLIST_PATH, WATCHLIST_FALLBACK]:
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            return
        except:
            pass
    print("⚠️ Could not save data")

def add_position(ticker, side, qty, price, note=""):
    data = load_data()
    pos = {
        "ticker": ticker,
        "side": side.upper(),
        "qty": int(qty),
        "entry_price": int(price),
        "cost": int(qty) * int(price),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "note": note,
    }
    data["positions"].append(pos)
    save_data(data)
    print(f"✅ Added: {side.upper()} {qty}x {ticker} @ {price}¢")
    print(f"   Cost: ${int(qty) * int(price) / 100:.2f}")

def close_position(ticker, won=True):
    data = load_data()
    found = None
    for i, pos in enumerate(data["positions"]):
        if pos["ticker"] == ticker:
            found = i
            break
    
    if found is None:
        print(f"❌ Position {ticker} not found")
        return
    
    pos = data["positions"].pop(found)
    settle = 100 if won else 0
    pnl_per = settle - pos["entry_price"] if pos["side"] == "YES" else pos["entry_price"] - settle
    pnl = pos["qty"] * pnl_per
    
    record = {
        **pos,
        "close_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "result": "WIN" if won else "LOSS",
        "pnl_cents": pnl,
        "pnl_dollars": pnl / 100,
    }
    data["history"].append(record)
    save_data(data)
    
    icon = "✅" if won else "❌"
    print(f"{icon} Closed: {pos['side']} {pos['qty']}x {ticker}")
    print(f"   Entry: {pos['entry_price']}¢ → Settle: {settle}¢")
    print(f"   P&L: ${pnl/100:+.2f}")

def show_portfolio():
    data = load_data()
    positions = data.get("positions", [])
    history = data.get("history", [])
    
    print("=" * 55)
    print("💼 KALSHI PORTFOLIO")
    print("=" * 55)
    
    if not positions:
        print("\n  No open positions")
    else:
        print(f"\n📊 OPEN POSITIONS ({len(positions)})")
        print("-" * 50)
        total_cost = 0
        for p in positions:
            cost = p["qty"] * p["entry_price"]
            total_cost += cost
            max_profit = p["qty"] * (100 - p["entry_price"])
            ret = ((100 - p["entry_price"]) / p["entry_price"]) * 100
            print(f"  {p['side']}  {p['qty']}x @ {p['entry_price']}¢  |  ${cost/100:.2f}  |  +{ret:.0f}%")
            print(f"    {p['ticker']}")
            if p.get("note"):
                print(f"    📝 {p['note']}")
            print(f"    Opened: {p['date']}")
            print()
        print(f"  Total invested: ${total_cost/100:.2f}")
        print(f"  Max return if all win: ${(len(positions) * 100 * positions[0]['qty'] - total_cost)/100:.2f}" if positions else "")
    
    # P&L summary
    if history:
        print(f"\n📈 TRADE HISTORY ({len(history)})")
        print("-" * 50)
        total_pnl = 0
        wins = 0
        losses = 0
        for h in history[-10:]:  # Last 10
            icon = "✅" if h["result"] == "WIN" else "❌"
            pnl = h.get("pnl_dollars", h.get("pnl_cents", 0) / 100)
            total_pnl += pnl
            if h["result"] == "WIN":
                wins += 1
            else:
                losses += 1
            print(f"  {icon} {h['side']} {h['qty']}x @ {h['entry_price']}¢ → ${pnl:+.2f} ({h['close_date']})")
            print(f"     {h['ticker']}")
        
        print(f"\n  Total P&L: ${total_pnl:+.2f}")
        print(f"  Win rate: {wins}/{wins+losses} ({wins/(wins+losses)*100:.0f}%)" if (wins+losses) > 0 else "")

def show_history():
    data = load_data()
    history = data.get("history", [])
    if not history:
        print("No trade history")
        return
    
    print("📜 FULL TRADE HISTORY")
    print("=" * 55)
    total = 0
    for h in history:
        icon = "✅" if h["result"] == "WIN" else "❌"
        pnl = h.get("pnl_dollars", h.get("pnl_cents", 0) / 100)
        total += pnl
        print(f"{icon} {h['date']} → {h['close_date']}  {h['side']} {h['qty']}x @ {h['entry_price']}¢  ${pnl:+.2f}")
        print(f"   {h['ticker']}")
        if h.get("note"):
            print(f"   📝 {h['note']}")
    print(f"\nCumulative P&L: ${total:+.2f}")

def main():
    if len(sys.argv) < 2:
        show_portfolio()
        return
    
    cmd = sys.argv[1]
    
    if cmd == "add":
        if len(sys.argv) < 6:
            print("Usage: portfolio.py add <ticker> <YES/NO> <qty> <price> [note]")
            return
        note = " ".join(sys.argv[6:]) if len(sys.argv) > 6 else ""
        add_position(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], note)
    
    elif cmd == "close":
        if len(sys.argv) < 3:
            print("Usage: portfolio.py close <ticker>")
            return
        close_position(sys.argv[2], won=True)
    
    elif cmd == "loss":
        if len(sys.argv) < 3:
            print("Usage: portfolio.py loss <ticker>")
            return
        close_position(sys.argv[2], won=False)
    
    elif cmd == "history":
        show_history()
    
    elif cmd == "watch":
        data = load_data()
        if len(sys.argv) >= 3:
            data["watching"].append({
                "ticker": sys.argv[2],
                "note": " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "",
                "added": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })
            save_data(data)
            print(f"👁️ Watching: {sys.argv[2]}")
        else:
            print("👁️ WATCHLIST")
            for w in data.get("watching", []):
                print(f"  {w['ticker']} — {w.get('note', '')} ({w.get('added', '')})")
    
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: add, close, loss, history, watch")

if __name__ == "__main__":
    main()
