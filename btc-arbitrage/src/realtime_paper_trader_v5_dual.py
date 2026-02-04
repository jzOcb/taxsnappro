#!/usr/bin/env python3
"""
Real-time Paper Trader v5 - Dual Market (15min + Hourly)
Changes from v4:
- 同时监控15分钟和hourly市场
- 可以在两个市场同时开仓
- 动态选择最佳机会
- Flash Crash仍然禁用
"""
import asyncio, json, time, sys, os, traceback, signal
sys.path.insert(0, '/tmp/pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import websockets
from datetime import datetime
from urllib import request
from collections import deque

class BTCPriceFeed:
    """Same as v4"""
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
                    print(f"[Coinbase] {e}", flush=True)
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
                    print(f"[Kraken] {e}", flush=True)
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
                    print(f"[Bitstamp] {e}", flush=True)
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
                    print(f"[Binance] {e}", flush=True)
                    await self._reconnect_backoff('binance_us')
    
    async def run(self):
        tasks = [
            asyncio.create_task(self._coinbase()),
            asyncio.create_task(self._kraken()),
            asyncio.create_task(self._bitstamp()),
            asyncio.create_task(self._binance())
        ]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.running = False
            for task in tasks:
                task.cancel()

class DualMarketPoller:
    """Polls both 15min and hourly markets"""
    def __init__(self, interval=5):
        self.interval = interval
        self.markets = {}  # {'15m': {...}, '1h': {...}}
        self.history = {'15m': deque(maxlen=200), '1h': deque(maxlen=200)}
        self.last_tickers = {'15m': None, '1h': None}
        self.running = True
    
    def is_market_transition(self, market_type):
        """Check if market transitioned for specific type"""
        if market_type not in self.markets or market_type not in self.last_tickers:
            return False
        current = self.markets[market_type]
        last = self.last_tickers[market_type]
        if current and last and current['ticker'] != last:
            return True
        return False
    
    def _fetch(self, series_ticker):
        """Fetch market for specific series"""
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
        except Exception as e:
            print(f"[Kalshi {series_ticker}] {e}", flush=True)
        return None
    
    async def run(self):
        try:
            while self.running:
                # Fetch both markets
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

class PaperTrader:
    """Same as v4, but tracks market_type"""
    def __init__(self, balance=1000, trade_size=10):
        self.balance = balance
        self.initial = balance
        self.trade_size = trade_size
        self.positions = []
        self.trades = []
        self.pnl = 0
    
    def open(self, direction, price, ticker, market_type):
        cost = self.trade_size * price
        if cost > self.balance: return None
        pos = {'id': len(self.positions), 'dir': direction, 'size': self.trade_size,
               'entry': price, 'time': time.time(), 'ticker': ticker, 'open': True,
               'market_type': market_type}
        self.positions.append(pos)
        self.balance -= cost
        return pos['id']
    
    def close(self, pos_id, exit_price):
        pos = next((p for p in self.positions if p['id'] == pos_id and p['open']), None)
        if not pos: return None
        pnl = (exit_price - pos['entry']) * pos['size']
        if pos['dir'] == 'NO': pnl = -pnl
        pos['exit'] = exit_price
        pos['pnl'] = pnl
        pos['open'] = False
        pos['close_time'] = time.time()
        self.balance += pos['size'] * exit_price
        self.pnl += pnl
        self.trades.append(pos.copy())
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
            'trades': self.trades
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
        self.state_file = '/home/clawdbot/clawd/btc-arbitrage/data/rt_v5_state.json'
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
            state = {
                'elapsed_sec': elapsed,
                'start_time': self.start_time,
                'trader': self.trader.to_dict(),
                'signals': self.signals,
                'last_checkpoint': time.time()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            self._dual_log(f"[{elapsed:5d}s] 💾 Checkpoint saved")
        except Exception as e:
            self._dual_log(f"⚠️ Checkpoint failed: {e}")
    
    async def _checkpoint_loop(self):
        while not self.graceful_shutdown:
            await asyncio.sleep(300)
            self._save_checkpoint()
    
    def _setup_signal_handlers(self):
        def handler(signum, frame):
            self._dual_log("\n⚠️ Shutdown signal")
            self.graceful_shutdown = True
            self._summary()
            sys.exit(0)
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
    
    def _process_market(self, market_type, elapsed, brti, momentum_1m):
        """Process delay arb for one market"""
        if market_type not in self.poller.markets:
            return
        
        kalshi = self.poller.markets[market_type]
        last_bid = self.last_kalshi_bids[market_type]
        
        # Skip if market transition
        if self.poller.is_market_transition(market_type):
            self._dual_log(f"[{elapsed:5d}s] 🔄 {market_type.upper()} transition: {kalshi['ticker']}")
            self.last_kalshi_bids[market_type] = None
            return
        
        # Delay Arbitrage
        if momentum_1m is not None and last_bid is not None and last_bid > 0.01:
            kalshi_chg = ((kalshi['yes_bid'] - last_bid) / last_bid * 100)
            if abs(momentum_1m) > 0.15 and abs(kalshi_chg) < 5:
                # Check if we already have position in this market
                if len(self.trader.get_open(market_type)) == 0:
                    direction = 'YES' if momentum_1m > 0 else 'NO'
                    entry = kalshi['yes_ask'] if direction == 'YES' else (1 - kalshi['yes_bid'])
                    if 0.05 < entry < 0.95:
                        pos_id = self.trader.open(direction, entry, kalshi['ticker'], market_type)
                        if pos_id is not None:
                            sig = f"[{elapsed:5d}s] 🎯 {market_type.upper()} DELAY: BTC {momentum_1m:+.3f}% K {kalshi_chg:+.1f}% → {direction} @ ${entry:.2f}"
                            self._dual_log(sig)
                            self.signals.append({'type': 'delay', 'market': market_type, 'time': elapsed})
        
        # Update last bid
        self.last_kalshi_bids[market_type] = kalshi['yes_bid']
    
    async def run(self):
        try:
            self.start_time = time.time()
            end_time = self.start_time + self.duration
            os.makedirs('/home/clawdbot/clawd/btc-arbitrage/logs', exist_ok=True)
            os.makedirs('/home/clawdbot/clawd/btc-arbitrage/data', exist_ok=True)
            
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_timestamped = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_v5_{ts}.log', 'w')
            log_live = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_v5_live.log', 'w')
            self.log_files = [log_live, log_timestamped]
            
            self._setup_signal_handlers()
            
            header = f"\n{'='*70}\nREAL-TIME PAPER TRADING v5 (15min + Hourly)\n{'='*70}\n" + \
                    f"Duration: {self.duration//60}min | Start: {datetime.now().strftime('%H:%M:%S')}\n" + \
                    f"Strategy: Delay Arb on BOTH markets\nCheckpoints: Every 5min\n{'='*70}\n"
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
                
                # Position management (both markets)
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
                    
                    should_close = False
                    reason = ""
                    if pct > 8: should_close, reason = True, "PROFIT"
                    elif pct < -12: should_close, reason = True, "STOP"
                    elif hold_time > 360: should_close, reason = True, "TIMEOUT"
                    
                    if should_close:
                        pnl = self.trader.close(pos['id'], current)
                        status = "WIN" if pnl > 0 else "LOSS"
                        sig = f"[{elapsed:5d}s] {'✅' if pnl>0 else '❌'} {market_type.upper()} CLOSE ({reason}): ${pnl:+.2f} [{status}] | Total: ${self.trader.pnl:+.2f}"
                        self._dual_log(sig)
                
                # Status
                if time.time() - last_status > 60:
                    n_ex = len(self.feed.prices)
                    mom_str = f"{momentum_1m:+.3f}%" if momentum_1m else "N/A"
                    
                    # Show both markets
                    k15 = self.poller.markets.get('15m', {})
                    k1h = self.poller.markets.get('1h', {})
                    k15_str = f"{k15.get('yes_bid', 0):.2f}/{k15.get('yes_ask', 0):.2f}" if k15 else "N/A"
                    k1h_str = f"{k1h.get('yes_bid', 0):.2f}/{k1h.get('yes_ask', 0):.2f}" if k1h else "N/A"
                    
                    st = f"[{elapsed:5d}s] BRTI: ${brti:,.2f} ({n_ex}ex, {mom_str}) | 15m: {k15_str} | 1h: {k1h_str} | P&L: ${self.trader.pnl:+.2f} ({len(self.trader.trades)})"
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
        summary = f"\n{'='*70}\nSUMMARY\n{'='*70}\nDuration: {elapsed//60}min | Signals: {len(self.signals)}\nTrades: {len(self.trader.trades)} | P&L: ${self.trader.pnl:+.2f}\n"
        
        # Breakdown by market
        trades_15m = [t for t in self.trader.trades if t.get('market_type') == '15m']
        trades_1h = [t for t in self.trader.trades if t.get('market_type') == '1h']
        
        if trades_15m:
            wins_15m = [t for t in trades_15m if t['pnl'] > 0]
            pnl_15m = sum(t['pnl'] for t in trades_15m)
            summary += f"15min: {len(trades_15m)} trades, {len(wins_15m)} wins ({len(wins_15m)/len(trades_15m)*100:.1f}%), ${pnl_15m:+.2f}\n"
        
        if trades_1h:
            wins_1h = [t for t in trades_1h if t['pnl'] > 0]
            pnl_1h = sum(t['pnl'] for t in trades_1h)
            summary += f"Hourly: {len(trades_1h)} trades, {len(wins_1h)} wins ({len(wins_1h)/len(trades_1h)*100:.1f}%), ${pnl_1h:+.2f}\n"
        
        summary += f"{'='*70}\n"
        self._dual_log(summary)
        
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'/home/clawdbot/clawd/btc-arbitrage/data/rt_v5_{ts}.json', 'w') as f:
            json.dump({'duration_min': elapsed//60, 'pnl': self.trader.pnl, 'signals': self.signals,
                      'trades': self.trader.trades, 'complete': not self.graceful_shutdown}, f, indent=2, default=str)
        
        for f in self.log_files:
            if f and not f.closed: f.close()

async def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 480
    feed = BTCPriceFeed()
    poller = DualMarketPoller(interval=5)
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
        print("✅ All tasks stopped", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Keyboard interrupt", flush=True)
    except Exception as e:
        print(f"\n❌ Fatal: {e}\n{traceback.format_exc()}", flush=True)
