#!/usr/bin/env python3
"""
Track Kalshi KXBTC15M settlements and compare to our BRTI proxy
This validates if our proxy accurately predicts actual settlements
"""

import json
import time
import os
from datetime import datetime, timedelta
from urllib import request

def get_brti_proxy():
    """BRTI proxy calculation"""
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
    return sum(prices) / len(prices) if prices else None

def get_settled_markets():
    """Get recently settled KXBTC15M markets"""
    url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=200&series_ticker=KXBTC15M&status=closed"
    
    req = request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    
    try:
        with request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        return data.get('markets', [])
    except Exception as e:
        print(f"Error: {e}")
        return []

def track_settlements(check_interval_minutes=5):
    """
    Periodically check for new settlements
    Compare actual settlement to what our BRTI proxy was at close time
    """
    print(f"\n{'='*70}")
    print("KALSHI SETTLEMENT TRACKER")
    print(f"{'='*70}")
    print(f"Tracking KXBTC15M settlements vs BRTI proxy")
    print(f"Check interval: {check_interval_minutes} minutes\n")
    
    seen_markets = set()
    settlement_log = []
    
    while True:
        markets = get_settled_markets()
        
        for market in markets:
            ticker = market['ticker']
            
            # Skip if we've already logged this one
            if ticker in seen_markets:
                continue
            
            # Only process if it has a settlement result
            result = market.get('result')
            if not result:
                continue
            
            seen_markets.add(ticker)
            
            # Get settlement info
            close_time = market.get('close_time')
            settlement_result = result  # "yes" or "no"
            
            # Get our BRTI proxy NOW (after settlement)
            # In production, we'd want the BRTI at close_time
            current_brti = get_brti_proxy()
            
            settlement_record = {
                'timestamp': datetime.now().isoformat(),
                'ticker': ticker,
                'close_time': close_time,
                'settlement_result': settlement_result,
                'brti_proxy_at_check': current_brti,
                'volume': market.get('volume', 0),
            }
            
            settlement_log.append(settlement_record)
            
            print(f"\n🔔 NEW SETTLEMENT")
            print(f"  Market: {ticker}")
            print(f"  Close: {close_time}")
            print(f"  Result: {settlement_result.upper()}")
            print(f"  BRTI Proxy (now): ${current_brti:,.2f}" if current_brti else "  BRTI: N/A")
            print(f"  Volume: {market.get('volume', 0)}")
            
            # Save to file
            os.makedirs('data', exist_ok=True)
            with open('data/settlements.json', 'w') as f:
                json.dump(settlement_log, f, indent=2)
        
        # Wait before next check
        time.sleep(check_interval_minutes * 60)

if __name__ == "__main__":
    import sys
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    
    try:
        track_settlements(interval)
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped")
