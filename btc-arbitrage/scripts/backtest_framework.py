#!/usr/bin/env python3
"""
Backtest Framework for BTC Arbitrage Strategies
Tests different strategies against historical data
"""

import json
from datetime import datetime

class Strategy:
    """Base class for arbitrage strategies"""
    
    def __init__(self, name):
        self.name = name
        self.trades = []
        self.pnl = 0
        
    def should_trade(self, brti_proxy, kalshi_market, historical_data):
        """
        Override this method with strategy logic
        
        Returns: ('BUY_YES', size) or ('BUY_NO', size) or None
        """
        raise NotImplementedError
    
    def execute_trade(self, action, size, entry_price, exit_price):
        """Record a trade"""
        pnl = (exit_price - entry_price) * size if action == 'BUY_YES' else (entry_price - exit_price) * size
        
        self.trades.append({
            'action': action,
            'entry': entry_price,
            'exit': exit_price,
            'size': size,
            'pnl': pnl,
        })
        
        self.pnl += pnl
    
    def get_stats(self):
        """Calculate strategy statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
            }
        
        wins = [t for t in self.trades if t['pnl'] > 0]
        
        return {
            'total_trades': len(self.trades),
            'win_rate': len(wins) / len(self.trades) * 100,
            'total_pnl': self.pnl,
            'avg_pnl': self.pnl / len(self.trades),
            'max_win': max(t['pnl'] for t in self.trades),
            'max_loss': min(t['pnl'] for t in self.trades),
        }

class DelayArbitrageStrategy(Strategy):
    """
    Strategy: Trade when BRTI moves but Kalshi lags
    """
    
    def __init__(self, brti_threshold=0.1, kalshi_threshold=0.05):
        super().__init__("Delay Arbitrage")
        self.brti_threshold = brti_threshold  # % move required
        self.kalshi_threshold = kalshi_threshold  # max % Kalshi can move
        
    def should_trade(self, brti_change_pct, kalshi_change_pct, current_kalshi_price):
        """
        Trade if:
        - BRTI moved significantly
        - Kalshi hasn't moved much yet
        """
        if brti_change_pct is None or kalshi_change_pct is None:
            return None
        
        # BTC moved up but Kalshi didn't
        if brti_change_pct > self.brti_threshold and abs(kalshi_change_pct) < self.kalshi_threshold:
            # Buy YES (expect Kalshi to follow BRTI upward)
            return ('BUY_YES', 100)  # 100 contracts
        
        # BTC moved down but Kalshi didn't
        if brti_change_pct < -self.brti_threshold and abs(kalshi_change_pct) < self.kalshi_threshold:
            # Buy NO (expect Kalshi to follow BRTI downward)
            return ('BUY_NO', 100)
        
        return None

class MomentumStrategy(Strategy):
    """
    Strategy: Trade based on BTC momentum regardless of Kalshi lag
    """
    
    def __init__(self, momentum_threshold=0.2):
        super().__init__("Momentum")
        self.momentum_threshold = momentum_threshold
        
    def should_trade(self, brti_change_pct, kalshi_yes_price):
        """
        Trade if BTC has strong momentum
        """
        if brti_change_pct is None:
            return None
        
        # Strong upward momentum
        if brti_change_pct > self.momentum_threshold:
            # Only buy YES if price is attractive
            if kalshi_yes_price < 0.7:
                return ('BUY_YES', 100)
        
        # Strong downward momentum  
        if brti_change_pct < -self.momentum_threshold:
            # Only buy NO if price is attractive
            if kalshi_yes_price > 0.3:
                return ('BUY_NO', 100)
        
        return None

def backtest(data_file, strategy):
    """
    Run backtest on historical monitoring data
    
    Args:
        data_file: Path to continuous_monitor JSON output
        strategy: Strategy instance to test
    """
    print(f"\n{'='*70}")
    print(f"BACKTESTING: {strategy.name}")
    print(f"{'='*70}\n")
    
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    measurements = data['measurements']
    print(f"Total data points: {len(measurements)}")
    
    for i, m in enumerate(measurements):
        brti_chg = m.get('brti_change_pct')
        kalshi_chg = m.get('kalshi_change_pct')
        kalshi_yes = m['kalshi']['yes_bid']
        
        # Check if strategy wants to trade
        trade = strategy.should_trade(brti_chg, kalshi_chg, kalshi_yes)
        
        if trade:
            action, size = trade
            entry_price = kalshi_yes
            
            # Simulate exit at next period (simplified)
            if i + 1 < len(measurements):
                exit_price = measurements[i + 1]['kalshi']['yes_bid']
                strategy.execute_trade(action, size, entry_price, exit_price)
                
                print(f"[{i:4d}] TRADE: {action} @ {entry_price:.2f} → {exit_price:.2f}")
    
    # Print results
    stats = strategy.get_stats()
    
    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print(f"Total trades: {stats['total_trades']}")
    print(f"Win rate: {stats['win_rate']:.1f}%")
    print(f"Total PnL: ${stats['total_pnl']:,.2f}")
    print(f"Avg PnL per trade: ${stats['avg_pnl']:,.2f}")
    if stats['total_trades'] > 0:
        print(f"Max win: ${stats['max_win']:,.2f}")
        print(f"Max loss: ${stats['max_loss']:,.2f}")
    
    return stats

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 backtest_framework.py <data_file.json>")
        print("\nExample strategies will be tested.")
        sys.exit(1)
    
    data_file = sys.argv[1]
    
    # Test both strategies
    strategies = [
        DelayArbitrageStrategy(brti_threshold=0.1, kalshi_threshold=0.05),
        MomentumStrategy(momentum_threshold=0.15),
    ]
    
    for strategy in strategies:
        backtest(data_file, strategy)
        print("\n")
