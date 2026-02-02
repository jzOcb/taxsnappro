#!/usr/bin/env python3
import json, time, sys
from datetime import datetime
from urllib import request

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

print(f"\n{'='*70}", flush=True)
print(f"OVERNIGHT MONITOR - {duration_min}min / {interval_sec}s interval", flush=True)
print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", flush=True)
print(f"{'='*70}\n", flush=True)

start = time.time()
end = start + (duration_min * 60)
results = []
last_brti = None

while time.time() < end:
    elapsed = int(time.time() - start)
    brti = fetch_brti()
    kalshi = fetch_kalshi()
    
    if brti and kalshi:
        chg = ((brti - last_brti) / last_brti * 100) if last_brti else None
        chg_str = f"{chg:+.3f}%" if chg else "N/A"
        
        print(f"[{elapsed:4d}s] BRTI: ${brti:,.2f} ({chg_str}) | "
              f"Kalshi: {kalshi['yes_bid']:.2f}/{kalshi['yes_ask']:.2f}", flush=True)
        
        results.append({
            'time': datetime.now().isoformat(),
            'brti': brti,
            'brti_chg': chg,
            'kalshi': kalshi,
        })
        last_brti = brti
    else:
        print(f"[{elapsed:4d}s] ⚠️  Data fetch failed", flush=True)
    
    time.sleep(interval_sec)

# Save
import os
os.makedirs('data', exist_ok=True)
filename = f"data/overnight_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump({'duration_min': duration_min, 'measurements': results}, f, indent=2)

print(f"\n✅ Complete: {len(results)} measurements saved to {filename}", flush=True)
