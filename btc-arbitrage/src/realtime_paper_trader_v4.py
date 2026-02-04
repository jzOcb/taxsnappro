#!/usr/bin/env python3
"""
Real-time Paper Trader v4 - Major Strategy Overhaul
====================================================
Key Changes from v3:
1. BTC spot price direction filter (Binance API) — skip trades when BTC dropping
2. Polymarket daily trend filter — sentiment indicator from prediction market
3. Volatility-adaptive stop-loss (20-30%) — was 12% fixed, way too tight
4. Time window filters — avoid noisy first 30s and illiquid last 60s
5. Fair value estimation — only trade significant deviations (>15%)
6. Crash classification — distinguish liquidity vs informational crashes

Architecture: Same as v3 (WebSocket feeds + REST polling + paper trading)
"""
import asyncio, json, time, sys, os, traceback, signal, math
sys.path.insert(0, '/tmp/pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import websockets
from datetime import datetime, timezone
from urllib import request as urllib_request
from collections import deque


# =============================================================================
# BTC Price Feed (WebSocket from 4 exchanges + Binance REST for spot checks)
# =============================================================================
class BTCPriceFeed:
    def __init__(self):
        self.prices = {}
        self.timestamps = {}
        self.weighted_price = None
        self.price_history = deque(maxlen=1000)  # ~16 min at 1/sec
        self.weights = {'coinbase': 0.35, 'kraken': 0.25, 'bitstamp': 0.20, 'binance_us': 0.20}
        self.reconnect_delays = {}
        self.running = True
        # Binance spot price (separate from US WebSocket)
        self.binance_spot = None
        self.binance_spot_history = deque(maxlen=300)  # 5 min at 1/sec
        self.binance_spot_time = 0

    def get_weighted(self):
        if not self.prices:
            return None
        total_w = w_sum = 0
        for ex, p in self.prices.items():
            w = self.weights.get(ex, 0.1)
            w_sum += p * w
            total_w += w
        return w_sum / total_w if total_w > 0 else None

    def _update(self, exchange, price):
        self.prices[exchange] = price
        self.timestamps[exchange] = time.time()
        self.weighted_price = self.get_weighted()
        if self.weighted_price:
            self.price_history.append({'time': time.time(), 'price': self.weighted_price})
        self.reconnect_delays[exchange] = 1

    def get_momentum(self, lookback_sec=60):
        """BTC price change % over lookback period"""
        if len(self.price_history) < 2:
            return None
        cutoff = time.time() - lookback_sec
        old = next((e['price'] for e in self.price_history if e['time'] >= cutoff), None)
        return ((self.weighted_price - old) / old) * 100 if old and self.weighted_price else None

    def get_btc_trend_2min(self):
        """Get BTC price change over last 2 minutes — for crash classification"""
        return self.get_momentum(120)

    def get_btc_trend_5min(self):
        """Get BTC price change over last 5 minutes"""
        return self.get_momentum(300)

    def get_volatility(self, lookback_sec=300):
        """BTC price volatility (coefficient of variation) over lookback"""
        if len(self.price_history) < 10:
            return 0.01
        cutoff = time.time() - lookback_sec
        prices = [e['price'] for e in self.price_history if e['time'] >= cutoff]
        if len(prices) < 10:
            return 0.01
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std = math.sqrt(variance)
        return std / mean if mean > 0 else 0.01

    def is_btc_dropping(self, threshold_pct=-0.1, window_sec=120):
        """Check if BTC has dropped more than threshold in window — primary crash filter"""
        momentum = self.get_momentum(window_sec)
        if momentum is None:
            return False, 0.0
        return momentum < threshold_pct, momentum

    async def _fetch_binance_spot(self):
        """Periodically fetch BTC spot from Binance global API (not US)"""
        while self.running:
            try:
                def _do_fetch():
                    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
                    req = urllib_request.Request(url)
                    req.add_header('User-Agent', 'Mozilla/5.0')
                    with urllib_request.urlopen(req, timeout=3) as r:
                        data = json.loads(r.read())
                    return float(data['price'])

                price = await asyncio.get_event_loop().run_in_executor(None, _do_fetch)
                self.binance_spot = price
                self.binance_spot_time = time.time()
                self.binance_spot_history.append({'time': time.time(), 'price': price})
            except Exception:
                pass
            await asyncio.sleep(5)  # poll every 5s

    async def _reconnect_backoff(self, exchange):
        delay = self.reconnect_delays.get(exchange, 1)
        await asyncio.sleep(min(delay, 60))
        self.reconnect_delays[exchange] = min(delay * 2, 60)

    async def _coinbase(self):
        self.reconnect_delays['coinbase'] = 1
        while self.running:
            try:
                async with websockets.connect("wss://ws-feed.exchange.coinbase.com", ping_interval=20) as ws:
                    await ws.send(json.dumps({"type": "subscribe", "channels": [{"name": "ticker", "product_ids": ["BTC-USD"]}]}))
                    async for msg in ws:
                        if not self.running:
                            break
                        d = json.loads(msg)
                        if d.get('type') == 'ticker' and 'price' in d:
                            self._update('coinbase', float(d['price']))
            except Exception as e:
                if self.running:
                    print(f"[Coinbase] {e}", flush=True)
                    await self._reconnect_backoff('coinbase')

    async def _kraken(self):
        self.reconnect_delays['kraken'] = 1
        while self.running:
            try:
                async with websockets.connect("wss://ws.kraken.com", ping_interval=20) as ws:
                    await ws.send(json.dumps({"event": "subscribe", "pair": ["XBT/USD"], "subscription": {"name": "ticker"}}))
                    async for msg in ws:
                        if not self.running:
                            break
                        d = json.loads(msg)
                        if isinstance(d, list) and len(d) >= 4 and isinstance(d[1], dict) and 'c' in d[1]:
                            self._update('kraken', float(d[1]['c'][0]))
            except Exception as e:
                if self.running:
                    print(f"[Kraken] {e}", flush=True)
                    await self._reconnect_backoff('kraken')

    async def _bitstamp(self):
        self.reconnect_delays['bitstamp'] = 1
        while self.running:
            try:
                async with websockets.connect("wss://ws.bitstamp.net", ping_interval=20) as ws:
                    await ws.send(json.dumps({"event": "bts:subscribe", "data": {"channel": "live_trades_btcusd"}}))
                    async for msg in ws:
                        if not self.running:
                            break
                        d = json.loads(msg)
                        if d.get('event') == 'trade' and 'price' in d.get('data', {}):
                            self._update('bitstamp', float(d['data']['price']))
            except Exception as e:
                if self.running:
                    print(f"[Bitstamp] {e}", flush=True)
                    await self._reconnect_backoff('bitstamp')

    async def _binance(self):
        self.reconnect_delays['binance_us'] = 1
        while self.running:
            try:
                async with websockets.connect("wss://stream.binance.us:9443/ws/btcusdt@ticker", ping_interval=20) as ws:
                    async for msg in ws:
                        if not self.running:
                            break
                        d = json.loads(msg)
                        if 'c' in d:
                            self._update('binance_us', float(d['c']))
            except Exception as e:
                if self.running:
                    print(f"[Binance] {e}", flush=True)
                    await self._reconnect_backoff('binance_us')

    async def run(self):
        tasks = [
            asyncio.create_task(self._coinbase()),
            asyncio.create_task(self._kraken()),
            asyncio.create_task(self._bitstamp()),
            asyncio.create_task(self._binance()),
            asyncio.create_task(self._fetch_binance_spot()),
        ]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.running = False
            for task in tasks:
                task.cancel()


# =============================================================================
# Polymarket Sentiment Feed
# =============================================================================
class PolymarketSentiment:
    """
    Fetches Polymarket "Bitcoin above X" daily markets for sentiment.
    If the closest-strike YES price is dropping, it's a bearish signal.
    """
    def __init__(self, poll_interval=60):
        self.poll_interval = poll_interval
        self.running = True
        self.markets = []  # list of {question, strike, yes_price, ...}
        self.closest_market = None
        self.sentiment_history = deque(maxlen=60)  # 1 hour at 1/min
        self.last_fetch_time = 0
        self.bearish = False  # overall sentiment signal

    def _fetch_markets(self):
        """Fetch Bitcoin price markets from Polymarket gamma API"""
        try:
            url = "https://gamma-api.polymarket.com/markets?tag=crypto&closed=false&limit=50"
            req = urllib_request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Accept', 'application/json')
            with urllib_request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())

            btc_markets = []
            for m in data if isinstance(data, list) else data.get('data', data.get('markets', [])):
                q = m.get('question', '').lower()
                # Look for "bitcoin above" or "btc above" style markets
                if ('bitcoin' in q or 'btc' in q) and ('above' in q or 'over' in q or 'price' in q):
                    # Try to extract strike price
                    strike = self._extract_strike(q)
                    if strike:
                        # Get YES price from outcomes
                        yes_price = None
                        outcomes = m.get('outcomePrices', m.get('outcomes', []))
                        if isinstance(outcomes, str):
                            try:
                                outcomes = json.loads(outcomes)
                            except:
                                outcomes = []
                        if isinstance(outcomes, list) and len(outcomes) > 0:
                            try:
                                yes_price = float(outcomes[0])
                            except (ValueError, TypeError):
                                pass
                        if yes_price is None:
                            yes_price = m.get('bestBid', m.get('lastTradePrice'))
                            if yes_price:
                                yes_price = float(yes_price)

                        if yes_price and 0 < yes_price < 1:
                            btc_markets.append({
                                'question': m.get('question', ''),
                                'strike': strike,
                                'yes_price': yes_price,
                                'id': m.get('id', ''),
                                'time': time.time()
                            })

            return btc_markets
        except Exception as e:
            return []

    def _extract_strike(self, question):
        """Extract dollar strike from question like 'Bitcoin above $100,000?'"""
        import re
        # Match patterns like $100,000 or $100000 or 100k or 100,000
        patterns = [
            r'\$?([\d,]+(?:\.\d+)?)\s*[kK]',  # 100k
            r'\$([\d,]+(?:\.\d+)?)',  # $100,000
            r'([\d,]+)\s*(?:dollars|usd)',  # 100000 dollars
        ]
        for pat in patterns:
            match = re.search(pat, question)
            if match:
                val = match.group(1).replace(',', '')
                try:
                    num = float(val)
                    if 'k' in question.lower() and num < 1000:
                        num *= 1000
                    if num > 10000:  # reasonable BTC strike
                        return num
                except:
                    pass
        return None

    def update_sentiment(self, current_btc_price):
        """Find closest strike to current BTC and update sentiment"""
        if not self.markets or not current_btc_price:
            return

        # Find closest strike
        closest = min(self.markets, key=lambda m: abs(m['strike'] - current_btc_price))
        self.closest_market = closest

        self.sentiment_history.append({
            'time': time.time(),
            'yes_price': closest['yes_price'],
            'strike': closest['strike']
        })

        # Check if sentiment is dropping (bearish)
        if len(self.sentiment_history) >= 3:
            recent = list(self.sentiment_history)[-3:]
            price_trend = recent[-1]['yes_price'] - recent[0]['yes_price']
            self.bearish = price_trend < -0.02  # YES dropping by >2% = bearish

    async def run(self):
        try:
            while self.running:
                markets = await asyncio.get_event_loop().run_in_executor(None, self._fetch_markets)
                if markets:
                    self.markets = markets
                    self.last_fetch_time = time.time()
                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            self.running = False


# =============================================================================
# Kalshi Market Poller
# =============================================================================
class KalshiPoller:
    def __init__(self, interval=5):
        self.interval = interval
        self.latest = None
        self.history = deque(maxlen=200)
        self.last_ticker = None
        self.running = True
        # Track window open price for fair value
        self.window_open_brti = None
        self.window_ticker = None

    def is_market_transition(self):
        if self.latest and self.last_ticker and self.latest['ticker'] != self.last_ticker:
            return True
        return False

    def time_until_close(self):
        """Seconds until current market closes"""
        if not self.latest or not self.latest.get('close_time'):
            return 999
        try:
            close_str = self.latest['close_time']
            close = datetime.fromisoformat(close_str.replace('Z', '+00:00'))
            return close.timestamp() - time.time()
        except:
            return 999

    def seconds_since_open(self):
        """Seconds since current 15-min window opened"""
        remaining = self.time_until_close()
        if remaining > 900:
            return 0  # shouldn't happen for 15-min markets
        return 900 - remaining

    def get_k_volatility(self, lookback=20):
        """Calculate K-value std dev over recent history"""
        prices = [m['yes_bid'] for m in list(self.history)[-lookback:] if m.get('yes_bid', 0) > 0]
        if len(prices) < 5:
            return 0.05
        mean = sum(prices) / len(prices)
        if mean == 0:
            return 0.05
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return math.sqrt(variance)

    def _fetch(self):
        url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=10&series_ticker=KXBTC15M&status=open"
        req = urllib_request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')
        try:
            with urllib_request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read())
            if data.get('markets'):
                m = data['markets'][0]
                return {
                    'ticker': m['ticker'],
                    'yes_bid': m.get('yes_bid', 0) / 100,
                    'yes_ask': m.get('yes_ask', 0) / 100,
                    'volume': m.get('volume', 0),
                    'close_time': m.get('close_time'),
                    'open_time': m.get('open_time'),
                    'time': time.time(),
                }
        except Exception as e:
            print(f"[Kalshi] {e}", flush=True)
        return None

    async def run(self):
        try:
            while self.running:
                market = await asyncio.get_event_loop().run_in_executor(None, self._fetch)
                if market:
                    self.last_ticker = self.latest['ticker'] if self.latest else None
                    self.latest = market
                    self.history.append(market)
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            self.running = False


# =============================================================================
# Paper Trader
# =============================================================================
class PaperTrader:
    def __init__(self, balance=1000, trade_size=10):
        self.balance = balance
        self.initial = balance
        self.trade_size = trade_size
        self.positions = []
        self.trades = []
        self.pnl = 0
        self.last_exit_time = 0

    def open(self, direction, price, ticker, strategy, metadata=None):
        cost = self.trade_size * price
        if cost > self.balance:
            return None
        pos = {
            'id': len(self.positions), 'dir': direction, 'size': self.trade_size,
            'entry': price, 'time': time.time(), 'ticker': ticker, 'open': True,
            'strategy': strategy, 'metadata': metadata or {}
        }
        self.positions.append(pos)
        self.balance -= cost
        return pos['id']

    def close(self, pos_id, exit_price):
        pos = next((p for p in self.positions if p['id'] == pos_id and p['open']), None)
        if not pos:
            return None
        pnl = (exit_price - pos['entry']) * pos['size']
        if pos['dir'] == 'NO':
            pnl = -pnl
        pos['exit'] = exit_price
        pos['pnl'] = pnl
        pos['open'] = False
        pos['close_time'] = time.time()
        self.balance += pos['size'] * exit_price
        self.pnl += pnl
        self.trades.append(pos.copy())
        self.last_exit_time = time.time()
        return pnl

    def get_open(self):
        return [p for p in self.positions if p['open']]

    def to_dict(self):
        return {
            'balance': self.balance, 'initial': self.initial, 'pnl': self.pnl,
            'positions': self.positions, 'trades': self.trades
        }


# =============================================================================
# Trading Engine v4 — The Brain
# =============================================================================
class TradingEngine:
    def __init__(self, feed, poller, polymarket, duration_min=480):
        self.feed = feed
        self.poller = poller
        self.polymarket = polymarket
        self.trader = PaperTrader()
        self.duration = duration_min * 60
        self.start_time = None
        self.signals = []
        self.skipped_signals = []  # track filtered-out trades
        self.log_files = []
        self.last_market_ticker = None
        self.state_file = '/home/clawdbot/clawd/btc-arbitrage/data/rt_v4_state.json'
        self.graceful_shutdown = False
        # Track window open BTC price for fair value
        self.window_open_brti = None
        self.window_ticker = None
        # Last K bid for crash detection
        self.last_kalshi_bid = None

    def _dual_log(self, msg):
        for f in self.log_files:
            if f and not f.closed:
                f.write(f"{datetime.now().isoformat()} {msg}\n")
                f.flush()
        print(msg, flush=True)

    def _save_checkpoint(self):
        try:
            elapsed = int(time.time() - self.start_time)
            state = {
                'version': 'v4',
                'elapsed_sec': elapsed,
                'start_time': self.start_time,
                'trader': self.trader.to_dict(),
                'signals': self.signals,
                'skipped': len(self.skipped_signals),
                'last_checkpoint': time.time()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            self._dual_log(f"[{elapsed:5d}s] 💾 Checkpoint saved (skipped: {len(self.skipped_signals)})")
        except Exception as e:
            self._dual_log(f"⚠️ Checkpoint failed: {e}")

    async def _checkpoint_loop(self):
        while not self.graceful_shutdown:
            await asyncio.sleep(300)
            self._save_checkpoint()

    def _setup_signal_handlers(self):
        def handler(signum, frame):
            self._dual_log("\n⚠️ Shutdown signal received, saving state...")
            self.graceful_shutdown = True
            self._summary()
            sys.exit(0)
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    # =========================================================================
    # FEATURE 4: Time Window Filters
    # =========================================================================
    def _check_time_window(self, elapsed):
        """
        Don't enter in first 30s (noisy price discovery) or last 60s (low liquidity).
        Only trade when >5 min remaining.
        Returns (allowed, reason)
        """
        time_remaining = self.poller.time_until_close()
        seconds_since = self.poller.seconds_since_open()

        if seconds_since < 30:
            return False, f"first_30s (opened {seconds_since:.0f}s ago)"
        if time_remaining < 60:
            return False, f"last_60s ({time_remaining:.0f}s left)"
        if time_remaining < 300:
            return False, f"<5min_remaining ({time_remaining:.0f}s left)"
        return True, "ok"

    # =========================================================================
    # FEATURE 5: Fair Value Estimation
    # =========================================================================
    def _estimate_fair_value(self, brti_price, time_remaining):
        """
        Estimate K fair value based on:
        - Current BTC vs window open price
        - Time remaining in window
        - Historical volatility
        
        Simple model: K(YES) ≈ probability that BRTI stays above the open at settlement.
        If BTC is above open → K should be > 0.50
        If BTC is below open → K should be < 0.50
        """
        if not self.window_open_brti or self.window_open_brti == 0:
            return 0.50  # no data, assume 50/50

        # Direction: how far above/below window open
        pct_from_open = (brti_price - self.window_open_brti) / self.window_open_brti * 100

        # Time factor: more time = more uncertainty = closer to 0.50
        # Less time = more binary (converges to 0 or 1)
        if time_remaining > 600:
            time_factor = 0.3  # 10+ min: mild directional tilt
        elif time_remaining > 300:
            time_factor = 0.6  # 5-10 min: moderate tilt
        else:
            time_factor = 1.0  # <5 min: strong tilt toward outcome

        # Volatility factor: higher vol = more uncertainty
        btc_vol = self.feed.get_volatility(300)
        vol_dampener = max(0.5, 1.0 - btc_vol * 50)  # high vol → less confident

        # Fair value estimate
        # pct_from_open of 0.1% ≈ 5% K shift when time_factor=1
        directional_shift = pct_from_open * 50 * time_factor * vol_dampener
        fair = 0.50 + directional_shift / 100

        # Clamp to [0.05, 0.95]
        fair = max(0.05, min(0.95, fair))
        return fair

    # =========================================================================
    # FEATURE 6: Crash Classification
    # =========================================================================
    def _classify_crash(self, kalshi_drop_pct, btc_2min_momentum):
        """
        Classify a K-value crash:
        - "liquidity"     = K drops but BTC stable → BUY (will recover)
        - "informational" = K drops AND BTC dropping → SKIP
        - "delayed"       = BTC moved but K hasn't caught up fully → BUY cautiously
        """
        if btc_2min_momentum is None:
            return "unknown", "no BTC data"

        btc_stable = abs(btc_2min_momentum) < 0.1  # <0.1% move in 2 min
        btc_dropping = btc_2min_momentum < -0.1     # >0.1% drop in 2 min
        btc_rising = btc_2min_momentum > 0.1

        if kalshi_drop_pct < -25:
            if btc_stable or btc_rising:
                return "liquidity", f"K crashed {kalshi_drop_pct:.1f}% but BTC {btc_2min_momentum:+.3f}% (stable/up)"
            elif btc_dropping:
                return "informational", f"K crashed {kalshi_drop_pct:.1f}% AND BTC {btc_2min_momentum:+.3f}% (both dropping)"
            else:
                return "ambiguous", f"K crashed {kalshi_drop_pct:.1f}%, BTC {btc_2min_momentum:+.3f}%"

        # Not a crash, but check for delay opportunity
        if abs(kalshi_drop_pct) < 5 and abs(btc_2min_momentum) > 0.15:
            return "delayed", f"BTC moved {btc_2min_momentum:+.3f}% but K only {kalshi_drop_pct:+.1f}%"

        return "none", "no crash detected"

    # =========================================================================
    # FEATURE 3: Volatility-Adaptive Stop-Loss
    # =========================================================================
    def _get_adaptive_stop(self):
        """
        Stop-loss based on recent K variance.
        High vol → wider stop (30%), low vol → tighter stop (20%).
        NEVER tighter than 20% (was 12% in v3, way too tight).
        """
        k_vol = self.poller.get_k_volatility(lookback=20)  # last ~100 seconds
        btc_vol = self.feed.get_volatility(300)

        # Base: 25%
        # K vol of 0.05 → normal, 0.10 → high
        vol_score = k_vol * 5 + btc_vol * 100  # combined vol metric
        adaptive_stop = 0.20 + vol_score * 0.05

        # Clamp to [20%, 30%] — NEVER below 20%
        adaptive_stop = max(0.20, min(0.30, adaptive_stop))
        return adaptive_stop

    # =========================================================================
    # FEATURE 1 & 2: BTC Direction + Polymarket Filters
    # =========================================================================
    def _apply_entry_filters(self, direction, entry_price, kalshi, elapsed, crash_type=None):
        """
        Apply all entry filters. Returns (allowed, reason).
        """
        # FILTER 1: BTC spot price direction
        btc_dropping, btc_2min = self.feed.is_btc_dropping(threshold_pct=-0.1, window_sec=120)
        if direction == 'YES' and btc_dropping:
            reason = f"BTC dropping {btc_2min:+.3f}% in 2min"
            self._dual_log(f"[{elapsed:5d}s] [FILTER] Skipped: {reason}")
            self.skipped_signals.append({'type': 'btc_dropping', 'time': elapsed, 'btc_2min': btc_2min})
            return False, reason

        # Also check: if buying NO and BTC is rising sharply, skip
        if direction == 'NO':
            btc_rising = btc_2min is not None and btc_2min > 0.1
            if btc_rising:
                reason = f"BTC rising {btc_2min:+.3f}% in 2min (NO trade blocked)"
                self._dual_log(f"[{elapsed:5d}s] [FILTER] Skipped: {reason}")
                self.skipped_signals.append({'type': 'btc_rising_no_block', 'time': elapsed})
                return False, reason

        # FILTER 2: Polymarket sentiment
        if self.polymarket.bearish and self.polymarket.closest_market:
            pm_yes = self.polymarket.closest_market.get('yes_price', 0)
            if direction == 'YES' and entry_price > 0.40:
                # Bearish day + buying expensive YES = risky
                reason = f"Polymarket bearish (YES@{pm_yes:.2f}), raising threshold"
                self._dual_log(f"[{elapsed:5d}s] [FILTER] Skipped: {reason}")
                self.skipped_signals.append({'type': 'polymarket_bearish', 'time': elapsed})
                return False, reason

        # FILTER: Spread too wide
        spread = kalshi['yes_ask'] - kalshi['yes_bid']
        if spread > 0.05:
            return False, f"spread too wide ({spread:.2f})"

        # FILTER: Volume too low
        if kalshi.get('volume', 0) < 50:
            return False, f"volume too low ({kalshi.get('volume', 0)})"

        # FILTER: Cooldown — no entry within 60s of last exit
        if time.time() - self.trader.last_exit_time < 60:
            return False, "cooldown period"

        # FILTER 5: Fair value — only trade when K deviates >15% from fair value
        brti = self.feed.weighted_price
        time_remaining = self.poller.time_until_close()
        fair_value = self._estimate_fair_value(brti, time_remaining)

        if direction == 'YES':
            deviation = fair_value - entry_price  # positive = K is cheap
        else:
            deviation = entry_price - (1 - fair_value)  # positive = NO is cheap

        if deviation < 0.15 and crash_type != 'liquidity':
            # Not enough edge, and not a liquidity crash
            return False, f"insufficient edge (dev={deviation:+.3f}, fair={fair_value:.2f})"

        return True, f"passed (fair={fair_value:.2f}, dev={deviation:+.3f})"

    # =========================================================================
    # Main Trading Loop
    # =========================================================================
    async def run(self):
        try:
            self.start_time = time.time()
            end_time = self.start_time + self.duration
            os.makedirs('/home/clawdbot/clawd/btc-arbitrage/logs', exist_ok=True)
            os.makedirs('/home/clawdbot/clawd/btc-arbitrage/data', exist_ok=True)

            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_ts = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_v4_{ts}.log', 'w')
            log_live = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_v4_live.log', 'w')
            self.log_files = [log_live, log_ts]

            self._setup_signal_handlers()

            header = (
                f"\n{'='*70}\n"
                f"REAL-TIME PAPER TRADING v4 — Major Strategy Overhaul\n"
                f"{'='*70}\n"
                f"Duration: {self.duration//60}min | Start: {datetime.now().strftime('%H:%M:%S UTC')}\n"
                f"NEW: BTC direction filter, Polymarket sentiment, adaptive stop (20-30%),\n"
                f"     time window filters, fair value estimation, crash classification\n"
                f"Strategies: Delay Arb + Classified Flash Crash + Mean Reversion\n"
                f"{'='*70}\n"
            )
            self._dual_log(header)

            checkpoint_task = asyncio.create_task(self._checkpoint_loop())
            last_status = time.time()

            while time.time() < end_time and not self.graceful_shutdown:
                await asyncio.sleep(1)
                brti = self.feed.weighted_price
                kalshi = self.poller.latest
                if not brti or not kalshi:
                    continue

                elapsed = int(time.time() - self.start_time)
                momentum_1m = self.feed.get_momentum(60)
                btc_2min = self.feed.get_btc_trend_2min()

                # Update Polymarket sentiment with current BTC price
                self.polymarket.update_sentiment(brti)

                # --- Detect market transition ---
                if self.poller.is_market_transition():
                    self._dual_log(f"[{elapsed:5d}s] 🔄 Market transition: {self.last_market_ticker} → {kalshi['ticker']}")
                    self.last_market_ticker = kalshi['ticker']
                    self.last_kalshi_bid = None
                    self.window_open_brti = brti  # record window open price
                    self.window_ticker = kalshi['ticker']
                    continue

                # Track window open price
                if self.window_ticker != kalshi['ticker']:
                    self.window_open_brti = brti
                    self.window_ticker = kalshi['ticker']
                self.last_market_ticker = kalshi['ticker']

                # --- FEATURE 4: Time window filter ---
                time_ok, time_reason = self._check_time_window(elapsed)
                if not time_ok:
                    # Still manage positions, just don't open new ones
                    self._manage_positions(kalshi, elapsed)
                    self.last_kalshi_bid = kalshi['yes_bid']
                    continue

                # --- Skip if already have open position ---
                if len(self.trader.get_open()) > 0:
                    self._manage_positions(kalshi, elapsed)
                    self.last_kalshi_bid = kalshi['yes_bid']
                    # Status updates
                    if time.time() - last_status > 60:
                        self._log_status(elapsed, brti, kalshi, momentum_1m)
                        last_status = time.time()
                    continue

                k_bid = kalshi['yes_bid']
                k_ask = kalshi['yes_ask']

                # --- STRATEGY A: Classified Flash Crash ---
                if self.last_kalshi_bid and self.last_kalshi_bid > 0.15:
                    kalshi_drop = (k_bid - self.last_kalshi_bid) / self.last_kalshi_bid * 100

                    if kalshi_drop < -25 and not self.poller.is_market_transition():
                        # FEATURE 6: Classify the crash
                        crash_type, crash_reason = self._classify_crash(kalshi_drop, btc_2min)
                        self._dual_log(f"[{elapsed:5d}s] 🔍 CRASH DETECTED: {crash_type.upper()} — {crash_reason}")

                        if crash_type == "liquidity":
                            # Recoverable — BUY YES
                            entry = k_ask
                            if 0.10 < entry < 0.85:
                                allowed, filter_reason = self._apply_entry_filters('YES', entry, kalshi, elapsed, crash_type)
                                if allowed:
                                    pos_id = self.trader.open('YES', entry, kalshi['ticker'], 'flash_liquidity',
                                                              {'crash_type': crash_type, 'btc_2min': btc_2min})
                                    if pos_id is not None:
                                        self._dual_log(f"[{elapsed:5d}s] ⚡ LIQUIDITY CRASH → YES @ ${entry:.2f} | {filter_reason}")
                                        self.signals.append({'type': 'flash_liquidity', 'time': elapsed, 'crash': crash_reason})

                        elif crash_type == "informational":
                            self._dual_log(f"[{elapsed:5d}s] [FILTER] Skipped flash crash: INFORMATIONAL (BTC also dropping)")
                            self.skipped_signals.append({'type': 'informational_crash', 'time': elapsed, 'btc_2min': btc_2min})

                        elif crash_type == "delayed":
                            # BTC moved but K hasn't → buy cautiously (in BTC direction)
                            if btc_2min and btc_2min > 0.15:
                                entry = k_ask
                                if 0.10 < entry < 0.85:
                                    allowed, filter_reason = self._apply_entry_filters('YES', entry, kalshi, elapsed)
                                    if allowed:
                                        pos_id = self.trader.open('YES', entry, kalshi['ticker'], 'delayed_reaction',
                                                                  {'btc_2min': btc_2min})
                                        if pos_id is not None:
                                            self._dual_log(f"[{elapsed:5d}s] ⏱️ DELAYED REACTION → YES @ ${entry:.2f} (cautious)")
                                            self.signals.append({'type': 'delayed_reaction', 'time': elapsed})

                # --- STRATEGY B: Delay Arbitrage (BTC momentum vs K lag) ---
                if momentum_1m is not None and self.last_kalshi_bid is not None and self.last_kalshi_bid > 0.01:
                    kalshi_chg = ((k_bid - self.last_kalshi_bid) / self.last_kalshi_bid * 100)

                    if abs(momentum_1m) > 0.15 and abs(kalshi_chg) < 5 and len(self.trader.get_open()) == 0:
                        direction = 'YES' if momentum_1m > 0 else 'NO'
                        entry = k_ask if direction == 'YES' else (1 - k_bid)

                        if 0.05 < entry < 0.95:
                            allowed, filter_reason = self._apply_entry_filters(direction, entry, kalshi, elapsed)
                            if allowed:
                                pos_id = self.trader.open(direction, entry, kalshi['ticker'], 'delay_arb',
                                                          {'momentum_1m': momentum_1m, 'kalshi_chg': kalshi_chg})
                                if pos_id is not None:
                                    self._dual_log(f"[{elapsed:5d}s] 🎯 DELAY: BTC {momentum_1m:+.3f}% K {kalshi_chg:+.1f}% → {direction} @ ${entry:.2f} | {filter_reason}")
                                    self.signals.append({'type': 'delay', 'time': elapsed, 'direction': direction})

                # --- Manage open positions ---
                self._manage_positions(kalshi, elapsed)

                # --- Status ---
                if time.time() - last_status > 60:
                    self._log_status(elapsed, brti, kalshi, momentum_1m)
                    last_status = time.time()

                self.last_kalshi_bid = kalshi['yes_bid']

            checkpoint_task.cancel()
            self._summary()

        except Exception as e:
            err = f"\n❌ FATAL: {e}\n{traceback.format_exc()}"
            self._dual_log(err)
            self._save_checkpoint()
            self._summary()

    def _manage_positions(self, kalshi, elapsed):
        """Position management with adaptive stop-loss"""
        for pos in self.trader.get_open():
            hold_time = time.time() - pos['time']
            current = kalshi['yes_bid'] if pos['dir'] == 'YES' else (1 - kalshi['yes_ask'])
            unrealized = (current - pos['entry']) * pos['size']
            if pos['dir'] == 'NO':
                unrealized = -unrealized
            pct = (unrealized / (pos['entry'] * pos['size'])) * 100 if pos['entry'] > 0 else 0

            # FEATURE 3: Adaptive stop-loss
            stop_pct = self._get_adaptive_stop() * 100  # e.g. 25%

            should_close = False
            reason = ""
            if pct > 8:
                should_close, reason = True, "PROFIT"
            elif pct < -stop_pct:
                should_close, reason = True, f"STOP(-{stop_pct:.0f}%)"
            elif hold_time > 360:
                should_close, reason = True, "TIMEOUT"

            if should_close:
                pnl = self.trader.close(pos['id'], current)
                status = "WIN" if pnl > 0 else "LOSS"
                strategy = pos.get('strategy', '?')
                self._dual_log(
                    f"[{elapsed:5d}s] {'✅' if pnl>0 else '❌'} CLOSE ({reason}) [{strategy}]: "
                    f"${pnl:+.2f} | Total: ${self.trader.pnl:+.2f}"
                )

    def _log_status(self, elapsed, brti, kalshi, momentum_1m):
        n_ex = len(self.feed.prices)
        mom_str = f"{momentum_1m:+.3f}%" if momentum_1m else "N/A"
        fair = self._estimate_fair_value(brti, self.poller.time_until_close())
        k_vol = self.poller.get_k_volatility()
        stop = self._get_adaptive_stop() * 100
        pm_str = "bearish" if self.polymarket.bearish else "neutral"
        if self.polymarket.closest_market:
            pm_str += f" (${self.polymarket.closest_market['strike']:,.0f} YES@{self.polymarket.closest_market['yes_price']:.2f})"

        time_left = self.poller.time_until_close()
        st = (
            f"[{elapsed:5d}s] BTC: ${brti:,.2f} ({n_ex}ex, {mom_str}) | "
            f"K: {kalshi['yes_bid']:.2f}/{kalshi['yes_ask']:.2f} (fair:{fair:.2f}) | "
            f"Stop: {stop:.0f}% | PM: {pm_str} | "
            f"Window: {time_left:.0f}s left | "
            f"P&L: ${self.trader.pnl:+.2f} ({len(self.trader.trades)}t, {len(self.skipped_signals)}skip)"
        )
        self._dual_log(st)

    def _summary(self):
        elapsed = int(time.time() - self.start_time) if self.start_time else 0
        summary = (
            f"\n{'='*70}\n"
            f"SUMMARY — Paper Trader v4\n"
            f"{'='*70}\n"
            f"Duration: {elapsed//60}min | Signals: {len(self.signals)} | Skipped: {len(self.skipped_signals)}\n"
            f"Trades: {len(self.trader.trades)} | P&L: ${self.trader.pnl:+.2f}\n"
        )

        if self.trader.trades:
            wins = [t for t in self.trader.trades if t['pnl'] > 0]
            summary += f"Win Rate: {len(wins)}/{len(self.trader.trades)} ({len(wins)/len(self.trader.trades)*100:.1f}%)\n"

        # Strategy breakdown
        strategies = {}
        for t in self.trader.trades:
            s = t.get('strategy', 'unknown')
            if s not in strategies:
                strategies[s] = {'count': 0, 'wins': 0, 'pnl': 0}
            strategies[s]['count'] += 1
            if t['pnl'] > 0:
                strategies[s]['wins'] += 1
            strategies[s]['pnl'] += t['pnl']

        if strategies:
            summary += "\nStrategy Breakdown:\n"
            for s, stats in strategies.items():
                wr = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
                summary += f"  {s}: {stats['count']} trades, {wr:.0f}% win, ${stats['pnl']:+.2f}\n"

        # Skip breakdown
        skip_types = {}
        for s in self.skipped_signals:
            t = s.get('type', 'unknown')
            skip_types[t] = skip_types.get(t, 0) + 1
        if skip_types:
            summary += "\nFiltered Out:\n"
            for t, c in sorted(skip_types.items(), key=lambda x: -x[1]):
                summary += f"  {t}: {c}\n"

        summary += f"{'='*70}\n"
        self._dual_log(summary)

        # Save final results
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'/home/clawdbot/clawd/btc-arbitrage/data/rt_v4_{ts}.json', 'w') as f:
            json.dump({
                'version': 'v4',
                'duration_min': elapsed // 60,
                'pnl': self.trader.pnl,
                'signals': self.signals,
                'skipped_signals': self.skipped_signals,
                'trades': self.trader.trades,
                'complete': not self.graceful_shutdown
            }, f, indent=2, default=str)

        for f in self.log_files:
            if f and not f.closed:
                f.close()


# =============================================================================
# Main
# =============================================================================
async def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 480

    feed = BTCPriceFeed()
    poller = KalshiPoller(interval=5)
    polymarket = PolymarketSentiment(poll_interval=60)
    engine = TradingEngine(feed, poller, polymarket, duration_min=duration)

    feed_task = asyncio.create_task(feed.run())
    poller_task = asyncio.create_task(poller.run())
    poly_task = asyncio.create_task(polymarket.run())

    try:
        await engine.run()
    finally:
        feed.running = False
        poller.running = False
        polymarket.running = False
        feed_task.cancel()
        poller_task.cancel()
        poly_task.cancel()
        try:
            await asyncio.gather(feed_task, poller_task, poly_task, return_exceptions=True)
        except:
            pass
        print("✅ All tasks stopped", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Keyboard interrupt", flush=True)
    except Exception as e:
        print(f"\n❌ Fatal: {e}\n{traceback.format_exc()}", flush=True)
