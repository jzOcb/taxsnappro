#!/usr/bin/env python3
"""
Real-time Paper Trader v3 - 稳定性改进版
- 定期保存状态
- 更robust的异常处理
- WebSocket重连退避
- 双日志文件（live + timestamped）
"""
import asyncio, json, time, sys, os, traceback, signal
sys.path.insert(0, '/tmp/pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import websockets
from datetime import datetime
from urllib import request
from collections import deque

class BTCPriceFeed:
    def __init__(self):
        self.prices = {}
        self.timestamps = {}
        self.weighted_price = None
        self.price_history = deque(maxlen=500)
        self.weights = {'coinbase': 0.35, 'kraken': 0.25, 'bitstamp': 0.20, 'binance_us': 0.20}
        self.reconnect_delays = {}  # 指数退避
    
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
        # 重连成功，重置延迟
        self.reconnect_delays[exchange] = 1
    
    def get_momentum(self, lookback_sec=60):
        if len(self.price_history) < 2: return None
        cutoff = time.time() - lookback_sec
        old = next((e['price'] for e in self.price_history if e['time'] >= cutoff), None)
        return ((self.weighted_price - old) / old) * 100 if old and self.weighted_price else None
    
    async def _reconnect_backoff(self, exchange):
        """指数退避重连"""
        delay = self.reconnect_delays.get(exchange, 1)
        await asyncio.sleep(min(delay, 60))  # 最多等60秒
        self.reconnect_delays[exchange] = min(delay * 2, 60)
    
    async def _coinbase(self):
        self.reconnect_delays['coinbase'] = 1
        while True:
            try:
                async with websockets.connect("wss://ws-feed.exchange.coinbase.com", ping_interval=20) as ws:
                    await ws.send(json.dumps({"type":"subscribe","channels":[{"name":"ticker","product_ids":["BTC-USD"]}]}))
                    async for msg in ws:
                        d = json.loads(msg)
                        if d.get('type') == 'ticker' and 'price' in d:
                            self._update('coinbase', float(d['price']))
            except Exception as e:
                print(f"[Coinbase Error] {e}", flush=True)
                await self._reconnect_backoff('coinbase')
    
    async def _kraken(self):
        self.reconnect_delays['kraken'] = 1
        while True:
            try:
                async with websockets.connect("wss://ws.kraken.com", ping_interval=20) as ws:
                    await ws.send(json.dumps({"event":"subscribe","pair":["XBT/USD"],"subscription":{"name":"ticker"}}))
                    async for msg in ws:
                        d = json.loads(msg)
                        if isinstance(d, list) and len(d) >= 4 and isinstance(d[1], dict) and 'c' in d[1]:
                            self._update('kraken', float(d[1]['c'][0]))
            except Exception as e:
                print(f"[Kraken Error] {e}", flush=True)
                await self._reconnect_backoff('kraken')
    
    async def _bitstamp(self):
        self.reconnect_delays['bitstamp'] = 1
        while True:
            try:
                async with websockets.connect("wss://ws.bitstamp.net", ping_interval=20) as ws:
                    await ws.send(json.dumps({"event":"bts:subscribe","data":{"channel":"live_trades_btcusd"}}))
                    async for msg in ws:
                        d = json.loads(msg)
                        if d.get('event') == 'trade' and 'price' in d.get('data', {}):
                            self._update('bitstamp', float(d['data']['price']))
            except Exception as e:
                print(f"[Bitstamp Error] {e}", flush=True)
                await self._reconnect_backoff('bitstamp')
    
    async def _binance(self):
        self.reconnect_delays['binance_us'] = 1
        while True:
            try:
                async with websockets.connect("wss://stream.binance.us:9443/ws/btcusdt@ticker", ping_interval=20) as ws:
                    async for msg in ws:
                        d = json.loads(msg)
                        if 'c' in d:
                            self._update('binance_us', float(d['c']))
            except Exception as e:
                print(f"[Binance Error] {e}", flush=True)
                await self._reconnect_backoff('binance_us')
    
    async def run(self):
        tasks = [
            asyncio.create_task(self._coinbase()),
            asyncio.create_task(self._kraken()),
            asyncio.create_task(self._bitstamp()),
            asyncio.create_task(self._binance())
        ]
        # 单独监控每个任务
        for task in tasks:
            task.add_done_callback(lambda t: print(f"⚠️ Feed task died: {t.exception()}", flush=True))
        await asyncio.gather(*tasks, return_exceptions=True)

class KalshiPoller:
    def __init__(self, interval=5):
        self.interval = interval
        self.latest = None
        self.history = deque(maxlen=200)
        self.last_ticker = None
    
    def is_market_transition(self):
        if self.latest and self.last_ticker and self.latest['ticker'] != self.last_ticker:
            return True
        return False
    
    def _fetch(self):
        url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=10&series_ticker=KXBTC15M&status=open"
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
                       'close_time': m.get('close_time'), 'time': time.time()}
        except Exception as e:
            print(f"[Kalshi fetch error] {e}", flush=True)
        return None
    
    async def run(self):
        while True:
            try:
                market = await asyncio.get_event_loop().run_in_executor(None, self._fetch)
                if market:
                    self.last_ticker = self.latest['ticker'] if self.latest else None
                    self.latest = market
                    self.history.append(market)
                await asyncio.sleep(self.interval)
            except Exception as e:
                print(f"[Kalshi poller error] {e}", flush=True)
                await asyncio.sleep(self.interval)

class PaperTrader:
    def __init__(self, balance=1000, trade_size=10):
        self.balance = balance
        self.initial = balance
        self.trade_size = trade_size
        self.positions = []
        self.trades = []
        self.pnl = 0
    
    def open(self, direction, price, ticker):
        cost = self.trade_size * price
        if cost > self.balance: return None
        pos = {'id': len(self.positions), 'dir': direction, 'size': self.trade_size,
               'entry': price, 'time': time.time(), 'ticker': ticker, 'open': True}
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
    
    def get_open(self):
        return [p for p in self.positions if p['open']]
    
    def to_dict(self):
        """序列化状态"""
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
        self.log_files = []  # [live, timestamped]
        self.last_market_ticker = None
        self.state_file = '/home/clawdbot/clawd/btc-arbitrage/data/rt_v3_state.json'
        self.last_checkpoint = 0
        self.graceful_shutdown = False
    
    def _dual_log(self, msg):
        """同时写入live和timestamped日志"""
        for f in self.log_files:
            if f and not f.closed:
                f.write(f"{datetime.now().isoformat()} {msg}\n")
                f.flush()
        # 同时打印到控制台
        print(msg, flush=True)
    
    def _save_checkpoint(self):
        """定期保存状态"""
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
            self._dual_log(f"⚠️ Checkpoint save failed: {e}")
    
    async def _checkpoint_loop(self):
        """每5分钟保存一次状态"""
        while not self.graceful_shutdown:
            await asyncio.sleep(300)  # 5分钟
            self._save_checkpoint()
    
    def _setup_signal_handlers(self):
        """优雅退出"""
        def handler(signum, frame):
            self._dual_log("\n⚠️ Received shutdown signal, saving state...")
            self.graceful_shutdown = True
            self._summary()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
    
    async def run(self):
        try:
            self.start_time = time.time()
            end_time = self.start_time + self.duration
            os.makedirs('/home/clawdbot/clawd/btc-arbitrage/logs', exist_ok=True)
            os.makedirs('/home/clawdbot/clawd/btc-arbitrage/data', exist_ok=True)
            
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_timestamped = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_v3_{ts}.log', 'w')
            log_live = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_v3_live.log', 'w')
            self.log_files = [log_live, log_timestamped]
            
            self._setup_signal_handlers()
            
            header = f"\n{'='*70}\nREAL-TIME PAPER TRADING v3 (Stability Enhanced)\n{'='*70}\n" + \
                    f"Duration: {self.duration//60}min | Start: {datetime.now().strftime('%H:%M:%S')}\n" + \
                    f"Strategy: Delay Arb + Flash Crash\nCheckpoints: Every 5min\n{'='*70}\n"
            self._dual_log(header)
            
            # 启动checkpoint loop
            checkpoint_task = asyncio.create_task(self._checkpoint_loop())
            
            last_kalshi_bid = None
            last_status = time.time()
            
            while time.time() < end_time and not self.graceful_shutdown:
                await asyncio.sleep(1)
                brti = self.feed.weighted_price
                kalshi = self.poller.latest
                if not brti or not kalshi: continue
                
                elapsed = int(time.time() - self.start_time)
                momentum_1m = self.feed.get_momentum(60)
                
                # 检测市场切换
                if self.poller.is_market_transition():
                    self._dual_log(f"[{elapsed:5d}s] 🔄 Market transition: {self.last_market_ticker} → {kalshi['ticker']}")
                    self.last_market_ticker = kalshi['ticker']
                    last_kalshi_bid = None
                    continue
                
                self.last_market_ticker = kalshi['ticker']
                
                # Delay Arbitrage
                if momentum_1m is not None and last_kalshi_bid is not None and last_kalshi_bid > 0.01:
                    kalshi_chg = ((kalshi['yes_bid'] - last_kalshi_bid) / last_kalshi_bid * 100)
                    if abs(momentum_1m) > 0.15 and abs(kalshi_chg) < 5 and len(self.trader.get_open()) == 0:
                        direction = 'YES' if momentum_1m > 0 else 'NO'
                        entry = kalshi['yes_ask'] if direction == 'YES' else (1 - kalshi['yes_bid'])
                        if 0.05 < entry < 0.95:
                            pos_id = self.trader.open(direction, entry, kalshi['ticker'])
                            if pos_id is not None:
                                sig = f"[{elapsed:5d}s] 🎯 DELAY: BTC {momentum_1m:+.3f}% K {kalshi_chg:+.1f}% → {direction} @ ${entry:.2f}"
                                self._dual_log(sig)
                                self.signals.append({'type': 'delay', 'time': elapsed})
                
                # Flash Crash
                if last_kalshi_bid and last_kalshi_bid > 0.15:
                    kalshi_drop = (kalshi['yes_bid'] - last_kalshi_bid) / last_kalshi_bid * 100
                    if kalshi_drop < -25 and not self.poller.is_market_transition():
                        if len(self.trader.get_open()) == 0:
                            entry = kalshi['yes_ask']
                            if 0.10 < entry < 0.85:
                                pos_id = self.trader.open('YES', entry, kalshi['ticker'])
                                if pos_id is not None:
                                    sig = f"[{elapsed:5d}s] ⚡ CRASH: K dropped {kalshi_drop:.1f}% → YES @ ${entry:.2f}"
                                    self._dual_log(sig)
                                    self.signals.append({'type': 'flash', 'time': elapsed})
                
                # Position管理
                for pos in self.trader.get_open():
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
                        sig = f"[{elapsed:5d}s] {'✅' if pnl>0 else '❌'} CLOSE ({reason}): ${pnl:+.2f} [{status}] | Total: ${self.trader.pnl:+.2f}"
                        self._dual_log(sig)
                
                # Status
                if time.time() - last_status > 60:
                    n_ex = len(self.feed.prices)
                    mom_str = f"{momentum_1m:+.3f}%" if momentum_1m else "N/A"
                    st = f"[{elapsed:5d}s] BRTI*: ${brti:,.2f} ({n_ex}ex, {mom_str}) | K: {kalshi['yes_bid']:.2f}/{kalshi['yes_ask']:.2f} | P&L: ${self.trader.pnl:+.2f} ({len(self.trader.trades)})"
                    self._dual_log(st)
                    last_status = time.time()
                
                last_kalshi_bid = kalshi['yes_bid']
            
            checkpoint_task.cancel()
            self._summary()
            
        except Exception as e:
            err = f"\n❌ FATAL ERROR: {e}\n{traceback.format_exc()}"
            self._dual_log(err)
            self._save_checkpoint()
            self._summary()
    
    def _summary(self):
        elapsed = int(time.time() - self.start_time) if self.start_time else 0
        summary = f"\n{'='*70}\nSUMMARY\n{'='*70}\nDuration: {elapsed//60}min | Signals: {len(self.signals)}\nTrades: {len(self.trader.trades)} | P&L: ${self.trader.pnl:+.2f}\n"
        if self.trader.trades:
            wins = [t for t in self.trader.trades if t['pnl'] > 0]
            summary += f"Win: {len(wins)}/{len(self.trader.trades)} ({len(wins)/len(self.trader.trades)*100:.1f}%)\n"
        summary += f"{'='*70}\n"
        self._dual_log(summary)
        
        # 保存最终结果
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'/home/clawdbot/clawd/btc-arbitrage/data/rt_v3_{ts}.json', 'w') as f:
            json.dump({'duration_min': elapsed//60, 'pnl': self.trader.pnl, 'signals': self.signals,
                      'trades': self.trader.trades, 'complete': not self.graceful_shutdown}, f, indent=2, default=str)
        
        for f in self.log_files:
            if f and not f.closed: f.close()

async def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 480
    feed = BTCPriceFeed()
    poller = KalshiPoller(interval=5)
    engine = TradingEngine(feed, poller, duration_min=duration)
    
    # 单独监控三个主任务
    tasks = [
        asyncio.create_task(feed.run()),
        asyncio.create_task(poller.run()),
        asyncio.create_task(engine.run())
    ]
    
    # 等待任一任务完成（通常是engine到时间）
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    
    # 取消其他任务
    for task in pending:
        task.cancel()
    
    print("✅ Graceful shutdown complete", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Keyboard interrupt", flush=True)
    except Exception as e:
        print(f"\n❌ Main loop crashed: {e}\n{traceback.format_exc()}", flush=True)
