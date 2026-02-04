#!/usr/bin/env python3
"""
Real-time Paper Trader v9 — Corrected Best-of-Breed

V8 had the right strategy selection but WRONG risk parameters.
V8 used V7's loose risk params (5s cooldown, 5 pos/mkt) which destroyed performance.

V9 FIX: Use V6's DISCIPLINE parameters with the best strategies.

What went wrong in V8 (2.7h data):
  - V6 MR High: 12 trades, 100% WR, +$3.07 (60s cooldown, 1 pos max)
  - V8 MR High: 148 trades, 3% WR, -$25.86 (5s cooldown, 5 pos max)  
  Same strategy, different discipline = opposite results.

Strategy Selection (same as V8):
  ✅ MR High — V6 params (K > 0.80, momentum < 0.05, buy NO)
  ✅ Delay Arb — V6 entry logic + V7 sustained momentum filter
  ❌ MR Low (27% WR — structurally losing)

Risk Management: V6 DISCIPLINE parameters (the key difference)
  - 60s global cooldown (not 5s)
  - 1 position per market type (not 5)
  - 1 position per ticker (same)
  - 360s hold timeout (not 180s — V6's longer hold captured more profit)
  - V6's adaptive stop-loss (15-40% based on volatility)
"""
import asyncio, json, time, sys, os, traceback, signal, math
sys.path.insert(0, '/tmp/pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import websockets
from datetime import datetime
from urllib import request
from collections import deque
try:
    from orderbook_executor import get_real_entry_price, get_real_exit_price
    HAS_ORDERBOOK = True
except ImportError:
    HAS_ORDERBOOK = False

# ═══════════════════════════════════════════════════════
#  TUNABLE PARAMETERS — V8 Best-of-Breed
# ═══════════════════════════════════════════════════════
TRADE_SIZE = 10              # $10 per trade
COOLDOWN_SEC = 60            # 60s GLOBAL cooldown (V6! V8's 5s = machine gun = 3% WR)
MAX_POSITIONS_PER_MARKET = 1 # 1 position per market type (V6! V8's 5 = piling into losses)

# MR High — V6 parameters (100% WR in V6, 12 trades in 2.7h)
MR_HIGH_THRESHOLD = 0.80     # K > 0.80 triggers MR High (V6 value)
# No ceiling — V6 had no upper bound

# Delay Arb — V7's sustained momentum filter + V6's entry range
DELAY_MOMENTUM_THR = 0.15    # V6's 0.15 (V6 had 89% WR; V7's 0.20 filtered good signals)

# Risk Management — V6 parameters (the winning discipline)
HOLD_TIMEOUT = 360           # 6min hold (V6! V8's 3min cut winners too early)
PROFIT_TARGET = 0.08         # 8% take profit
SPREAD_FILTER = 0.05         # 5¢ max spread (V6! tighter = better entries)
MIN_TIME_REMAINING = 120     # 2min before settlement
VOLUME_FILTER = 50           # Min volume to enter (V6 had this, V8 didn't)


class BTCPriceFeed:
    def __init__(self):
        self.prices = {}
        self.timestamps = {}
        self.weighted_price = None
        self.price_history = deque(maxlen=500)
        self.weights = {'coinbase': 0.35, 'kraken': 0.25, 'bitstamp': 0.20, 'binance_us': 0.20}
        self.reconnect_delays = {}
        self.running = True

    def get_weighted(self):
        if not self.prices: return None
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
        if len(self.price_history) < 2: return None
        cutoff = time.time() - lookback_sec
        old = next((e['price'] for e in self.price_history if e['time'] >= cutoff), None)
        return ((self.weighted_price - old) / old) * 100 if old and self.weighted_price else None

    def get_volatility(self, lookback_sec=300):
        if len(self.price_history) < 10: return 0.01
        cutoff = time.time() - lookback_sec
        prices = [e['price'] for e in self.price_history if e['time'] >= cutoff]
        if len(prices) < 10: return 0.01
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return math.sqrt(variance) / mean if mean > 0 else 0.01

    async def _reconnect_backoff(self, exchange):
        delay = self.reconnect_delays.get(exchange, 1)
        await asyncio.sleep(min(delay, 60))
        self.reconnect_delays[exchange] = min(delay * 2, 60)

    async def _coinbase(self):
        self.reconnect_delays['coinbase'] = 1
        while self.running:
            try:
                async with websockets.connect("wss://ws-feed.exchange.coinbase.com", ping_interval=20) as ws:
                    await ws.send(json.dumps({"type":"subscribe","channels":[{"name":"ticker","product_ids":["BTC-USD"]}]}))
                    async for msg in ws:
                        if not self.running: break
                        d = json.loads(msg)
                        if d.get('type') == 'ticker' and 'price' in d:
                            self._update('coinbase', float(d['price']))
            except Exception as e:
                if self.running:
                    print(f"⚠️ Coinbase WS error: {e}", flush=True)
                    await self._reconnect_backoff('coinbase')

    async def _kraken(self):
        self.reconnect_delays['kraken'] = 1
        while self.running:
            try:
                async with websockets.connect("wss://ws.kraken.com", ping_interval=20) as ws:
                    await ws.send(json.dumps({"event":"subscribe","pair":["XBT/USD"],"subscription":{"name":"ticker"}}))
                    async for msg in ws:
                        if not self.running: break
                        d = json.loads(msg)
                        if isinstance(d, list) and len(d) >= 4 and isinstance(d[1], dict) and 'c' in d[1]:
                            self._update('kraken', float(d[1]['c'][0]))
            except Exception as e:
                if self.running:
                    print(f"⚠️ Kraken WS error: {e}", flush=True)
                    await self._reconnect_backoff('kraken')

    async def _bitstamp(self):
        self.reconnect_delays['bitstamp'] = 1
        while self.running:
            try:
                async with websockets.connect("wss://ws.bitstamp.net", ping_interval=20) as ws:
                    await ws.send(json.dumps({"event":"bts:subscribe","data":{"channel":"live_trades_btcusd"}}))
                    async for msg in ws:
                        if not self.running: break
                        d = json.loads(msg)
                        if d.get('event') == 'trade' and 'price' in d.get('data', {}):
                            self._update('bitstamp', float(d['data']['price']))
            except Exception as e:
                if self.running:
                    print(f"⚠️ Bitstamp WS error: {e}", flush=True)
                    await self._reconnect_backoff('bitstamp')

    async def _binance(self):
        self.reconnect_delays['binance_us'] = 1
        while self.running:
            try:
                async with websockets.connect("wss://stream.binance.us:9443/ws/btcusdt@ticker", ping_interval=20) as ws:
                    async for msg in ws:
                        if not self.running: break
                        d = json.loads(msg)
                        if 'c' in d:
                            self._update('binance_us', float(d['c']))
            except Exception as e:
                if self.running:
                    print(f"⚠️ Binance WS error: {e}", flush=True)
                    await self._reconnect_backoff('binance_us')

    async def run(self):
        tasks = [
            asyncio.create_task(self._coinbase()),
            asyncio.create_task(self._kraken()),
            asyncio.create_task(self._bitstamp()),
            asyncio.create_task(self._binance())
        ]
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            self.running = False
            for task in tasks:
                task.cancel()


class MultiMarketPoller:
    """Polls ALL open brackets for KXBTC15M and KXBTC1H series."""
    def __init__(self, interval=5):
        self.interval = interval
        self.all_markets = {'15m': [], '1h': []}
        self.primary = {'15m': None, '1h': None}
        self.history = {'15m': deque(maxlen=200), '1h': deque(maxlen=200)}
        self.last_tickers = {'15m': set(), '1h': set()}
        self.running = True

    def _parse_bracket(self, ticker):
        try:
            parts = ticker.split('-')
            if len(parts) >= 3:
                return int(parts[-1])
        except:
            pass
        return None

    def time_until_close(self, market):
        close_str = market.get('close_time')
        if not close_str:
            return 999
        try:
            close = datetime.fromisoformat(close_str.replace('Z', '+00:00'))
            return close.timestamp() - time.time()
        except:
            return 999

    def get_k_volatility(self, market_type, lookback=20):
        prices = [m['yes_bid'] for m in list(self.history[market_type])[-lookback:] if 'yes_bid' in m]
        if len(prices) < 5: return 0.05
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return math.sqrt(variance)

    def _fetch_all(self, series_ticker):
        url = f"https://api.elections.kalshi.com/trade-api/v2/markets?limit=50&series_ticker={series_ticker}&status=open"
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')
        try:
            with request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            markets = []
            for m in data.get('markets', []):
                yes_bid = m.get('yes_bid', 0) / 100
                yes_ask = m.get('yes_ask', 0) / 100
                markets.append({
                    'ticker': m['ticker'],
                    'yes_bid': yes_bid,
                    'yes_ask': yes_ask,
                    'no_bid': 1 - yes_ask,
                    'no_ask': 1 - yes_bid,
                    'volume': m.get('volume', 0),
                    'close_time': m.get('close_time'),
                    'time': time.time(),
                    'series': series_ticker,
                    'bracket': self._parse_bracket(m['ticker']),
                    'subtitle': m.get('subtitle', ''),
                    'floor_strike': m.get('floor_strike'),
                    'cap_strike': m.get('cap_strike'),
                })
            return markets
        except Exception as e:
            return []

    async def run(self):
        try:
            while self.running:
                for series, mtype in [('KXBTC15M', '15m'), ('KXBTC1H', '1h')]:
                    markets = await asyncio.get_event_loop().run_in_executor(
                        None, self._fetch_all, series
                    )
                    if markets:
                        self.last_tickers[mtype] = {m['ticker'] for m in self.all_markets[mtype]}
                        self.all_markets[mtype] = markets
                        self.primary[mtype] = markets[0] if markets else None
                        if markets:
                            self.history[mtype].append(markets[0])
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            self.running = False


class PaperTrader:
    def __init__(self, balance=1000, trade_size=TRADE_SIZE):
        self.balance = balance
        self.initial = balance
        self.trade_size = trade_size
        self.positions = []
        self.trades = []
        self.pnl = 0
        self.last_exit_times = {}  # per-ticker cooldown

    def open(self, direction, price, ticker, market_type, strategy):
        theoretical_price = price
        actual_price = price
        fill_info = None
        if HAS_ORDERBOOK:
            try:
                real_price, fill_info = get_real_entry_price(ticker, direction, self.trade_size)
                if real_price and real_price > 0:
                    actual_price = real_price
            except Exception:
                pass
        
        cost = self.trade_size * actual_price
        if cost > self.balance: return None
        pos = {
            'id': len(self.positions), 'dir': direction, 'size': self.trade_size,
            'entry': actual_price, 'theoretical_entry': theoretical_price,
            'slippage_entry': actual_price - theoretical_price,
            'time': time.time(), 'ticker': ticker, 'open': True,
            'market_type': market_type, 'strategy': strategy
        }
        if fill_info:
            pos['entry_fill'] = {'vwap': fill_info.get('vwap', 0),
                                 'levels': fill_info.get('levels_consumed', 0),
                                 'slippage': fill_info.get('slippage', 0),
                                 'partial': fill_info.get('partial', False)}
        self.positions.append(pos)
        self.balance -= cost
        return pos['id']

    def close(self, pos_id, exit_price):
        pos = next((p for p in self.positions if p['id'] == pos_id and p['open']), None)
        if not pos: return None
        
        theoretical_exit = exit_price
        actual_exit = exit_price
        fill_info = None
        if HAS_ORDERBOOK:
            try:
                real_price, fill_info = get_real_exit_price(pos['ticker'], pos['dir'], pos['size'])
                if real_price and real_price > 0:
                    actual_exit = real_price
            except Exception:
                pass
        
        pnl = (actual_exit - pos['entry']) * pos['size']
        pos['exit'] = actual_exit
        pos['theoretical_exit'] = theoretical_exit
        pos['slippage_exit'] = actual_exit - theoretical_exit
        pos['pnl'] = pnl
        pos['open'] = False
        pos['close_time'] = time.time()
        if fill_info:
            pos['exit_fill'] = {'vwap': fill_info.get('vwap', 0),
                                'levels': fill_info.get('levels_consumed', 0),
                                'slippage': fill_info.get('slippage', 0),
                                'partial': fill_info.get('partial', False)}
        self.balance += pos['size'] * actual_exit
        self.pnl += pnl
        self.trades.append(pos.copy())
        self.last_exit_times[pos['ticker']] = time.time()
        return pnl

    def get_open(self, market_type=None, ticker=None):
        result = [p for p in self.positions if p['open']]
        if market_type:
            result = [p for p in result if p.get('market_type') == market_type]
        if ticker:
            result = [p for p in result if p.get('ticker') == ticker]
        return result

    def count_open_by_strategy(self, strategy):
        return len([p for p in self.positions if p['open'] and p.get('strategy') == strategy])

    def to_dict(self):
        return {
            'balance': self.balance, 'initial': self.initial, 'pnl': self.pnl,
            'positions': self.positions, 'trades': self.trades
        }


class TradingEngine:
    def __init__(self, feed, poller, duration_min=480):
        self.feed = feed
        self.poller = poller
        self.trader = PaperTrader()
        self.duration = duration_min * 60
        self.start_time = None
        self.signals = []
        self.log_files = []
        self.state_file = '/home/clawdbot/clawd/btc-arbitrage/data/rt_v9_state.json'
        self.graceful_shutdown = False

    def _dual_log(self, msg):
        for f in self.log_files:
            if f and not f.closed:
                f.write(f"{datetime.now().isoformat()} {msg}\n")
                f.flush()
        print(msg, flush=True)

    def _save_checkpoint(self):
        try:
            elapsed = int(time.time() - self.start_time)
            strats = {}
            for t in self.trader.trades:
                s = t.get('strategy', 'unknown')
                if s not in strats:
                    strats[s] = {'count': 0, 'wins': 0, 'pnl': 0}
                strats[s]['count'] += 1
                if t.get('pnl', 0) > 0: strats[s]['wins'] += 1
                strats[s]['pnl'] += t.get('pnl', 0)

            state = {
                'version': 'v9',
                'elapsed_sec': elapsed,
                'start_time': self.start_time,
                'trader': self.trader.to_dict(),
                'signals': self.signals[-100:],
                'strategy_stats': strats,
                'brackets_scanned': {
                    '15m': len(self.poller.all_markets.get('15m', [])),
                    '1h': len(self.poller.all_markets.get('1h', []))
                },
                'last_checkpoint': time.time()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except:
            pass

    async def _checkpoint_loop(self):
        while not self.graceful_shutdown:
            await asyncio.sleep(120)
            self._save_checkpoint()

    def _setup_signal_handlers(self):
        def handler(signum, frame):
            sig_name = signal.Signals(signum).name
            msg = f"\n⚠️ SIGNAL: {sig_name} at {datetime.now().isoformat()}"
            self._dual_log(msg)
            self.graceful_shutdown = True
            # Iron Law: no sys.exit(0) — would mask crashes
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def _can_enter(self, market, market_type):
        """Entry filters — V6 discipline."""
        ticker = market['ticker']

        # Time remaining
        time_remaining = self.poller.time_until_close(market)
        if time_remaining < MIN_TIME_REMAINING:
            return False, "too_close"

        # Spread filter (V6: 5¢ max)
        spread = market.get('yes_ask', 1) - market.get('yes_bid', 0)
        if spread > SPREAD_FILTER:
            return False, "spread_wide"

        # Volume filter (V6 had this, V8 dropped it)
        if market.get('volume', 0) < VOLUME_FILTER:
            return False, "low_volume"

        # GLOBAL cooldown — V6 style: 60s since ANY last exit
        # This is the key difference. V8 used per-ticker 5s = machine gun
        if hasattr(self, '_last_global_exit') and time.time() - self._last_global_exit < COOLDOWN_SEC:
            return False, "global_cooldown"

        # Max positions per market type (V6: 1 per type)
        open_in_type = len(self.trader.get_open(market_type=market_type))
        if open_in_type >= MAX_POSITIONS_PER_MARKET:
            return False, "max_positions"

        return True, "ok"

    def _get_adaptive_stop(self):
        """Volatility-adaptive stop-loss (V6 implementation)."""
        k_vol = max(self.poller.get_k_volatility('15m'), self.poller.get_k_volatility('1h'))
        btc_vol = self.feed.get_volatility(300)
        # Base stop: 25% (V6's wider base, not V8's narrower)
        base_stop = 0.25
        vol_multiplier = 1.0 + (btc_vol * 10)
        return max(0.15, min(0.40, base_stop * vol_multiplier))

    def _process_market(self, market, market_type, elapsed, btc_price, momentum_1m, momentum_30s):
        """Process a single bracket for MR High and Delay Arb only."""
        ticker = market['ticker']
        k_bid = market['yes_bid']
        k_ask = market['yes_ask']
        time_remaining = self.poller.time_until_close(market)

        can_enter, reason = self._can_enter(market, market_type)

        # Debug log every 30s
        if not hasattr(self, '_last_debug') or time.time() - self._last_debug > 30:
            self._last_debug = time.time()
            self._dual_log(f"[{elapsed:5d}s] 🔍 DEBUG {ticker}: K={k_bid:.2f} ask={k_ask:.2f} ttc={time_remaining:.0f}s can_enter={can_enter}({reason})")

        if not can_enter:
            return

        # Already have position on this ticker?
        if self.trader.get_open(ticker=ticker):
            return

        # ─── STRATEGY 1: Mean Reversion High (V6 params: K > 0.80, buy NO) ───
        if k_bid > MR_HIGH_THRESHOLD and momentum_1m is not None and momentum_1m < 0.05:
            no_price = 1 - k_bid
            pos_id = self.trader.open('NO', no_price, ticker, market_type, 'mean_reversion_high')
            if pos_id is not None:
                self._dual_log(f"[{elapsed:5d}s] 📈 MR-HIGH {ticker}: K@{k_bid:.2f} → NO@{no_price:.2f} (mom={momentum_1m:+.3f}%)")
                self.signals.append({'type': 'mr_high', 'market': market_type, 'ticker': ticker, 'time': elapsed})
                return

        # ─── STRATEGY 2: Delay Arbitrage (V7 params: sustained momentum) ───
        if momentum_1m is not None and momentum_30s is not None:
            # Both 30s and 60s momentum must agree in direction (sustained move)
            same_direction = (momentum_1m > 0 and momentum_30s > 0) or (momentum_1m < 0 and momentum_30s < 0)
            if same_direction and abs(momentum_1m) > DELAY_MOMENTUM_THR:
                # Only enter in first 7 minutes of window
                if time_remaining > (900 - 420 if market_type == '15m' else 3600 - 420):
                    direction = 'YES' if momentum_1m > 0 else 'NO'
                    entry = k_ask if direction == 'YES' else (1 - k_bid)
                    if 0.10 < entry < 0.90:
                        pos_id = self.trader.open(direction, entry, ticker, market_type, 'delay_arb')
                        if pos_id is not None:
                            self._dual_log(f"[{elapsed:5d}s] 🎯 DELAY {ticker}: BTC {momentum_1m:+.3f}%(1m) {momentum_30s:+.3f}%(30s) → {direction}@{entry:.2f}")
                            self.signals.append({'type': 'delay', 'market': market_type, 'ticker': ticker, 'time': elapsed})

    def _manage_positions(self, elapsed):
        """Manage open positions — stop loss, take profit, timeout."""
        for pos in self.trader.get_open():
            ticker = pos['ticker']
            market_type = pos.get('market_type', '15m')

            # Find current market data
            all_markets = self.poller.all_markets.get(market_type, [])
            market = next((m for m in all_markets if m['ticker'] == ticker), None)
            if not market:
                hold_time = time.time() - pos['time']
                if hold_time > 60:
                    self.trader.close(pos['id'], pos['entry'])
                continue

            hold_time = time.time() - pos['time']
            if pos['dir'] == 'YES':
                current = market['yes_bid']
            elif pos['dir'] == 'NO':
                current = 1 - market['yes_ask']
            else:
                continue

            pct = ((current - pos['entry']) / pos['entry']) * 100 if pos['entry'] > 0 else 0

            should_close = False
            reason = ""
            stop_pct = -self._get_adaptive_stop() * 100

            if pct > PROFIT_TARGET * 100:
                should_close, reason = True, "PROFIT"
            elif pct < stop_pct:
                should_close, reason = True, f"STOP({stop_pct:.0f}%)"
            elif hold_time > HOLD_TIMEOUT:
                should_close, reason = True, "TIMEOUT"

            if should_close:
                pnl = self.trader.close(pos['id'], current)
                if pnl is not None:
                    self._last_global_exit = time.time()  # Track for global cooldown
                    icon = '✅' if pnl > 0 else '❌'
                    self._dual_log(f"[{elapsed:5d}s] {icon} {pos['strategy']} {ticker} CLOSE ({reason}): ${pnl:+.2f} | Total: ${self.trader.pnl:+.2f}")

    async def run(self):
        try:
            self.start_time = time.time()
            end_time = self.start_time + self.duration
            os.makedirs('/home/clawdbot/clawd/btc-arbitrage/logs', exist_ok=True)
            os.makedirs('/home/clawdbot/clawd/btc-arbitrage/data', exist_ok=True)

            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_ts = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_v9_{ts}.log', 'w')
            log_live = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_v9_live.log', 'w')
            self.log_files = [log_live, log_ts]

            self._setup_signal_handlers()

            header = f"""
{'='*70}
v9 — Corrected Best-of-Breed: V6 discipline + best strategies
{'='*70}
Duration: {self.duration//60}min | Start: {datetime.now().strftime('%H:%M:%S UTC')}
Strategies:
  MR-High: K > {MR_HIGH_THRESHOLD} + momentum < 0.05 → buy NO (V6 params)
  Delay Arb: sustained momentum > {DELAY_MOMENTUM_THR}% → follow BTC direction
Risk: cooldown={COOLDOWN_SEC}s GLOBAL, max_pos={MAX_POSITIONS_PER_MARKET}/mkt, timeout={HOLD_TIMEOUT}s, spread<{SPREAD_FILTER}, vol>{VOLUME_FILTER}
KEY FIX: V6 discipline (60s cooldown, 1 pos/mkt) instead of V8's (5s, 5 pos/mkt)
{'='*70}
"""
            self._dual_log(header)

            checkpoint_task = asyncio.create_task(self._checkpoint_loop())
            last_status = time.time()

            while time.time() < end_time and not self.graceful_shutdown:
                await asyncio.sleep(1)
                btc_price = self.feed.weighted_price
                if not btc_price: continue

                elapsed = int(time.time() - self.start_time)
                momentum_1m = self.feed.get_momentum(60)
                momentum_30s = self.feed.get_momentum(30)

                # Process ALL brackets for both market types
                for mtype in ['15m', '1h']:
                    for market in self.poller.all_markets.get(mtype, []):
                        self._process_market(market, mtype, elapsed, btc_price, momentum_1m, momentum_30s)

                # Manage positions
                self._manage_positions(elapsed)

                # Status log every 60s
                if time.time() - last_status > 60:
                    n_brackets = len(self.poller.all_markets.get('15m', [])) + len(self.poller.all_markets.get('1h', []))
                    n_open = len(self.trader.get_open())
                    n_trades = len(self.trader.trades)
                    rate = n_trades / (elapsed / 3600) if elapsed > 0 else 0
                    mom_str = f"{momentum_1m:+.3f}%" if momentum_1m else "N/A"

                    # Strategy breakdown
                    mr_count = sum(1 for t in self.trader.trades if t.get('strategy') == 'mean_reversion_high')
                    da_count = sum(1 for t in self.trader.trades if t.get('strategy') == 'delay_arb')

                    st = f"[{elapsed:5d}s] BTC: ${btc_price:,.2f} ({mom_str}) | Brackets: {n_brackets} | Open: {n_open} | Trades: {n_trades} (MR:{mr_count} DA:{da_count}) | P&L: ${self.trader.pnl:+.2f}"
                    self._dual_log(st)
                    last_status = time.time()

            checkpoint_task.cancel()
            self._save_checkpoint()
            self._summary()

        except Exception as e:
            err = f"\n❌ FATAL: {e}\n{traceback.format_exc()}"
            self._dual_log(err)
            self._save_checkpoint()
            self._summary()

    def _summary(self):
        elapsed = int(time.time() - self.start_time) if self.start_time else 0
        hours = elapsed / 3600 if elapsed > 0 else 1

        summary = f"""
{'='*70}
v9 SUMMARY — Corrected Best-of-Breed (V6 discipline + best strategies)
{'='*70}
Duration: {elapsed//60}min ({hours:.1f}h)
Total Trades: {len(self.trader.trades)}
Trade Rate: {len(self.trader.trades)/hours:.1f}/hr
P&L: ${self.trader.pnl:+.2f}
Final Balance: ${self.trader.balance:.2f}
"""
        strategies = {}
        for t in self.trader.trades:
            s = t.get('strategy', 'unknown')
            if s not in strategies:
                strategies[s] = {'count': 0, 'wins': 0, 'pnl': 0, 'pnls': []}
            strategies[s]['count'] += 1
            if t.get('pnl', 0) > 0: strategies[s]['wins'] += 1
            strategies[s]['pnl'] += t.get('pnl', 0)
            strategies[s]['pnls'].append(t.get('pnl', 0))

        for s, stats in sorted(strategies.items()):
            wr = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            avg = stats['pnl'] / stats['count'] if stats['count'] > 0 else 0
            summary += f"\n  {s}:"
            summary += f"\n    Trades: {stats['count']}, Win Rate: {wr:.0f}%, P&L: ${stats['pnl']:+.2f}, Avg: ${avg:+.3f}"

        summary += f"\n{'='*70}\n"
        self._dual_log(summary)

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'/home/clawdbot/clawd/btc-arbitrage/data/rt_v9_{ts}.json', 'w') as f:
            json.dump({
                'version': 'v9', 'duration_min': elapsed // 60, 'pnl': self.trader.pnl,
                'signals': self.signals, 'trades': self.trader.trades,
                'strategy_stats': {s: {k: v for k, v in st.items() if k != 'pnls'} for s, st in strategies.items()},
                'complete': not self.graceful_shutdown
            }, f, indent=2, default=str)

        for f in self.log_files:
            if f and not f.closed: f.close()


async def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 480
    feed = BTCPriceFeed()
    poller = MultiMarketPoller(interval=5)
    engine = TradingEngine(feed, poller, duration_min=duration)

    feed_task = asyncio.create_task(feed.run())
    poller_task = asyncio.create_task(poller.run())

    try:
        await engine.run()
    finally:
        feed.running = False
        poller.running = False
        feed_task.cancel()
        poller_task.cancel()
        try:
            await asyncio.gather(feed_task, poller_task, return_exceptions=True)
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Interrupt", flush=True)
    except Exception as e:
        print(f"\n❌ Fatal: {e}\n{traceback.format_exc()}", flush=True)
