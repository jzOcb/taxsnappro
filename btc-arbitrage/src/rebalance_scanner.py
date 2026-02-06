#!/usr/bin/env python3
"""
Kalshi Market Rebalancing Arbitrage Scanner
============================================

Scans Kalshi BTC markets for rebalancing opportunities where YES + NO prices
don't sum to $1.00. When YES + NO < $1.00, buying both guarantees profit at settlement.

Market series focused on:
- KXBTC15M (15-minute BTC price windows)
- KXBTC1H (1-hour BTC price windows)

Author: Claude Code (OpenClaw subagent)
Created: 2026-02-04
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib import request
from typing import List, Dict, Optional, Tuple

# Add kalshi module to path for existing API helpers
sys.path.insert(0, '/home/clawdbot/clawd/kalshi')
try:
    from kalshi import api_get
    HAS_KALSHI_MODULE = True
except ImportError:
    HAS_KALSHI_MODULE = False
    print("⚠️ kalshi module not available, using direct API calls")

# API Configuration
API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
BTC_SERIES = ["KXBTC15M", "KXBTC1H"]

# Trading Parameters 
KALSHI_FEE_RATE = 0.00  # Kalshi fee rate (TODO: verify actual fee structure)
MIN_ARBITRAGE_PROFIT = 0.005  # Minimum $0.005 (0.5¢) profit to be interesting
MIN_ORDER_SIZE = 1  # Minimum order size
MAX_ORDER_SIZE = 100  # Maximum order size for slippage estimation

def api_get_fallback(endpoint: str, params: dict = None) -> Optional[dict]:
    """Fallback API request function if kalshi module not available"""
    try:
        url = f"{API_BASE}{endpoint}"
        if params:
            from urllib.parse import urlencode
            url += "?" + urlencode(params)
        
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (rebalance-scanner)')
        req.add_header('Accept', 'application/json')
        
        with request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        return data
    except Exception as e:
        print(f"⚠️ API error on {endpoint}: {e}")
        return None

def make_api_call(endpoint: str, params: dict = None) -> Optional[dict]:
    """Make API call using available method"""
    if HAS_KALSHI_MODULE:
        return api_get(endpoint, params)
    else:
        return api_get_fallback(endpoint, params)

def fetch_active_markets(series_ticker: str) -> List[Dict]:
    """Fetch all active markets for a given series"""
    print(f"📡 Fetching active markets for {series_ticker}...")
    
    data = make_api_call("/markets", {
        "series_ticker": series_ticker,
        "status": "open",
        "limit": 20  # Get more than just the first one
    })
    
    if not data or "markets" not in data:
        print(f"❌ No data returned for {series_ticker}")
        return []
    
    markets = data["markets"]
    print(f"✅ Found {len(markets)} active markets for {series_ticker}")
    return markets

def fetch_orderbook(ticker: str) -> Optional[Dict]:
    """Fetch orderbook for a specific market ticker"""
    data = make_api_call(f"/markets/{ticker}/orderbook")
    
    if not data or "orderbook" not in data:
        print(f"⚠️ No orderbook data for {ticker}")
        return None
    
    return data["orderbook"]

def calculate_rebalance_opportunity(market: Dict, orderbook: Dict = None) -> Dict:
    """
    Calculate rebalancing arbitrage opportunity for a market.
    
    Returns dict with:
    - ticker: market ticker
    - opportunity_type: 'buy_both', 'sell_both', or 'none'
    - yes_price: YES price used in calculation
    - no_price: NO price used in calculation  
    - total_cost: cost to execute strategy
    - max_profit: maximum profit possible
    - profit_margin: profit margin percentage
    - details: human-readable explanation
    """
    ticker = market.get("ticker", "UNKNOWN")
    
    # Get prices from market data (these are the displayed best bid/ask)
    yes_bid = market.get("yes_bid", 0) / 100.0  # Convert cents to dollars
    yes_ask = market.get("yes_ask", 0) / 100.0
    no_bid = market.get("no_bid", 0) / 100.0
    no_ask = market.get("no_ask", 0) / 100.0
    
    # Calculate NO prices from YES prices (NO = 1 - YES)
    if no_bid == 0 and yes_ask > 0:
        no_bid = 1.0 - yes_ask
    if no_ask == 0 and yes_bid > 0:
        no_ask = 1.0 - yes_bid
    
    # Strategy 1: Buy both YES and NO (when sum < $1.00)
    # Cost to buy both = YES ask + NO ask
    cost_buy_both = yes_ask + no_ask
    buy_both_profit = 1.0 - cost_buy_both - (KALSHI_FEE_RATE * 2)  # 2 transactions
    
    # Strategy 2: Sell both YES and NO (when sum > $1.00)  
    # Revenue from selling both = YES bid + NO bid
    revenue_sell_both = yes_bid + no_bid
    sell_both_profit = revenue_sell_both - 1.0 - (KALSHI_FEE_RATE * 2)
    
    # Determine best opportunity
    result = {
        "ticker": ticker,
        "series": market.get("series_ticker", ""),
        "yes_bid": yes_bid,
        "yes_ask": yes_ask,
        "no_bid": no_bid,
        "no_ask": no_ask,
        "opportunity_type": "none",
        "total_cost": 0,
        "max_profit": 0,
        "profit_margin": 0,
        "details": "",
        "volume": market.get("volume", 0),
        "close_time": market.get("close_time", ""),
    }
    
    if buy_both_profit > MIN_ARBITRAGE_PROFIT:
        result.update({
            "opportunity_type": "buy_both",
            "total_cost": cost_buy_both,
            "max_profit": buy_both_profit,
            "profit_margin": (buy_both_profit / cost_buy_both) * 100,
            "details": f"Buy YES@${yes_ask:.3f} + NO@${no_ask:.3f} = ${cost_buy_both:.3f} < $1.00. Profit: ${buy_both_profit:.3f}"
        })
    elif sell_both_profit > MIN_ARBITRAGE_PROFIT:
        result.update({
            "opportunity_type": "sell_both", 
            "total_cost": 1.0,  # You're selling $1.00 worth
            "max_profit": sell_both_profit,
            "profit_margin": sell_both_profit * 100,  # Profit margin on $1 base
            "details": f"Sell YES@${yes_bid:.3f} + NO@${no_bid:.3f} = ${revenue_sell_both:.3f} > $1.00. Profit: ${sell_both_profit:.3f}"
        })
    else:
        # No arbitrage opportunity
        closest_to_dollar = abs(1.0 - cost_buy_both)
        result["details"] = f"No arbitrage: YES@${yes_ask:.3f} + NO@${no_ask:.3f} = ${cost_buy_both:.3f} (${closest_to_dollar:.3f} from $1.00)"
    
    return result

def scan_all_btc_markets() -> Tuple[List[Dict], List[Dict]]:
    """
    Scan all active BTC markets for rebalancing opportunities.
    
    Returns:
    - opportunities: List of profitable arbitrage opportunities
    - all_results: List of all market scan results
    """
    print(f"\n🔍 KALSHI BTC REBALANCING ARBITRAGE SCANNER")
    print(f"📅 Scan Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🎯 Target Series: {', '.join(BTC_SERIES)}")
    print(f"💰 Min Profit Threshold: ${MIN_ARBITRAGE_PROFIT:.3f}")
    print("=" * 70)
    
    opportunities = []
    all_results = []
    
    for series in BTC_SERIES:
        print(f"\n📊 Scanning {series} markets...")
        
        # Fetch all active markets for this series
        markets = fetch_active_markets(series)
        
        if not markets:
            print(f"   ⚠️ No active markets found for {series}")
            continue
        
        for market in markets:
            ticker = market.get("ticker", "UNKNOWN")
            print(f"   🎲 Analyzing {ticker}...")
            
            # Calculate opportunity
            result = calculate_rebalance_opportunity(market)
            all_results.append(result)
            
            # Check if this is a profitable opportunity
            if result["opportunity_type"] != "none":
                opportunities.append(result)
                print(f"   💡 OPPORTUNITY FOUND: {result['details']}")
            else:
                print(f"   ✅ {result['details']}")
    
    return opportunities, all_results

def print_summary(opportunities: List[Dict], all_results: List[Dict]):
    """Print detailed summary of scan results"""
    print("\n" + "=" * 70)
    print("📋 SCAN SUMMARY")
    print("=" * 70)
    
    print(f"🎲 Total Markets Scanned: {len(all_results)}")
    print(f"💡 Arbitrage Opportunities Found: {len(opportunities)}")
    
    if opportunities:
        print(f"\n🚨 LIVE ARBITRAGE OPPORTUNITIES:")
        print("-" * 50)
        
        for i, opp in enumerate(opportunities, 1):
            print(f"\n{i}. {opp['ticker']} ({opp['series']})")
            print(f"   Strategy: {opp['opportunity_type'].replace('_', ' ').title()}")
            print(f"   {opp['details']}")
            print(f"   Profit Margin: {opp['profit_margin']:.2f}%")
            print(f"   Volume: {opp['volume']:,}")
            
            # Time until close
            try:
                close_time = datetime.fromisoformat(opp['close_time'].replace('Z', '+00:00'))
                time_remaining = close_time - datetime.now(timezone.utc)
                hours, remainder = divmod(int(time_remaining.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                print(f"   Time to Close: {hours:02d}:{minutes:02d}:{seconds:02d}")
            except:
                print(f"   Close Time: {opp['close_time']}")
                
        # Calculate total potential profit
        total_profit = sum(opp['max_profit'] for opp in opportunities)
        print(f"\n💰 Total Potential Profit: ${total_profit:.3f}")
        
    else:
        print(f"\n✅ No arbitrage opportunities currently available.")
        print(f"   All BTC markets are efficiently priced (YES + NO ≈ $1.00)")
        
        # Show how close markets are to arbitrage
        print(f"\n📊 Market Efficiency Analysis:")
        for result in all_results:
            yes_ask = result['yes_ask']
            no_ask = result['no_ask'] 
            sum_price = yes_ask + no_ask
            deviation = abs(1.0 - sum_price)
            print(f"   {result['ticker']}: YES+NO = ${sum_price:.3f} (${deviation:.3f} from $1.00)")

def save_results(opportunities: List[Dict], all_results: List[Dict]):
    """Save scan results to JSON file"""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filename = f"/home/clawdbot/clawd/btc-arbitrage/data/rebalance_scan_{timestamp}.json"
    
    results = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "series_scanned": BTC_SERIES,
        "total_markets": len(all_results),
        "opportunities_found": len(opportunities),
        "min_profit_threshold": MIN_ARBITRAGE_PROFIT,
        "fee_rate": KALSHI_FEE_RATE,
        "opportunities": opportunities,
        "all_results": all_results
    }
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {filename}")

def main():
    """Main scanner function"""
    try:
        # Run the scan
        opportunities, all_results = scan_all_btc_markets()
        
        # Print summary  
        print_summary(opportunities, all_results)
        
        # Save results
        save_results(opportunities, all_results)
        
        # Exit codes for automation
        if opportunities:
            print(f"\n🎯 ARBITRAGE DETECTED! {len(opportunities)} opportunities found.")
            return 0  # Success with opportunities
        else:
            print(f"\n🔍 Scan complete. No arbitrage opportunities currently available.")
            return 1  # Success but no opportunities
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Scan interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())