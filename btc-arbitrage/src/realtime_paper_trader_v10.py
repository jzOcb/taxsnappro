#!/usr/bin/env python3
"""
Real-time Paper Trader v10 - WebSocket + Enhanced Features
Upgraded from v6 with:
1. WebSocket real-time data (fallback to REST polling)
2. Enhanced flash crash detection 
3. Dynamic position sizing
4. All v6 features preserved

Key Features:
- BTC momentum filter for crash detection
- Volatility-adaptive stop-loss  
- Entry quality filters
- Market timing restrictions (first/last 30s excluded)
- Mean reversion at extremes (>80¢, NO <20¢ disabled)
- Dual market support (15min + hourly)
- Real-time WebSocket updates with REST fallback
- Flash crash detection with sliding window
- Dynamic position sizing based on win rate
"""
import asyncio, json, time, sys, os, traceback, signal
import math
from collections import deque
sys.path.insert(0, '/tmp/pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import websockets
from datetime import datetime
from urllib import request

# Import WebSocket client
try:
    from kalshi_websocket import KalshiWebSocketClient
    HAS_WEBSOCKET = True  # Enabled - RSA auth configured
    print("✅ WebSocket client available", flush=True)
except ImportError:
    HAS_WEBSOCKET = False
    print("⚠️ WebSocket client not available, will use REST fallback", flush=True)

# Import orderbook executor
try:
    from orderbook_executor import get_real_entry_price, get_real_exit_price
    HAS_ORDERBOOK = True
except ImportError:
    HAS_ORDERBOOK = False

class BTCPriceFeed:
    """BTC price feed from 4 exchanges - unchanged from v6"""
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
        """Calculate BTC price volatility (std dev)"""
        if len(self.price_history) < 10: return 0.01
        cutoff = time.time() - lookback_sec
        prices = [e['price'] for e in self.price_history if e['time'] >= cutoff]
        if len(prices) < 10: return 0.01
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std = math.sqrt(variance)
        return std / mean if mean > 0 else 0.01
    
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
                    print(f"⚠️ Coinbase WebSocket error: {e}", flush=True)
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
                    print(f"⚠️ Kraken WebSocket error: {e}", flush=True)
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
                    print(f"⚠️ Bitstamp WebSocket error: {e}", flush=True)
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
                    print(f"⚠️ Binance WebSocket error: {e}", flush=True)
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

class FlashCrashDetector:
    """Enhanced flash crash detection with sliding window"""
    def __init__(self, window_sec=30, drop_threshold=0.15):
        self.window_sec = window_sec
        self.drop_threshold = drop_threshold
        self.k_history = {'15m': deque(maxlen=1000), '1h': deque(maxlen=1000)}
        self.flash_crashes = []
    
    def update_k_value(self, market_type, k_value):
        """Update K-value history with timestamp"""
        timestamp = time.time()
        self.k_history[market_type].append({'time': timestamp, 'k': k_value})
    
    def detect_flash_crash(self, market_type, current_k):
        """Detect rapid K-value drops within sliding window"""
        if market_type not in self.k_history:
            return False, 0
        
        history = self.k_history[market_type]
        if len(history) < 2:
            return False, 0
        
        # Check last 10 seconds for rapid drops
        cutoff = time.time() - 10
        recent = [h for h in history if h['time'] >= cutoff]
        
        if len(recent) < 2:
            return False, 0
        
        # Find maximum K in window and current drop
        max_k = max(h['k'] for h in recent)
        if max_k <= 0:
            return False, 0
        
        drop_pct = (max_k - current_k) / max_k
        
        # Flash crash if drop > threshold in <10 seconds
        is_flash_crash = drop_pct > self.drop_threshold
        
        if is_flash_crash:
            crash_event = {
                'time': time.time(),
                'market_type': market_type,
                'max_k': max_k,
                'current_k': current_k,
                'drop_pct': drop_pct,
                'window_sec': 10
            }
            self.flash_crashes.append(crash_event)
            
        return is_flash_crash, drop_pct

class DualMarketPoller:
    """Dual market poller - kept as fallback for WebSocket"""
    def __init__(self, interval=5):
        self.interval = interval
        self.markets = {}
        self.history = {'15m': deque(maxlen=200), '1h': deque(maxlen=200)}
        self.last_tickers = {'15m': None, '1h': None}
        self.running = True
        self.mode = "REST"  # Track which mode is active
    
    def is_market_transition(self, market_type):
        if market_type not in self.markets or market_type not in self.last_tickers:
            return False
        current = self.markets[market_type]
        last = self.last_tickers[market_type]
        if current and last and current['ticker'] != last:
            return True
        return False
    
    def time_until_close(self, market_type):
        """Seconds until market closes"""
        if market_type not in self.markets:
            return 999
        close_str = self.markets[market_type].get('close_time')
        if not close_str:
            return 999
        try:
            close = datetime.fromisoformat(close_str.replace('Z', '+00:00'))
            return (close.timestamp() - time.time())
        except:
            return 999
    
    def get_k_volatility(self, market_type, lookback=20):
        """Calculate K-value volatility"""
        if market_type not in self.history:
            return 0.05
        prices = [m['yes_bid'] for m in list(self.history[market_type])[-lookback:] if 'yes_bid' in m]
        if len(prices) < 5:
            return 0.05
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return math.sqrt(variance) if len(prices) > 0 else 0.05
    
    def _fetch(self, series_ticker):
        url = f"https://api.elections.kalshi.com/trade-api/v2/markets?limit=10&series_ticker={series_ticker}&status=open"
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')
        try:
            with request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read())
            if data.get('markets'):
                m = data['markets'][0]
                return {'ticker': m['ticker'], 'yes_bid': m.get('yes_bid', 0) / 100,
                       'yes_ask': m.get('yes_ask', 0) / 100, 'volume': m.get('volume', 0),
                       'close_time': m.get('close_time'), 'time': time.time(),
                       'series': series_ticker}
        except:
            pass
        return None
    
    async def run(self):
        try:
            while self.running:
                m15 = await asyncio.get_event_loop().run_in_executor(None, self._fetch, 'KXBTC15M')
                m1h = await asyncio.get_event_loop().run_in_executor(None, self._fetch, 'KXBTC1H')
                
                if m15:
                    self.last_tickers['15m'] = self.markets.get('15m', {}).get('ticker')
                    self.markets['15m'] = m15
                    self.history['15m'].append(m15)
                
                if m1h:
                    self.last_tickers['1h'] = self.markets.get('1h', {}).get('ticker')
                    self.markets['1h'] = m1h
                    self.history['1h'].append(m1h)
                
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            self.running = False

class KalshiWebSocketPoller:
    """WebSocket-based market poller with REST fallback"""
    def __init__(self):
        self.markets = {}
        self.history = {'15m': deque(maxlen=200), '1h': deque(maxlen=200)}
        self.last_tickers = {'15m': None, '1h': None}
        self.running = True
        self.mode = "WebSocket"
        self.rest_fallback = DualMarketPoller(interval=5)
        self.ws_connected = False
        self.ws_client = None
        
    def is_market_transition(self, market_type):
        return self.rest_fallback.is_market_transition(market_type)
    
    def time_until_close(self, market_type):
        return self.rest_fallback.time_until_close(market_type)
    
    def get_k_volatility(self, market_type, lookback=20):
        return self.rest_fallback.get_k_volatility(market_type, lookback)
    
    def _on_ticker(self, data):
        """Handle WebSocket ticker updates"""
        try:
            ticker = data.get('market_ticker', '')
            if 'KXBTC15M' in ticker:
                market_type = '15m'
            elif 'KXBTC1H' in ticker:
                market_type = '1h'
            else:
                return
            
            # Convert to same format as REST
            market_data = {
                'ticker': ticker,
                'yes_bid': data.get('yes_bid', 0) / 100 if 'yes_bid' in data else 0,
                'yes_ask': data.get('yes_ask', 0) / 100 if 'yes_ask' in data else 0,
                'volume': data.get('volume', 0),
                'close_time': data.get('close_time'),
                'time': time.time(),
                'series': 'KXBTC15M' if '15M' in ticker else 'KXBTC1H'
            }
            
            self.last_tickers[market_type] = self.markets.get(market_type, {}).get('ticker')
            self.markets[market_type] = market_data
            self.history[market_type].append(market_data)
            
        except Exception as e:
            print(f"⚠️ WebSocket ticker processing error: {e}", flush=True)
    
    def _on_orderbook(self, data):
        """Handle WebSocket orderbook updates"""
        # For now, we mainly need ticker data, but this can be extended
        pass
    
    def _on_error(self, error):
        """Handle WebSocket errors"""
        print(f"⚠️ WebSocket error: {error}", flush=True)
        self.ws_connected = False
    
    async def _try_websocket(self):
        """Attempt to use WebSocket for real-time updates"""
        if not HAS_WEBSOCKET:
            return False
            
        try:
            self.ws_client = KalshiWebSocketClient(
                on_ticker=self._on_ticker,
                on_orderbook=self._on_orderbook,
                on_error=self._on_error
            )
            
            # Try to start WebSocket (non-blocking attempt)
            self._ws_task = asyncio.create_task(self.ws_client.start(series="KXBTC15M"))
            
            # Wait briefly to see if connection succeeds
            try:
                await asyncio.sleep(3)
                if self.ws_client.ws and getattr(self.ws_client.ws, "close_code", None) is None:
                    self.ws_connected = True
                    print("✅ Kalshi WebSocket connected successfully", flush=True)
                    return True
            except:
                pass
            
            # WebSocket failed — cancel the task to stop retry loop
            if hasattr(self, '_ws_task'):
                self._ws_task.cancel()
                try:
                    await self._ws_task
                except (asyncio.CancelledError, Exception):
                    pass
            if self.ws_client:
                await self.ws_client.stop()
                self.ws_client = None
                
        except Exception as e:
            print(f"⚠️ WebSocket connection failed: {e}", flush=True)
        
        return False
    
    async def run(self):
        """Run with WebSocket primary, REST fallback"""
        
        # Try WebSocket first (skip if disabled)
        websocket_success = False if not HAS_WEBSOCKET else await self._try_websocket()
        
        if websocket_success:
            self.mode = "WebSocket"
            print("🚀 Using WebSocket mode for Kalshi data", flush=True)
            
            # Keep WebSocket running and also run REST as backup
            rest_task = asyncio.create_task(self.rest_fallback.run())
            
            # Monitor WebSocket health
            while self.running:
                if not self.ws_connected or not self.ws_client or (self.ws_client.ws and getattr(self.ws_client.ws, "close_code", None) is not None):
                    print("⚠️ WebSocket disconnected, falling back to REST", flush=True)
                    self.mode = "REST"
                    break
                await asyncio.sleep(1)
            
            if self.ws_client:
                await self.ws_client.stop()
            rest_task.cancel()
        else:
            # Use REST polling as fallback
            self.mode = "REST"
            print("🔄 Using REST polling mode for Kalshi data (WebSocket unavailable)", flush=True)
            
            # Copy data from REST fallback
            while self.running:
                self.markets = self.rest_fallback.markets.copy()
                self.history = {k: deque(v) for k, v in self.rest_fallback.history.items()}
                self.last_tickers = self.rest_fallback.last_tickers.copy()
                await asyncio.sleep(1)

class PaperTrader:
    """Enhanced paper trader with dynamic position sizing"""
    def __init__(self, balance=1000, base_trade_size=10):
        self.balance = balance
        self.initial = balance
        self.base_trade_size = base_trade_size
        self.current_trade_size = base_trade_size
        self.positions = []
        self.trades = []
        self.pnl = 0
        self.last_exit_time = 0
        self.consecutive_wins = 0
        self.session_stats = {'wins': 0, 'losses': 0, 'total': 0}
    
    def _calculate_dynamic_size(self, strategy):
        """Dynamic position sizing based on performance"""
        base_size = self.base_trade_size
        
        # Win rate this session
        win_rate = self.session_stats['wins'] / max(self.session_stats['total'], 1)
        
        # Base sizing rules
        if win_rate > 0.80 and self.session_stats['total'] >= 5:
            # High win rate: increase to $15
            size = 15
        else:
            # Default size
            size = base_size
        
        # Consecutive wins bonus (max $20)
        if self.consecutive_wins >= 3:
            size = min(20, size + 5)
        
        self.current_trade_size = size
        return size
    
    def open(self, direction, price, ticker, market_type, strategy):
        # Calculate dynamic position size
        trade_size = self._calculate_dynamic_size(strategy)
        
        # Use orderbook depth for real execution price
        theoretical_price = price
        actual_price = price
        fill_info = None
        if HAS_ORDERBOOK:
            try:
                real_price, fill_info = get_real_entry_price(ticker, direction, trade_size)
                if real_price and real_price > 0:
                    actual_price = real_price
            except Exception:
                pass  # Fall back to theoretical price
        
        cost = trade_size * actual_price
        if cost > self.balance: return None
        pos = {'id': len(self.positions), 'dir': direction, 'size': trade_size,
               'entry': actual_price, 'theoretical_entry': theoretical_price,
               'slippage_entry': actual_price - theoretical_price,
               'time': time.time(), 'ticker': ticker, 'open': True,
               'market_type': market_type, 'strategy': strategy,
               'sizing_decision': {
                   'base_size': self.base_trade_size,
                   'calculated_size': trade_size,
                   'win_rate': self.session_stats['wins'] / max(self.session_stats['total'], 1),
                   'consecutive_wins': self.consecutive_wins
               }}
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
        
        # Use orderbook depth for real exit price
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
        # NO direction: pnl already correct (sell price - buy price)
        # Bug fix: removed incorrect sign flip for NO trades
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
        self.last_exit_time = time.time()
        
        # Update session stats and consecutive wins
        self.session_stats['total'] += 1
        if pnl > 0:
            self.session_stats['wins'] += 1
            self.consecutive_wins += 1
        else:
            self.session_stats['losses'] += 1
            self.consecutive_wins = 0  # Reset consecutive wins on loss
        
        return pnl
    
    def get_open(self, market_type=None):
        if market_type:
            return [p for p in self.positions if p['open'] and p.get('market_type') == market_type]
        return [p for p in self.positions if p['open']]
    
    def to_dict(self):
        return {
            'balance': self.balance,
            'initial': self.initial,
            'pnl': self.pnl,
            'positions': self.positions,
            'trades': self.trades,
            'session_stats': self.session_stats,
            'consecutive_wins': self.consecutive_wins
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
        self.last_kalshi_bids = {'15m': None, '1h': None}
        self.state_file = '/home/clawdbot/clawd/btc-arbitrage/data/rt_v10_state.json'
        self.graceful_shutdown = False
        
        # Enhanced flash crash detector
        self.flash_detector = FlashCrashDetector()
    
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
                'elapsed_sec': elapsed,
                'start_time': self.start_time,
                'trader': self.trader.to_dict(),
                'signals': self.signals,
                'flash_crashes': self.flash_detector.flash_crashes,
                'websocket_mode': self.poller.mode,
                'last_checkpoint': time.time()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            self._dual_log(f"[{elapsed:5d}s] 💾 Checkpoint")
        except:
            pass
    
    async def _checkpoint_loop(self):
        while not self.graceful_shutdown:
            await asyncio.sleep(300)
            self._save_checkpoint()
    
    def _setup_signal_handlers(self):
        def handler(signum, frame):
            sig_name = signal.Signals(signum).name
            msg = f"\n⚠️ SIGNAL RECEIVED: {sig_name} (signum={signum}) at {datetime.now().isoformat()}"
            self._dual_log(msg)
            print(msg, flush=True)
            self.graceful_shutdown = True
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
    
    def _should_enter(self, market_type, elapsed):
        """Entry quality filters (Priority 4 from RESEARCH-NOTES.md)"""
        # Check time remaining
        time_remaining = self.poller.time_until_close(market_type)
        if time_remaining < 300:  # <5 min
            return False, "too_close_to_settlement"
        
        # Check if in first/last 30 seconds of window
        market_age = (time_remaining % 900) if market_type == '15m' else (time_remaining % 3600)
        if market_age < 30 or market_age > (870 if market_type == '15m' else 3570):
            return False, "market_transition_window"
        
        # Check spread
        kalshi = self.poller.markets.get(market_type, {})
        spread = kalshi.get('yes_ask', 1) - kalshi.get('yes_bid', 0)
        if spread > 0.05:
            return False, "spread_too_wide"
        
        # Check volume
        if kalshi.get('volume', 0) < 50:
            return False, "volume_too_low"
        
        # Check cooldown (no entry within 60s of last exit)
        if time.time() - self.trader.last_exit_time < 60:
            return False, "cooldown_period"
        
        return True, "passed"
    
    def _get_adaptive_stop(self, entry_price):
        """Volatility-adaptive stop-loss (Priority 2)"""
        k_vol = max(self.poller.get_k_volatility('15m'), self.poller.get_k_volatility('1h'))
        btc_vol = self.feed.get_volatility(300)
        
        # Base stop: 25% (much wider than old 12%)
        base_stop = 0.25
        
        # Adjust by volatility
        vol_multiplier = 1.0 + (btc_vol * 10)  # Higher vol = wider stop
        adaptive_stop = base_stop * vol_multiplier
        
        # Clamp to [15%, 40%]
        adaptive_stop = max(0.15, min(0.40, adaptive_stop))
        
        return adaptive_stop
    
    def _process_market(self, market_type, elapsed, brti, momentum_1m):
        """Process all strategies for one market"""
        if market_type not in self.poller.markets:
            return
        
        kalshi = self.poller.markets[market_type]
        last_bid = self.last_kalshi_bids[market_type]
        
        # Skip if market transition
        if self.poller.is_market_transition(market_type):
            self._dual_log(f"[{elapsed:5d}s] 🔄 {market_type.upper()} transition")
            self.last_kalshi_bids[market_type] = None
            return
        
        # Check entry filters
        can_enter, reason = self._should_enter(market_type, elapsed)
        if not can_enter:
            # Only log significant rejections
            if reason in ['too_close_to_settlement', 'spread_too_wide']:
                pass  # Skip logging
            self.last_kalshi_bids[market_type] = kalshi['yes_bid']
            return
        
        # Already have position in this market?
        if len(self.trader.get_open(market_type)) > 0:
            self.last_kalshi_bids[market_type] = kalshi['yes_bid']
            return
        
        k_bid = kalshi['yes_bid']
        k_ask = kalshi['yes_ask']
        
        # Update flash crash detector
        self.flash_detector.update_k_value(market_type, k_bid)
        
        # Check for flash crash
        is_flash_crash, drop_pct = self.flash_detector.detect_flash_crash(market_type, k_bid)
        
        # STRATEGY 1: Mean Reversion — ALL DISABLED
        # PnL bug discovered: NO trades had inverted PnL display
        # Real performance across all versions: mean_rev_high loses money (-$29.60 v6, -$40.70 v7, -$61.50 v8)
        # Flash crash detection kept for logging only, not trading
        if is_flash_crash:
            self._dual_log(f"[{elapsed:5d}s] ⚡ FLASH CRASH LOGGED (no trade): {market_type.upper()} K dropped {drop_pct:.1%}")
        
        # STRATEGY 2: Delay Arbitrage — ONLY profitable strategy
        elif last_bid is not None and last_bid > 0.01 and momentum_1m is not None:
            kalshi_chg = ((k_bid - last_bid) / last_bid * 100)
            
            # BTC moved but K hasn't caught up
            if abs(momentum_1m) > 0.20 and abs(kalshi_chg) < 5:
                direction = 'YES' if momentum_1m > 0 else 'NO'
                entry = k_ask if direction == 'YES' else (1 - k_bid)
                
                if 0.05 < entry < 0.95:
                    pos_id = self.trader.open(direction, entry, kalshi['ticker'], market_type, 'delay_arb')
                    if pos_id is not None:
                        self._dual_log(f"[{elapsed:5d}s] 🎯 {market_type.upper()} DELAY: BTC {momentum_1m:+.3f}% K {kalshi_chg:+.1f}% → {direction}@{entry:.2f} (size=${self.trader.current_trade_size})")
                        self.signals.append({'type': 'delay', 'market': market_type, 'time': elapsed})
        
        self.last_kalshi_bids[market_type] = k_bid
    
    async def run(self):
        try:
            self.start_time = time.time()
            end_time = self.start_time + self.duration
            os.makedirs('/home/clawdbot/clawd/btc-arbitrage/logs', exist_ok=True)
            os.makedirs('/home/clawdbot/clawd/btc-arbitrage/data', exist_ok=True)
            
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_timestamped = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_v10_{ts}.log', 'w')
            log_live = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_v10_live.log', 'w')
            self.log_files = [log_live, log_timestamped]
            
            self._setup_signal_handlers()
            
            header = f"\n{'='*70}\nv10 - WebSocket + Enhanced Features\n{'='*70}\n" + \
                    f"Duration: {self.duration//60}min | Start: {datetime.now().strftime('%H:%M:%S')}\n" + \
                    f"New Features: WebSocket real-time updates, flash crash detection,\n" + \
                    f"              dynamic position sizing, enhanced mean reversion\n" + \
                    f"Data Mode: {self.poller.mode}\n" + \
                    f"Markets: 15min + Hourly\n{'='*70}\n"
            self._dual_log(header)
            
            checkpoint_task = asyncio.create_task(self._checkpoint_loop())
            last_status = time.time()
            
            while time.time() < end_time and not self.graceful_shutdown:
                await asyncio.sleep(1)
                brti = self.feed.weighted_price
                if not brti: continue
                
                elapsed = int(time.time() - self.start_time)
                momentum_1m = self.feed.get_momentum(60)
                
                # Process both markets
                self._process_market('15m', elapsed, brti, momentum_1m)
                self._process_market('1h', elapsed, brti, momentum_1m)
                
                # Position management (adaptive stop-loss)
                for pos in self.trader.get_open():
                    market_type = pos.get('market_type', '15m')
                    if market_type not in self.poller.markets:
                        continue
                    
                    kalshi = self.poller.markets[market_type]
                    hold_time = time.time() - pos['time']
                    current = kalshi['yes_bid'] if pos['dir'] == 'YES' else (1 - kalshi['yes_ask'])
                    unrealized = (current - pos['entry']) * pos['size']
                    if pos['dir'] == 'NO': unrealized = -unrealized
                    pct = (unrealized / (pos['entry'] * pos['size'])) * 100 if pos['entry'] > 0 else 0
                    
                    # Adaptive stop-loss
                    stop_threshold = -self._get_adaptive_stop(pos['entry']) * 100
                    
                    should_close = False
                    reason = ""
                    if pct > 8: should_close, reason = True, "PROFIT"
                    elif pct < stop_threshold: should_close, reason = True, f"STOP({stop_threshold:.0f}%)"
                    elif hold_time > 180: should_close, reason = True, "TIMEOUT"
                    
                    if should_close:
                        pnl = self.trader.close(pos['id'], current)
                        status = "WIN" if pnl > 0 else "LOSS"
                        strategy = pos.get('strategy', 'unknown')
                        sig = f"[{elapsed:5d}s] {'✅' if pnl>0 else '❌'} {market_type.upper()} {strategy} CLOSE ({reason}): ${pnl:+.2f} | Total: ${self.trader.pnl:+.2f}"
                        self._dual_log(sig)
                
                # Status
                if time.time() - last_status > 60:
                    n_ex = len(self.feed.prices)
                    mom_str = f"{momentum_1m:+.3f}%" if momentum_1m else "N/A"
                    k15 = self.poller.markets.get('15m', {})
                    k1h = self.poller.markets.get('1h', {})
                    k15_str = f"{k15.get('yes_bid', 0):.2f}/{k15.get('yes_ask', 0):.2f}" if k15 else "N/A"
                    k1h_str = f"{k1h.get('yes_bid', 0):.2f}/{k1h.get('yes_ask', 0):.2f}" if k1h else "N/A"
                    
                    wr = self.trader.session_stats['wins'] / max(self.trader.session_stats['total'], 1)
                    flash_count = len(self.flash_detector.flash_crashes)
                    
                    st = f"[{elapsed:5d}s] BTC: ${brti:,.2f} ({n_ex}ex, {mom_str}) | {self.poller.mode} | 15m: {k15_str} | 1h: {k1h_str} | P&L: ${self.trader.pnl:+.2f} ({len(self.trader.trades)}, {wr:.1%} WR, {flash_count} flash)"
                    self._dual_log(st)
                    last_status = time.time()
            
            checkpoint_task.cancel()
            self._summary()
            
        except Exception as e:
            err = f"\n❌ FATAL: {e}\n{traceback.format_exc()}"
            self._dual_log(err)
            self._save_checkpoint()
            self._summary()
    
    def _summary(self):
        elapsed = int(time.time() - self.start_time) if self.start_time else 0
        flash_count = len(self.flash_detector.flash_crashes)
        
        summary = f"\n{'='*70}\nSUMMARY v10\n{'='*70}\nDuration: {elapsed//60}min | Mode: {self.poller.mode} | Signals: {len(self.signals)}\nTrades: {len(self.trader.trades)} | P&L: ${self.trader.pnl:+.2f} | Flash Crashes: {flash_count}\n"
        
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
        
        for s, stats in strategies.items():
            wr = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            summary += f"{s}: {stats['count']} trades, {wr:.0f}% win, ${stats['pnl']:+.2f}\n"
        
        # Dynamic sizing analysis
        size_decisions = [t.get('sizing_decision', {}) for t in self.trader.trades]
        avg_size = sum(t['size'] for t in self.trader.trades) / max(len(self.trader.trades), 1)
        summary += f"Avg position size: ${avg_size:.0f} (base: ${self.trader.base_trade_size})\n"
        
        # Flash crash analysis
        if flash_count > 0:
            flash_trades = [s for s in self.signals if s.get('type') == 'mean_rev_flash']
            summary += f"Flash crash triggers: {len(flash_trades)}/{flash_count} detected\n"
        
        summary += f"{'='*70}\n"
        self._dual_log(summary)
        
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'/home/clawdbot/clawd/btc-arbitrage/data/rt_v10_{ts}.json', 'w') as f:
            json.dump({'duration_min': elapsed//60, 'pnl': self.trader.pnl, 'signals': self.signals,
                      'trades': self.trader.trades, 'flash_crashes': self.flash_detector.flash_crashes,
                      'websocket_mode': self.poller.mode, 'complete': not self.graceful_shutdown}, f, indent=2, default=str)
        
        for f in self.log_files:
            if f and not f.closed: f.close()

async def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 480
    feed = BTCPriceFeed()
    
    # Use WebSocket poller with REST fallback
    poller = KalshiWebSocketPoller()
    
    engine = TradingEngine(feed, poller, duration_min=duration)
    
    feed_task = asyncio.create_task(feed.run())
    poller_task = asyncio.create_task(poller.run())
    
    try:
        await engine.run()
    finally:
        feed.running = False
        poller.running = False
        poller.rest_fallback.running = False
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