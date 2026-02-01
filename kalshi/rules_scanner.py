#!/usr/bin/env python3
"""Kalshi Contract Rules Scanner — Extract settlement rules and find edge cases."""
import sys, os, json, time, re
sys.path.insert(0, '/tmp/pip_packages')
import requests

API = "https://api.elections.kalshi.com/trade-api/v2"
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache', 'rules')

# Key series where rules interpretation gives edge
KEY_SERIES = [
    'KXGOVSHUTLENGTH', 'KXTRUMPMEETING', 'KXGDP', 'KXCPI',
    'KXGREENLAND', 'KXFED', 'KXSCOTUS', 'KXRECESSION',
    'KXGOVTCUTS', 'KXDOGE', 'KXTARIFF',
]


def fetch_market_details(ticker):
    """Fetch full market details including rules URL."""
    try:
        r = requests.get(f'{API}/markets/{ticker}', timeout=10)
        if r.status_code == 200:
            return r.json().get('market', {})
    except:
        pass
    return {}


def fetch_markets_for_series(series_ticker):
    """Fetch active markets for a series."""
    try:
        r = requests.get(f'{API}/markets', params={
            'limit': 20, 'series_ticker': series_ticker
        }, timeout=10)
        return r.json().get('markets', [])
    except:
        return []


def extract_rules_from_market(market):
    """Extract settlement rules and key definitions from market data."""
    rules = {
        'ticker': market.get('ticker', ''),
        'title': market.get('title', ''),
        'category': market.get('category', ''),
        'close_time': market.get('close_time', ''),
        'expiration_time': market.get('expiration_time', ''),
        'settlement_timer_seconds': market.get('settlement_timer_seconds'),
        'rules_primary': market.get('rules_primary', ''),
        'rules_secondary': market.get('rules_secondary', ''),
        'resolution_source': market.get('resolution_source', ''),
        'settlement_source_url': market.get('settlement_source_url', ''),
        'strike_type': market.get('strike_type', ''),
        'floor_strike': market.get('floor_strike'),
        'cap_strike': market.get('cap_strike'),
        'expected_expiration_time': market.get('expected_expiration_time', ''),
    }
    
    # Analyze for gotchas
    gotchas = []
    primary = (rules['rules_primary'] or '').lower()
    secondary = (rules['rules_secondary'] or '').lower()
    all_rules = primary + ' ' + secondary
    
    # Check for broad definitions
    if 'includ' in all_rules:
        includes = re.findall(r'(?:includes?|including)\s+([^.;]+)', all_rules)
        if includes:
            gotchas.append(f"Broad definition: includes {includes[0][:100]}")
    
    # Check for phone/virtual counting as meeting
    if 'phone' in all_rules or 'virtual' in all_rules or 'call' in all_rules:
        gotchas.append("Phone/virtual may count!")
    
    # Check for specific data sources
    if 'bea' in all_rules or 'bls' in all_rules or 'bureau' in all_rules:
        gotchas.append(f"Official data source specified")
    
    # Check for revision clauses
    if 'revis' in all_rules or 'preliminary' in all_rules or 'advance' in all_rules:
        gotchas.append("Uses preliminary/advance estimate (may be revised)")
    
    # Check for time zone specifics
    if 'eastern' in all_rules or 'et ' in all_rules or 'est' in all_rules:
        gotchas.append("Eastern Time zone specified")
    
    # Check for ambiguous language
    if 'sole discretion' in all_rules:
        gotchas.append("Kalshi has sole discretion on resolution")
    
    if 'reasonabl' in all_rules:
        gotchas.append("Contains 'reasonable' — subjective term")
    
    rules['gotchas'] = gotchas
    return rules


def scan_series(series_ticker):
    """Scan a series and extract rules for all markets."""
    markets = fetch_markets_for_series(series_ticker)
    results = []
    
    for m in markets[:5]:  # Limit to 5 per series to avoid rate limits
        ticker = m.get('ticker', '')
        # Always fetch full details for rules
        details = fetch_market_details(ticker)
        if details:
            rules = extract_rules_from_market(details)
        else:
            rules = extract_rules_from_market(m)
        
        if rules['rules_primary'] or rules['gotchas']:
            results.append(rules)
        time.sleep(0.15)  # Be gentle with API
    
    return results


def save_rules(series_ticker, rules_list):
    """Save rules to cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f'{series_ticker}.json')
    try:
        with open(path, 'w') as f:
            json.dump(rules_list, f, indent=2)
    except:
        pass


def main():
    import datetime
    now = datetime.datetime.utcnow().strftime('%m/%d %H:%M UTC')
    print(f"📜 Kalshi Rules Scanner — {now}")
    print()
    
    all_gotchas = []
    
    for series in KEY_SERIES:
        print(f"Scanning {series}...")
        results = scan_series(series)
        
        if results:
            save_rules(series, results)
            
            # Show gotchas
            for r in results:
                if r['gotchas']:
                    all_gotchas.append(r)
                    
            # Show first market's rules as sample
            sample = results[0]
            if sample['rules_primary']:
                print(f"  Rules: {sample['rules_primary'][:120]}...")
            print(f"  Markets: {len(results)} | Gotchas found: {sum(1 for r in results if r['gotchas'])}")
        else:
            print(f"  No markets or rules found")
        print()
        time.sleep(0.1)
    
    # Summary of gotchas
    if all_gotchas:
        print(f"\n{'='*60}")
        print(f"⚠️  GOTCHAS — Rules That Could Surprise You")
        print(f"{'='*60}\n")
        
        for r in all_gotchas:
            yes = '?'  # We don't have price here, just rules
            print(f"📌 {r['ticker']}")
            print(f"   {r['title'][:70]}")
            for g in r['gotchas']:
                print(f"   ⚠️  {g}")
            print()
    
    print(f"📊 Scanned {len(KEY_SERIES)} series, found {len(all_gotchas)} markets with gotchas")
    print(f"   Rules cached to {CACHE_DIR}/")


if __name__ == '__main__':
    main()
