#!/usr/bin/env python3
"""
Measure delay between Binance.US and Kalshi KXBTC15M markets
Critical for arbitrage opportunity assessment
"""

import json
import time
import os
from datetime import datetime
from urllib import request
from urllib.error import URLError

# API endpoints
BINANCE_URL = "https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT"
KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_EMAIL = os.getenv('KALSHI_EMAIL')
KALSHI_PASSWORD = os.getenv('KALSHI_PASSWORD')

def get_binance_price():
    """Get BTC price from Binance.US"""
    req = request.Request(BINANCE_URL)
    req.add_header('User-Agent', 'Mozilla/5.0')
    
    try:
        with request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
        return {
            'price': float(data['price']),
            'timestamp': datetime.now(),
            'source': 'Binance.US'
        }
    except Exception as e:
        print(f"❌ Binance error: {e}")
        return None

def get_kalshi_btc_market():
    """Get current active KXBTC15M market"""
    # Use the search endpoint we know works
    url = f"{KALSHI_API_BASE}/markets?limit=200&series_ticker=KXBTC15M&status=open"
    
    req = request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    
    try:
        with request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        
        if data.get('markets') and len(data['markets']) > 0:
            # Get the most recent market (usually first in list)
            market = data['markets'][0]
            return {
                'ticker': market['ticker'],
                'yes_bid': market.get('yes_bid', 0) / 100,  # Convert cents to dollars
                'yes_ask': market.get('yes_ask', 0) / 100,
                'no_bid': market.get('no_bid', 0) / 100,
                'no_ask': market.get('no_ask', 0) / 100,
                'volume': market.get('volume', 0),
                'close_time': market.get('close_time'),
                'timestamp': datetime.now(),
                'source': 'Kalshi'
            }
        else:
            print("No open KXBTC15M markets found")
            return None
            
    except Exception as e:
        print(f"❌ Kalshi error: {e}")
        return None

def measure_once():
    """Single measurement cycle"""
    print(f"\n{'='*70}")
    print(f"Measurement @ {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    print(f"{'='*70}")
    
    # Get both prices simultaneously
    start = time.time()
    binance_data = get_binance_price()
    binance_latency = (time.time() - start) * 1000
    
    start = time.time()
    kalshi_data = get_kalshi_btc_market()
    kalshi_latency = (time.time() - start) * 1000
    
    if not binance_data or not kalshi_data:
        print("❌ Failed to get data from one or both sources")
        return None
    
    # Calculate implied Kalshi price (mid-point of yes_bid and yes_ask)
    # In KXBTC15M, YES means "BTC will be above X", so we need to extract the strike
    # For now, just show the market prices
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'binance': {
            'price': binance_data['price'],
            'latency_ms': binance_latency,
            'timestamp': binance_data['timestamp'].isoformat()
        },
        'kalshi': {
            'ticker': kalshi_data['ticker'],
            'yes_bid': kalshi_data['yes_bid'],
            'yes_ask': kalshi_data['yes_ask'],
            'latency_ms': kalshi_latency,
            'timestamp': kalshi_data['timestamp'].isoformat()
        }
    }
    
    print(f"\n📊 Binance.US:")
    print(f"   Price: ${binance_data['price']:,.2f}")
    print(f"   Latency: {binance_latency:.1f}ms")
    
    print(f"\n📊 Kalshi {kalshi_data['ticker']}:")
    print(f"   YES bid: ${kalshi_data['yes_bid']:.2f}")
    print(f"   YES ask: ${kalshi_data['yes_ask']:.2f}")
    print(f"   Latency: {kalshi_latency:.1f}ms")
    print(f"   Volume: {kalshi_data['volume']}")
    
    return result

def measure_continuous(duration=60, interval=5):
    """Continuous measurement for duration"""
    print("\n" + "🔍 " * 25)
    print("BINANCE.US vs KALSHI DELAY MEASUREMENT")
    print("🔍 " * 25)
    print(f"\nDuration: {duration}s | Interval: {interval}s")
    
    results = []
    start_time = time.time()
    measurement_count = 0
    
    while time.time() - start_time < duration:
        measurement_count += 1
        print(f"\n[Measurement #{measurement_count}]")
        
        result = measure_once()
        if result:
            results.append(result)
        
        time.sleep(interval)
    
    # Save results
    output_file = f"data/delay_measurement_binance_us_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs('data', exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            'measurements': results,
            'summary': {
                'total_measurements': len(results),
                'duration_seconds': duration,
                'interval_seconds': interval
            }
        }, f, indent=2)
    
    print(f"\n{'='*70}")
    print("MEASUREMENT COMPLETE")
    print(f"{'='*70}")
    print(f"Total measurements: {len(results)}")
    print(f"Saved to: {output_file}")
    
    if results:
        avg_binance_latency = sum(r['binance']['latency_ms'] for r in results) / len(results)
        avg_kalshi_latency = sum(r['kalshi']['latency_ms'] for r in results) / len(results)
        
        print(f"\nAverage latencies:")
        print(f"  Binance.US: {avg_binance_latency:.1f}ms")
        print(f"  Kalshi: {avg_kalshi_latency:.1f}ms")
        print(f"  Difference: {abs(avg_kalshi_latency - avg_binance_latency):.1f}ms")

if __name__ == "__main__":
    import sys
    
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    try:
        measure_continuous(duration, interval)
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
