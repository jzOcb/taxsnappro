#!/usr/bin/env python3
"""
Live Trading Engine - Detects signals and executes paper trades in real-time
Connects all components: monitoring → signal detection → trade execution
"""

import json
import time
from datetime import datetime
from urllib import request
import os

# Import our paper trader
import sys
sys.path.insert(0, 'scripts')

class TradingEngine:
    """Main trading engine - combines monitoring and execution"""
    
    def __init__(self, paper_mode=True, initial_balance=1000):
        self.paper_mode = paper_mode
        self.balance = initial_balance
        self.positions = {}
        self.trades = []
        self.signals_detected = 0
        self.signals_traded = 0
        
        # Strategy parameters
        self.btc_threshold = 0.08  # BTC must move >0.08%
        self.kalshi_threshold = 0.03  # Kalshi must move <0.03%
        self.position_size = 50  # contracts per trade
        self.max_positions = 3  # max concurrent positions
        
    def get_btc_price(self):
        """Get BTC from Binance.US"""
        req = request.Request("https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT")
        req.add_header('User-Agent', 'Mozilla/5.0')
        try:
            with request.urlopen(req, timeout=2) as r:
                return float(json.loads(r.read())['price'])
        except:
            return None
    
    def get_kalshi_market(self):
        """Get current Kalshi market"""
        req = request.Request("https://api.elections.kalshi.com/trade-api/v2/markets?limit=10&series_ticker=KXBTC15M&status=open")
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')
        try:
            with request.urlopen(req, timeout=2) as r:
                d = json.loads(r.read())
            if d.get('markets'):
                m = d['markets'][0]
                return {
                    'ticker': m['ticker'],
                    'yes_bid': m.get('yes_bid', 0) / 100,
                    'yes_ask': m.get('yes_ask', 0) / 100,
                    'close_time': m.get('close_time'),
                }
        except:
            pass
        return None
    
    def detect_signal(self, btc_change, kalshi_change, btc_price, kalshi_market):
        """
        Detect trading signal
        Returns: ('YES', confidence) or ('NO', confidence) or None
        """
        if btc_change is None or kalshi_change is None:
            return None
        
        # Strong upward BTC move, Kalshi hasn't reacted
        if btc_change > self.btc_threshold and abs(kalshi_change) < self.kalshi_threshold:
            # BTC moved up significantly, buy YES
            confidence = min(abs(btc_change) / 0.2, 1.0)  # 0.2% = 100% confidence
            return ('YES', confidence)
        
        # Strong downward BTC move, Kalshi hasn't reacted
        if btc_change < -self.btc_threshold and abs(kalshi_change) < self.kalshi_threshold:
            # BTC moved down significantly, buy NO
            confidence = min(abs(btc_change) / 0.2, 1.0)
            return ('NO', confidence)
        
        return None
    
    def execute_trade(self, signal, market, confidence):
        """Execute trade (paper mode)"""
        direction, _ = signal
        
        # Check if we can open more positions
        open_positions = sum(1 for p in self.positions.values() if p['status'] == 'open')
        if open_positions >= self.max_positions:
            print(f"⚠️  Max positions reached ({self.max_positions}), skipping trade")
            return None
        
        # Determine entry price
        if direction == 'YES':
            entry_price = market['yes_ask']  # Buy at ask
        else:
            entry_price = 1 - market['yes_bid']  # Buy NO at (1 - YES bid)
        
        # Calculate position size based on confidence
        size = int(self.position_size * confidence)
        cost = size * entry_price
        
        if cost > self.balance:
            print(f"⚠️  Insufficient balance: ${self.balance:.2f} < ${cost:.2f}")
            return None
        
        # Create position
        pos_id = len(self.trades)
        position = {
            'id': pos_id,
            'direction': direction,
            'size': size,
            'entry_price': entry_price,
            'entry_time': datetime.now().isoformat(),
            'market': market['ticker'],
            'confidence': confidence,
            'status': 'open',
        }
        
        self.positions[pos_id] = position
        self.balance -= cost
        self.signals_traded += 1
        
        print(f"✅ TRADE: {direction} {size} @ ${entry_price:.2f} | "
              f"Confidence: {confidence:.0%} | Cost: ${cost:.2f} | "
              f"Balance: ${self.balance:.2f}")
        
        return pos_id
    
    def check_exits(self, kalshi_market):
        """Check if any positions should be closed"""
        for pos_id, pos in list(self.positions.items()):
            if pos['status'] != 'open':
                continue
            
            # Exit logic: close after market has updated OR close before market close
            # For now: simple time-based exit (hold for 30 seconds)
            entry_time = datetime.fromisoformat(pos['entry_time'])
            age = (datetime.now() - entry_time).total_seconds()
            
            if age > 30:  # Hold for 30 seconds then exit
                # Determine exit price
                if pos['direction'] == 'YES':
                    exit_price = kalshi_market['yes_bid']  # Sell at bid
                else:
                    exit_price = 1 - kalshi_market['yes_ask']  # Sell NO
                
                # Calculate P&L
                entry_cost = pos['size'] * pos['entry_price']
                exit_value = pos['size'] * exit_price
                pnl = exit_value - entry_cost
                
                pos['exit_price'] = exit_price
                pos['exit_time'] = datetime.now().isoformat()
                pos['pnl'] = pnl
                pos['status'] = 'closed'
                
                self.balance += exit_value
                self.trades.append(pos.copy())
                
                win_loss = "WIN" if pnl > 0 else "LOSS"
                print(f"{'✅' if pnl > 0 else '❌'} CLOSE: {pos['direction']} {pos['size']} @ ${exit_price:.2f} | "
                      f"P&L: ${pnl:+.2f} | [{win_loss}]")
    
    def run(self, duration_seconds=300):
        """
        Run live trading engine
        duration_seconds: how long to run (default 5 min)
        """
        print(f"\n{'='*70}")
        print(f"LIVE TRADING ENGINE - {'PAPER MODE' if self.paper_mode else 'LIVE MODE'}")
        print(f"{'='*70}")
        print(f"Duration: {duration_seconds}s")
        print(f"Initial Balance: ${self.balance:,.2f}")
        print(f"Strategy: BTC >{self.btc_threshold:.2f}%, Kalshi <{self.kalshi_threshold:.2f}%")
        print(f"Position Size: {self.position_size} contracts")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        last_btc = None
        last_kalshi_bid = None
        
        while time.time() < end_time:
            tick_start = time.time()
            
            # Get market data
            btc = self.get_btc_price()
            kalshi = self.get_kalshi_market()
            
            if btc and kalshi:
                # Calculate changes
                btc_chg = ((btc - last_btc) / last_btc * 100) if last_btc else None
                kalshi_chg = ((kalshi['yes_bid'] - last_kalshi_bid) / last_kalshi_bid * 100) if last_kalshi_bid and last_kalshi_bid > 0 else None
                
                # Detect signal
                if btc_chg and kalshi_chg:
                    signal = self.detect_signal(btc_chg, kalshi_chg, btc, kalshi)
                    
                    if signal:
                        self.signals_detected += 1
                        direction, confidence = signal
                        
                        print(f"\n⚡ SIGNAL: {direction} | BTC: {btc_chg:+.3f}%, Kalshi: {kalshi_chg:+.3f}% | Confidence: {confidence:.0%}")
                        
                        # Execute trade
                        self.execute_trade(signal, kalshi, confidence)
                
                # Check for exits
                self.check_exits(kalshi)
                
                # Update last values
                last_btc = btc
                last_kalshi_bid = kalshi['yes_bid']
            
            # Sleep
            elapsed = time.time() - tick_start
            sleep_time = max(0, 2 - elapsed)  # Check every 2 seconds
            time.sleep(sleep_time)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print trading summary"""
        wins = [t for t in self.trades if t.get('pnl', 0) > 0]
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        
        print(f"\n{'='*70}")
        print("TRADING SESSION SUMMARY")
        print(f"{'='*70}")
        print(f"Signals Detected: {self.signals_detected}")
        print(f"Signals Traded: {self.signals_traded}")
        print(f"Total Trades: {len(self.trades)}")
        
        if self.trades:
            print(f"Wins: {len(wins)} | Losses: {len(self.trades) - len(wins)}")
            print(f"Win Rate: {len(wins)/len(self.trades)*100:.1f}%")
            print(f"Total P&L: ${total_pnl:+.2f}")
            print(f"Final Balance: ${self.balance:,.2f}")
            roi = (total_pnl / (self.balance - total_pnl)) * 100
            print(f"ROI: {roi:+.2f}%")


if __name__ == "__main__":
    import sys
    
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300  # 5 min default
    
    engine = TradingEngine(paper_mode=True, initial_balance=1000)
    
    try:
        engine.run(duration)
    except KeyboardInterrupt:
        print("\n⚠️  Stopped by user")
        engine.print_summary()
