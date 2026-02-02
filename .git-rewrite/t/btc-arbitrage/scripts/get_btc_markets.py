#!/usr/bin/env python3
"""Get detailed info on Kalshi BTC price markets"""
import json
from urllib import request

# Key series we found
series_of_interest = [
    'KXBTC15M',   # 15min price prediction
    'KXETH15M',   # ETH 15min 
    'BTCD',       # BTC price above/below
    'KXBTC100',   # BTC hitting 100k
]

print("=" * 70)
print("KALSHI BTC PRICE MARKETS - DETAILED ANALYSIS")
print("=" * 70)

for series_ticker in series_of_interest:
    print(f"\n🔍 Fetching markets for {series_ticker}...")
    
    url = f"https://api.elections.kalshi.com/trade-api/v2/series/{series_ticker}"
    req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with request.urlopen(req, timeout=10) as response:
            series_data = json.loads(response.read())
        
        series_info = series_data.get('series', {})
        print(f"\n📊 {series_info.get('title', 'N/A')}")
        print(f"Category: {series_info.get('category', 'N/A')}")
        print(f"Frequency: {series_info.get('frequency', 'N/A')}")
        
        # Get markets in this series
        markets_url = f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={series_ticker}&status=open&limit=20"
        req2 = request.Request(markets_url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with request.urlopen(req2, timeout=10) as response:
            markets_data = json.loads(response.read())
        
        markets = markets_data.get('markets', [])
        print(f"Active markets: {len(markets)}\n")
        
        if markets:
            for m in markets[:5]:  # Show first 5
                ticker = m.get('ticker', 'N/A')
                title = m.get('title', 'N/A')
                yes_bid = m.get('yes_bid', 0)
                yes_ask = m.get('yes_ask', 0)
                volume = m.get('volume', 0)
                close_time = m.get('close_time', 'N/A')
                
                print(f"  {ticker}")
                print(f"    {title[:70]}")
                print(f"    YES: {yes_bid}¢ bid / {yes_ask}¢ ask")
                print(f"    Volume: ${volume:,}")
                print(f"    Closes: {close_time}")
                print()
            
            if len(markets) > 5:
                print(f"  ... and {len(markets) - 5} more markets\n")
        
    except Exception as e:
        print(f"  ❌ Error: {e}\n")

print("\n" + "=" * 70)
print("KEY FINDING:")
print("=" * 70)
print("✅ Kalshi has BTC/ETH 15-minute price markets")
print("✅ These are PERFECT for the arbitrage strategy")
print("\nNext: Measure delay between Binance and Kalshi price updates")
