#!/usr/bin/env python3
"""
CF Benchmarks BRTI Proxy
Aggregates BTC prices from multiple exchanges to simulate BRTI

BRTI (Bitcoin Real-Time Index) is used by Kalshi for settlement.
We don't have access to the real BRTI, so we build a proxy using public APIs.
"""

import json
from urllib import request
from datetime import datetime

# Exchange APIs (all free, no auth required)
EXCHANGES = {
    'binance_us': 'https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT',
    'coinbase': 'https://api.coinbase.com/v2/prices/BTC-USD/spot',
    'kraken': 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD',
}

# Weights (estimate - real BRTI methodology is proprietary)
# Using volume-based weighting as approximation
WEIGHTS = {
    'binance_us': 0.33,
    'coinbase': 0.33,
    'kraken': 0.34,
}

def get_price(exchange, url):
    """Fetch BTC price from an exchange"""
    req = request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    
    try:
        with request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
        
        # Parse response based on exchange
        if exchange == 'binance_us':
            return float(data['price'])
        elif exchange == 'coinbase':
            return float(data['data']['amount'])
        elif exchange == 'kraken':
            # Kraken returns nested dict
            pair_data = data['result']['XXBTZUSD']
            # Use 'c' (last trade price)
            return float(pair_data['c'][0])
            
    except Exception as e:
        print(f"❌ Error fetching {exchange}: {e}")
        return None

def calculate_brti_proxy():
    """Calculate BRTI proxy as weighted average of exchange prices"""
    prices = {}
    
    print("Fetching BTC prices from exchanges...")
    for exchange, url in EXCHANGES.items():
        price = get_price(exchange, url)
        if price:
            prices[exchange] = price
            print(f"  {exchange:12s}: ${price:,.2f}")
    
    if len(prices) == 0:
        print("❌ Failed to fetch any prices")
        return None
    
    # Calculate weighted average
    total_weight = sum(WEIGHTS[ex] for ex in prices.keys())
    weighted_sum = sum(prices[ex] * WEIGHTS[ex] for ex in prices.keys())
    proxy_price = weighted_sum / total_weight
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'prices': prices,
        'weights': {ex: WEIGHTS[ex] for ex in prices.keys()},
        'proxy_brti': proxy_price,
    }
    
    print(f"\n✅ BRTI Proxy: ${proxy_price:,.2f}")
    print(f"Timestamp: {result['timestamp']}")
    
    # Calculate spread (max - min)
    if prices:
        price_values = list(prices.values())
        spread = max(price_values) - min(price_values)
        spread_pct = (spread / proxy_price) * 100
        print(f"Exchange spread: ${spread:.2f} ({spread_pct:.3f}%)")
    
    return result

if __name__ == "__main__":
    result = calculate_brti_proxy()
    
    if result:
        # Optionally save to file
        filename = f"data/brti_proxy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import os
        os.makedirs('data', exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\nSaved to: {filename}")
