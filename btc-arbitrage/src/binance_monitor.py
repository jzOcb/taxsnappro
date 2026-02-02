#!/usr/bin/env python3
"""
Binance WebSocket Monitor - Real-time BTC price tracking

This will be the core of our arbitrage bot.
Monitors BTC price changes and triggers trading signals.

Note: Requires websocket-client package
Install: pip install websocket-client
"""

import json
import time
from datetime import datetime

# For now, using REST API as placeholder
# TODO: Replace with WebSocket implementation
from urllib import request

class BinanceMonitor:
    """Monitor Binance BTC price in real-time"""
    
    def __init__(self, symbol='BTCUSDT'):
        self.symbol = symbol
        self.last_price = None
        self.price_history = []
        
    def get_current_price(self):
        """Get current BTC price (REST API - to be replaced with WebSocket)"""
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={self.symbol}"
        
        try:
            with request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
            
            price = float(data['price'])
            timestamp = datetime.now()
            
            return {
                'price': price,
                'timestamp': timestamp,
                'symbol': self.symbol
            }
        except Exception as e:
            print(f"Error fetching price: {e}")
            return None
    
    def detect_move(self, threshold=0.001):
        """
        Detect significant price moves
        
        Args:
            threshold: Percentage change threshold (0.001 = 0.1%)
        
        Returns:
            dict with move direction and magnitude, or None
        """
        current = self.get_current_price()
        if not current:
            return None
        
        price = current['price']
        
        if self.last_price is not None:
            change_pct = (price - self.last_price) / self.last_price
            
            if abs(change_pct) >= threshold:
                move = {
                    'direction': 'UP' if change_pct > 0 else 'DOWN',
                    'from_price': self.last_price,
                    'to_price': price,
                    'change_pct': change_pct * 100,
                    'change_usd': price - self.last_price,
                    'timestamp': current['timestamp']
                }
                
                self.last_price = price
                self.price_history.append(move)
                
                return move
        
        self.last_price = price
        return None
    
    def monitor(self, duration=60, interval=1):
        """
        Monitor price for a duration
        
        Args:
            duration: How long to monitor (seconds)
            interval: Check interval (seconds)
        """
        print(f"Monitoring {self.symbol} for {duration}s (checking every {interval}s)\n")
        print("Time     | Price      | Move")
        print("-" * 50)
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            move = self.detect_move(threshold=0.0005)  # 0.05% threshold
            
            if move:
                direction_symbol = "📈" if move['direction'] == 'UP' else "📉"
                print(f"{move['timestamp'].strftime('%H:%M:%S')} | ${move['to_price']:>10,.2f} | {direction_symbol} {move['change_pct']:>+6.2f}% (${move['change_usd']:>+7.2f})")
            
            time.sleep(interval)
        
        print(f"\nTotal significant moves: {len(self.price_history)}")
        
        if self.price_history:
            total_change = self.price_history[-1]['to_price'] - self.price_history[0]['from_price']
            print(f"Net change: ${total_change:+,.2f}")

# Simple test
if __name__ == "__main__":
    print("=" * 60)
    print("BINANCE BTC PRICE MONITOR - TEST")
    print("=" * 60)
    print()
    
    monitor = BinanceMonitor()
    
    # Quick 30-second test
    try:
        monitor.monitor(duration=30, interval=2)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    
    print("\n✅ Monitor test complete")
    print("\nNext steps:")
    print("1. Replace REST API with WebSocket for true real-time")
    print("2. Integrate with Kalshi API for trading signals")
    print("3. Add risk management logic")
