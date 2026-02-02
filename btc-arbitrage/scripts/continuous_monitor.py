#!/usr/bin/env python3
"""
Continuous BRTI Proxy vs Kalshi Market Monitoring
"""

import json
import time
import os
from datetime import datetime
from urllib import request

def get_brti_proxy():
    """Quick BRTI proxy - average of 3 exchanges"""
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
            with request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
            
            if name == 'binance_us':
                prices.append(float(data['price']))
            elif name == 'coinbase':
                prices.append(float(data['data']['amount']))
            elif name == 'kraken':
                prices.append(float(data['result']['XXBTZUSD']['c'][0]))
        except:
            pass
    
    if prices:
        return sum(prices) / len(prices)
    return None

def get_kalshi_market():
    """Get current active KXBTC15M market"""
    url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=200&series_ticker=KXBTC15M&status=open"
    
    req = request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    
    try:
        with request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        
        if data.get('markets') and len(data['markets']) > 0:
            market = data['markets'][0]
            return {
                'ticker': market['ticker'],
                'yes_bid': market.get('yes_bid', 0) / 100,
                'yes_ask': market.get('yes_ask', 0) / 100,
                'volume': market.get('volume', 0),
                'close_time': market.get('close_time'),
            }
    except Exception as e:
        print(f"Kalshi error: {e}")
    
    return None

def monitor_continuously(duration_minutes=60, interval_seconds=10):
    """Monitor for extended period"""
    print(f"\n{'='*70}")
    print(f"CONTINUOUS BRTI PROXY vs KALSHI MONITORING")
    print(f"{'='*70}")
    print(f"Duration: {duration_minutes} minutes")
    print(f"Interval: {interval_seconds} seconds")
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*70}\n")
    
    results = []
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    last_brti = None
    last_kalshi_bid = None
    
    while time.time() < end_time:
        measurement_time = datetime.now()
        
        brti = get_brti_proxy()
        kalshi = get_kalshi_market()
        
        if brti and kalshi:
            brti_chg = None
            kalshi_chg = None
            signal = None
            
            if last_brti:
                brti_chg = ((brti - last_brti) / last_brti) * 100
            
            if last_kalshi_bid and last_kalshi_bid > 0:
                kalshi_chg = ((kalshi['yes_bid'] - last_kalshi_bid) / last_kalshi_bid) * 100
            
            # Detect arbitrage window
            if brti_chg is not None and kalshi_chg is not None:
                if abs(brti_chg) > 0.1 and abs(kalshi_chg) < 0.1:
                    signal = "WINDOW"
            
            result = {
                'timestamp': measurement_time.isoformat(),
                'brti_proxy': brti,
                'brti_change_pct': brti_chg,
                'kalshi': kalshi,
                'kalshi_change_pct': kalshi_chg,
                'signal': signal,
            }
            
            results.append(result)
            
            elapsed = int(time.time() - start_time)
            brti_str = f"{brti_chg:+.3f}%" if brti_chg else "N/A"
            kalshi_str = f"{kalshi_chg:+.2f}%" if kalshi_chg else "N/A"
            sig_str = f" [{signal}]" if signal else ""
            
            print(f"[{elapsed:4d}s] BRTI: ${brti:,.2f} ({brti_str}) | "
                  f"Kalshi: {kalshi['yes_bid']:.2f}/{kalshi['yes_ask']:.2f} ({kalshi_str}){sig_str}")
            
            last_brti = brti
            last_kalshi_bid = kalshi['yes_bid']
        
        time.sleep(interval_seconds)
    
    # Save
    os.makedirs('data', exist_ok=True)
    filename = f"data/continuous_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            'duration_minutes': duration_minutes,
            'measurements': results,
        }, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"COMPLETE: {len(results)} measurements")
    print(f"Saved: {filename}")
    
    windows = [r for r in results if r.get('signal')]
    if windows:
        print(f"\n⚡ WINDOWS: {len(windows)}")

if __name__ == "__main__":
    import sys
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    try:
        monitor_continuously(duration, interval)
    except KeyboardInterrupt:
        print("\n⚠️  Stopped")
