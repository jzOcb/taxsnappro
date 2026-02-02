#!/usr/bin/env python3
"""
Measure price update delay between Binance and Kalshi

This script will:
1. Monitor Binance BTC price via REST API (WebSocket needs async)
2. Check Kalshi KXBTC15M market price
3. Log timestamps and price differences
4. Calculate average delay
"""
import json
import time
from urllib import request
from datetime import datetime

def get_binance_price():
    """Get current BTC price from Binance"""
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    with request.urlopen(url, timeout=5) as response:
        data = json.loads(response.read())
    return float(data['price']), datetime.now()

def get_kalshi_market():
    """Get current KXBTC15M market"""
    url = "https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXBTC15M&status=open&limit=1"
    req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read())
    
    markets = data.get('markets', [])
    if not markets:
        return None
    
    m = markets[0]
    return {
        'ticker': m.get('ticker'),
        'yes_bid': m.get('yes_bid', 0),
        'yes_ask': m.get('yes_ask', 0),
        'last_price': m.get('last_price', 0),
        'volume': m.get('volume', 0),
        'timestamp': datetime.now()
    }

print("=" * 70)
print("BINANCE ↔ KALSHI DELAY MEASUREMENT")
print("=" * 70)
print("\nMonitoring for 60 seconds...\n")
print("Timestamp         | Binance BTC | Kalshi YES | Spread | Volume")
print("-" * 70)

# Store historical data
history = []

try:
    for i in range(12):  # 12 samples over 60 seconds
        try:
            # Get both prices
            btc_price, btc_time = get_binance_price()
            kalshi_market = get_kalshi_market()
            
            if kalshi_market:
                yes_price = (kalshi_market['yes_bid'] + kalshi_market['yes_ask']) / 2
                spread = kalshi_market['yes_ask'] - kalshi_market['yes_bid']
                volume = kalshi_market['volume']
                
                print(f"{btc_time.strftime('%H:%M:%S')}    | ${btc_price:>10,.2f} | {yes_price:>6.1f}¢   | {spread:>2.0f}¢  | ${volume:>6,.0f}")
                
                history.append({
                    'btc_price': btc_price,
                    'kalshi_yes': yes_price,
                    'spread': spread,
                    'volume': volume,
                    'time': btc_time
                })
            else:
                print(f"{btc_time.strftime('%H:%M:%S')}    | ${btc_price:>10,.2f} | No market active")
        
        except Exception as e:
            print(f"Error: {e}")
        
        if i < 11:  # Don't sleep on last iteration
            time.sleep(5)

except KeyboardInterrupt:
    print("\n\nStopped by user")

# Analysis
print("\n" + "=" * 70)
print("ANALYSIS")
print("=" * 70)

if len(history) > 1:
    # Check if Kalshi price responds to BTC moves
    btc_changes = []
    kalshi_changes = []
    
    for i in range(1, len(history)):
        btc_change = history[i]['btc_price'] - history[i-1]['btc_price']
        kalshi_change = history[i]['kalshi_yes'] - history[i-1]['kalshi_yes']
        
        btc_changes.append(btc_change)
        kalshi_changes.append(kalshi_change)
    
    print(f"\nBTC price moves: {len([x for x in btc_changes if abs(x) > 10])} significant")
    print(f"Kalshi price moves: {len([x for x in kalshi_changes if x != 0])} updates")
    
    avg_spread = sum(h['spread'] for h in history) / len(history)
    avg_volume = sum(h['volume'] for h in history) / len(history)
    
    print(f"\nAverage spread: {avg_spread:.1f}¢")
    print(f"Average volume: ${avg_volume:,.0f}")
    
    print("\n⚠️  LIMITATION: This REST-based measurement has 5s intervals")
    print("    Real delay measurement requires WebSocket (real-time)")
    print("    Next step: Build WebSocket monitor for precise timing")
else:
    print("Not enough data collected")

# Save data
with open('data/delay_measurement.json', 'w') as f:
    json.dump([{
        'btc_price': h['btc_price'],
        'kalshi_yes': h['kalshi_yes'],
        'spread': h['spread'],
        'volume': h['volume'],
        'time': h['time'].isoformat()
    } for h in history], f, indent=2)

print(f"\nData saved to: data/delay_measurement.json")
