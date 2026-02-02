#!/usr/bin/env python3
"""
Flash Crash Strategy Backtest
基于社区策略：检测突然概率下跌，买入后等待反弹
"""
import json
import sys
from datetime import datetime
from collections import deque, defaultdict

class FlashCrashStrategy:
    def __init__(self, 
                 drop_threshold=0.30,      # 30% drop triggers signal
                 lookback_ticks=5,         # Look back 5 ticks (~10s with 2s polling)
                 take_profit=0.10,         # 10% profit target
                 stop_loss=0.05,           # 5% stop loss
                 min_price=0.05,           # Avoid extreme prices
                 max_price=0.95,
                 trade_size=10.0):
        
        self.drop_threshold = drop_threshold
        self.lookback_ticks = lookback_ticks
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.min_price = min_price
        self.max_price = max_price
        self.trade_size = trade_size
        
        # Price history per market
        self.price_history = defaultdict(lambda: {
            'yes_bid': deque(maxlen=lookback_ticks),
            'no_bid': deque(maxlen=lookback_ticks)
        })
        
        # Active trades
        self.active_trades = []
        self.completed_trades = []
        
    def detect_flash_crash(self, market_id, yes_bid, no_bid):
        """
        Detect if there's a flash crash (sudden price drop)
        
        Returns: (crashed_side, entry_price) or (None, None)
        """
        history = self.price_history[market_id]
        
        # Add current prices to history
        history['yes_bid'].append(yes_bid)
        history['no_bid'].append(no_bid)
        
        # Need enough history
        if len(history['yes_bid']) < self.lookback_ticks:
            return None, None
        
        # Check YES side for crash
        if yes_bid is not None:
            max_yes = max(history['yes_bid'])
            if max_yes > 0:
                drop_pct = (max_yes - yes_bid) / max_yes
                if drop_pct >= self.drop_threshold:
                    # Flash crash detected on YES side
                    if self.min_price <= yes_bid <= self.max_price:
                        return 'YES', yes_bid
        
        # Check NO side for crash
        if no_bid is not None:
            max_no = max(history['no_bid'])
            if max_no > 0:
                drop_pct = (max_no - no_bid) / max_no
                if drop_pct >= self.drop_threshold:
                    # Flash crash detected on NO side
                    if self.min_price <= no_bid <= self.max_price:
                        return 'NO', no_bid
        
        return None, None
    
    def enter_trade(self, timestamp, market_id, ticker, side, entry_price):
        """Enter a new trade"""
        trade = {
            'entry_time': timestamp,
            'market_id': market_id,
            'ticker': ticker,
            'side': side,
            'entry_price': entry_price,
            'size': self.trade_size,
            'take_profit_price': entry_price * (1 + self.take_profit),
            'stop_loss_price': entry_price * (1 - self.stop_loss),
            'status': 'OPEN'
        }
        self.active_trades.append(trade)
        return trade
    
    def check_exits(self, timestamp, market_id, yes_bid, no_bid, yes_ask, no_ask):
        """Check if any active trades should exit"""
        to_remove = []
        
        for i, trade in enumerate(self.active_trades):
            if trade['market_id'] != market_id:
                continue
            
            exit_price = None
            exit_reason = None
            
            # Get current price for this trade's side
            if trade['side'] == 'YES':
                # We bought YES, so we sell at YES bid
                current_price = yes_bid
                if current_price is None:
                    continue
                
                # Check take profit
                if current_price >= trade['take_profit_price']:
                    exit_price = min(current_price, trade['take_profit_price'])
                    exit_reason = 'TAKE_PROFIT'
                
                # Check stop loss
                elif current_price <= trade['stop_loss_price']:
                    exit_price = max(current_price, trade['stop_loss_price'])
                    exit_reason = 'STOP_LOSS'
            
            elif trade['side'] == 'NO':
                # We bought NO, so we sell at NO bid
                current_price = no_bid
                if current_price is None:
                    continue
                
                # Check take profit
                if current_price >= trade['take_profit_price']:
                    exit_price = min(current_price, trade['take_profit_price'])
                    exit_reason = 'TAKE_PROFIT'
                
                # Check stop loss
                elif current_price <= trade['stop_loss_price']:
                    exit_price = max(current_price, trade['stop_loss_price'])
                    exit_reason = 'STOP_LOSS'
            
            # Execute exit if triggered
            if exit_price is not None:
                trade['exit_time'] = timestamp
                trade['exit_price'] = exit_price
                trade['exit_reason'] = exit_reason
                trade['pnl'] = (exit_price - trade['entry_price']) * trade['size']
                trade['roi'] = (exit_price - trade['entry_price']) / trade['entry_price']
                trade['status'] = 'CLOSED'
                
                self.completed_trades.append(trade)
                to_remove.append(i)
        
        # Remove closed trades
        for i in reversed(to_remove):
            self.active_trades.pop(i)
    
    def on_data(self, data_point):
        """Process one data point"""
        timestamp = data_point.get('timestamp')
        markets = data_point.get('markets', {})
        
        for market_id, market_data in markets.items():
            ticker = market_data.get('ticker', '')
            yes_bid = market_data.get('yes_bid')
            no_bid = market_data.get('no_bid')
            yes_ask = market_data.get('yes_ask')
            no_ask = market_data.get('no_ask')
            
            # Check for exits first
            self.check_exits(timestamp, market_id, yes_bid, no_bid, yes_ask, no_ask)
            
            # Detect flash crash
            crashed_side, entry_price = self.detect_flash_crash(market_id, yes_bid, no_bid)
            
            if crashed_side and entry_price:
                # Check if we already have a position in this market
                has_position = any(
                    trade['market_id'] == market_id and trade['status'] == 'OPEN' 
                    for trade in self.active_trades
                )
                
                if not has_position:
                    trade = self.enter_trade(timestamp, market_id, ticker, crashed_side, entry_price)
                    # print(f"[{timestamp}] FLASH CRASH: {ticker} {crashed_side} at ${entry_price:.2f}")
    
    def finalize(self):
        """Close all open trades (at last known price)"""
        # Mark remaining trades as expired
        for trade in self.active_trades:
            trade['status'] = 'EXPIRED'
            trade['pnl'] = 0  # Assume break-even
            trade['roi'] = 0
            self.completed_trades.append(trade)
        
        self.active_trades = []

def load_data(filepath):
    """Load JSONL data"""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def analyze_results(completed_trades):
    """Analyze backtest results"""
    if not completed_trades:
        return {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'breakeven': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_pnl': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'take_profit_exits': 0,
            'stop_loss_exits': 0,
            'conclusion': 'NO SIGNALS DETECTED'
        }
    
    total_trades = len(completed_trades)
    wins = [t for t in completed_trades if t.get('pnl', 0) > 0]
    losses = [t for t in completed_trades if t.get('pnl', 0) < 0]
    breakeven = [t for t in completed_trades if t.get('pnl', 0) == 0]
    
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    total_pnl = sum(t.get('pnl', 0) for t in completed_trades)
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
    
    avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
    
    # Breakdown by exit reason
    tp_trades = [t for t in completed_trades if t.get('exit_reason') == 'TAKE_PROFIT']
    sl_trades = [t for t in completed_trades if t.get('exit_reason') == 'STOP_LOSS']
    
    return {
        'total_trades': total_trades,
        'wins': len(wins),
        'losses': len(losses),
        'breakeven': len(breakeven),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'take_profit_exits': len(tp_trades),
        'stop_loss_exits': len(sl_trades),
        'conclusion': 'VIABLE' if win_rate > 55 and total_pnl > 0 else 'NO-GO'
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python flash_crash_backtest.py <data_file.jsonl>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    print(f"Loading data from {filepath}...")
    data = load_data(filepath)
    print(f"Loaded {len(data)} data points")
    
    print("\nRunning Flash Crash Strategy Backtest...")
    print("Parameters:")
    print("  Drop Threshold: 30%")
    print("  Lookback: 5 ticks (~10 seconds)")
    print("  Take Profit: 10%")
    print("  Stop Loss: 5%")
    print("  Trade Size: $10.00\n")
    
    strategy = FlashCrashStrategy(
        drop_threshold=0.30,
        lookback_ticks=5,
        take_profit=0.10,
        stop_loss=0.05,
        trade_size=10.0
    )
    
    # Run backtest
    for data_point in data:
        strategy.on_data(data_point)
    
    # Finalize
    strategy.finalize()
    
    # Analyze
    results = analyze_results(strategy.completed_trades)
    
    print(f"{'='*80}")
    print(f"FLASH CRASH BACKTEST RESULTS")
    print(f"{'='*80}\n")
    
    print(f"📊 Trading Statistics:")
    print(f"  Total Signals: {results['total_trades']}")
    print(f"  Wins: {results['wins']}")
    print(f"  Losses: {results['losses']}")
    print(f"  Breakeven: {results['breakeven']}")
    print(f"  Win Rate: {results['win_rate']:.1f}%")
    print(f"\n💰 P&L:")
    print(f"  Total PnL: ${results['total_pnl']:.2f}")
    print(f"  Average PnL/Trade: ${results['avg_pnl']:.2f}")
    print(f"  Average Win: ${results['avg_win']:.2f}")
    print(f"  Average Loss: ${results['avg_loss']:.2f}")
    print(f"\n📉 Exit Breakdown:")
    print(f"  Take Profit: {results['take_profit_exits']}")
    print(f"  Stop Loss: {results['stop_loss_exits']}")
    
    print(f"\n🎯 Conclusion: {results['conclusion']}")
    
    if results['conclusion'] == 'VIABLE':
        print("  ✅ Flash Crash策略在历史数据上表现良好！")
        print("  ✅ 建议进行paper trading验证")
    else:
        print("  ❌ Flash Crash策略在当前参数下无效")
        print("  ⚠️ 可能原因：")
        print("    1. Kalshi BTC市场没有足够的flash crash")
        print("    2. 参数需要调整")
        print("    3. REST polling太慢（需要WebSocket）")
    
    # Show sample trades
    if results['total_trades'] > 0:
        print(f"\n📋 Sample Trades (first 5):")
        print(f"{'Time':<20} {'Ticker':<30} {'Side':<5} {'Entry':<8} {'Exit':<8} {'Reason':<12} {'PnL':<10}")
        print("-" * 100)
        
        for trade in strategy.completed_trades[:5]:
            print(f"{trade['entry_time']:<20} {trade['ticker']:<30} {trade['side']:<5} "
                  f"${trade['entry_price']:<7.2f} ${trade.get('exit_price', 0):<7.2f} "
                  f"{trade.get('exit_reason', 'N/A'):<12} ${trade.get('pnl', 0):<9.2f}")
    
    # Save results
    output_file = filepath.replace('.jsonl', '_flash_crash_results.json')
    with open(output_file, 'w') as f:
        json.dump({
            'parameters': {
                'drop_threshold': strategy.drop_threshold,
                'lookback_ticks': strategy.lookback_ticks,
                'take_profit': strategy.take_profit,
                'stop_loss': strategy.stop_loss
            },
            'results': results,
            'trades': strategy.completed_trades
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")

if __name__ == "__main__":
    main()
