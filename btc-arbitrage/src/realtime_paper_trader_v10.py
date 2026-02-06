#!/usr/bin/env python3
"""
Real-time Paper Trader v10 - WebSocket + Enhanced Features + Kelly Criterion + Clustering
Upgraded from v6 with:
1. WebSocket real-time data (fallback to REST polling)
2. Enhanced flash crash detection 
3. Kelly Criterion dynamic position sizing
4. Cross-Exchange Momentum Clustering strategy
5. Closing Line Value (CLV) tracking
6. Orderbook Imbalance strategy
7. Settlement Rush strategy
8. All v6 features preserved

Key Features:
- BTC momentum filter for crash detection
- Volatility-adaptive stop-loss  
- Entry quality filters
- Market timing restrictions (first/last 30s excluded)
- Mean reversion at extremes (>80¢, NO <20¢ disabled)
- 15min market support (KXBTC15M)
- Real-time WebSocket updates with REST fallback
- Flash crash detection with sliding window
- Kelly Criterion position sizing (half-Kelly for safety, 20 trade minimum)
- Cross-exchange momentum clustering detection (3+ exchanges, >0.08% strength)
- CLV tracking for strategy performance analysis
- Orderbook imbalance detection (bid/ask volume ratio)
- Settlement rush aggressive entry in last 5 minutes
- Cached orderbook data with smart rate limiting
"""
import asyncio, json, time, sys, os, traceback, signal
import math
from collections import deque
sys.path.insert(0, '/tmp/pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import websockets
from datetime import datetime
from urllib import request, parse

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

class TickBurstDetector:
    """Detect rapid consecutive BTC price moves in the same direction"""
    def __init__(self, history_length=20):
        self.history_length = history_length
        self.tick_history = deque(maxlen=history_length)
        self.current_burst_direction = None
        self.current_burst_length = 0
        self.current_burst_total_move = 0.0
        
    def update(self, price):
        """Update with new BTC price tick and detect bursts"""
        current_time = time.time()
        
        if len(self.tick_history) > 0:
            last_tick = self.tick_history[-1]
            price_change = price - last_tick['price']
            pct_change = (price_change / last_tick['price']) * 100 if last_tick['price'] > 0 else 0
            
            # Determine if this is a significant move (>$10 or >0.01%)
            is_significant_move = abs(price_change) > 10 or abs(pct_change) > 0.01
            
            if is_significant_move:
                move_direction = 'up' if price_change > 0 else 'down'
                
                if move_direction == self.current_burst_direction:
                    # Continue current burst
                    self.current_burst_length += 1
                    self.current_burst_total_move += abs(pct_change)
                else:
                    # Direction changed or starting new burst
                    self.current_burst_direction = move_direction
                    self.current_burst_length = 1
                    self.current_burst_total_move = abs(pct_change)
            else:
                # Reset burst on insignificant move
                self.current_burst_direction = None
                self.current_burst_length = 0
                self.current_burst_total_move = 0.0
        
        # Add current tick to history
        self.tick_history.append({
            'time': current_time,
            'price': price
        })
        
        # Return burst info
        return self.get_burst_status()
    
    def get_burst_status(self):
        """Return current burst status"""
        if self.current_burst_length >= 3:  # Minimum 3 ticks for a burst
            return {
                'direction': self.current_burst_direction,
                'burst_length': self.current_burst_length,
                'total_move_pct': self.current_burst_total_move
            }
        return {
            'direction': None,
            'burst_length': 0,
            'total_move_pct': 0.0
        }

class SteamDetector:
    """Detect 'smart money' moving Kalshi odds - unusual volume or price jumps"""
    def __init__(self, price_history_duration=300):  # 5 minutes
        self.price_history_duration = price_history_duration
        self.market_price_history = {}  # ticker -> deque of price points
        self.market_volume_history = {}  # ticker -> deque of volume points
        
    def update_market_data(self, ticker, yes_bid, volume):
        """Update price and volume history for a market"""
        current_time = time.time()
        
        # Initialize histories if not present
        if ticker not in self.market_price_history:
            self.market_price_history[ticker] = deque()
            self.market_volume_history[ticker] = deque()
        
        # Add current data
        self.market_price_history[ticker].append({
            'time': current_time,
            'price': yes_bid
        })
        self.market_volume_history[ticker].append({
            'time': current_time,
            'volume': volume
        })
        
        # Clean old data
        cutoff_time = current_time - self.price_history_duration
        while (self.market_price_history[ticker] and 
               self.market_price_history[ticker][0]['time'] < cutoff_time):
            self.market_price_history[ticker].popleft()
        while (self.market_volume_history[ticker] and 
               self.market_volume_history[ticker][0]['time'] < cutoff_time):
            self.market_volume_history[ticker].popleft()
    
    def detect_steam(self, ticker):
        """Detect steam moves: price jumps >3¢ in 60s OR volume spikes >3x average"""
        if ticker not in self.market_price_history:
            return {
                'steam_detected': False,
                'steam_type': None,
                'price_move_cents': 0,
                'volume_spike_ratio': 0,
                'direction': None
            }
        
        current_time = time.time()
        price_history = self.market_price_history[ticker]
        volume_history = self.market_volume_history[ticker]
        
        # Check for price steam (>3¢ move in 60 seconds)
        price_steam_detected = False
        price_move_cents = 0
        price_direction = None
        
        if len(price_history) >= 2:
            # Find price 60 seconds ago
            cutoff_60s = current_time - 60
            price_60s_ago = None
            for price_point in price_history:
                if price_point['time'] >= cutoff_60s:
                    price_60s_ago = price_point['price']
                    break
            
            if price_60s_ago is not None and len(price_history) > 0:
                current_price = price_history[-1]['price']
                price_move_cents = abs(current_price - price_60s_ago) * 100  # Convert to cents
                
                if price_move_cents > 3:  # >3¢ move
                    price_steam_detected = True
                    price_direction = 'up' if current_price > price_60s_ago else 'down'
        
        # Check for volume steam (volume spike >3x average minute volume)
        volume_steam_detected = False
        volume_spike_ratio = 0
        
        if len(volume_history) >= 2:
            # Calculate average minute volume over last 5 minutes
            cutoff_5min = current_time - 300
            cutoff_1min = current_time - 60
            
            # Volume in last minute
            recent_volume = 0
            for vol_point in volume_history:
                if vol_point['time'] >= cutoff_1min:
                    recent_volume = vol_point['volume']
                    break
            
            # Average volume per minute over 5 minutes
            volume_5min_data = [v for v in volume_history if v['time'] >= cutoff_5min]
            if len(volume_5min_data) > 1:
                total_volume_5min = max([v['volume'] for v in volume_5min_data])
                avg_minute_volume = total_volume_5min / 5 if total_volume_5min > 0 else 1
                
                if avg_minute_volume > 0:
                    volume_spike_ratio = recent_volume / avg_minute_volume
                    if volume_spike_ratio > 3:  # 3x average
                        volume_steam_detected = True
        
        # Determine overall steam detection and direction
        # REQUIRE price+volume confirmation (price-only = too many false signals)
        # Price-only allowed if move is huge (>6¢ in 60s)
        if price_steam_detected and price_move_cents >= 6:
            steam_detected = True  # Big price move alone is valid
        else:
            steam_detected = price_steam_detected and volume_steam_detected  # Need both
        steam_type = None
        direction = None
        
        if steam_detected:
            if price_steam_detected and volume_steam_detected:
                steam_type = 'price_and_volume'
                direction = price_direction
            elif price_steam_detected:
                steam_type = 'price'
                direction = price_direction
            else:
                steam_type = 'volume'
                # For volume-only steam, we can't determine direction from this signal alone
                direction = None
        
        return {
            'steam_detected': steam_detected,
            'steam_type': steam_type,
            'price_move_cents': price_move_cents,
            'volume_spike_ratio': volume_spike_ratio,
            'direction': direction
        }

class OrderbookCache:
    """Cache for Kalshi orderbook data with automatic refresh"""
    def __init__(self, cache_duration=30):
        self.cache_duration = cache_duration  # seconds
        self.orderbooks = {}  # ticker -> {data, timestamp}
        self.last_fetch_times = {}
        
    def _fetch_orderbook(self, ticker):
        """Fetch orderbook data from Kalshi API"""
        try:
            # Encode ticker for URL safety
            encoded_ticker = parse.quote(ticker)
            url = f"https://api.elections.kalshi.com/trade-api/v2/markets/{encoded_ticker}/orderbook"
            
            req = request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Accept', 'application/json')
            
            with request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
                
            if 'orderbook' in data:
                return data['orderbook']
            return None
            
        except Exception as e:
            # Silently fail and return None - don't spam logs
            return None
    
    def get_orderbook(self, ticker):
        """Get cached orderbook data or fetch if needed"""
        now = time.time()
        
        # Check if we have cached data that's still valid
        if (ticker in self.orderbooks and 
            now - self.orderbooks[ticker]['timestamp'] < self.cache_duration):
            return self.orderbooks[ticker]['data']
        
        # Check rate limiting - don't fetch more than once every 15 seconds
        if (ticker in self.last_fetch_times and 
            now - self.last_fetch_times[ticker] < 15):
            # Return cached data even if expired, rather than hitting API too often
            if ticker in self.orderbooks:
                return self.orderbooks[ticker]['data']
            return None
        
        # Fetch new data
        self.last_fetch_times[ticker] = now
        orderbook_data = self._fetch_orderbook(ticker)
        
        if orderbook_data:
            self.orderbooks[ticker] = {
                'data': orderbook_data,
                'timestamp': now
            }
            return orderbook_data
        
        # Return cached data if fetch failed
        if ticker in self.orderbooks:
            return self.orderbooks[ticker]['data']
        
        return None
    
    def calculate_imbalance_score(self, ticker):
        """Calculate orderbook imbalance score: (bid_vol - ask_vol) / (bid_vol + ask_vol)"""
        orderbook = self.get_orderbook(ticker)
        if not orderbook:
            return None, 0, 0
        
        # Parse YES side orderbook
        yes_bids = orderbook.get('yes', [])
        yes_asks = orderbook.get('no', [])  # NO orders are asks for YES
        
        # Calculate bid volume (people buying YES)
        total_bid_volume = 0
        for bid_order in yes_bids:
            # Format: [price_cents, quantity]
            if isinstance(bid_order, list) and len(bid_order) >= 2:
                total_bid_volume += bid_order[1]  # quantity
        
        # Calculate ask volume (people selling YES, i.e., buying NO)
        total_ask_volume = 0
        for ask_order in yes_asks:
            if isinstance(ask_order, list) and len(ask_order) >= 2:
                total_ask_volume += ask_order[1]  # quantity
        
        # Calculate imbalance score
        total_volume = total_bid_volume + total_ask_volume
        if total_volume == 0:
            return None, 0, 0
        
        imbalance_score = (total_bid_volume - total_ask_volume) / total_volume
        
        return imbalance_score, total_bid_volume, total_ask_volume

class BTCPriceFeed:
    """BTC and ETH price feed from exchanges"""
    def __init__(self):
        # BTC data (unchanged)
        self.prices = {}
        self.timestamps = {}
        self.weighted_price = None
        self.price_history = deque(maxlen=500)
        self.weights = {'coinbase': 0.35, 'kraken': 0.25, 'bitstamp': 0.20, 'binance_us': 0.20}
        self.reconnect_delays = {}
        self.running = True
        
        # ETH data (new)
        self.eth_prices = {}
        self.eth_timestamps = {}
        self.eth_weighted_price = None
        self.eth_price_history = deque(maxlen=500)
        self.eth_weights = {'coinbase': 0.35, 'kraken': 0.25, 'bitstamp': 0.20, 'binance_us': 0.20}
        self.eth_reconnect_delays = {}
    
    def get_weighted(self):
        if not self.prices: return None
        total_w = w_sum = 0
        for ex, p in self.prices.items():
            w = self.weights.get(ex, 0.1)
            w_sum += p * w
            total_w += w
        return w_sum / total_w if total_w > 0 else None
    
    def get_eth_weighted(self):
        if not self.eth_prices: return None
        total_w = w_sum = 0
        for ex, p in self.eth_prices.items():
            w = self.eth_weights.get(ex, 0.1)
            w_sum += p * w
            total_w += w
        return w_sum / total_w if total_w > 0 else None
    
    def _update(self, exchange, price):
        self.prices[exchange] = price
        self.timestamps[exchange] = time.time()
        self.weighted_price = self.get_weighted()
        if self.weighted_price:
            self.price_history.append({
                'time': time.time(), 
                'price': self.weighted_price,
                'exchange_prices': self.prices.copy()
            })
        self.reconnect_delays[exchange] = 1
    
    def _update_eth(self, exchange, price):
        self.eth_prices[exchange] = price
        self.eth_timestamps[exchange] = time.time()
        self.eth_weighted_price = self.get_eth_weighted()
        if self.eth_weighted_price:
            self.eth_price_history.append({
                'time': time.time(), 
                'price': self.eth_weighted_price,
                'exchange_prices': self.eth_prices.copy()
            })
        self.eth_reconnect_delays[exchange] = 1
    
    def get_momentum(self, lookback_sec=60):
        if len(self.price_history) < 2: return None
        cutoff = time.time() - lookback_sec
        old = next((e['price'] for e in self.price_history if e['time'] >= cutoff), None)
        return ((self.weighted_price - old) / old) * 100 if old and self.weighted_price else None
    
    def get_eth_momentum(self, lookback_sec=60):
        if len(self.eth_price_history) < 2: return None
        cutoff = time.time() - lookback_sec
        old = next((e['price'] for e in self.eth_price_history if e['time'] >= cutoff), None)
        return ((self.eth_weighted_price - old) / old) * 100 if old and self.eth_weighted_price else None
    
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
    
    def get_cluster_signal(self, lookback_sec=10):
        """Detect cross-exchange momentum clustering"""
        if len(self.price_history) < 2:
            return None, 0.0, 0
        
        # Get prices from lookback_sec ago
        cutoff = time.time() - lookback_sec
        old_prices = {}
        
        # Find oldest suitable price point for each exchange
        for entry in self.price_history:
            if entry['time'] >= cutoff:
                break
            # Use the last price before cutoff for each exchange
            for exchange in self.prices:
                if exchange in entry.get('exchange_prices', {}):
                    old_prices[exchange] = entry['exchange_prices'][exchange]
        
        # If we don't have historical exchange-specific data, use price_history
        if not old_prices:
            # Fallback: estimate individual exchange movements from overall trend
            if len(self.price_history) < 5:
                return None, 0.0, 0
            
            cutoff_price = None
            for entry in self.price_history:
                if entry['time'] >= cutoff:
                    cutoff_price = entry['price']
                    break
            
            if not cutoff_price or not self.weighted_price:
                return None, 0.0, 0
            
            # Estimate exchange movements assuming they follow the overall trend
            overall_change = (self.weighted_price - cutoff_price) / cutoff_price
            agreeing_exchanges = 0
            total_strength = 0
            
            # Assume all exchanges moved in the same direction as overall trend
            if abs(overall_change) > 0.0005:  # >0.05% movement
                agreeing_exchanges = len(self.prices)
                total_strength = abs(overall_change)
                direction = 'up' if overall_change > 0 else 'down'
                avg_strength = total_strength
                return direction, avg_strength, agreeing_exchanges
            else:
                return None, 0.0, 0
        
        # Calculate percentage changes for each exchange
        current_prices = self.prices
        changes = {}
        
        for exchange in current_prices:
            if exchange in old_prices and old_prices[exchange] > 0:
                pct_change = (current_prices[exchange] - old_prices[exchange]) / old_prices[exchange]
                changes[exchange] = pct_change
        
        if len(changes) < 3:  # Need at least 3 exchanges for clustering
            return None, 0.0, 0
        
        # Find direction and count agreements
        up_exchanges = [ex for ex, chg in changes.items() if chg > 0.0005]  # >0.05%
        down_exchanges = [ex for ex, chg in changes.items() if chg < -0.0005]  # <-0.05%
        
        # Determine if we have a cluster (3+ exchanges agree)
        if len(up_exchanges) >= 3:
            direction = 'up'
            agreeing_exchanges = len(up_exchanges)
            total_strength = sum(changes[ex] for ex in up_exchanges)
            avg_strength = total_strength / len(up_exchanges)
        elif len(down_exchanges) >= 3:
            direction = 'down' 
            agreeing_exchanges = len(down_exchanges)
            total_strength = sum(abs(changes[ex]) for ex in down_exchanges)
            avg_strength = total_strength / len(down_exchanges)
        else:
            return None, 0.0, 0
        
        return direction, avg_strength, agreeing_exchanges
    
    async def _reconnect_backoff(self, exchange):
        delay = self.reconnect_delays.get(exchange, 1)
        await asyncio.sleep(min(delay, 60))
        self.reconnect_delays[exchange] = min(delay * 2, 60)
    
    async def _coinbase(self):
        self.reconnect_delays['coinbase'] = 1
        while self.running:
            try:
                async with websockets.connect("wss://ws-feed.exchange.coinbase.com", ping_interval=20) as ws:
                    await ws.send(json.dumps({"type":"subscribe","channels":[{"name":"ticker","product_ids":["BTC-USD", "ETH-USD"]}]}))
                    async for msg in ws:
                        if not self.running: break
                        d = json.loads(msg)
                        if d.get('type') == 'ticker' and 'price' in d:
                            if d.get('product_id') == 'BTC-USD':
                                self._update('coinbase', float(d['price']))
                            elif d.get('product_id') == 'ETH-USD':
                                self._update_eth('coinbase', float(d['price']))
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
        self.k_history = {'15m': deque(maxlen=1000), 'btc_daily': deque(maxlen=1000), 'eth_15m': deque(maxlen=1000), 'eth_daily': deque(maxlen=1000)}
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
        self.history = {'15m': deque(maxlen=200), 'btc_daily': deque(maxlen=200), 'eth_15m': deque(maxlen=200), 'eth_daily': deque(maxlen=200)}
        self.last_tickers = {'15m': None, 'btc_daily': None, 'eth_15m': None, 'eth_daily': None}
        self.running = True
        self.mode = "REST"  # Track which mode is active
        self.orderbook_cache = OrderbookCache(cache_duration=30)
    
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
                markets = data['markets']
                
                # For KXBTCD (daily BTC), pick the contract closest to ATM (mid-price closest to 0.50)
                if series_ticker in ('KXBTCD', 'KXETHD'):
                    # Group by settlement time, pick NEAREST settlement first
                    from collections import defaultdict
                    by_close = defaultdict(list)
                    now = time.time()
                    for market in markets:
                        ct = market.get('close_time', '')
                        by_close[ct].append(market)
                    
                    # Sort settlement times by how soon they close
                    sorted_closes = sorted(by_close.keys(), key=lambda ct: ct)  # ISO strings sort correctly
                    
                    for close_time in sorted_closes:
                        group = by_close[close_time]
                        best_market = None
                        best_distance = float('inf')
                        
                        for market in group:
                            yes_bid = market.get('yes_bid', 0) / 100
                            yes_ask = market.get('yes_ask', 0) / 100
                            spread = yes_ask - yes_bid
                            
                            if spread > 0.10:
                                continue
                            
                            mid_price = (yes_bid + yes_ask) / 2
                            distance = abs(mid_price - 0.50)
                            
                            if distance < best_distance:
                                best_distance = distance
                                best_market = market
                        
                        if best_market:
                            m = best_market
                            return {'ticker': m['ticker'], 'yes_bid': m.get('yes_bid', 0) / 100,
                                   'yes_ask': m.get('yes_ask', 0) / 100, 'volume': m.get('volume', 0),
                                   'close_time': m.get('close_time'), 'time': time.time(),
                                   'series': series_ticker}
                else:
                    # For other series, use first market as before
                    m = markets[0]
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
                # Fetch all market types
                m15 = await asyncio.get_event_loop().run_in_executor(None, self._fetch, 'KXBTC15M')
                mbtcd = await asyncio.get_event_loop().run_in_executor(None, self._fetch, 'KXBTCD')
                meth15 = await asyncio.get_event_loop().run_in_executor(None, self._fetch, 'KXETH15M')
                methd = await asyncio.get_event_loop().run_in_executor(None, self._fetch, 'KXETHD')
                
                # Update markets
                for key, data in [('15m', m15), ('btc_daily', mbtcd), ('eth_15m', meth15), ('eth_daily', methd)]:
                    if data:
                        self.last_tickers[key] = self.markets.get(key, {}).get('ticker')
                        self.markets[key] = data
                        self.history[key].append(data)
                
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            self.running = False

class KalshiWebSocketPoller:
    """WebSocket-based market poller with REST fallback"""
    def __init__(self):
        self.markets = {}
        self.history = {'15m': deque(maxlen=200), 'btc_daily': deque(maxlen=200), 'eth_15m': deque(maxlen=200), 'eth_daily': deque(maxlen=200)}
        self.last_tickers = {'15m': None, 'btc_daily': None, 'eth_15m': None, 'eth_daily': None}
        self.running = True
        self.mode = "WebSocket"
        self.rest_fallback = DualMarketPoller(interval=5)
        self.ws_connected = False
        self.ws_client = None
        self.orderbook_cache = OrderbookCache(cache_duration=30)
        
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
            
            # Track last WS update time
            self._last_ws_update = time.time()
            
            if 'KXBTC15M' in ticker:
                market_type = '15m'
            elif 'KXETHD' in ticker:
                market_type = 'eth_daily'
            elif 'KXBTCD' in ticker:
                market_type = 'btc_daily'
            elif 'KXETH15M' in ticker:
                market_type = 'eth_15m'
            else:
                return
            
            # Convert to same format as REST
            if market_type == '15m':
                series = 'KXBTC15M'
            elif market_type == 'btc_daily':
                series = 'KXBTCD'
            elif market_type == 'eth_15m':
                series = 'KXETH15M'
            else:
                series = 'UNKNOWN'
            
            market_data = {
                'ticker': ticker,
                'yes_bid': data.get('yes_bid', 0) / 100 if 'yes_bid' in data else 0,
                'yes_ask': data.get('yes_ask', 0) / 100 if 'yes_ask' in data else 0,
                'volume': data.get('volume', 0),
                'close_time': data.get('close_time'),
                'time': time.time(),
                'series': series
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
            self._ws_task = asyncio.create_task(self.ws_client.start(series=["KXBTC15M", "KXBTCD", "KXETH15M", "KXETHD"]))
            
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
            
            # Monitor WebSocket health — also sync REST data as fallback
            ws_data_count = 0
            while self.running:
                if not self.ws_connected or not self.ws_client or (self.ws_client.ws and getattr(self.ws_client.ws, "close_code", None) is not None):
                    print("⚠️ WebSocket disconnected, falling back to REST", flush=True)
                    self.mode = "REST"
                    break
                # Check if WebSocket is actively delivering market data
                ws_active = hasattr(self, '_last_ws_update') and (time.time() - self._last_ws_update < 30)
                
                if ws_active and self.markets.get('15m'):
                    # WS is delivering data — use it directly
                    if self.mode != "WebSocket":
                        self.mode = "WebSocket"
                        print("📡 WebSocket data flowing — switching to pure WebSocket mode", flush=True)
                    ws_data_count += 1
                elif self.rest_fallback.markets.get('15m'):
                    # WS not delivering — use REST fallback
                    self.markets = self.rest_fallback.markets.copy()
                    self.history = {k: deque(v) for k, v in self.rest_fallback.history.items()}
                    self.last_tickers = self.rest_fallback.last_tickers.copy()
                    if self.mode != "REST+WS":
                        self.mode = "REST+WS"
                await asyncio.sleep(1)
            
            if self.ws_client:
                await self.ws_client.stop()
            rest_task.cancel()
        else:
            # Use REST polling as fallback
            self.mode = "REST"
            print("🔄 Using REST polling mode for Kalshi data (WebSocket unavailable)", flush=True)
            
            # Copy data from REST fallback
            rest_task = asyncio.create_task(self.rest_fallback.run())
            while self.running:
                self.markets = self.rest_fallback.markets.copy()
                self.history = {k: deque(v) for k, v in self.rest_fallback.history.items()}
                self.last_tickers = self.rest_fallback.last_tickers.copy()
                # Share orderbook cache with REST fallback
                self.orderbook_cache = self.rest_fallback.orderbook_cache
                await asyncio.sleep(1)
            rest_task.cancel()

class PaperTrader:
    """Enhanced paper trader with Kelly Criterion sizing and CLV tracking"""
    def __init__(self, balance=1000, base_trade_size=10):
        self.balance = balance
        self.initial = balance
        self.base_trade_size = base_trade_size
        self.current_trade_size = base_trade_size
        self.positions = []
        self.trades = []
        self.pnl = 0
        self.last_exit_time = 0
        self.last_exit_time_by_market = {}  # Per-market cooldown tracking
        self.consecutive_losses_by_market = {}  # Per-market loss streaks
        self.consecutive_wins = 0
        self.session_stats = {'wins': 0, 'losses': 0, 'total': 0}
        
        # Kelly Criterion data per strategy
        self.strategy_stats = {
            'delay_arb': {'wins': 0, 'losses': 0, 'total_win_amount': 0, 'total_loss_amount': 0, 'trades': []},
            'orderbook_imbalance': {'wins': 0, 'losses': 0, 'total_win_amount': 0, 'total_loss_amount': 0, 'trades': []},
            'settlement_rush': {'wins': 0, 'losses': 0, 'total_win_amount': 0, 'total_loss_amount': 0, 'trades': []},
            'momentum_cluster': {'wins': 0, 'losses': 0, 'total_win_amount': 0, 'total_loss_amount': 0, 'trades': []}
        }
        
        # CLV tracking
        self.clv_data = []
    
    def _calculate_kelly_size(self, strategy):
        """Calculate Kelly Criterion position size for given strategy"""
        if strategy not in self.strategy_stats:
            return self.base_trade_size
        
        stats = self.strategy_stats[strategy]
        total_trades = len(stats['trades'])
        
        # Use fixed size until we have 20 trades for this strategy
        if total_trades < 20:
            return self.base_trade_size
        
        wins = stats['wins']
        losses = total_trades - wins
        
        if losses == 0 or wins == 0:
            # Not enough data for Kelly, use fixed size
            return self.base_trade_size
        
        # Calculate win rate
        win_rate = wins / total_trades
        
        # Calculate average win and loss amounts
        avg_win = stats['total_win_amount'] / wins if wins > 0 else 0
        avg_loss = abs(stats['total_loss_amount']) / losses if losses > 0 else 1
        
        if avg_loss == 0:
            avg_loss = 1  # Prevent division by zero
        
        # Kelly formula: f* = p - q/b
        # where p = win rate, q = loss rate, b = average win / average loss
        win_loss_ratio = avg_win / avg_loss
        kelly_fraction = win_rate - (1 - win_rate) / win_loss_ratio
        
        # Use HALF-Kelly for safety
        half_kelly = kelly_fraction / 2
        
        # Convert fraction to dollar amount (assume $100 as base capital for fraction calculation)
        kelly_size = half_kelly * 100
        
        # Clamp between $5 and $50
        kelly_size = max(5, min(50, kelly_size))
        
        return int(kelly_size)
    
    def open(self, direction, price, ticker, market_type, strategy):
        # Calculate Kelly Criterion position size
        trade_size = self._calculate_kelly_size(strategy)
        
        # ETH 15M: half position size (choppier market, wider spreads)
        if market_type == 'eth_15m':
            trade_size = max(5, trade_size // 2)
        
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
        
        # Calculate Kelly metrics for logging
        strategy_stats = self.strategy_stats.get(strategy, {})
        total_trades = len(strategy_stats.get('trades', []))
        win_rate = 0
        win_loss_ratio = 0
        kelly_fraction = 0
        
        if total_trades >= 20:
            wins = strategy_stats.get('wins', 0)
            win_rate = wins / total_trades if total_trades > 0 else 0
            avg_win = strategy_stats.get('total_win_amount', 0) / max(wins, 1)
            avg_loss = abs(strategy_stats.get('total_loss_amount', 0)) / max(total_trades - wins, 1)
            win_loss_ratio = avg_win / max(avg_loss, 1)
            kelly_fraction = (win_rate - (1 - win_rate) / win_loss_ratio) / 2  # Half-Kelly
        
        pos = {'id': len(self.positions), 'dir': direction, 'size': trade_size,
               'entry': actual_price, 'theoretical_entry': theoretical_price,
               'slippage_entry': actual_price - theoretical_price,
               'time': time.time(), 'ticker': ticker, 'open': True,
               'market_type': market_type, 'strategy': strategy,
               'sizing_decision': {
                   'method': 'kelly' if total_trades >= 20 else 'fixed',
                   'base_size': self.base_trade_size,
                   'calculated_size': trade_size,
                   'strategy_trades': total_trades,
                   'win_rate': win_rate,
                   'win_loss_ratio': win_loss_ratio,
                   'kelly_fraction': kelly_fraction
               }}
        if fill_info:
            pos['entry_fill'] = {'vwap': fill_info.get('vwap', 0), 
                                 'levels': fill_info.get('levels_consumed', 0),
                                 'slippage': fill_info.get('slippage', 0),
                                 'partial': fill_info.get('partial', False)}
        self.positions.append(pos)
        self.balance -= cost
        return pos['id']
    
    def close(self, pos_id, exit_price, settlement_price=None):
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
        market_type = pos.get('market_type', 'unknown')
        self.last_exit_time_by_market[market_type] = time.time()
        
        # Update session stats and consecutive wins
        self.session_stats['total'] += 1
        if pnl > 0:
            self.session_stats['wins'] += 1
            self.consecutive_wins += 1
            self.consecutive_losses_by_market[market_type] = 0
        else:
            self.session_stats['losses'] += 1
            self.consecutive_wins = 0  # Reset consecutive wins on loss
            self.consecutive_losses_by_market[market_type] = self.consecutive_losses_by_market.get(market_type, 0) + 1
        
        # Update strategy-specific Kelly stats
        strategy = pos.get('strategy', 'unknown')
        if strategy in self.strategy_stats:
            self.strategy_stats[strategy]['trades'].append(pos.copy())
            if pnl > 0:
                self.strategy_stats[strategy]['wins'] += 1
                self.strategy_stats[strategy]['total_win_amount'] += pnl
            else:
                self.strategy_stats[strategy]['total_loss_amount'] += pnl
        
        # Track CLV data
        if settlement_price is not None:
            # Calculate CLV: how much better/worse our entry was vs settlement
            entry_price = pos['entry']
            if pos['dir'] == 'YES':
                clv = settlement_price - entry_price
            else:  # NO position
                clv = (1 - settlement_price) - entry_price
            
            clv_record = {
                'strategy': strategy,
                'entry_price': entry_price,
                'exit_price': actual_exit,
                'settlement_price': settlement_price,
                'clv': clv,
                'direction': pos['dir'],
                'pnl': pnl,
                'close_time': time.time()
            }
            self.clv_data.append(clv_record)
        
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
            'consecutive_wins': self.consecutive_wins,
            'strategy_stats': self.strategy_stats,
            'clv_data': self.clv_data
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
        self.last_kalshi_bids = {'15m': None, 'btc_daily': None, 'eth_15m': None, 'eth_daily': None}
        self.state_file = '/home/clawdbot/clawd/btc-arbitrage/data/rt_v10_state.json'
        self.graceful_shutdown = False
        
        # Enhanced flash crash detector
        self.flash_detector = FlashCrashDetector()
        
        # Placeholder detectors (to avoid errors with incomplete strategies)
        self.steam_detector = type('SteamDetector', (), {
            'update_market_data': lambda self, *args: None,
            'detect_steam': lambda self, *args: {'steam_detected': False, 'direction': None}
        })()
        self.tick_burst_detector = type('TickBurstDetector', (), {
            'update': lambda self, *args: None
        })()
        
        # New strategy detectors
        self.tick_burst_detector = TickBurstDetector()
        self.steam_detector = SteamDetector()
    
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
                'tick_burst_status': self.tick_burst_detector.get_burst_status(),
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
    
    def _should_enter(self, market_type, elapsed, strategy=None):
        """Entry quality filters (Priority 4 from RESEARCH-NOTES.md)"""
        # Startup grace period: 120s for SteamDetector to build reliable history
        if elapsed < 120:
            return False, "startup_warmup"
        
        kalshi = self.poller.markets.get(market_type, {})
        time_remaining = self.poller.time_until_close(market_type)
        
        # Settlement rush strategy has different rules
        if strategy == 'settlement_rush':
            # Only check basic spread and volume for settlement rush
            spread = kalshi.get('yes_ask', 1) - kalshi.get('yes_bid', 0)
            if spread > 0.05:
                return False, "spread_too_wide"
            if kalshi.get('volume', 0) < 50:
                return False, "volume_too_low"
            return True, "passed_settlement_rush"
        
        # Regular strategy filters
        # Check time remaining
        if time_remaining < 300:  # <5 min
            return False, "too_close_to_settlement"
        
        # Check if in first/last 30 seconds of window
        market_age = (time_remaining % 900)
        if market_age < 30 or market_age > 870:
            return False, "market_transition_window"
        
        # MIN PRICE FILTER: Skip contracts priced below $0.15 or above $0.85
        # These are deep ITM/OTM — tiny moves = massive % swings = pure noise
        yes_bid = kalshi.get('yes_bid', 0)
        yes_ask = kalshi.get('yes_ask', 1)
        mid_price = (yes_bid + yes_ask) / 2
        if mid_price < 0.15 or mid_price > 0.85:
            return False, "price_too_extreme"
        
        # Check spread (tighter for ETH — wider spreads eat into edge)
        spread = yes_ask - yes_bid
        max_spread = 0.04 if market_type in ('eth_15m', 'eth_daily') else 0.05
        if spread > max_spread:
            return False, "spread_too_wide"
        
        # Check volume
        if kalshi.get('volume', 0) < 50:
            return False, "volume_too_low"
        
        # Check per-market cooldown (120s after a loss on same market, 60s after a win)
        last_exit_market = self.trader.last_exit_time_by_market.get(market_type, 0)
        consec_losses = self.trader.consecutive_losses_by_market.get(market_type, 0)
        cooldown_secs = 120 if consec_losses > 0 else 60
        # Circuit breaker: 3+ consecutive losses on same market → 300s cooldown
        if consec_losses >= 3:
            cooldown_secs = 300
        if time.time() - last_exit_market < cooldown_secs:
            return False, f"cooldown_period({cooldown_secs}s,losses={consec_losses})"
        
        # Global cooldown (no entry within 30s of ANY exit)
        if time.time() - self.trader.last_exit_time < 30:
            return False, "global_cooldown"
        
        return True, "passed"
    
    def _get_stop_dollar(self, entry_price, strategy=None, market_type=None):
        """Absolute dollar stop-loss — better for cheap contracts.
        
        Returns max loss in dollars per contract (e.g., 0.08 = lose $0.08 max).
        For cheap contracts ($0.15-0.35), percentage stops are nonsensical
        because a 1-2 cent move = 5-15% swing.
        """
        btc_vol = self.feed.get_volatility(300)
        
        # Base stop: $0.08 per contract
        base_stop = 0.08
        
        # Steam trades: widened stops to survive noise — BTC $0.15, ETH $0.12
        if strategy == 'steam_follow':
            base_stop = 0.12 if market_type in ('eth_15m', 'eth_daily') else 0.15
        
        # Settlement rush: tighter stop ($0.05) — should resolve fast
        if strategy == 'settlement_rush':
            base_stop = 0.05
        
        # Widen slightly in high vol
        vol_adj = 1.0 + min(btc_vol * 5, 0.5)  # up to 50% wider in high vol
        stop = base_stop * vol_adj
        
        # Clamp: min $0.04, max $0.15
        return max(0.04, min(0.15, stop))
    
    def _process_market(self, market_type, elapsed, brti, momentum_1m):
        """Process all strategies for one market"""
        if market_type not in self.poller.markets:
            return
        
        kalshi = self.poller.markets[market_type]
        last_bid = self.last_kalshi_bids[market_type]
        
        # Skip if market transition (but only for 5 seconds, then accept new market)
        if self.poller.is_market_transition(market_type):
            if not hasattr(self, '_transition_start'):
                self._transition_start = {}
            if market_type not in self._transition_start:
                self._transition_start[market_type] = time.time()
                self._dual_log(f"[{elapsed:5d}s] 🔄 {market_type.upper()} transition — new market detected")
            
            # After 5 seconds, accept the new market
            if time.time() - self._transition_start[market_type] > 5:
                # Force update last_tickers to accept new market
                new_ticker = self.poller.markets.get(market_type, {}).get('ticker')
                if hasattr(self.poller, 'rest_fallback'):
                    self.poller.rest_fallback.last_tickers[market_type] = new_ticker
                self.poller.last_tickers[market_type] = new_ticker
                del self._transition_start[market_type]
                # Record when transition completed — enforce cooldown before trading
                if not hasattr(self, '_transition_complete_time'):
                    self._transition_complete_time = {}
                self._transition_complete_time[market_type] = time.time()
                # Clear steam detector history for this market's old ticker
                # (prevents false signals from old vs new contract price comparison)
                self.steam_detector.market_price_history.clear()
                self.steam_detector.market_volume_history.clear()
                self._dual_log(f"[{elapsed:5d}s] ✅ {market_type.upper()} transition complete → {new_ticker}")
            
            self.last_kalshi_bids[market_type] = None
            return
        
        # Post-transition cooldown: 120s after transition completes (price discovery period)
        if hasattr(self, '_transition_complete_time') and market_type in self._transition_complete_time:
            secs_since = time.time() - self._transition_complete_time[market_type]
            if secs_since < 120:
                self.last_kalshi_bids[market_type] = kalshi.get('yes_bid')
                return
        
        # Check entry filters
        can_enter, reason = self._should_enter(market_type, elapsed)
        if not can_enter:
            # Only log significant rejections
            if reason in ['too_close_to_settlement', 'spread_too_wide']:
                pass  # Skip logging
            self.last_kalshi_bids[market_type] = kalshi['yes_bid']
            return
        
        # Already have position in this market from ANY strategy?
        if len(self.trader.get_open(market_type)) > 0:
            self.last_kalshi_bids[market_type] = kalshi['yes_bid']
            return
        
        k_bid = kalshi['yes_bid']
        k_ask = kalshi['yes_ask']
        ticker = kalshi['ticker']
        
        # Update detectors with current data (skip flash/steam for daily — ATM contract changes cause false signals)
        is_15m = market_type in ('15m', 'eth_15m')
        if is_15m:
            self.flash_detector.update_k_value(market_type, k_bid)
            self.steam_detector.update_market_data(ticker, k_bid, kalshi.get('volume', 0))
        
        # Update tick burst detector if we have BTC price
        tick_burst_status = None
        if brti is not None and is_15m:
            tick_burst_status = self.tick_burst_detector.update(brti)
        
        # Check for flash crash (15m only)
        is_flash_crash, drop_pct = (False, 0)
        if is_15m:
            is_flash_crash, drop_pct = self.flash_detector.detect_flash_crash(market_type, k_bid)
        
        # Check time until settlement for settlement rush
        time_until_close = self.poller.time_until_close(market_type)
        
        # STRATEGY 1: Mean Reversion — ALL DISABLED
        # PnL bug discovered: NO trades had inverted PnL display
        # Real performance across all versions: mean_rev_high loses money (-$29.60 v6, -$40.70 v7, -$61.50 v8)
        # Flash crash detection kept for logging only, not trading
        if is_flash_crash:
            self._dual_log(f"[{elapsed:5d}s] ⚡ FLASH CRASH LOGGED (no trade): {market_type.upper()} K dropped {drop_pct:.1%}")
        
        # STRATEGY 2: Settlement Rush - Last 5 minutes for 15m/eth_15m, 1 hour for daily markets
        settlement_window = 3600 if market_type in ('btc_daily', 'eth_daily') else 300  # 1 hour vs 5 minutes
        underlying_price = brti if market_type in ('15m', 'btc_daily') else self.feed.eth_weighted_price
        
        if time_until_close <= settlement_window and underlying_price is not None:
            # Extract strike price from ticker (format: KXBTC-26FEB02-95000)
            try:
                parts = ticker.split('-')
                if len(parts) >= 3:
                    strike_price = float(parts[-1])
                    
                    # Calculate how far underlying asset is from strike (implied probability)
                    distance_from_strike = abs(underlying_price - strike_price) / strike_price
                    implied_prob = 0.5 + (0.5 * ((underlying_price - strike_price) / strike_price) / 0.02)  # Rough approximation
                    implied_prob = max(0.1, min(0.9, implied_prob))  # Clamp to reasonable range
                    
                    # If BTC price clearly favors one side (>60% probability) and spread is reasonable
                    spread = k_ask - k_bid
                    if spread < 0.05:  # Spread < 5¢
                        if underlying_price > strike_price and implied_prob > 0.6:
                            # Asset clearly above strike, buy YES
                            entry = k_ask
                            direction = 'YES'
                            pos_id = self.trader.open(direction, entry, ticker, market_type, 'settlement_rush')
                            if pos_id is not None:
                                # Log Kelly sizing decision
                                pos = self.trader.positions[-1]  # Get the position we just opened
                                sizing = pos.get('sizing_decision', {})
                                if sizing.get('method') == 'kelly':
                                    self._dual_log(f"[{elapsed:5d}s] 💰 Kelly: settlement_rush WR={sizing['win_rate']:.0%} W/L={sizing['win_loss_ratio']:.1f}x → half-kelly={sizing['kelly_fraction']:.2f} → size=${sizing['calculated_size']}")
                                
                                asset_name = 'BTC' if market_type in ('15m', 'btc_daily') else 'ETH'
                                self._dual_log(f"[{elapsed:5d}s] 🚀 {market_type.upper()} SETTLEMENT_RUSH: {asset_name} ${underlying_price:,.0f} vs ${strike_price:,.0f} → {direction}@{entry:.2f} (T-{time_until_close:.0f}s)")
                                self.signals.append({'type': 'settlement_rush', 'market': market_type, 'time': elapsed})
                        elif underlying_price < strike_price and (1 - implied_prob) > 0.6:
                            # Asset clearly below strike, buy NO
                            entry = 1 - k_bid
                            direction = 'NO'
                            pos_id = self.trader.open(direction, entry, ticker, market_type, 'settlement_rush')
                            if pos_id is not None:
                                # Log Kelly sizing decision
                                pos = self.trader.positions[-1]  # Get the position we just opened
                                sizing = pos.get('sizing_decision', {})
                                if sizing.get('method') == 'kelly':
                                    self._dual_log(f"[{elapsed:5d}s] 💰 Kelly: settlement_rush WR={sizing['win_rate']:.0%} W/L={sizing['win_loss_ratio']:.1f}x → half-kelly={sizing['kelly_fraction']:.2f} → size=${sizing['calculated_size']}")
                                
                                asset_name = 'BTC' if market_type in ('15m', 'btc_daily') else 'ETH'
                                self._dual_log(f"[{elapsed:5d}s] 🚀 {market_type.upper()} SETTLEMENT_RUSH: {asset_name} ${underlying_price:,.0f} vs ${strike_price:,.0f} → {direction}@{entry:.2f} (T-{time_until_close:.0f}s)")
                                self.signals.append({'type': 'settlement_rush', 'market': market_type, 'time': elapsed})
            except (ValueError, IndexError):
                pass  # Could not parse strike price
        
        # STRATEGY 3: Steam Move Detection - Smart money following
        elif time_until_close > settlement_window:  # Only use when not in settlement rush period
            steam_result = self.steam_detector.detect_steam(ticker)
            
            if steam_result['steam_detected'] and steam_result['direction']:
                # Follow the direction of the steam move
                direction = 'YES' if steam_result['direction'] == 'up' else 'NO'
                entry = k_ask if direction == 'YES' else (1 - k_bid)
                
                if 0.15 <= entry <= 0.85:
                    pos_id = self.trader.open(direction, entry, ticker, market_type, 'steam_follow')
                    if pos_id is not None:
                        steam_desc = f"{steam_result['steam_type']}"
                        if steam_result['price_move_cents'] > 0:
                            steam_desc += f" +{steam_result['price_move_cents']:.0f}¢"
                        if steam_result['volume_spike_ratio'] > 1:
                            steam_desc += f" (vol spike {steam_result['volume_spike_ratio']:.1f}x)"
                        
                        self._dual_log(f"[{elapsed:5d}s] 🔥 {market_type.upper()} STEAM: K price jumped {steam_desc} → {direction}@{entry:.2f}")
                        self.signals.append({'type': 'steam_follow', 'market': market_type, 'time': elapsed})
        
        # STRATEGY 4: Tick Momentum Burst Detection
        elif time_until_close > settlement_window and tick_burst_status and tick_burst_status['direction']:
            # Check if we have a strong enough burst
            if (tick_burst_status['burst_length'] >= 4 and 
                tick_burst_status['total_move_pct'] > 0.10):
                
                direction = 'YES' if tick_burst_status['direction'] == 'up' else 'NO'
                entry = k_ask if direction == 'YES' else (1 - k_bid)
                
                if 0.15 <= entry <= 0.85:
                    pos_id = self.trader.open(direction, entry, ticker, market_type, 'tick_burst')
                    if pos_id is not None:
                        self._dual_log(f"[{elapsed:5d}s] ⚡ {market_type.upper()} TICK_BURST: {tick_burst_status['burst_length']} consecutive {tick_burst_status['direction'].upper()} ticks, total +{tick_burst_status['total_move_pct']:.2f}% → {direction}@{entry:.2f}")
                        self.signals.append({'type': 'tick_burst', 'market': market_type, 'time': elapsed})
        
        # STRATEGY 5: Cross-Exchange Momentum Clustering
        elif time_until_close > settlement_window:  # Only use when not in settlement rush period
            cluster_direction, cluster_strength, num_agreeing = self.feed.get_cluster_signal(lookback_sec=10)
            
            if (cluster_direction is not None and 
                num_agreeing >= 3 and 
                cluster_strength > 0.0008):  # >0.08% strength
                
                # Don't trade if delay_arb would also trigger (avoid doubling up)
                delay_arb_would_trigger = False
                if last_bid is not None and last_bid > 0.01 and momentum_1m is not None:
                    kalshi_chg = ((k_bid - last_bid) / last_bid * 100)
                    if abs(momentum_1m) > 0.20 and abs(kalshi_chg) < 5:
                        delay_arb_would_trigger = True
                
                if not delay_arb_would_trigger:
                    direction = 'YES' if cluster_direction == 'up' else 'NO'
                    entry = k_ask if direction == 'YES' else (1 - k_bid)
                    
                    if 0.15 <= entry <= 0.85:
                        pos_id = self.trader.open(direction, entry, ticker, market_type, 'momentum_cluster')
                        if pos_id is not None:
                            # Log Kelly sizing decision
                            pos = self.trader.positions[-1]  # Get the position we just opened
                            sizing = pos.get('sizing_decision', {})
                            if sizing.get('method') == 'kelly':
                                self._dual_log(f"[{elapsed:5d}s] 💰 Kelly: momentum_cluster WR={sizing['win_rate']:.0%} W/L={sizing['win_loss_ratio']:.1f}x → half-kelly={sizing['kelly_fraction']:.2f} → size=${sizing['calculated_size']}")
                            
                            self._dual_log(f"[{elapsed:5d}s] 🔄 {market_type.upper()} CLUSTER: {num_agreeing}/4 exchanges {cluster_direction.upper()} avg +{cluster_strength:.3%} → {direction}@{entry:.2f}")
                            self.signals.append({'type': 'momentum_cluster', 'market': market_type, 'time': elapsed, 'strength': cluster_strength, 'num_agreeing': num_agreeing})
        
        # STRATEGY 6: Orderbook Imbalance
        elif time_until_close > settlement_window:  # Only use when not in settlement rush period
            imbalance_score, bid_vol, ask_vol = self.poller.orderbook_cache.calculate_imbalance_score(ticker)
            
            if imbalance_score is not None:
                total_volume = bid_vol + ask_vol
                min_volume_threshold = 100  # Minimum volume to avoid thin books
                
                if total_volume > min_volume_threshold:
                    # Strong buy pressure suggests price going up
                    if imbalance_score > 0.3:
                        direction = 'YES'
                        entry = k_ask
                        pos_id = self.trader.open(direction, entry, ticker, market_type, 'orderbook_imbalance')
                        if pos_id is not None:
                            # Log Kelly sizing decision
                            pos = self.trader.positions[-1]  # Get the position we just opened
                            sizing = pos.get('sizing_decision', {})
                            if sizing.get('method') == 'kelly':
                                self._dual_log(f"[{elapsed:5d}s] 💰 Kelly: orderbook_imbalance WR={sizing['win_rate']:.0%} W/L={sizing['win_loss_ratio']:.1f}x → half-kelly={sizing['kelly_fraction']:.2f} → size=${sizing['calculated_size']}")
                            
                            self._dual_log(f"[{elapsed:5d}s] 📊 {market_type.upper()} OB_IMBALANCE: score={imbalance_score:+.2f} bid_vol={bid_vol} ask_vol={ask_vol} → {direction}@{entry:.2f}")
                            self.signals.append({'type': 'orderbook_imbalance', 'market': market_type, 'time': elapsed, 'score': imbalance_score})
                    
                    # Strong sell pressure suggests price going down
                    elif imbalance_score < -0.3:
                        direction = 'NO'
                        entry = 1 - k_bid
                        pos_id = self.trader.open(direction, entry, ticker, market_type, 'orderbook_imbalance')
                        if pos_id is not None:
                            # Log Kelly sizing decision
                            pos = self.trader.positions[-1]  # Get the position we just opened
                            sizing = pos.get('sizing_decision', {})
                            if sizing.get('method') == 'kelly':
                                self._dual_log(f"[{elapsed:5d}s] 💰 Kelly: orderbook_imbalance WR={sizing['win_rate']:.0%} W/L={sizing['win_loss_ratio']:.1f}x → half-kelly={sizing['kelly_fraction']:.2f} → size=${sizing['calculated_size']}")
                            
                            self._dual_log(f"[{elapsed:5d}s] 📊 {market_type.upper()} OB_IMBALANCE: score={imbalance_score:+.2f} bid_vol={bid_vol} ask_vol={ask_vol} → {direction}@{entry:.2f}")
                            self.signals.append({'type': 'orderbook_imbalance', 'market': market_type, 'time': elapsed, 'score': imbalance_score})
        
        # STRATEGY 7: Delay Arbitrage — Original profitable strategy
        elif last_bid is not None and last_bid > 0.01 and momentum_1m is not None:
            kalshi_chg = ((k_bid - last_bid) / last_bid * 100)
            
            # BTC moved but K hasn't caught up
            if abs(momentum_1m) > 0.20 and abs(kalshi_chg) < 5:
                direction = 'YES' if momentum_1m > 0 else 'NO'
                entry = k_ask if direction == 'YES' else (1 - k_bid)
                
                if 0.15 <= entry <= 0.85:
                    pos_id = self.trader.open(direction, entry, ticker, market_type, 'delay_arb')
                    if pos_id is not None:
                        # Log Kelly sizing decision
                        pos = self.trader.positions[-1]  # Get the position we just opened
                        sizing = pos.get('sizing_decision', {})
                        if sizing.get('method') == 'kelly':
                            self._dual_log(f"[{elapsed:5d}s] 💰 Kelly: delay_arb WR={sizing['win_rate']:.0%} W/L={sizing['win_loss_ratio']:.1f}x → half-kelly={sizing['kelly_fraction']:.2f} → size=${sizing['calculated_size']}")
                        
                        self._dual_log(f"[{elapsed:5d}s] 🎯 {market_type.upper()} DELAY_ARB: BTC {momentum_1m:+.3f}% K {kalshi_chg:+.1f}% → {direction}@{entry:.2f}")
                        self.signals.append({'type': 'delay_arb', 'market': market_type, 'time': elapsed})
        
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
            
            header = f"\n{'='*70}\nv10 - WebSocket + Multi-Market Support\n{'='*70}\n" + \
                    f"Duration: {self.duration//60}min | Start: {datetime.now().strftime('%H:%M:%S')}\n" + \
                    f"New Features: WebSocket real-time updates, flash crash detection,\n" + \
                    f"              dynamic position sizing, multi-market support\n" + \
                    f"Data Mode: {self.poller.mode}\n" + \
                    f"Markets: KXBTC15M, KXBTCD, KXETH15M, KXETHD\n{'='*70}\n"
            self._dual_log(header)
            
            checkpoint_task = asyncio.create_task(self._checkpoint_loop())
            last_status = time.time()

            
            while time.time() < end_time and not self.graceful_shutdown:
                await asyncio.sleep(1)
                brti = self.feed.weighted_price
                if not brti: continue
                
                elapsed = int(time.time() - self.start_time)
                try:
                    momentum_1m = self.feed.get_momentum(60)
                    eth_momentum_1m = self.feed.get_eth_momentum(60)
                    
                    # Process all markets
                    for mt, price, mom in [('15m', brti, momentum_1m), ('btc_daily', brti, momentum_1m)]:
                        self._process_market(mt, elapsed, price, mom)
                    eth_price = self.feed.eth_weighted_price
                    if eth_price:
                        for mt in ['eth_daily', 'eth_15m']:
                            self._process_market(mt, elapsed, eth_price, eth_momentum_1m)
                except Exception as e:
                    self._dual_log(f"[{elapsed:5d}s] ⚠️ LOOP ERROR: {e}")
                    import traceback; traceback.print_exc()
                
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
                    
                    # Dollar-based stop-loss + trailing stop
                    # NOTE: `current` already accounts for direction:
                    #   YES: current = yes_bid (higher = better)
                    #   NO:  current = 1 - yes_ask (higher = better)
                    # So profit/loss is always: current - entry (same for both)
                    strategy = pos.get('strategy', 'unknown')
                    stop_dollar = self._get_stop_dollar(pos['entry'], strategy, market_type)
                    profit_per_contract = current - pos['entry']
                    loss_per_contract = pos['entry'] - current  # positive when losing
                    
                    # Trailing stop: track highest profit, lock in gains
                    if 'max_profit' not in pos:
                        pos['max_profit'] = profit_per_contract
                    else:
                        pos['max_profit'] = max(pos['max_profit'], profit_per_contract)
                    
                    # Adaptive trailing: wider for steam_follow (bigger stops = need bigger wins)
                    if strategy == 'steam_follow':
                        trailing_threshold = 0.05  # activate trailing after $0.05 profit
                        trailing_distance = 0.04   # trail by $0.04 from peak
                    else:
                        trailing_threshold = 0.03  # activate trailing after $0.03 profit
                        trailing_distance = 0.03   # trail by $0.03 from peak
                    
                    should_close = False
                    reason = ""
                    
                    # Trailing stop: if we've been up $0.03+, close if we drop $0.03 from peak
                    if pos['max_profit'] >= trailing_threshold:
                        pullback = pos['max_profit'] - profit_per_contract
                        if pullback >= trailing_distance:
                            should_close = True
                            reason = f"TRAIL(peak+${pos['max_profit']:.2f})"
                    
                    # Hard stop: still protect against initial loss
                    if not should_close and loss_per_contract >= stop_dollar:
                        should_close, reason = True, f"STOP(-${stop_dollar:.2f})"
                    
                    # Timeout
                    if not should_close and hold_time > 180:
                        should_close, reason = True, "TIMEOUT"
                    
                    if should_close:
                        # Use current bid as estimated settlement price for CLV tracking
                        settlement_estimate = kalshi.get('yes_bid', current)
                        pnl = self.trader.close(pos['id'], current, settlement_price=settlement_estimate)
                        status = "WIN" if pnl > 0 else "LOSS"
                        strategy = pos.get('strategy', 'unknown')
                        sig = f"[{elapsed:5d}s] {'✅' if pnl>0 else '❌'} {market_type.upper()} {strategy} CLOSE ({reason}): ${pnl:+.2f} | Total: ${self.trader.pnl:+.2f}"
                        self._dual_log(sig)
                
                # Status
                if time.time() - last_status > 60:
                    n_ex = len(self.feed.prices)
                    n_eth_ex = len(self.feed.eth_prices)
                    mom_str = f"{momentum_1m:+.3f}%" if momentum_1m else "N/A"
                    eth_mom_str = f"{eth_momentum_1m:+.3f}%" if eth_momentum_1m else "N/A"
                    
                    # Market data
                    k15 = self.poller.markets.get('15m', {})
                    kbtcd = self.poller.markets.get('btc_daily', {})
                    kethd = self.poller.markets.get('eth_daily', {})
                    keth15 = self.poller.markets.get('eth_15m', {})
                    
                    k15_str = f"{k15.get('yes_bid', 0):.2f}/{k15.get('yes_ask', 0):.2f}" if k15 else "N/A"
                    kbtcd_str = f"{kbtcd.get('yes_bid', 0):.2f}/{kbtcd.get('yes_ask', 0):.2f}" if kbtcd else "N/A"
                    kethd_str = f"{kethd.get('yes_bid', 0):.2f}/{kethd.get('yes_ask', 0):.2f}" if kethd else "N/A"
                    keth15_str = f"{keth15.get('yes_bid', 0):.2f}/{keth15.get('yes_ask', 0):.2f}" if keth15 else "N/A"
                    
                    wr = self.trader.session_stats['wins'] / max(self.trader.session_stats['total'], 1)
                    flash_count = len(self.flash_detector.flash_crashes)
                    
                    eth_price_str = f"${self.feed.eth_weighted_price:,.0f}" if self.feed.eth_weighted_price else "N/A"
                    
                    st = f"[{elapsed:5d}s] BTC: ${brti:,.2f} ({n_ex}ex, {mom_str}) | ETH: {eth_price_str} ({n_eth_ex}ex, {eth_mom_str}) | {self.poller.mode}"
                    st2 = f"  15m: {k15_str} | btcD: {kbtcd_str} | eth15m: {keth15_str} | ethD: {kethd_str} | P&L: ${self.trader.pnl:+.2f} ({len(self.trader.trades)}, {wr:.1%} WR, {flash_count} flash)"
                    self._dual_log(st)
                    self._dual_log(st2)
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
        
        # Kelly Criterion analysis
        kelly_trades = [t for t in self.trader.trades if t.get('sizing_decision', {}).get('method') == 'kelly']
        if kelly_trades:
            kelly_avg_size = sum(t['size'] for t in kelly_trades) / len(kelly_trades)
            summary += f"Kelly-sized trades: {len(kelly_trades)}/{len(self.trader.trades)}, avg size: ${kelly_avg_size:.0f}\n"
        
        # CLV (Closing Line Value) analysis
        if self.trader.clv_data:
            clv_by_strategy = {}
            for clv_record in self.trader.clv_data:
                strategy = clv_record['strategy']
                if strategy not in clv_by_strategy:
                    clv_by_strategy[strategy] = []
                clv_by_strategy[strategy].append(clv_record['clv'])
            
            clv_summary = []
            for strategy, clvs in clv_by_strategy.items():
                avg_clv = sum(clvs) / len(clvs)
                clv_summary.append(f"{strategy} avg {avg_clv:+.3f}")
            
            if clv_summary:
                summary += f"CLV: {' | '.join(clv_summary)}\n"
        
        # Flash crash analysis
        if flash_count > 0:
            flash_trades = [s for s in self.signals if s.get('type') == 'mean_rev_flash']
            summary += f"Flash crash triggers: {len(flash_trades)}/{flash_count} detected\n"
        
        # Strategy signal breakdown
        strategy_signals = {}
        for s in self.signals:
            strategy_type = s.get('type', 'unknown')
            if strategy_type not in strategy_signals:
                strategy_signals[strategy_type] = 0
            strategy_signals[strategy_type] += 1
        
        if strategy_signals:
            summary += "Strategy signals: "
            summary += ", ".join([f"{k}={v}" for k, v in strategy_signals.items()])
            summary += "\n"
        
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