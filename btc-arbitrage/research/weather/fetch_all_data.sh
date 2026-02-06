#!/bin/bash
# Fetch remaining Kalshi tickers
for ticker in KXHIGHPHIL KXHIGHTSEA KXHIGHTLV KXHIGHTNOLA KXHIGHTATL KXHIGHTMIN KXHIGHTPHX KXLOWTNYC KXLOWTDEN KXSNOWNYC KXRAINNYC; do
  echo "=== $ticker ==="
  curl -s "https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=${ticker}&status=open&limit=10" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    markets = data.get('markets', [])
    print(f'Found {len(markets)} markets')
    for m in markets:
        t = m.get('ticker','')
        title = m.get('title','')
        yes_bid = m.get('yes_bid',0)
        yes_ask = m.get('yes_ask',0)
        vol = m.get('volume',0)
        rules = m.get('rules_primary','')[:200]
        print(f'  {t}: bid={yes_bid}¢ ask={yes_ask}¢ vol={vol} | {title}')
        if 'rules_primary' in m:
            # extract weather station
            import re
            station = re.search(r'recorded (?:at|in) (.+?) for', rules)
            if station:
                print(f'    Station: {station.group(1)}')
except Exception as e:
    print(f'Error: {e}')
" 2>/dev/null
  sleep 1
done
