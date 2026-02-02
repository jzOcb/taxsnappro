#!/bin/bash
# Search GitHub for prediction market trading repositories

echo "==================================================================="
echo "GITHUB SEARCH: Polymarket Trading Bots"
echo "==================================================================="
echo

# Search GitHub repositories
curl -s "https://api.github.com/search/repositories?q=polymarket+trading+bot&sort=stars&order=desc" | \
python3 << 'ENDPY'
import json, sys
data = json.load(sys.stdin)
repos = data.get('items', [])[:10]

for r in repos:
    print(f"⭐ {r['stargazers_count']:>4} | {r['full_name']}")
    print(f"       {r['description'] or 'No description'}")
    print(f"       {r['html_url']}")
    print()
ENDPY

echo
echo "==================================================================="
echo "GITHUB SEARCH: Kalshi Trading"
echo "==================================================================="
echo

curl -s "https://api.github.com/search/repositories?q=kalshi+trading&sort=stars&order=desc" | \
python3 << 'ENDPY'
import json, sys
data = json.load(sys.stdin)
repos = data.get('items', [])[:10]

for r in repos:
    print(f"⭐ {r['stargazers_count']:>4} | {r['full_name']}")
    print(f"       {r['description'] or 'No description'}")
    print(f"       {r['html_url']}")
    print()
ENDPY

echo
echo "==================================================================="
echo "GITHUB SEARCH: Prediction Market Arbitrage"
echo "==================================================================="
echo

curl -s "https://api.github.com/search/repositories?q=prediction+market+arbitrage&sort=stars&order=desc" | \
python3 << 'ENDPY'
import json, sys
data = json.load(sys.stdin)
repos = data.get('items', [])[:10]

for r in repos:
    print(f"⭐ {r['stargazers_count']:>4} | {r['full_name']}")
    print(f"       {r['description'] or 'No description'}")
    print(f"       {r['html_url']}")
    print()
ENDPY
