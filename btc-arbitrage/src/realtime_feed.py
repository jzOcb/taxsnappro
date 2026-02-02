#!/usr/bin/env python3
"""
Real-time BTC Price Feed via Public WebSockets
No API key needed - uses exchange public streams
"""
import asyncio
import json
import time
import sys
import os

# Add websockets lib
sys.path.insert(0, '/tmp/pylib')
import websockets

from datetime import datetime
from urllib import request
from collections import deque


class BTCPriceFeed:
    """Real-time BTC price from multiple exchanges via WebSocket"""
    
    def __init__(self):
        self.prices = {}  # exchange -> latest price
        self.timestamps = {}  # exchange -> timestamp
        self.history = deque(maxlen=1000)
        self.callbacks = []
        
        # Volume weights (approximate daily volume ratio)
        self.weights = {
            'coinbase': 0.35,
            'kraken': 0.25,
            'bitstamp': 0.20,
            'binance_us': 0.20,
        }
    
    def on_price(self, callback):
        """Register callback for price updates"""
        self.callbacks.append(callback)
    
    def get_weighted_price(self):
        """Get volume-weighted average price"""
        if not self.prices:
            return None
        
        total_weight = 0
        weighted_sum = 0
        
        for exchange, price in self.prices.items():
            w = self.weights.get(exchange, 0.1)
            weighted_sum += price * w
            total_weight += w
        
        return weighted_sum / total_weight if total_weight > 0 else None
    
    async def _coinbase_feed(self):
        """Coinbase WebSocket - public ticker"""
        while True:
            try:
                async with websockets.connect("wss://ws-feed.exchange.coinbase.com") as ws:
                    sub = json.dumps({
                        "type": "subscribe",
                        "channels": [{"name": "ticker", "product_ids": ["BTC-USD"]}]
                    })
                    await ws.send(sub)
                    
                    async for msg in ws:
                        data = json.loads(msg)
                        if data.get('type') == 'ticker' and 'price' in data:
                            price = float(data['price'])
                            self.prices['coinbase'] = price
                            self.timestamps['coinbase'] = time.time()
                            await self._notify(price, 'coinbase')
            except Exception as e:
                print(f"[Coinbase WS] Error: {e}, reconnecting...", flush=True)
                await asyncio.sleep(2)
    
    async def _kraken_feed(self):
        """Kraken WebSocket - public ticker"""
        while True:
            try:
                async with websockets.connect("wss://ws.kraken.com") as ws:
                    sub = json.dumps({
                        "event": "subscribe",
                        "pair": ["XBT/USD"],
                        "subscription": {"name": "ticker"}
                    })
                    await ws.send(sub)
                    
                    async for msg in ws:
                        data = json.loads(msg)
                        if isinstance(data, list) and len(data) >= 4:
                            # Kraken ticker format: [channelID, data, channelName, pair]
                            ticker = data[1]
                            if isinstance(ticker, dict) and 'c' in ticker:
                                price = float(ticker['c'][0])  # last trade price
                                self.prices['kraken'] = price
                                self.timestamps['kraken'] = time.time()
                                await self._notify(price, 'kraken')
            except Exception as e:
                print(f"[Kraken WS] Error: {e}, reconnecting...", flush=True)
                await asyncio.sleep(2)
    
    async def _bitstamp_feed(self):
        """Bitstamp WebSocket - public ticker"""
        while True:
            try:
                async with websockets.connect("wss://ws.bitstamp.net") as ws:
                    sub = json.dumps({
                        "event": "bts:subscribe",
                        "data": {"channel": "live_trades_btcusd"}
                    })
                    await ws.send(sub)
                    
                    async for msg in ws:
                        data = json.loads(msg)
                        if data.get('event') == 'trade':
                            trade = data.get('data', {})
                            if 'price' in trade:
                                price = float(trade['price'])
                                self.prices['bitstamp'] = price
                                self.timestamps['bitstamp'] = time.time()
                                await self._notify(price, 'bitstamp')
            except Exception as e:
                print(f"[Bitstamp WS] Error: {e}, reconnecting...", flush=True)
                await asyncio.sleep(2)

    async def _binance_feed(self):
        """Binance US WebSocket - public trades"""
        while True:
            try:
                async with websockets.connect("wss://stream.binance.us:9443/ws/btcusdt@ticker") as ws:
                    async for msg in ws:
                        data = json.loads(msg)
                        if 'c' in data:  # last price
                            price = float(data['c'])
                            self.prices['binance_us'] = price
                            self.timestamps['binance_us'] = time.time()
                            await self._notify(price, 'binance_us')
            except Exception as e:
                print(f"[Binance WS] Error: {e}, reconnecting...", flush=True)
                await asyncio.sleep(2)
    
    async def _notify(self, price, exchange):
        """Notify callbacks"""
        weighted = self.get_weighted_price()
        if weighted:
            entry = {
                'time': time.time(),
                'exchange': exchange,
                'price': price,
                'weighted': weighted,
                'prices': dict(self.prices),
            }
            self.history.append(entry)
            for cb in self.callbacks:
                await cb(entry)
    
    async def run(self):
        """Start all feeds"""
        print("🚀 Starting real-time BTC feeds (no auth needed)...", flush=True)
        await asyncio.gather(
            self._coinbase_feed(),
            self._kraken_feed(),
            self._bitstamp_feed(),
            self._binance_feed(),
            return_exceptions=True,
        )


class KalshiPoller:
    """Poll Kalshi REST API for market data (public, no auth)"""
    
    def __init__(self, interval=5):
        self.interval = interval
        self.latest = None
        self.callbacks = []
    
    def on_market(self, callback):
        self.callbacks.append(callback)
    
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
        print(f"📊 Starting Kalshi poller (every {self.interval}s, no auth)...", flush=True)
        while True:
            market = await asyncio.get_event_loop().run_in_executor(None, self._fetch)
            if market:
                self.latest = market
                for cb in self.callbacks:
                    await cb(market)
            await asyncio.sleep(self.interval)


async def main():
    """Demo: run feeds and print updates"""
    feed = BTCPriceFeed()
    poller = KalshiPoller(interval=5)
    
    last_print = [0]
    
    async def on_price(entry):
        now = time.time()
        if now - last_print[0] > 2:  # Print every 2s max
            kalshi = poller.latest
            kalshi_str = f"Kalshi: {kalshi['yes_bid']:.2f}/{kalshi['yes_ask']:.2f}" if kalshi else "Kalshi: waiting..."
            
            n_exchanges = len(entry['prices'])
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"BRTI*: ${entry['weighted']:,.2f} ({n_exchanges} exchanges) | "
                  f"{kalshi_str}", flush=True)
            last_print[0] = now
    
    feed.on_price(on_price)
    
    await asyncio.gather(feed.run(), poller.run())


if __name__ == "__main__":
    print("="*70, flush=True)
    print("REAL-TIME BTC + KALSHI FEED", flush=True)
    print("Public WebSocket feeds - no API key needed!", flush=True)
    print("="*70, flush=True)
    asyncio.run(main())
