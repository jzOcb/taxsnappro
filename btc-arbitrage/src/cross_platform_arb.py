#!/usr/bin/env python3
"""
Cross-Platform Arbitrage Scanner: Kalshi vs Polymarket BTC Markets
Version 1.0 - Built Feb 4, 2026

CRITICAL FINDING: As of Feb 2026, Polymarket does not have equivalent 
BTC 15-minute and 1-hour markets to match Kalshi's KXBTC15M and KXBTC1H.

This scanner is built to:
1. Monitor both platforms for BTC markets
2. Detect arbitrage opportunities when comparable markets exist
3. Paper trade arbitrage strategies
4. Alert when profitable opportunities arise

Usage:
  python3 src/cross_platform_arb.py --scan-once     # Single scan
  python3 src/cross_platform_arb.py --continuous    # Continuous monitoring
"""

import asyncio
import json
import time
import sys
import os
import argparse
import traceback
from datetime import datetime
from urllib import request, parse
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

@dataclass
class Market:
    """Represents a prediction market"""
    platform: str
    ticker: str
    question: str
    yes_price: float
    no_price: float
    yes_bid: float = 0.0
    yes_ask: float = 0.0
    no_bid: float = 0.0
    no_ask: float = 0.0
    volume: float = 0.0
    strike_price: Optional[float] = None
    end_time: Optional[str] = None
    market_type: str = "binary"  # binary, 15min, 1hour
    active: bool = True

@dataclass
class ArbitrageOpportunity:
    """Represents a detected arbitrage opportunity"""
    kalshi_market: Market
    polymarket_market: Market
    strategy: str  # "strike_diff", "price_diff"
    estimated_profit: float
    total_cost: float
    confidence: float
    timestamp: float

class PlatformFetcher:
    """Base class for platform data fetchers"""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.last_fetch_time = 0
        self.rate_limit_delay = 5  # seconds between requests
    
    def _should_fetch(self) -> bool:
        """Check if enough time has passed since last fetch"""
        return time.time() - self.last_fetch_time >= self.rate_limit_delay
    
    def _mark_fetch_time(self):
        """Mark the time of successful fetch"""
        self.last_fetch_time = time.time()

class KalshiFetcher(PlatformFetcher):
    """Fetches BTC markets from Kalshi"""
    
    def __init__(self):
        super().__init__("Kalshi")
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
    
    def fetch_btc_markets(self) -> List[Market]:
        """Fetch active BTC markets from Kalshi"""
        if not self._should_fetch():
            return []
        
        markets = []
        
        # Fetch 15-minute markets
        markets.extend(self._fetch_series("KXBTC15M", "15min"))
        
        # Fetch 1-hour markets  
        markets.extend(self._fetch_series("KXBTC1H", "1hour"))
        
        self._mark_fetch_time()
        return markets
    
    def _fetch_series(self, series_ticker: str, market_type: str) -> List[Market]:
        """Fetch markets for a specific series"""
        try:
            url = f"{self.base_url}/markets?series_ticker={series_ticker}&status=open&limit=10"
            
            req = request.Request(url)
            req.add_header('User-Agent', 'CrossPlatformArbitrage/1.0')
            req.add_header('Accept', 'application/json')
            
            with request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
            
            markets = []
            for market_data in data.get('markets', []):
                # Extract strike price from ticker (e.g., KXBTC15M-24FEB04-89500)
                ticker = market_data.get('ticker', '')
                strike_price = self._extract_strike_price(ticker)
                
                market = Market(
                    platform="Kalshi",
                    ticker=ticker,
                    question=market_data.get('title', ''),
                    yes_price=market_data.get('yes_bid', 0) / 100.0,
                    no_price=1 - (market_data.get('yes_bid', 0) / 100.0),
                    yes_bid=market_data.get('yes_bid', 0) / 100.0,
                    yes_ask=market_data.get('yes_ask', 0) / 100.0,
                    no_bid=1 - (market_data.get('yes_ask', 0) / 100.0),
                    no_ask=1 - (market_data.get('yes_bid', 0) / 100.0),
                    volume=market_data.get('volume', 0),
                    strike_price=strike_price,
                    end_time=market_data.get('close_time'),
                    market_type=market_type,
                    active=True
                )
                markets.append(market)
            
            return markets
            
        except Exception as e:
            print(f"Error fetching Kalshi {market_type} markets: {e}")
            return []
    
    def _extract_strike_price(self, ticker: str) -> Optional[float]:
        """Extract strike price from Kalshi ticker"""
        try:
            # Format: KXBTC15M-24FEB04-89500
            parts = ticker.split('-')
            if len(parts) >= 3:
                price_str = parts[-1]
                return float(price_str)
        except:
            pass
        return None

class PolymarketFetcher(PlatformFetcher):
    """Fetches BTC markets from Polymarket"""
    
    def __init__(self):
        super().__init__("Polymarket")
        self.gamma_api_url = "https://gamma-api.polymarket.com/markets"
        self.clob_api_url = "https://clob.polymarket.com"
    
    def fetch_btc_markets(self) -> List[Market]:
        """Fetch active BTC markets from Polymarket"""
        if not self._should_fetch():
            return []
        
        markets = []
        
        # Search for Bitcoin markets
        markets.extend(self._search_btc_markets())
        
        self._mark_fetch_time()
        return markets
    
    def _search_btc_markets(self) -> List[Market]:
        """Search for Bitcoin-related markets"""
        try:
            # Search for active, non-archived markets
            url = f"{self.gamma_api_url}?limit=200&closed=false&archived=false&order_by=-volume"
            
            req = request.Request(url)
            req.add_header('User-Agent', 'CrossPlatformArbitrage/1.0')
            req.add_header('Accept', 'application/json')
            
            with request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
            
            markets = []
            
            # Filter for Bitcoin-related markets
            for market_data in data:
                question = market_data.get('question', '').lower()
                
                # Look for Bitcoin keywords and short-term timeframes
                if any(keyword in question for keyword in ['bitcoin', 'btc']) and \
                   any(timeframe in question for timeframe in ['minute', 'hour', 'day', 'week']):
                    
                    # Parse outcome prices
                    outcome_prices = json.loads(market_data.get('outcomePrices', '["0", "0"]'))
                    outcomes = json.loads(market_data.get('outcomes', '["Yes", "No"]'))
                    
                    yes_price = float(outcome_prices[0]) if len(outcome_prices) > 0 else 0
                    no_price = float(outcome_prices[1]) if len(outcome_prices) > 1 else 0
                    
                    # Extract strike price if possible
                    strike_price = self._extract_strike_price(question)
                    
                    market = Market(
                        platform="Polymarket",
                        ticker=market_data.get('slug', ''),
                        question=market_data.get('question', ''),
                        yes_price=yes_price,
                        no_price=no_price,
                        yes_bid=yes_price * 0.99,  # Estimate bid/ask spread
                        yes_ask=yes_price * 1.01,
                        no_bid=no_price * 0.99,
                        no_ask=no_price * 1.01,
                        volume=float(market_data.get('volume', 0)),
                        strike_price=strike_price,
                        end_time=market_data.get('endDate'),
                        market_type=self._classify_market_type(question),
                        active=market_data.get('active', False) and not market_data.get('closed', True)
                    )
                    
                    if market.active:
                        markets.append(market)
            
            return markets
            
        except Exception as e:
            print(f"Error searching Polymarket BTC markets: {e}")
            return []
    
    def _extract_strike_price(self, question: str) -> Optional[float]:
        """Extract strike price from Polymarket question"""
        import re
        
        # Look for price patterns like $89,000, $89k, etc.
        patterns = [
            r'\$([0-9,]+)k',  # $89k
            r'\$([0-9,]+)',   # $89,000
            r'([0-9,]+)k',    # 89k
            r'([0-9,]+)'      # 89000
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, question.lower())
            if matches:
                try:
                    price_str = matches[0].replace(',', '')
                    if 'k' in question.lower() and 'k' not in price_str:
                        return float(price_str) * 1000
                    else:
                        return float(price_str)
                except:
                    continue
        
        return None
    
    def _classify_market_type(self, question: str) -> str:
        """Classify market type based on question"""
        question = question.lower()
        
        if '15' in question and 'minute' in question:
            return "15min"
        elif 'hour' in question and ('1' in question or 'one' in question):
            return "1hour"
        elif 'day' in question:
            return "daily"
        else:
            return "binary"

class ArbitrageDetector:
    """Detects arbitrage opportunities between platforms"""
    
    def __init__(self):
        self.opportunities = []
        self.min_profit_threshold = 0.02  # 2 cents minimum profit
    
    def detect_opportunities(self, kalshi_markets: List[Market], 
                           polymarket_markets: List[Market]) -> List[ArbitrageOpportunity]:
        """Detect arbitrage opportunities between markets"""
        opportunities = []
        
        # Compare markets with similar timeframes and strike prices
        for k_market in kalshi_markets:
            for p_market in polymarket_markets:
                
                # Check if markets are comparable
                if self._are_comparable(k_market, p_market):
                    opportunity = self._analyze_arbitrage(k_market, p_market)
                    if opportunity and opportunity.estimated_profit > self.min_profit_threshold:
                        opportunities.append(opportunity)
        
        return opportunities
    
    def _are_comparable(self, market1: Market, market2: Market) -> bool:
        """Check if two markets are comparable for arbitrage"""
        
        # Must be same market type (15min, 1hour)
        if market1.market_type != market2.market_type:
            return False
        
        # If both have strike prices, they should be different for arbitrage
        if market1.strike_price and market2.strike_price:
            return abs(market1.strike_price - market2.strike_price) > 500  # At least $500 difference
        
        # For now, only compare if we have strike prices
        return market1.strike_price is not None and market2.strike_price is not None
    
    def _analyze_arbitrage(self, k_market: Market, p_market: Market) -> Optional[ArbitrageOpportunity]:
        """Analyze potential arbitrage between two markets"""
        
        if not (k_market.strike_price and p_market.strike_price):
            return None
        
        # Strike price arbitrage strategy
        if k_market.strike_price != p_market.strike_price:
            return self._analyze_strike_arbitrage(k_market, p_market)
        
        return None
    
    def _analyze_strike_arbitrage(self, k_market: Market, p_market: Market) -> Optional[ArbitrageOpportunity]:
        """
        Analyze strike price arbitrage opportunity.
        
        Strategy: When Kalshi and Polymarket have different strike prices,
        create a "middle zone" where both positions pay out.
        
        Example:
        - Kalshi strike: $89k (YES pays if BTC >= $89k)  
        - Polymarket strike: $90k (UP pays if BTC >= $90k)
        - Strategy: Buy Kalshi YES + Polymarket DOWN
        - If BTC lands between $89k-90k: BOTH pay out ($2 total revenue)
        """
        
        k_strike = k_market.strike_price
        p_strike = p_market.strike_price
        
        # Determine the arbitrage strategy
        if k_strike < p_strike:
            # Buy Kalshi YES (lower strike) + Polymarket NO/DOWN (higher strike)
            cost = k_market.yes_ask + p_market.no_ask
            strategy = f"Buy Kalshi YES@{k_strike} + Polymarket NO@{p_strike}"
        else:
            # Buy Kalshi NO (higher strike) + Polymarket YES/UP (lower strike)  
            cost = k_market.no_ask + p_market.yes_ask
            strategy = f"Buy Kalshi NO@{k_strike} + Polymarket YES@{p_strike}"
        
        # Calculate potential profit
        # In the "middle zone" both positions pay out = $2.00 revenue
        max_revenue = 2.00
        estimated_profit = max_revenue - cost
        
        # Outside the middle zone, only one position pays = $1.00 revenue
        min_revenue = 1.00
        worst_case_profit = min_revenue - cost
        
        # Only flag as opportunity if worst case is still profitable
        if worst_case_profit > 0:
            confidence = min(estimated_profit / 0.10, 1.0)  # Scale by 10 cent max expected
            
            return ArbitrageOpportunity(
                kalshi_market=k_market,
                polymarket_market=p_market,
                strategy=strategy,
                estimated_profit=estimated_profit,
                total_cost=cost,
                confidence=confidence,
                timestamp=time.time()
            )
        
        return None

class PaperTrader:
    """Paper trading functionality for arbitrage opportunities"""
    
    def __init__(self, initial_balance: float = 1000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions = []
        self.trade_history = []
        self.total_pnl = 0.0
    
    def execute_arbitrage(self, opportunity: ArbitrageOpportunity) -> bool:
        """Execute paper trade for arbitrage opportunity"""
        
        if opportunity.total_cost > self.current_balance:
            return False  # Insufficient funds
        
        # Create paper trade record
        trade = {
            'timestamp': time.time(),
            'strategy': opportunity.strategy,
            'cost': opportunity.total_cost,
            'estimated_profit': opportunity.estimated_profit,
            'kalshi_market': opportunity.kalshi_market.ticker,
            'polymarket_market': opportunity.polymarket_market.ticker,
            'status': 'open'
        }
        
        self.current_balance -= opportunity.total_cost
        self.positions.append(trade)
        
        print(f"📈 PAPER TRADE EXECUTED: {opportunity.strategy}")
        print(f"   Cost: ${opportunity.total_cost:.3f}")
        print(f"   Estimated Profit: ${opportunity.estimated_profit:.3f}")
        print(f"   Remaining Balance: ${self.current_balance:.2f}")
        
        return True
    
    def get_summary(self) -> dict:
        """Get trading summary"""
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_trades': len(self.positions),
            'open_positions': len([p for p in self.positions if p['status'] == 'open']),
            'total_pnl': self.total_pnl
        }

class CrossPlatformScanner:
    """Main scanner class"""
    
    def __init__(self):
        self.kalshi_fetcher = KalshiFetcher()
        self.polymarket_fetcher = PolymarketFetcher()
        self.arbitrage_detector = ArbitrageDetector()
        self.paper_trader = PaperTrader()
        self.state_file = '/home/clawdbot/clawd/btc-arbitrage/data/cross_platform_arb_state.json'
        self.scan_count = 0
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
    
    def scan_once(self) -> Dict[str, Any]:
        """Perform a single scan of both platforms"""
        scan_start = time.time()
        self.scan_count += 1
        
        print(f"\n{'='*70}")
        print(f"Cross-Platform Arbitrage Scan #{self.scan_count}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'='*70}")
        
        # Fetch markets from both platforms
        print("📊 Fetching Kalshi BTC markets...")
        kalshi_markets = self.kalshi_fetcher.fetch_btc_markets()
        print(f"   Found {len(kalshi_markets)} active Kalshi BTC markets")
        
        print("📊 Fetching Polymarket BTC markets...")
        polymarket_markets = self.polymarket_fetcher.fetch_btc_markets()
        print(f"   Found {len(polymarket_markets)} active Polymarket BTC markets")
        
        # Display discovered markets
        self._display_markets("KALSHI", kalshi_markets)
        self._display_markets("POLYMARKET", polymarket_markets)
        
        # Detect arbitrage opportunities
        print("\n🔍 Scanning for arbitrage opportunities...")
        opportunities = self.arbitrage_detector.detect_opportunities(kalshi_markets, polymarket_markets)
        
        if opportunities:
            print(f"🎯 Found {len(opportunities)} arbitrage opportunities!")
            for i, opp in enumerate(opportunities, 1):
                print(f"\n💰 Opportunity #{i}:")
                print(f"   Strategy: {opp.strategy}")
                print(f"   Estimated Profit: ${opp.estimated_profit:.3f}")
                print(f"   Total Cost: ${opp.total_cost:.3f}")
                print(f"   Confidence: {opp.confidence:.1%}")
                
                # Execute paper trade
                if opp.estimated_profit > 0.02:  # More than 2 cents profit
                    self.paper_trader.execute_arbitrage(opp)
        else:
            print("❌ No arbitrage opportunities detected")
            
            # Show why no opportunities were found
            if not kalshi_markets and not polymarket_markets:
                print("   Reason: No active BTC markets found on either platform")
            elif not kalshi_markets:
                print("   Reason: No active BTC markets found on Kalshi")
            elif not polymarket_markets:
                print("   Reason: No active BTC markets found on Polymarket")
            else:
                print("   Reason: No comparable markets with profitable arbitrage potential")
        
        # Save state
        scan_result = {
            'timestamp': scan_start,
            'scan_count': self.scan_count,
            'kalshi_markets_found': len(kalshi_markets),
            'polymarket_markets_found': len(polymarket_markets), 
            'opportunities_found': len(opportunities),
            'kalshi_markets': [self._market_to_dict(m) for m in kalshi_markets],
            'polymarket_markets': [self._market_to_dict(m) for m in polymarket_markets],
            'opportunities': [self._opportunity_to_dict(o) for o in opportunities],
            'paper_trader_summary': self.paper_trader.get_summary()
        }
        
        self._save_state(scan_result)
        
        # Display summary
        print(f"\n📈 Paper Trading Summary:")
        summary = self.paper_trader.get_summary()
        print(f"   Balance: ${summary['current_balance']:.2f} (Started: ${summary['initial_balance']:.2f})")
        print(f"   Trades: {summary['total_trades']} total, {summary['open_positions']} open")
        print(f"   P&L: ${summary['total_pnl']:.2f}")
        
        scan_duration = time.time() - scan_start
        print(f"\n⏱️  Scan completed in {scan_duration:.2f} seconds")
        print(f"{'='*70}")
        
        return scan_result
    
    def run_continuous(self, interval_seconds: int = 30):
        """Run continuous monitoring"""
        print(f"🔄 Starting continuous monitoring (every {interval_seconds} seconds)")
        print("   Press Ctrl+C to stop")
        
        try:
            while True:
                self.scan_once()
                
                print(f"⏳ Waiting {interval_seconds} seconds until next scan...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            print("Final summary:")
            summary = self.paper_trader.get_summary()
            print(f"   Total scans: {self.scan_count}")
            print(f"   Final balance: ${summary['current_balance']:.2f}")
            print(f"   Total trades: {summary['total_trades']}")
    
    def _display_markets(self, platform: str, markets: List[Market]):
        """Display markets for a platform"""
        if not markets:
            print(f"\n📍 {platform}: No active BTC markets found")
            return
        
        print(f"\n📍 {platform} Active BTC Markets:")
        for market in markets:
            strike_info = f" (Strike: ${market.strike_price:,.0f})" if market.strike_price else ""
            print(f"   • {market.ticker}{strike_info}")
            print(f"     Question: {market.question}")
            print(f"     Prices: YES {market.yes_price:.3f} / NO {market.no_price:.3f}")
            print(f"     Volume: ${market.volume:,.0f}")
    
    def _market_to_dict(self, market: Market) -> dict:
        """Convert Market to dictionary"""
        return {
            'platform': market.platform,
            'ticker': market.ticker,
            'question': market.question,
            'yes_price': market.yes_price,
            'no_price': market.no_price,
            'strike_price': market.strike_price,
            'market_type': market.market_type,
            'volume': market.volume,
            'end_time': market.end_time
        }
    
    def _opportunity_to_dict(self, opp: ArbitrageOpportunity) -> dict:
        """Convert ArbitrageOpportunity to dictionary"""
        return {
            'strategy': opp.strategy,
            'estimated_profit': opp.estimated_profit,
            'total_cost': opp.total_cost,
            'confidence': opp.confidence,
            'timestamp': opp.timestamp,
            'kalshi_market': self._market_to_dict(opp.kalshi_market),
            'polymarket_market': self._market_to_dict(opp.polymarket_market)
        }
    
    def _save_state(self, scan_result: dict):
        """Save state to JSON file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(scan_result, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Warning: Could not save state: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Cross-Platform BTC Arbitrage Scanner')
    parser.add_argument('--scan-once', action='store_true', 
                       help='Perform a single scan and exit')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=30,
                       help='Interval between scans in continuous mode (default: 30 seconds)')
    
    args = parser.parse_args()
    
    # Print header
    print("🚀 Cross-Platform BTC Arbitrage Scanner v1.0")
    print("   Monitoring: Kalshi vs Polymarket")
    print("   Strategy: Strike price arbitrage detection")
    
    scanner = CrossPlatformScanner()
    
    try:
        if args.scan_once:
            scanner.scan_once()
        elif args.continuous:
            scanner.run_continuous(args.interval)
        else:
            # Default: single scan
            scanner.scan_once()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())