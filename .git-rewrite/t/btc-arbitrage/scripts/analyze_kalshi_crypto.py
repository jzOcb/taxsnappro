#!/usr/bin/env python3
"""Analyze Kalshi crypto markets in detail"""
import json
from urllib import request

url = "https://api.elections.kalshi.com/trade-api/v2/series"
req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

with request.urlopen(req, timeout=10) as response:
    data = json.loads(response.read())

series = data.get('series', [])
keywords = ['btc', 'bitcoin', 'crypto', 'eth', 'ethereum']
crypto_series = [s for s in series if any(kw in s.get('title','').lower() for kw in keywords)]

print(f"Found {len(crypto_series)} crypto series on Kalshi:\n")

# Group by category
from collections import defaultdict
by_category = defaultdict(list)
for s in crypto_series:
    by_category[s.get('category', 'Unknown')].append(s)

for cat, items in sorted(by_category.items()):
    print(f"\n📂 {cat} ({len(items)} series)")
    for s in items[:5]:  # Show first 5 of each category
        print(f"   • {s.get('ticker')}: {s.get('title')[:80]}")
    if len(items) > 5:
        print(f"   ... and {len(items)-5} more")

# Check for price-based markets
print("\n" + "="*60)
print("Looking for PRICE-based markets:")
print("="*60)

price_keywords = ['price', 'reach', 'above', 'below', '$', 'value']
price_series = [s for s in crypto_series if any(kw in s.get('title','').lower() for kw in price_keywords)]

if price_series:
    print(f"\nFound {len(price_series)} potential price markets:\n")
    for s in price_series[:10]:
        print(f"📊 {s.get('ticker')}: {s.get('title')}")
else:
    print("\n❌ No price-based markets found")
    print("   Kalshi crypto markets may be event-based only")
