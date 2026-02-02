#!/usr/bin/env python3
"""
Paper Trading Simulator - Test strategies without real money
Simulates order execution and tracks P&L
"""

import json
import time
from datetime import datetime
from urllib import request

class PaperTrader:
    """Simulates trading without real money"""
    
    def __init__(self, initial_balance=1000):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.positions = []
        self.trades = []
        self.pnl = 0
        
    def can_trade(self, size, price):
        """Check if we have enough balance"""
        cost = size * price
        return cost <= self.balance
    
    def open_position(self, direction, size, entry_price, market_ticker):
        """
        Open a position
        direction: 'YES' or 'NO'
        size: number of contracts
        entry_price: price per contract
        """
        cost = size * entry_price
        
        if not self.can_trade(size, entry_price):
            print(f"❌ Insufficient balance: ${self.balance:.2f} < ${cost:.2f}")
            return None
        
        position = {
            'id': len(self.positions),
            'direction': direction,
            'size': size,
            'entry_price': entry_price,
            'entry_time': datetime.now().isoformat(),
            'market': market_ticker,
            'status': 'open',
        }
        
        self.positions.append(position)
        self.balance -= cost
        
        print(f"✅ OPEN: {direction} {size} @ ${entry_price:.2f} | Cost: ${cost:.2f} | Remaining: ${self.balance:.2f}")
        
        return position['id']
    
    def close_position(self, position_id, exit_price):
        """Close a position and calculate P&L"""
        position = next((p for p in self.positions if p['id'] == position_id and p['status'] == 'open'), None)
        
        if not position:
            print(f"❌ Position {position_id} not found or already closed")
            return
        
        # Calculate P&L
        entry_cost = position['size'] * position['entry_price']
        exit_value = position['size'] * exit_price
        pnl = exit_value - entry_cost
        
        # For NO positions, P&L is inverted
        if position['direction'] == 'NO':
            pnl = -pnl
        
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now().isoformat()
        position['pnl'] = pnl
        position['status'] = 'closed'
        
        self.balance += exit_value
        self.pnl += pnl
        
        self.trades.append(position.copy())
        
        win_loss = "WIN" if pnl > 0 else "LOSS"
        print(f"{'✅' if pnl > 0 else '❌'} CLOSE: {position['direction']} {position['size']} @ ${exit_price:.2f} | "
              f"P&L: ${pnl:+.2f} | Total P&L: ${self.pnl:+.2f} | [{win_loss}]")
        
        return pnl
    
    def get_stats(self):
        """Get trading statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'roi': 0,
            }
        
        wins = [t for t in self.trades if t['pnl'] > 0]
        
        return {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(self.trades) - len(wins),
            'win_rate': len(wins) / len(self.trades) * 100,
            'total_pnl': self.pnl,
            'roi': (self.pnl / self.initial_balance) * 100,
            'final_balance': self.balance,
            'max_win': max((t['pnl'] for t in self.trades), default=0),
            'max_loss': min((t['pnl'] for t in self.trades), default=0),
        }
    
    def print_summary(self):
        """Print trading summary"""
        stats = self.get_stats()
        
        print(f"\n{'='*70}")
        print("PAPER TRADING SUMMARY")
        print(f"{'='*70}")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Final Balance: ${stats['final_balance']:,.2f}")
        print(f"Total P&L: ${stats['total_pnl']:+,.2f} ({stats['roi']:+.2f}% ROI)")
        print(f"\nTrades: {stats['total_trades']}")
        print(f"Wins: {stats['wins']} | Losses: {stats['losses']}")
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        
        if stats['total_trades'] > 0:
            print(f"\nBest Trade: ${stats['max_win']:+.2f}")
            print(f"Worst Trade: ${stats['max_loss']:+.2f}")


def get_current_market():
    """Get current Kalshi market"""
    url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=10&series_ticker=KXBTC15M&status=open"
    req = request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    
    try:
        with request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read())
        if data.get('markets'):
            m = data['markets'][0]
            return {
                'ticker': m['ticker'],
                'yes_bid': m.get('yes_bid', 0) / 100,
                'yes_ask': m.get('yes_ask', 0) / 100,
                'close_time': m.get('close_time'),
            }
    except:
        pass
    return None


if __name__ == "__main__":
    # Demo paper trading
    print("\n" + "="*70)
    print("PAPER TRADING SIMULATOR - DEMO")
    print("="*70 + "\n")
    
    trader = PaperTrader(initial_balance=1000)
    
    # Get current market
    market = get_current_market()
    
    if market:
        print(f"Current Market: {market['ticker']}")
        print(f"YES: Bid ${market['yes_bid']:.2f} / Ask ${market['yes_ask']:.2f}\n")
        
        # Simulate some trades
        print("Simulating trades...\n")
        
        # Buy YES
        pos1 = trader.open_position('YES', 100, market['yes_ask'], market['ticker'])
        time.sleep(1)
        
        # Simulate price movement
        exit_price = market['yes_ask'] + 0.05  # Simulate 5¢ profit
        trader.close_position(pos1, exit_price)
        
        time.sleep(1)
        
        # Buy NO (losing trade)
        pos2 = trader.open_position('NO', 50, 1 - market['yes_bid'], market['ticker'])
        time.sleep(1)
        
        exit_price2 = (1 - market['yes_bid']) - 0.03  # Simulate 3¢ loss
        trader.close_position(pos2, exit_price2)
    else:
        print("Could not fetch market data")
    
    # Print summary
    trader.print_summary()
