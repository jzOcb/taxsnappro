#!/usr/bin/env python3
"""24-hour data collection - runs continuously"""
import json, time, os
from datetime import datetime
from urllib import request

def get_data():
    """Get BTC + Kalshi data"""
    # BRTI Proxy
    exchanges = {
        'binance_us': 'https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT',
        'coinbase': 'https://api.coinbase.com/v2/prices/BTC-USD/spot',
        'kraken': 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD',
    }
    
    prices = []
    for name, url in exchanges.items():
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        try:
            with request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read())
            if name == 'binance_us':
                prices.append(float(data['price']))
            elif name == 'coinbase':
                prices.append(float(data['data']['amount']))
            elif name == 'kraken':
                prices.append(float(data['result']['XXBTZUSD']['c'][0]))
        except: pass
    
    brti = sum(prices)/len(prices) if prices else None
    
    # Kalshi
    req = request.Request("https://api.elections.kalshi.com/trade-api/v2/markets?limit=10&series_ticker=KXBTC15M&status=open")
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    
    kalshi = None
    try:
        with request.urlopen(req, timeout=3) as r:
            d = json.loads(r.read())
        if d.get('markets'):
            m = d['markets'][0]
            kalshi = {
                'ticker': m['ticker'],
                'yes_bid': m.get('yes_bid',0)/100,
                'yes_ask': m.get('yes_ask',0)/100,
                'volume': m.get('volume',0),
            }
    except: pass
    
    return brti, kalshi

# Collect data
os.makedirs('data', exist_ok=True)
filename = f"data/collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

print(f"Collecting data to {filename}")
print("Press Ctrl+C to stop\n")

last_brti, last_kalshi = None, None
count = 0

with open(filename, 'w') as f:
    while True:
        brti, kalshi = get_data()
        
        if brti and kalshi:
            # Calculate changes
            brti_chg = ((brti-last_brti)/last_brti*100) if last_brti else None
            kalshi_chg = ((kalshi['yes_bid']-last_kalshi)/last_kalshi*100) if last_kalshi and last_kalshi>0 else None
            
            # Detect signal
            signal = None
            if brti_chg and kalshi_chg:
                if abs(brti_chg) > 0.08 and abs(kalshi_chg) < 0.03:
                    signal = "WINDOW"
            
            record = {
                't': datetime.now().isoformat(),
                'brti': round(brti, 2),
                'brti_chg': round(brti_chg, 4) if brti_chg else None,
                'kalshi': kalshi,
                'kalshi_chg': round(kalshi_chg, 4) if kalshi_chg else None,
                'signal': signal,
            }
            
            f.write(json.dumps(record) + '\n')
            f.flush()
            
            count += 1
            if count % 10 == 0:
                sig_str = f" [{signal}]" if signal else ""
                print(f"[{count:4d}] BRTI: ${brti:,.2f} | Kalshi: {kalshi['yes_bid']:.2f}{sig_str}")
            
            last_brti, last_kalshi = brti, kalshi['yes_bid']
        
        time.sleep(30)  # Every 30 seconds
