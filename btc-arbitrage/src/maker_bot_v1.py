#!/usr/bin/env python3
"""
Maker Bot V1 — Paper Trading Market Maker for Kalshi BTC 15-Minute Markets

Strategy: Two-sided quoting (market making)
  - Place limit orders on BOTH YES and NO sides of the book
  - Earn the bid-ask spread when both sides fill
  - Directional bias from probability scorer (optional)
  - Inventory management to prevent one-sided exposure

This is PAPER TRADING only — simulates fills, does NOT place real orders.

Architecture:
  - Kalshi WebSocket for real-time YES/NO prices
  - Coinbase WebSocket for BTC spot price
  - REST fallback for market discovery
  - ProbabilityScorer for directional bias (optional)

Output:
  - State: data/maker_v1_state.json
  - Trades: data/maker_v1_trades.jsonl
  - Logs: stdout (managed-process.sh compatible)

IRON RULES compliance:
  - Rule #1: Research (maker strategy) → Data (paper trade) → Trade (later)
  - Rule #2: EV calculated per spread capture opportunity
  - Rule #5: KISS — simple two-sided quoting first
  - Rule #6: Log everything
  - Rule #7: End-of-period safety (widen/cancel in last 2min/30s)
"""

import asyncio
import json
import math
import os
import signal
import sys
import time
import traceback
from collections import deque
from datetime import datetime, timezone
from urllib import request, parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Optional: probability scorer for directional bias
try:
    from probability_scorer import ProbabilityScorer
    HAS_SCORER = True
except ImportError:
    HAS_SCORER = False
    print("⚠️ ProbabilityScorer not available, using symmetric quotes", flush=True)

# Optional: Kalshi WebSocket for real-time ticker
try:
    from kalshi_websocket import KalshiWebSocketClient
    HAS_WEBSOCKET = True
    print("✅ WebSocket client available", flush=True)
except ImportError:
    HAS_WEBSOCKET = False
    print("⚠️ WebSocket not available, using REST only", flush=True)

try:
    import websockets
    HAS_WS_LIB = True
except ImportError:
    HAS_WS_LIB = False
    print("⚠️ websockets library not installed", flush=True)

# ─── Configuration ───────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    # Spread parameters (in dollars, Kalshi prices are 0.00-1.00)
    'half_spread': 0.02,           # Half spread per side ($0.02 = 2 cents)
    'min_half_spread': 0.01,       # Minimum half spread
    'max_half_spread': 0.05,       # Maximum half spread
    
    # Quote size
    'quote_size': 10,              # Contracts per quote
    
    # Price bounds — don't quote outside these
    'min_yes_price': 0.05,         # Don't buy YES below $0.05
    'max_yes_price': 0.95,         # Don't buy YES above $0.95
    
    # Inventory limits
    'max_inventory': 100,          # Max contracts per side
    'inventory_skew_per_contract': 0.001,  # Skew per net contract of imbalance
    
    # Directional bias thresholds
    'bias_threshold': 0.55,        # prob_up > this → bullish shade
    'bias_shade': 0.01,            # How much to shade quotes when biased ($0.01)
    
    # Timing
    'quote_interval_sec': 7,       # Re-quote every N seconds
    'price_move_requote_pct': 0.005,  # Re-quote if BTC moves >0.5%
    
    # End-of-period safety
    'widen_spread_minutes': 2,     # Widen 2x in last N minutes
    'cancel_all_seconds': 30,      # Cancel all in last N seconds
    
    # Paper trading
    'paper_mode': True,            # Always True for V1
    
    # Logging
    'status_interval_sec': 30,     # Print status every N seconds
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def log(msg, level="INFO"):
    """Print with timestamp, flush for managed-process.sh compatibility"""
    ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
    print(f"[{ts}] [{level}] {msg}", flush=True)


def clamp(value, lo, hi):
    """Clamp value between lo and hi"""
    return max(lo, min(hi, value))


# ─── BTC Spot Price Feed (Coinbase WebSocket + REST fallback) ────────────────

class BTCSpotFeed:
    """Lightweight BTC spot price from Coinbase"""
    
    def __init__(self):
        self.price = None
        self.last_update = 0
        self.price_history = deque(maxlen=300)
        self.running = True
    
    def get_price(self):
        return self.price
    
    def get_momentum_1m(self):
        """1-minute price change as fraction (e.g., 0.001 = 0.1%)"""
        if len(self.price_history) < 2:
            return 0.0
        cutoff = time.time() - 60
        old_prices = [p for t, p in self.price_history if t < cutoff]
        if not old_prices:
            return 0.0
        old = old_prices[-1]
        return (self.price - old) / old if old > 0 else 0.0
    
    def _update(self, price):
        self.price = price
        self.last_update = time.time()
        self.price_history.append((time.time(), price))
    
    def _fetch_rest(self):
        """REST fallback: fetch BTC price from Coinbase"""
        try:
            url = "https://api.exchange.coinbase.com/products/BTC-USD/ticker"
            req = request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            with request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read())
            return float(data.get('price', 0))
        except Exception:
            return None
    
    async def _ws_loop(self):
        """Coinbase WebSocket for real-time BTC price"""
        if not HAS_WS_LIB:
            return
        
        while self.running:
            try:
                async with websockets.connect(
                    "wss://ws-feed.exchange.coinbase.com",
                    ping_interval=20,
                    close_timeout=5
                ) as ws:
                    await ws.send(json.dumps({
                        "type": "subscribe",
                        "channels": [{"name": "ticker", "product_ids": ["BTC-USD"]}]
                    }))
                    async for msg in ws:
                        if not self.running:
                            break
                        d = json.loads(msg)
                        if d.get('type') == 'ticker' and 'price' in d:
                            self._update(float(d['price']))
            except asyncio.CancelledError:
                break
            except Exception as e:
                log(f"BTC feed error: {e}", "WARN")
                await asyncio.sleep(5)
    
    async def _rest_loop(self):
        """REST fallback polling"""
        while self.running:
            try:
                # Only poll REST if WebSocket hasn't updated recently
                if time.time() - self.last_update > 10:
                    price = await asyncio.get_event_loop().run_in_executor(
                        None, self._fetch_rest
                    )
                    if price and price > 0:
                        self._update(price)
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(10)
    
    async def run(self):
        """Start both WebSocket and REST fallback"""
        tasks = [asyncio.create_task(self._rest_loop())]
        if HAS_WS_LIB:
            tasks.append(asyncio.create_task(self._ws_loop()))
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop(self):
        self.running = False


# ─── Kalshi Market Poller (REST) ─────────────────────────────────────────────

class KalshiMarketPoller:
    """Poll Kalshi REST API for current BTC 15min market info"""
    
    def __init__(self, interval=5):
        self.interval = interval
        self.running = True
        self.current_market = None  # Latest market data dict
        self.market_history = deque(maxlen=200)
    
    def _fetch(self):
        """Fetch current active BTC 15min market"""
        try:
            url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=5&series_ticker=KXBTC15M&status=open"
            req = request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Accept', 'application/json')
            with request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read())
            
            if data.get('markets'):
                m = data['markets'][0]
                return {
                    'ticker': m['ticker'],
                    'yes_bid': m.get('yes_bid', 0) / 100,  # Kalshi returns cents
                    'yes_ask': m.get('yes_ask', 0) / 100,
                    'no_bid': m.get('no_bid', 0) / 100 if m.get('no_bid') else None,
                    'no_ask': m.get('no_ask', 0) / 100 if m.get('no_ask') else None,
                    'volume': m.get('volume', 0),
                    'close_time': m.get('close_time'),
                    'open_time': m.get('open_time'),
                    'time': time.time(),
                }
        except Exception as e:
            log(f"Kalshi REST error: {e}", "WARN")
        return None
    
    def _fetch_orderbook(self, ticker):
        """Fetch orderbook for a specific market"""
        try:
            encoded = parse.quote(ticker)
            url = f"https://api.elections.kalshi.com/trade-api/v2/markets/{encoded}/orderbook"
            req = request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Accept', 'application/json')
            with request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read())
            return data.get('orderbook')
        except Exception:
            return None
    
    def get_mid_price(self):
        """Get mid price from current market data"""
        if not self.current_market:
            return None
        yes_bid = self.current_market.get('yes_bid', 0)
        yes_ask = self.current_market.get('yes_ask', 0)
        if yes_bid > 0 and yes_ask > 0:
            return (yes_bid + yes_ask) / 2
        return None
    
    def time_until_close(self):
        """Seconds until current market closes"""
        if not self.current_market or not self.current_market.get('close_time'):
            return 999
        try:
            close_str = self.current_market['close_time']
            # Parse ISO 8601 datetime
            if close_str.endswith('Z'):
                close_str = close_str[:-1] + '+00:00'
            close_dt = datetime.fromisoformat(close_str)
            now = datetime.now(timezone.utc)
            return max(0, (close_dt - now).total_seconds())
        except Exception:
            return 999
    
    async def run(self):
        while self.running:
            try:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self._fetch
                )
                if data:
                    self.current_market = data
                    self.market_history.append(data)
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log(f"Market poller error: {e}", "WARN")
                await asyncio.sleep(10)
    
    async def stop(self):
        self.running = False


# ─── Kalshi WebSocket Ticker Handler ─────────────────────────────────────────

class KalshiWSHandler:
    """Wrapper around KalshiWebSocketClient for maker bot"""
    
    def __init__(self):
        self.latest_ticker = {}  # market_ticker -> data
        self.ws_client = None
        self.ws_connected = False
        self.running = True
    
    def _on_ticker(self, data):
        """Handle WebSocket ticker updates"""
        try:
            ticker = data.get('market_ticker', '')
            if 'KXBTC15M' not in ticker:
                return
            self.latest_ticker[ticker] = {
                'ticker': ticker,
                'yes_bid': data.get('yes_bid', 0) / 100,
                'yes_ask': data.get('yes_ask', 0) / 100,
                'volume': data.get('volume', 0),
                'close_time': data.get('close_time'),
                'time': time.time(),
            }
        except Exception as e:
            log(f"WS ticker error: {e}", "WARN")
    
    def _on_error(self, error):
        log(f"WS error: {error}", "WARN")
        self.ws_connected = False
    
    def get_market_data(self, ticker):
        """Get latest WS data for a specific ticker"""
        return self.latest_ticker.get(ticker)
    
    async def run(self):
        if not HAS_WEBSOCKET:
            return
        try:
            self.ws_client = KalshiWebSocketClient(
                on_ticker=self._on_ticker,
                on_error=self._on_error,
            )
            self.ws_connected = True
            await self.ws_client.start(series="KXBTC15M")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log(f"WS start error: {e}", "WARN")
            self.ws_connected = False
    
    async def stop(self):
        self.running = False
        if self.ws_client:
            await self.ws_client.stop()


# ─── Paper Order & Fill Tracking ─────────────────────────────────────────────

class PaperOrder:
    """Represents a simulated limit order"""
    
    def __init__(self, side, price, size, market_ticker, order_time):
        self.side = side            # 'YES' or 'NO'
        self.price = price          # Our bid price (what we pay)
        self.size = size            # Number of contracts
        self.market_ticker = market_ticker
        self.order_time = order_time
        self.filled = False
        self.fill_time = None
    
    def check_fill(self, market_yes_bid, market_yes_ask):
        """
        Check if our order would have been filled.
        
        For a YES limit buy at price P:
          - We'd fill if market yes_ask <= our bid price (someone sells to us)
        For a NO limit buy at price P:
          - NO ask = 1 - yes_bid, so we'd fill if (1 - yes_bid) <= our bid price
          - i.e., yes_bid >= (1 - our_no_price)
        """
        if self.filled:
            return False
        
        now = time.time()
        
        if self.side == 'YES':
            # We're buying YES at self.price
            # Fill if market yes_ask <= our price (or crosses through)
            if market_yes_ask > 0 and market_yes_ask <= self.price:
                self.filled = True
                self.fill_time = now
                return True
        
        elif self.side == 'NO':
            # We're buying NO at self.price
            # NO ask = 1 - yes_bid (approximately)
            # Fill if (1 - yes_bid) <= our price
            if market_yes_bid > 0 and (1.0 - market_yes_bid) <= self.price:
                self.filled = True
                self.fill_time = now
                return True
        
        return False
    
    def to_dict(self):
        return {
            'side': self.side,
            'price': self.price,
            'size': self.size,
            'market_ticker': self.market_ticker,
            'order_time': self.order_time,
            'filled': self.filled,
            'fill_time': self.fill_time,
        }


# ─── Main Maker Bot ─────────────────────────────────────────────────────────

class MakerBot:
    """
    Paper trading market maker for Kalshi BTC 15-minute markets.
    
    Places simulated two-sided quotes (YES bid + NO bid), tracks fills,
    manages inventory, and logs everything for analysis.
    """
    
    def __init__(self, config=None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.running = False
        self.start_time = time.time()
        
        # Data feeds
        self.btc_feed = BTCSpotFeed()
        self.kalshi_poller = KalshiMarketPoller(interval=5)
        self.kalshi_ws = KalshiWSHandler()
        
        # Probability scorer (optional)
        self.scorer = ProbabilityScorer() if HAS_SCORER else None
        
        # Current quotes
        self.active_yes_order = None   # PaperOrder or None
        self.active_no_order = None    # PaperOrder or None
        
        # Inventory tracking
        self.yes_inventory = 0         # Net YES contracts held
        self.no_inventory = 0          # Net NO contracts held
        
        # P&L tracking
        self.total_yes_cost = 0.0      # Total spent on YES fills
        self.total_no_cost = 0.0       # Total spent on NO fills
        self.total_pnl = 0.0           # Realized P&L
        self.spreads_captured = 0      # Number of complete round-trips
        self.total_spread_pnl = 0.0    # P&L from spread captures
        
        # Fill history
        self.fills = []                # List of fill dicts
        self.quote_cycles = 0
        
        # Market tracking
        self.current_market_ticker = None
        self.last_btc_price_at_quote = None
        self.last_quote_time = 0
        self.last_status_time = 0
        
        # State file paths
        self.base_dir = '/home/clawdbot/clawd/btc-arbitrage'
        self.state_file = os.path.join(self.base_dir, 'data', 'maker_v1_state.json')
        self.trades_file = os.path.join(self.base_dir, 'data', 'maker_v1_trades.jsonl')
        
        # Ensure dirs exist
        os.makedirs(os.path.join(self.base_dir, 'data'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'logs'), exist_ok=True)
        
        log("🏭 Maker Bot V1 initialized (PAPER MODE)")
        log(f"   half_spread=${self.config['half_spread']:.2f}  quote_size={self.config['quote_size']}  max_inventory={self.config['max_inventory']}")
    
    # ── Fair Value & Quoting ────────────────────────────────────────────────
    
    def calculate_fair_value(self):
        """
        Calculate fair value for YES contract.
        
        Simple approach: use Kalshi mid price.
        If probability scorer is available, blend with its estimate.
        
        Returns: float 0.0-1.0 or None
        """
        mid = self.kalshi_poller.get_mid_price()
        
        # If we have WS data for current market, prefer it (more real-time)
        if self.current_market_ticker:
            ws_data = self.kalshi_ws.get_market_data(self.current_market_ticker)
            if ws_data and time.time() - ws_data.get('time', 0) < 15:
                ws_bid = ws_data.get('yes_bid', 0)
                ws_ask = ws_data.get('yes_ask', 0)
                if ws_bid > 0 and ws_ask > 0:
                    mid = (ws_bid + ws_ask) / 2
        
        if mid is None:
            return None
        
        # Optionally blend with probability scorer
        if self.scorer and self.btc_feed.price:
            try:
                indicators = self._build_scorer_indicators()
                result = self.scorer.estimate_probability(indicators, market_type='BTC')
                prob_up = result.get('prob_up', 0.5)
                confidence = result.get('confidence', 0)
                
                # Blend: weight scorer by its confidence (0-1)
                # At 0 confidence → pure mid, at 1.0 → 50/50 blend
                blend_weight = confidence * 0.3  # Max 30% influence from scorer
                mid = mid * (1 - blend_weight) + prob_up * blend_weight
            except Exception:
                pass  # Fallback to pure mid
        
        return mid
    
    def _build_scorer_indicators(self):
        """Build indicator dict for ProbabilityScorer"""
        indicators = {}
        
        btc = self.btc_feed
        if btc.price:
            indicators['current_price'] = btc.price
        
        mom_1m = btc.get_momentum_1m()
        if mom_1m is not None:
            indicators['momentum_1m'] = mom_1m * 100  # Scorer expects percentage
        
        # Time remaining
        ttc = self.kalshi_poller.time_until_close()
        if ttc < 999:
            indicators['time_remaining_sec'] = ttc
        
        return indicators
    
    def get_directional_bias(self):
        """
        Get directional bias from probability scorer.
        Returns: 'bullish', 'bearish', or 'neutral'
        """
        if not self.scorer or not self.btc_feed.price:
            return 'neutral'
        
        try:
            indicators = self._build_scorer_indicators()
            result = self.scorer.estimate_probability(indicators, market_type='BTC')
            prob_up = result.get('prob_up', 0.5)
            
            threshold = self.config['bias_threshold']
            if prob_up > threshold:
                return 'bullish'
            elif prob_up < (1 - threshold):
                return 'bearish'
            return 'neutral'
        except Exception:
            return 'neutral'
    
    def calculate_quotes(self, fair_value):
        """
        Calculate YES and NO quote prices.
        
        Base logic:
          YES bid = fair_value - half_spread
          NO bid  = (1 - fair_value) - half_spread
        
        Adjustments:
          1. Directional bias (shade tighter on favored side)
          2. Inventory skew (shade to rebalance)
          3. End-of-period widening
          4. Price bounds enforcement
        
        Returns: (yes_bid_price, no_bid_price) or (None, None) if shouldn't quote
        """
        cfg = self.config
        half_spread = cfg['half_spread']
        
        # 1. Time-based adjustments
        ttc = self.kalshi_poller.time_until_close()
        
        # Last 30 seconds: cancel everything
        if ttc < cfg['cancel_all_seconds']:
            return None, None
        
        # Last 2 minutes: widen spread 2x
        if ttc < cfg['widen_spread_minutes'] * 60:
            half_spread *= 2.0
        
        # Clamp half_spread
        half_spread = clamp(half_spread, cfg['min_half_spread'], cfg['max_half_spread'])
        
        # 2. Base quotes
        yes_bid = fair_value - half_spread
        no_bid = (1.0 - fair_value) - half_spread
        
        # 3. Directional bias
        bias = self.get_directional_bias()
        shade = cfg['bias_shade']
        if bias == 'bullish':
            # More aggressive on YES (tighter), wider on NO
            yes_bid += shade
            no_bid -= shade
        elif bias == 'bearish':
            # More aggressive on NO (tighter), wider on YES
            no_bid += shade
            yes_bid -= shade
        
        # 4. Inventory skew
        # Net inventory: positive = too many YES, negative = too many NO
        net_inventory = self.yes_inventory - self.no_inventory
        skew_per = cfg['inventory_skew_per_contract']
        
        # If we have too many YES, lower YES bid (less eager to buy more YES)
        # and raise NO bid (more eager to buy NO to offset)
        yes_bid -= net_inventory * skew_per
        no_bid += net_inventory * skew_per
        
        # 5. Price bounds
        yes_bid = clamp(yes_bid, cfg['min_yes_price'], cfg['max_yes_price'])
        no_bid = clamp(no_bid, 1.0 - cfg['max_yes_price'], 1.0 - cfg['min_yes_price'])
        
        # 6. Inventory cap: don't quote if maxed out
        if self.yes_inventory >= cfg['max_inventory']:
            yes_bid = None  # Signal: don't place YES order
        if self.no_inventory >= cfg['max_inventory']:
            no_bid = None
        
        # 7. Round to cents (Kalshi's minimum tick)
        if yes_bid is not None:
            yes_bid = round(yes_bid, 2)
        if no_bid is not None:
            no_bid = round(no_bid, 2)
        
        return yes_bid, no_bid
    
    # ── Quote Management ────────────────────────────────────────────────────
    
    def should_requote(self):
        """Check if we should update quotes"""
        now = time.time()
        cfg = self.config
        
        # Time-based re-quote
        if now - self.last_quote_time >= cfg['quote_interval_sec']:
            return True
        
        # Price-based re-quote (BTC moved >0.5%)
        if (self.btc_feed.price and self.last_btc_price_at_quote and
                self.last_btc_price_at_quote > 0):
            move = abs(self.btc_feed.price - self.last_btc_price_at_quote) / self.last_btc_price_at_quote
            if move > cfg['price_move_requote_pct']:
                return True
        
        # Market transition (new ticker)
        market = self.kalshi_poller.current_market
        if market and market.get('ticker') != self.current_market_ticker:
            return True
        
        return False
    
    def place_quotes(self, fair_value):
        """Place new paper quotes (cancel old ones first)"""
        yes_bid, no_bid = self.calculate_quotes(fair_value)
        
        market = self.kalshi_poller.current_market
        if not market:
            return
        
        ticker = market['ticker']
        now = time.time()
        
        # Cancel old orders (in paper mode, just clear them)
        self.active_yes_order = None
        self.active_no_order = None
        
        # Place new quotes
        if yes_bid is not None and yes_bid > 0:
            self.active_yes_order = PaperOrder(
                side='YES',
                price=yes_bid,
                size=self.config['quote_size'],
                market_ticker=ticker,
                order_time=now,
            )
        
        if no_bid is not None and no_bid > 0:
            self.active_no_order = PaperOrder(
                side='NO',
                price=no_bid,
                size=self.config['quote_size'],
                market_ticker=ticker,
                order_time=now,
            )
        
        self.current_market_ticker = ticker
        self.last_btc_price_at_quote = self.btc_feed.price
        self.last_quote_time = now
        self.quote_cycles += 1
        
        # Log quote
        yes_str = f"YES@${yes_bid:.2f}" if yes_bid else "YES=OFF"
        no_str = f"NO@${no_bid:.2f}" if no_bid else "NO=OFF"
        ttc = self.kalshi_poller.time_until_close()
        
        log(f"📝 Quote #{self.quote_cycles}: {yes_str} | {no_str} | FV=${fair_value:.3f} | TTL={ttc:.0f}s | BTC=${self.btc_feed.price:.0f}" if self.btc_feed.price else
            f"📝 Quote #{self.quote_cycles}: {yes_str} | {no_str} | FV=${fair_value:.3f} | TTL={ttc:.0f}s")
    
    # ── Fill Checking & P&L ─────────────────────────────────────────────────
    
    def check_fills(self):
        """Check if any paper orders would have been filled"""
        market = self.kalshi_poller.current_market
        if not market:
            return
        
        yes_bid = market.get('yes_bid', 0)
        yes_ask = market.get('yes_ask', 0)
        
        # Prefer WebSocket data if available
        if self.current_market_ticker:
            ws_data = self.kalshi_ws.get_market_data(self.current_market_ticker)
            if ws_data and time.time() - ws_data.get('time', 0) < 10:
                yes_bid = ws_data.get('yes_bid', yes_bid)
                yes_ask = ws_data.get('yes_ask', yes_ask)
        
        if yes_bid <= 0 and yes_ask <= 0:
            return
        
        # Check YES order fill
        if self.active_yes_order and not self.active_yes_order.filled:
            if self.active_yes_order.check_fill(yes_bid, yes_ask):
                self._handle_fill(self.active_yes_order, yes_bid, yes_ask)
        
        # Check NO order fill
        if self.active_no_order and not self.active_no_order.filled:
            if self.active_no_order.check_fill(yes_bid, yes_ask):
                self._handle_fill(self.active_no_order, yes_bid, yes_ask)
    
    def _handle_fill(self, order, market_yes_bid, market_yes_ask):
        """Process a simulated fill"""
        fill_record = {
            'timestamp': time.time(),
            'timestamp_str': datetime.now(timezone.utc).isoformat(),
            'market_ticker': order.market_ticker,
            'side': order.side,
            'price': order.price,
            'size': order.size,
            'btc_price': self.btc_feed.price,
            'market_yes_bid': market_yes_bid,
            'market_yes_ask': market_yes_ask,
            'yes_inventory_before': self.yes_inventory,
            'no_inventory_before': self.no_inventory,
        }
        
        # Update inventory
        if order.side == 'YES':
            self.yes_inventory += order.size
            self.total_yes_cost += order.price * order.size
        else:
            self.no_inventory += order.size
            self.total_no_cost += order.price * order.size
        
        fill_record['yes_inventory_after'] = self.yes_inventory
        fill_record['no_inventory_after'] = self.no_inventory
        
        # Check for spread capture: if we have both YES and NO, they net to $1.00
        spread_captured = self._check_spread_capture()
        fill_record['spread_captured'] = spread_captured
        fill_record['total_pnl'] = self.total_pnl
        
        self.fills.append(fill_record)
        
        # Write to trade journal
        self._write_trade(fill_record)
        
        log(f"🎯 FILL: {order.side} x{order.size} @ ${order.price:.2f} | "
            f"Inv: YES={self.yes_inventory} NO={self.no_inventory} | "
            f"PnL: ${self.total_pnl:.2f}")
    
    def _check_spread_capture(self):
        """
        Check if we can net off YES + NO inventory for a spread capture.
        When YES + NO = 1 contract pair, they settle to $1.00 total.
        Profit = $1.00 - (YES cost + NO cost per pair).
        """
        captured = 0.0
        
        while self.yes_inventory > 0 and self.no_inventory > 0:
            # Net off 1 contract pair
            pairs = min(self.yes_inventory, self.no_inventory)
            
            # Average cost per contract
            avg_yes = self.total_yes_cost / max(self.yes_inventory, 1)
            avg_no = self.total_no_cost / max(self.no_inventory, 1)
            
            # Each pair settles at $1.00
            profit_per_pair = 1.00 - (avg_yes + avg_no)
            pair_profit = profit_per_pair * pairs
            
            # Update inventory
            cost_deducted_yes = avg_yes * pairs
            cost_deducted_no = avg_no * pairs
            
            self.yes_inventory -= pairs
            self.no_inventory -= pairs
            self.total_yes_cost -= cost_deducted_yes
            self.total_no_cost -= cost_deducted_no
            
            self.total_pnl += pair_profit
            self.total_spread_pnl += pair_profit
            self.spreads_captured += pairs
            
            captured += pair_profit
            
            log(f"💰 SPREAD CAPTURED: {pairs} pairs | Profit: ${pair_profit:.4f} | "
                f"YES@${avg_yes:.3f} + NO@${avg_no:.3f} = ${avg_yes + avg_no:.3f} (vs $1.00)")
            
            break  # One pass is enough since we take min
        
        return captured
    
    def handle_market_settlement(self, old_ticker):
        """
        Handle when a market settles (15min window ends).
        Any remaining inventory settles at either $1.00 or $0.00.
        In paper mode, we mark unsettled inventory as a loss (worst case).
        """
        if self.yes_inventory > 0 or self.no_inventory > 0:
            # For paper trading, assume 50/50 settlement outcome
            # YES settles at $1.00 with ~50% probability
            # This is conservative — actual EV depends on market conditions
            # For simplicity: settle remaining at current fair value
            
            fv = self.calculate_fair_value() or 0.5
            
            yes_settle_value = fv * self.yes_inventory
            no_settle_value = (1.0 - fv) * self.no_inventory
            
            yes_pnl = yes_settle_value - self.total_yes_cost
            no_pnl = no_settle_value - self.total_no_cost
            settlement_pnl = yes_pnl + no_pnl
            
            self.total_pnl += settlement_pnl
            
            log(f"⏰ SETTLEMENT: {old_ticker} | "
                f"YES inv={self.yes_inventory} pnl=${yes_pnl:.2f} | "
                f"NO inv={self.no_inventory} pnl=${no_pnl:.2f} | "
                f"Net: ${settlement_pnl:.2f}")
            
            # Reset inventory for next market
            self.yes_inventory = 0
            self.no_inventory = 0
            self.total_yes_cost = 0.0
            self.total_no_cost = 0.0
            
            # Cancel active orders
            self.active_yes_order = None
            self.active_no_order = None
    
    # ── State & Logging ─────────────────────────────────────────────────────
    
    def _write_trade(self, fill_record):
        """Append fill to JSONL trade journal"""
        try:
            with open(self.trades_file, 'a') as f:
                f.write(json.dumps(fill_record) + '\n')
        except Exception as e:
            log(f"Error writing trade: {e}", "ERROR")
    
    def save_state(self):
        """Save current state to JSON file"""
        try:
            state = {
                'timestamp': time.time(),
                'timestamp_str': datetime.now(timezone.utc).isoformat(),
                'elapsed_sec': time.time() - self.start_time,
                'config': self.config,
                'performance': {
                    'total_pnl': round(self.total_pnl, 4),
                    'spreads_captured': self.spreads_captured,
                    'total_spread_pnl': round(self.total_spread_pnl, 4),
                    'total_fills': len(self.fills),
                    'yes_fills': sum(1 for f in self.fills if f['side'] == 'YES'),
                    'no_fills': sum(1 for f in self.fills if f['side'] == 'NO'),
                    'quote_cycles': self.quote_cycles,
                },
                'inventory': {
                    'yes': self.yes_inventory,
                    'no': self.no_inventory,
                    'net': self.yes_inventory - self.no_inventory,
                    'total_yes_cost': round(self.total_yes_cost, 4),
                    'total_no_cost': round(self.total_no_cost, 4),
                },
                'market': {
                    'current_ticker': self.current_market_ticker,
                    'btc_price': self.btc_feed.price,
                    'time_until_close': self.kalshi_poller.time_until_close(),
                },
                'quotes': {
                    'yes_order': self.active_yes_order.to_dict() if self.active_yes_order else None,
                    'no_order': self.active_no_order.to_dict() if self.active_no_order else None,
                },
                'fills': self.fills[-50:],  # Last 50 fills
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            log(f"Error saving state: {e}", "ERROR")
    
    def print_status(self):
        """Print periodic status summary"""
        now = time.time()
        if now - self.last_status_time < self.config['status_interval_sec']:
            return
        self.last_status_time = now
        
        elapsed = now - self.start_time
        elapsed_str = f"{int(elapsed//3600)}h{int((elapsed%3600)//60)}m"
        
        market = self.kalshi_poller.current_market
        mid = self.kalshi_poller.get_mid_price()
        ttc = self.kalshi_poller.time_until_close()
        
        yes_str = f"${self.active_yes_order.price:.2f}" if self.active_yes_order else "OFF"
        no_str = f"${self.active_no_order.price:.2f}" if self.active_no_order else "OFF"
        
        log(f"📊 STATUS [{elapsed_str}] | "
            f"PnL=${self.total_pnl:.2f} | Spreads={self.spreads_captured} | "
            f"Fills={len(self.fills)} | "
            f"Inv: Y={self.yes_inventory} N={self.no_inventory} | "
            f"Quotes: Y={yes_str} N={no_str} | "
            f"Mid={'${:.3f}'.format(mid) if mid else '?'} | "
            f"TTL={ttc:.0f}s | "
            f"BTC=${'%.0f' % self.btc_feed.price if self.btc_feed.price else '?'}")
    
    # ── Main Loop ───────────────────────────────────────────────────────────
    
    async def run(self):
        """Main maker bot loop"""
        self.running = True
        log("🚀 Maker Bot V1 starting... (PAPER MODE)")
        
        # Start data feeds
        feed_tasks = [
            asyncio.create_task(self.btc_feed.run()),
            asyncio.create_task(self.kalshi_poller.run()),
        ]
        if HAS_WEBSOCKET:
            feed_tasks.append(asyncio.create_task(self.kalshi_ws.run()))
        
        # Wait for initial data
        log("⏳ Waiting for market data...")
        for _ in range(30):  # Up to 30 seconds
            if self.kalshi_poller.current_market and self.btc_feed.price:
                break
            await asyncio.sleep(1)
        
        if not self.kalshi_poller.current_market:
            log("❌ Failed to get Kalshi market data after 30s", "ERROR")
            # Continue anyway — poller will keep trying
        
        if self.btc_feed.price:
            log(f"✅ BTC spot: ${self.btc_feed.price:.2f}")
        
        if self.kalshi_poller.current_market:
            m = self.kalshi_poller.current_market
            log(f"✅ Kalshi market: {m['ticker']} | YES bid/ask: ${m['yes_bid']:.2f}/${m['yes_ask']:.2f}")
            self.current_market_ticker = m['ticker']
        
        log("🏭 Main loop starting...")
        
        try:
            while self.running:
                try:
                    await self._tick()
                    await asyncio.sleep(1)  # 1-second tick
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    log(f"Tick error: {e}", "ERROR")
                    traceback.print_exc()
                    await asyncio.sleep(5)
        finally:
            # Cleanup
            self.btc_feed.running = False
            self.kalshi_poller.running = False
            self.kalshi_ws.running = False
            for t in feed_tasks:
                t.cancel()
            self.save_state()
            log(f"🛑 Maker Bot V1 stopped | PnL=${self.total_pnl:.2f} | Fills={len(self.fills)} | Spreads={self.spreads_captured}")
    
    async def _tick(self):
        """Single iteration of the main loop"""
        market = self.kalshi_poller.current_market
        if not market:
            return
        
        # Detect market transition (new 15min window)
        new_ticker = market.get('ticker')
        if (self.current_market_ticker and 
                new_ticker != self.current_market_ticker):
            log(f"🔄 Market transition: {self.current_market_ticker} → {new_ticker}")
            self.handle_market_settlement(self.current_market_ticker)
            self.current_market_ticker = new_ticker
        
        # Check for fills on existing quotes
        self.check_fills()
        
        # Calculate fair value
        fair_value = self.calculate_fair_value()
        if fair_value is None:
            return
        
        # Should we re-quote?
        if self.should_requote():
            self.place_quotes(fair_value)
        
        # Periodic status
        self.print_status()
        
        # Save state periodically (every 60 seconds)
        if time.time() - getattr(self, '_last_save', 0) > 60:
            self.save_state()
            self._last_save = time.time()
    
    async def shutdown(self):
        """Graceful shutdown"""
        log("⚠️ Shutdown requested...")
        self.running = False


# ─── Entry Point ─────────────────────────────────────────────────────────────

async def main():
    """Main entry point"""
    print("=" * 70, flush=True)
    print("  Maker Bot V1 — Paper Trading Market Maker", flush=True)
    print("  Kalshi BTC 15-Minute Markets", flush=True)
    print("  Strategy: Two-Sided Quoting (Market Making)", flush=True)
    print("=" * 70, flush=True)
    print(f"  Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", flush=True)
    print(f"  Mode: PAPER TRADING (no real orders)", flush=True)
    print("=" * 70, flush=True)
    
    # Parse config from environment / args
    config = DEFAULT_CONFIG.copy()
    
    # Allow override via env vars
    if os.getenv('MAKER_HALF_SPREAD'):
        config['half_spread'] = float(os.getenv('MAKER_HALF_SPREAD'))
    if os.getenv('MAKER_QUOTE_SIZE'):
        config['quote_size'] = int(os.getenv('MAKER_QUOTE_SIZE'))
    if os.getenv('MAKER_MAX_INVENTORY'):
        config['max_inventory'] = int(os.getenv('MAKER_MAX_INVENTORY'))
    
    bot = MakerBot(config)
    
    # Signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler(sig, frame):
        log(f"Received signal {sig}, shutting down...")
        asyncio.ensure_future(bot.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        log("Keyboard interrupt")
    finally:
        bot.save_state()
        log("Maker Bot V1 exited.")


if __name__ == '__main__':
    asyncio.run(main())
