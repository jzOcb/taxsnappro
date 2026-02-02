#!/usr/bin/env python3
"""
Better delay measurement using Coinbase API
Longer intervals to avoid rate limits
"""
import json
import time
import urllib.request as request
from datetime import datetime

def get_btc_coinbase():
    """Coinbase has better rate limits"""
    req = request.Request("https://api.coinbase.com/v2/prices/BTC-USD/spot",
                         headers={'User-Agent': 'Mozilla/5.0'})
    with request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read())
    return float(data['data']['amount']), datetime.now()

def get_kalshi_market():
    req = request.Request("https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXBTC15M&status=open&limit=1",
                         headers={'User-Agent': 'Mozilla/5.0'})
    with request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read())
    markets = data.get('markets', [])
    if not markets:
        return None
    m = markets[0]
    return {
        'ticker': m.get('ticker'),
        'title': m.get('title'),
        'yes_bid': m.get('yes_bid', 0),
        'yes_ask': m.get('yes_ask', 0),
        'close_time': m.get('close_time'),
        'volume': m.get('volume', 0),
        'timestamp': datetime.now()
    }

print("=" * 70)
print("IMPROVED DELAY MEASUREMENT")
print("API: Coinbase (better rate limits)")
print("Interval: 10 seconds (avoid 429)")
print("=" * 70)

# Check current market status
kalshi = get_kalshi_market()
if kalshi:
    print(f"\n📊 Current market: {kalshi['ticker']}")
    print(f"   Question: {kalshi['title']}")
    print(f"   YES: {kalshi['yes_bid']}¢ / {kalshi['yes_ask']}¢")
    print(f"   Volume: ${kalshi['volume']:,}")
    print(f"   Closes: {kalshi['close_time']}")
    
    yes_mid = (kalshi['yes_bid'] + kalshi['yes_ask']) / 2
    if yes_mid > 95:
        print(f"\n⚠️  Market close to certainty ({yes_mid}¢)")
        print("   Best to wait for next 15-min market for meaningful test")
        print("\n   Run this script again in ~15 minutes for fresh market")
    else:
        print(f"\n✅ Market has uncertainty ({yes_mid}¢) - good for testing")
        print("\nStarting 2-minute monitoring...\n")
        print("Time     | BTC Price | Kalshi YES | Move")
        print("-" * 70)
        
        history = []
        for i in range(12):  # 2 minutes / 10sec intervals
            try:
                btc_price, btc_time = get_btc_coinbase()
                kalshi = get_kalshi_market()
                
                if kalshi:
                    yes_mid = (kalshi['yes_bid'] + kalshi['yes_ask']) / 2
                    
                    move = ""
                    if history:
                        last_btc = history[-1]['btc_price']
                        last_kalshi = history[-1]['kalshi_yes']
                        if abs(btc_price - last_btc) > 50:
                            move = f"BTC {'+' if btc_price > last_btc else ''}{btc_price - last_btc:.0f}"
                        if abs(yes_mid - last_kalshi) > 2:
                            move += f" | Kalshi {'+' if yes_mid > last_kalshi else ''}{yes_mid - last_kalshi:.0f}¢"
                    
                    print(f"{btc_time.strftime('%H:%M:%S')} | ${btc_price:>9,.0f} | {yes_mid:>6.1f}¢  | {move}")
                    
                    history.append({
                        'btc_price': btc_price,
                        'kalshi_yes': yes_mid,
                        'time': btc_time.isoformat()
                    })
            except Exception as e:
                print(f"Error: {e}")
            
            if i < 11:
                time.sleep(10)
        
        with open('data/delay_measurement_v2.json', 'w') as f:
            json.dump(history, f, indent=2)
        print(f"\n✅ Saved: data/delay_measurement_v2.json")
else:
    print("\n⚠️  No active KXBTC15M market right now")
    print("   Wait for next 15-minute window")
