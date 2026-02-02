#!/usr/bin/env python3
"""Search for BTC/crypto markets on Polymarket and Kalshi"""
import json
from urllib import request

def search_polymarket():
    print("🔍 Searching Polymarket for BTC markets...\n")
    url = "https://gamma-api.polymarket.com/events?limit=100&closed=false"
    req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with request.urlopen(req, timeout=10) as response:
            events = json.loads(response.read())
        
        keywords = ['btc', 'bitcoin', 'crypto', 'eth', 'ethereum']
        btc_events = [e for e in events if any(kw in e.get('title','').lower() for kw in keywords)]
        
        print(f"Found {len(btc_events)} crypto-related events:\n")
        
        for e in btc_events:
            print(f"📊 {e.get('title', 'N/A')}")
            print(f"   Volume: ${e.get('volume', 0):,.0f}")
            markets = e.get('markets', [])
            if markets:
                for m in markets[:3]:
                    print(f"   • {m.get('outcome', 'N/A')}: {m.get('lastPrice', 'N/A')}")
            print()
        
        return btc_events
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def search_kalshi():
    print("\n🔍 Searching Kalshi for crypto markets...\n")
    url = "https://api.elections.kalshi.com/trade-api/v2/series"
    req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        
        series = data.get('series', [])
        keywords = ['btc', 'bitcoin', 'crypto', 'eth', 'ethereum']
        crypto_series = [s for s in series if any(kw in s.get('title','').lower() for kw in keywords)]
        
        print(f"Found {len(crypto_series)} crypto-related series")
        if not crypto_series:
            print("❌ No crypto markets on Kalshi\n")
        
        return crypto_series
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    print("=" * 60)
    print("BTC Arbitrage Bot - Market Research")
    print("=" * 60 + "\n")
    
    poly_events = search_polymarket()
    kalshi_series = search_kalshi()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Polymarket: {len(poly_events)} BTC events")
    print(f"Kalshi: {len(kalshi_series)} crypto series")
    
    if poly_events:
        print("\n✅ Polymarket has BTC markets - proceed with strategy")
    if not kalshi_series:
        print("❌ Kalshi has no crypto - focus Polymarket only")
