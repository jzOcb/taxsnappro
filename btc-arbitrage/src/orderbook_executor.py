#!/usr/bin/env python3
"""
Orderbook-aware execution simulator for Kalshi paper trading.
Shared by v6/v7/v8 — replaces naive best-bid/ask with real depth-based VWAP.
"""

import json
import time
from urllib import request

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
_last_call = 0
_MIN_INTERVAL = 0.5  # Rate limit: max 2 calls/sec


def fetch_orderbook(ticker):
    """Fetch full orderbook for a ticker. Returns dict with yes/no depth."""
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    
    url = f"{API_BASE}/markets/{ticker}/orderbook"
    req = request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    try:
        _last_call = time.time()
        with request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read())
        ob = data.get('orderbook', {})
        return {
            'yes': ob.get('yes') or [],   # [[price_cents, qty], ...]
            'no': ob.get('no') or [],
            'time': time.time(),
            'ticker': ticker
        }
    except Exception as e:
        return {'yes': [], 'no': [], 'time': time.time(), 'ticker': ticker, 'error': str(e)}


def simulate_fill(orderbook_side, qty, side='buy'):
    """
    Simulate filling `qty` contracts against orderbook depth.
    
    For buying: orderbook_side should be the ASK side (sorted low to high).
    For selling: orderbook_side should be the BID side (sorted high to low).
    
    Returns:
        {
            'vwap': float,          # Volume-weighted average price (in dollars)
            'filled': int,          # Contracts actually filled
            'total_cost': float,    # Total cost in dollars
            'slippage': float,      # VWAP - best_price (dollars)
            'best_price': float,    # Best available price
            'levels_consumed': int, # How many price levels were hit
            'partial': bool,        # True if couldn't fill full qty
            'fills': list           # Detail: [{price, qty}]
        }
    """
    if not orderbook_side or qty <= 0:
        return {
            'vwap': 0, 'filled': 0, 'total_cost': 0, 'slippage': 0,
            'best_price': 0, 'levels_consumed': 0, 'partial': True, 'fills': []
        }
    
    # Sort: for buying, ascending (cheapest first); for selling, descending (highest first)
    sorted_levels = sorted(orderbook_side, key=lambda x: x[0], reverse=(side == 'sell'))
    
    remaining = qty
    total_cost = 0
    fills = []
    levels = 0
    best_price = sorted_levels[0][0] / 100.0  # Convert cents to dollars
    
    for price_cents, available in sorted_levels:
        if remaining <= 0:
            break
        levels += 1
        take = min(remaining, available)
        price_dollars = price_cents / 100.0
        total_cost += take * price_dollars
        fills.append({'price': price_dollars, 'qty': take})
        remaining -= take
    
    filled = qty - remaining
    vwap = total_cost / filled if filled > 0 else 0
    
    return {
        'vwap': vwap,
        'filled': filled,
        'total_cost': total_cost,
        'slippage': abs(vwap - best_price),
        'best_price': best_price,
        'levels_consumed': levels,
        'partial': remaining > 0,
        'fills': fills
    }


def get_real_entry_price(ticker, direction, qty):
    """
    Get real entry price considering orderbook depth.
    
    direction: 'YES' or 'NO'
    qty: number of contracts
    
    Returns: (actual_price, fill_info) or (None, None) if can't fill
    """
    ob = fetch_orderbook(ticker)
    if ob.get('error'):
        return None, {'error': ob['error']}
    
    if direction == 'YES':
        # Buying YES = taking from YES ask side
        # YES asks are people selling YES contracts
        # In Kalshi orderbook, 'yes' array = YES bids (people wanting to buy YES)
        # To BUY YES, you need to match against NO bids (which = YES asks)
        # Actually: 'yes' = resting YES orders, 'no' = resting NO orders
        # To buy YES at market: you take from the NO side (their NO bid = your YES ask)
        # NO bid at price X cents means they'll sell YES at (100-X) cents
        
        # Simpler: to buy YES, the ask prices come from NO orders
        # NO order at 20¢ = YES available at 80¢
        no_side = ob.get('no', [])
        if not no_side:
            return None, {'error': 'no depth on NO side'}
        
        # Convert NO bids to YES asks: YES ask = (100 - NO bid price)
        yes_asks = [[100 - price_c, qty_] for price_c, qty_ in no_side]
        # Sort ascending for buying (cheapest YES first = highest NO first)
        fill = simulate_fill(sorted(yes_asks, key=lambda x: x[0]), qty, side='buy')
        
    else:  # NO
        # Buying NO = taking from YES side (their YES bid = your NO ask)
        # YES bid at 80¢ means NO available at 20¢
        yes_side = ob.get('yes', [])
        if not yes_side:
            return None, {'error': 'no depth on YES side'}
        
        # Convert YES bids to NO asks: NO ask = (100 - YES bid price)  
        no_asks = [[100 - price_c, qty_] for price_c, qty_ in yes_side]
        fill = simulate_fill(sorted(no_asks, key=lambda x: x[0]), qty, side='buy')
    
    if fill['filled'] == 0:
        return None, fill
    
    return fill['vwap'], fill


def get_real_exit_price(ticker, direction, qty):
    """
    Get real exit price considering orderbook depth.
    
    direction: 'YES' or 'NO' (the position we're closing)
    qty: number of contracts to sell
    
    Returns: (actual_price, fill_info) or (None, None) if can't fill
    """
    ob = fetch_orderbook(ticker)
    if ob.get('error'):
        return None, {'error': ob['error']}
    
    if direction == 'YES':
        # Selling YES = hitting YES bids
        yes_side = ob.get('yes', [])
        if not yes_side:
            return None, {'error': 'no depth on YES side'}
        fill = simulate_fill(yes_side, qty, side='sell')
        
    else:  # NO
        # Selling NO = hitting NO bids
        no_side = ob.get('no', [])
        if not no_side:
            return None, {'error': 'no depth on NO side'}
        # NO bids: selling NO at these prices
        # But we need to convert: NO bid at X¢ means we get X¢ per NO contract
        fill = simulate_fill(no_side, qty, side='sell')
    
    if fill['filled'] == 0:
        return None, fill
    
    return fill['vwap'], fill
