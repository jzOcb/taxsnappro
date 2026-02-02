#!/usr/bin/env python3
import json, time, sys
from datetime import datetime
from urllib import request

class Trader:
    def __init__(self):
        self.balance = 1000
        self.initial = 1000
        self.positions = []
        self.trades = []
        self.pnl = 0
    
    def open(self, direction, size, price, ticker):
        cost = size * price
        if cost > self.balance:
            return None
        pos = {
            'id': len(self.positions),
            'dir': direction,
            'size': size,
            'entry': price,
            'time': datetime.now().isoformat(),
            'ticker': ticker,
            'open': True,
        }
        self.positions.append(pos)
        self.balance -= cost
        print(f"  ✅ OPEN {direction} {size} @ ${price:.2f}", flush=True)
        return pos['id']
    
    def close(self, pos_id, exit_price):
        pos = next((p for p in self.positions if p['id'] == pos_id and p['open']), None)
        if not pos:
            return
        
        pnl = (exit_price - pos['entry']) * pos['size']
        if pos['dir'] == 'NO':
            pnl = -pnl
        
        pos['exit'] = exit_price
        pos['pnl'] = pnl
        pos['open'] = False
        self.balance += pos['size'] * exit_price
        self.pnl += pnl
        self.trades.append(pos.copy())
        
        status = "WIN" if pnl > 0 else "LOSS"
        print(f"  {'✅' if pnl > 0 else '❌'} CLOSE {pos['dir']} @ ${exit_price:.2f} | P&L: ${pnl:+.2f} [{status}]", flush=True)
        return pnl
    
    def get_open(self):
        return [p for p in self.positions if p['open']]

def fetch_brti():
    try:
        req = request.Request('https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with request.urlopen(req, timeout=3) as r:
            return float(json.loads(r.read())['price'])
    except:
        return None

def fetch_kalshi():
    try:
        req = request.Request('https://api.elections.kalshi.com/trade-api/v2/markets?limit=10&series_ticker=KXBTC15M&status=open')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read())
            if data.get('markets'):
                m = data['markets'][0]
                return {
                    'ticker': m['ticker'],
                    'yes_bid': m.get('yes_bid', 0) / 100,
                    'yes_ask': m.get('yes_ask', 0) / 100,
                }
    except:
        pass
    return None

duration_min = int(sys.argv[1]) if len(sys.argv) > 1 else 480
interval_sec = int(sys.argv[2]) if len(sys.argv) > 2 else 60
trade_size = int(sys.argv[3]) if len(sys.argv) > 3 else 10

print(f"\n{'='*70}", flush=True)
print(f"PAPER TRADING - {duration_min}min / {interval_sec}s / {trade_size} contracts", flush=True)
print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", flush=True)
print(f"{'='*70}\n", flush=True)

trader = Trader()
start = time.time()
end = start + (duration_min * 60)
last_brti = None
last_kalshi_bid = None

while time.time() < end:
    elapsed = int(time.time() - start)
    brti = fetch_brti()
    kalshi = fetch_kalshi()
    
    if not brti or not kalshi:
        print(f"[{elapsed:4d}s] ⚠️  Data fetch failed", flush=True)
        time.sleep(interval_sec)
        continue
    
    brti_chg = ((brti - last_brti) / last_brti * 100) if last_brti else None
    kalshi_chg = ((kalshi['yes_bid'] - last_kalshi_bid) / last_kalshi_bid * 100) if last_kalshi_bid else None
    
    # Trading logic
    signal = None
    if brti_chg and kalshi_chg:
        if abs(brti_chg) > 0.2 and abs(kalshi_chg) < 0.1:
            signal = "WINDOW"
            if len(trader.get_open()) == 0:
                direction = 'YES' if brti_chg > 0 else 'NO'
                entry = kalshi['yes_ask'] if direction == 'YES' else (1 - kalshi['yes_bid'])
                trader.open(direction, trade_size, entry, kalshi['ticker'])
    
    # Check open positions
    for pos in trader.get_open():
        hold_sec = (datetime.now() - datetime.fromisoformat(pos['time'])).total_seconds()
        if hold_sec > 180:  # 3 minutes
            exit_price = kalshi['yes_bid'] if pos['dir'] == 'YES' else (1 - kalshi['yes_ask'])
            trader.close(pos['id'], exit_price)
    
    brti_str = f"{brti_chg:+.3f}%" if brti_chg else "N/A"
    kalshi_str = f"{kalshi_chg:+.2f}%" if kalshi_chg else "N/A"
    pos_str = f" | Pos: {len(trader.get_open())}" if trader.get_open() else ""
    pnl_str = f" | P&L: ${trader.pnl:+.2f}" if trader.trades else ""
    sig_str = f" [{signal}]" if signal else ""
    
    print(f"[{elapsed:4d}s] BRTI: ${brti:,.2f} ({brti_str}) | "
          f"Kalshi: {kalshi['yes_bid']:.2f}/{kalshi['yes_ask']:.2f} ({kalshi_str}){sig_str}{pos_str}{pnl_str}", flush=True)
    
    last_brti = brti
    last_kalshi_bid = kalshi['yes_bid']
    time.sleep(interval_sec)

# Summary
print(f"\n{'='*70}", flush=True)
print(f"SUMMARY: ${trader.initial:.2f} → ${trader.balance:.2f} | "
      f"P&L: ${trader.pnl:+.2f} | Trades: {len(trader.trades)}", flush=True)

if trader.trades:
    wins = [t for t in trader.trades if t['pnl'] > 0]
    print(f"Win Rate: {len(wins)}/{len(trader.trades)} = {len(wins)/len(trader.trades)*100:.1f}%", flush=True)

# Save
import os
os.makedirs('data', exist_ok=True)
filename = f"data/paper_trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump({
        'duration_min': duration_min,
        'initial': trader.initial,
        'final': trader.balance,
        'pnl': trader.pnl,
        'trades': trader.trades,
    }, f, indent=2)

print(f"Saved: {filename}", flush=True)
print(f"{'='*70}\n", flush=True)
