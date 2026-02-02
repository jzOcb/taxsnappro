#!/usr/bin/env python3
"""
Real-time Paper Trader with WebSocket feeds
Integrates realtime_feed.py with trading logic
"""
import asyncio
import json
import time
import sys
import os

sys.path.insert(0, '/tmp/pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import websockets
from datetime import datetime
from urllib import request
from collections import deque


# ============================================================
# BTC Price Feed (WebSocket, no auth)
# ============================================================
class BTCPriceFeed:
    def __init__(self):
        self.prices = {}
        self.timestamps = {}
        self.weighted_price = None
        self.price_history = deque(maxlen=500)
        self.weights = {'coinbase': 0.35, 'kraken': 0.25, 'bitstamp': 0.20, 'binance_us': 0.20}
    
    def get_weighted(self):
        if not self.prices:
            return None
        total_w = 0
        w_sum = 0
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
    
    def get_momentum(self, lookback_sec=60):
        """Get price change over lookback period"""
        if len(self.price_history) < 2:
            return None
        now = time.time()
        cutoff = now - lookback_sec
        old = None
        for entry in self.price_history:
            if entry['time'] >= cutoff:
                old = entry['price']
                break
        if old and self.weighted_price:
            return ((self.weighted_price - old) / old) * 100
        return None
    
    async def _coinbase(self):
        while True:
            try:
                async with websockets.connect("wss://ws-feed.exchange.coinbase.com") as ws:
                    await ws.send(json.dumps({"type":"subscribe","channels":[{"name":"ticker","product_ids":["BTC-USD"]}]}))
                    async for msg in ws:
                        d = json.loads(msg)
                        if d.get('type') == 'ticker' and 'price' in d:
                            self._update('coinbase', float(d['price']))
            except:
                await asyncio.sleep(2)
    
    async def _kraken(self):
        while True:
            try:
                async with websockets.connect("wss://ws.kraken.com") as ws:
                    await ws.send(json.dumps({"event":"subscribe","pair":["XBT/USD"],"subscription":{"name":"ticker"}}))
                    async for msg in ws:
                        d = json.loads(msg)
                        if isinstance(d, list) and len(d) >= 4 and isinstance(d[1], dict) and 'c' in d[1]:
                            self._update('kraken', float(d[1]['c'][0]))
            except:
                await asyncio.sleep(2)
    
    async def _bitstamp(self):
        while True:
            try:
                async with websockets.connect("wss://ws.bitstamp.net") as ws:
                    await ws.send(json.dumps({"event":"bts:subscribe","data":{"channel":"live_trades_btcusd"}}))
                    async for msg in ws:
                        d = json.loads(msg)
                        if d.get('event') == 'trade' and 'price' in d.get('data', {}):
                            self._update('bitstamp', float(d['data']['price']))
            except:
                await asyncio.sleep(2)
    
    async def _binance(self):
        while True:
            try:
                async with websockets.connect("wss://stream.binance.us:9443/ws/btcusdt@ticker") as ws:
                    async for msg in ws:
                        d = json.loads(msg)
                        if 'c' in d:
                            self._update('binance_us', float(d['c']))
            except:
                await asyncio.sleep(2)
    
    async def run(self):
        await asyncio.gather(self._coinbase(), self._kraken(), self._bitstamp(), self._binance(), return_exceptions=True)


# ============================================================
# Kalshi Poller (REST, no auth)
# ============================================================
class KalshiPoller:
    def __init__(self, interval=5):
        self.interval = interval
        self.latest = None
        self.history = deque(maxlen=200)
    
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
                return {
                    'ticker': m['ticker'],
                    'yes_bid': m.get('yes_bid', 0) / 100,
                    'yes_ask': m.get('yes_ask', 0) / 100,
                    'volume': m.get('volume', 0),
                    'close_time': m.get('close_time'),
                    'time': time.time(),
                }
        except:
            pass
        return None
    
    async def run(self):
        while True:
            market = await asyncio.get_event_loop().run_in_executor(None, self._fetch)
            if market:
                self.latest = market
                self.history.append(market)
            await asyncio.sleep(self.interval)


# ============================================================
# Paper Trader
# ============================================================
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
        if cost > self.balance:
            return None
        pos = {
            'id': len(self.positions),
            'dir': direction,
            'size': self.trade_size,
            'entry': price,
            'time': time.time(),
            'ticker': ticker,
            'open': True,
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
        return pnl
    
    def get_open(self):
        return [p for p in self.positions if p['open']]


# ============================================================
# Trading Engine
# ============================================================
class TradingEngine:
    def __init__(self, feed, poller, duration_min=480):
        self.feed = feed
        self.poller = poller
        self.trader = PaperTrader()
        self.duration = duration_min * 60
        self.start_time = None
        self.signals = []
        self.log_file = None
        
    async def run(self):
        self.start_time = time.time()
        end_time = self.start_time + self.duration
        
        # Open log file
        os.makedirs('/home/clawdbot/clawd/btc-arbitrage/logs', exist_ok=True)
        os.makedirs('/home/clawdbot/clawd/btc-arbitrage/data', exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = open(f'/home/clawdbot/clawd/btc-arbitrage/logs/rt_paper_{ts}.log', 'w')
        
        print(f"\n{'='*70}", flush=True)
        print(f"REAL-TIME PAPER TRADING ENGINE", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"Duration: {self.duration//60} minutes", flush=True)
        print(f"Start: {datetime.now().strftime('%H:%M:%S UTC')}", flush=True)
        print(f"Strategy: Delay Arb + Flash Crash Detection", flush=True)
        print(f"Data: 4x WebSocket + Kalshi REST (5s)", flush=True)
        print(f"{'='*70}\n", flush=True)
        
        last_kalshi_bid = None
        last_status = time.time()
        
        while time.time() < end_time:
            await asyncio.sleep(1)
            
            brti = self.feed.weighted_price
            kalshi = self.poller.latest
            
            if not brti or not kalshi:
                continue
            
            elapsed = int(time.time() - self.start_time)
            momentum_1m = self.feed.get_momentum(60)
            momentum_5m = self.feed.get_momentum(300)
            
            # === STRATEGY 1: Delay Arbitrage ===
            # BRTI moved significantly but Kalshi hasn't caught up
            if momentum_1m is not None and last_kalshi_bid is not None:
                kalshi_chg = ((kalshi['yes_bid'] - last_kalshi_bid) / last_kalshi_bid * 100) if last_kalshi_bid > 0.01 else None
                
                if abs(momentum_1m) > 0.15 and kalshi_chg is not None and abs(kalshi_chg) < 5:
                    open_pos = self.trader.get_open()
                    if len(open_pos) == 0:
                        direction = 'YES' if momentum_1m > 0 else 'NO'
                        entry = kalshi['yes_ask'] if direction == 'YES' else (1 - kalshi['yes_bid'])
                        if 0.05 < entry < 0.95:  # Avoid extremes
                            pos_id = self.trader.open(direction, entry, kalshi['ticker'])
                            if pos_id is not None:
                                sig = f"[{elapsed:5d}s] 🎯 DELAY ARB: BTC {momentum_1m:+.3f}% Kalshi {kalshi_chg:+.1f}% → {direction} @ ${entry:.2f}"
                                print(sig, flush=True)
                                self._log(sig)
                                self.signals.append({'type': 'delay', 'time': elapsed, 'momentum': momentum_1m})
            
            # === STRATEGY 2: Flash Crash Detection ===
            # Kalshi price drops >20% suddenly
            if last_kalshi_bid and last_kalshi_bid > 0.1:
                kalshi_drop = (kalshi['yes_bid'] - last_kalshi_bid) / last_kalshi_bid * 100
                if kalshi_drop < -20:
                    open_pos = self.trader.get_open()
                    if len(open_pos) == 0:
                        entry = kalshi['yes_ask']
                        if 0.05 < entry < 0.90:
                            pos_id = self.trader.open('YES', entry, kalshi['ticker'])
                            if pos_id is not None:
                                sig = f"[{elapsed:5d}s] ⚡ FLASH CRASH: Kalshi dropped {kalshi_drop:.1f}% → YES @ ${entry:.2f}"
                                print(sig, flush=True)
                                self._log(sig)
                                self.signals.append({'type': 'flash', 'time': elapsed, 'drop': kalshi_drop})
            
            # === Position Management ===
            for pos in self.trader.get_open():
                hold_time = time.time() - pos['time']
                current = kalshi['yes_bid'] if pos['dir'] == 'YES' else (1 - kalshi['yes_ask'])
                unrealized = (current - pos['entry']) * pos['size']
                if pos['dir'] == 'NO':
                    unrealized = -unrealized
                pct = (unrealized / (pos['entry'] * pos['size'])) * 100 if pos['entry'] > 0 else 0
                
                # Close conditions
                should_close = False
                reason = ""
                if pct > 5:  # 5% profit
                    should_close = True
                    reason = "TAKE PROFIT"
                elif pct < -10:  # 10% stop loss
                    should_close = True
                    reason = "STOP LOSS"
                elif hold_time > 300:  # 5 min timeout
                    should_close = True
                    reason = "TIMEOUT"
                
                if should_close:
                    pnl = self.trader.close(pos['id'], current)
                    status = "WIN" if pnl > 0 else "LOSS"
                    sig = f"[{elapsed:5d}s] {'✅' if pnl > 0 else '❌'} CLOSE ({reason}): P&L ${pnl:+.2f} [{status}] | Total: ${self.trader.pnl:+.2f}"
                    print(sig, flush=True)
                    self._log(sig)
            
            # === Status Update (every 60s) ===
            if time.time() - last_status > 60:
                n_ex = len(self.feed.prices)
                mom_str = f"{momentum_1m:+.3f}%" if momentum_1m else "N/A"
                pos_str = f" | Pos: {len(self.trader.get_open())}" if self.trader.get_open() else ""
                pnl_str = f" | P&L: ${self.trader.pnl:+.2f} ({len(self.trader.trades)} trades)" if self.trader.trades else ""
                
                status_line = (f"[{elapsed:5d}s] BRTI*: ${brti:,.2f} ({n_ex}ex, {mom_str}/1m) | "
                              f"Kalshi: {kalshi['yes_bid']:.2f}/{kalshi['yes_ask']:.2f}{pos_str}{pnl_str}")
                print(status_line, flush=True)
                self._log(status_line)
                last_status = time.time()
            
            last_kalshi_bid = kalshi['yes_bid']
        
        # === Summary ===
        self._summary()
    
    def _log(self, msg):
        if self.log_file:
            self.log_file.write(f"{datetime.now().isoformat()} {msg}\n")
            self.log_file.flush()
    
    def _summary(self):
        elapsed = int(time.time() - self.start_time)
        
        summary = f"""
{'='*70}
REAL-TIME PAPER TRADING SUMMARY
{'='*70}
Duration: {elapsed//60} minutes
Signals: {len(self.signals)} ({sum(1 for s in self.signals if s['type']=='delay')} delay, {sum(1 for s in self.signals if s['type']=='flash')} flash crash)
Trades: {len(self.trader.trades)}
Balance: ${self.trader.initial:.2f} → ${self.trader.balance:.2f}
P&L: ${self.trader.pnl:+.2f} ({(self.trader.pnl/self.trader.initial)*100:+.2f}% ROI)
"""
        if self.trader.trades:
            wins = [t for t in self.trader.trades if t['pnl'] > 0]
            summary += f"""Wins: {len(wins)} / Losses: {len(self.trader.trades) - len(wins)}
Win Rate: {len(wins)/len(self.trader.trades)*100:.1f}%
Best: ${max(t['pnl'] for t in self.trader.trades):+.2f}
Worst: ${min(t['pnl'] for t in self.trader.trades):+.2f}
"""
        summary += f"{'='*70}\n"
        
        print(summary, flush=True)
        self._log(summary)
        
        # Save results
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'/home/clawdbot/clawd/btc-arbitrage/data/rt_paper_{ts}.json'
        with open(filename, 'w') as f:
            json.dump({
                'duration_min': elapsed // 60,
                'initial': self.trader.initial,
                'final': self.trader.balance,
                'pnl': self.trader.pnl,
                'signals': self.signals,
                'trades': self.trader.trades,
            }, f, indent=2, default=str)
        
        print(f"Saved: {filename}", flush=True)
        
        if self.log_file:
            self.log_file.close()


async def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 480
    
    feed = BTCPriceFeed()
    poller = KalshiPoller(interval=5)
    engine = TradingEngine(feed, poller, duration_min=duration)
    
    await asyncio.gather(
        feed.run(),
        poller.run(),
        engine.run(),
        return_exceptions=True,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Stopped", flush=True)
