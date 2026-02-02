#!/usr/bin/env python3
"""
Momentum/Logic Arbitrage Backtest (Standard Library Only)
Validates momentum strategy on historical BTC-Kalshi data
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from collections import deque

# Configuration
CONFIG = {
    "lookback_rsi": 14,
    "lookback_macd_fast": 12,
    "lookback_macd_slow": 26,
    "lookback_macd_signal": 9,
    "roc_fast_period": 4,         # 2 minutes at 30s interval
    "roc_medium_period": 10,      # 5 minutes at 30s interval
    "min_time_remaining": 300,    # 5 minutes
    "max_spread": 0.05,
    "entry_threshold_roc": 0.15,  # 0.15%
    "profit_target": 0.10,        # 10% ROI
    "stop_loss": 0.15,            # 15% max loss
    "position_size": 100,         # $100 per trade
}


class SimpleIndicators:
    """Calculate technical indicators using standard library"""
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return [None] * len(prices)
        
        ema = [None] * len(prices)
        multiplier = 2 / (period + 1)
        
        # Start with SMA
        sma = sum(prices[:period]) / period
        ema[period - 1] = sma
        
        # Calculate EMA
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]
        
        return ema
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        rsi = [None] * len(prices)
        gains = []
        losses = []
        
        # Calculate initial average gain/loss
        for i in range(1, period + 1):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        # Calculate RSI
        for i in range(period, len(prices)):
            change = prices[i] - prices[i-1]
            
            if change > 0:
                gain = change
                loss = 0
            else:
                gain = 0
                loss = abs(change)
            
            # Smoothed averages
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            
            if avg_loss == 0:
                rsi[i] = 100
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(prices: List[float], 
                       fast: int = 12, 
                       slow: int = 26, 
                       signal: int = 9) -> Tuple[List, List, List]:
        """Calculate MACD, Signal Line, and Histogram"""
        ema_fast = SimpleIndicators.calculate_ema(prices, fast)
        ema_slow = SimpleIndicators.calculate_ema(prices, slow)
        
        macd = [None] * len(prices)
        for i in range(len(prices)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd[i] = ema_fast[i] - ema_slow[i]
        
        # Calculate signal line (EMA of MACD)
        macd_values = [m for m in macd if m is not None]
        signal_line = [None] * len(prices)
        
        if len(macd_values) >= signal:
            signal_ema = SimpleIndicators.calculate_ema(
                [m if m is not None else 0 for m in macd], 
                signal
            )
            signal_line = signal_ema
        
        # Calculate histogram
        histogram = [None] * len(prices)
        for i in range(len(prices)):
            if macd[i] is not None and signal_line[i] is not None:
                histogram[i] = macd[i] - signal_line[i]
        
        return macd, signal_line, histogram
    
    @staticmethod
    def calculate_roc(prices: List[float], period: int) -> List[float]:
        """Calculate Rate of Change"""
        roc = [None] * len(prices)
        
        for i in range(period, len(prices)):
            if prices[i - period] != 0:
                roc[i] = ((prices[i] - prices[i - period]) / prices[i - period]) * 100
        
        return roc


def load_data(data_path: Path) -> List[Dict]:
    """Load JSONL data"""
    print(f"📂 Loading data from {data_path}")
    
    records = []
    with open(data_path, 'r') as f:
        for line in f:
            data = json.loads(line)
            
            # Parse and enrich
            data['timestamp'] = datetime.fromisoformat(data['t'].replace('Z', '+00:00'))
            data['ticker'] = data['kalshi']['ticker']
            data['yes_bid'] = data['kalshi']['yes_bid']
            data['yes_ask'] = data['kalshi']['yes_ask']
            data['volume'] = data['kalshi']['volume']
            data['spread'] = data['yes_ask'] - data['yes_bid']
            data['mid_price'] = (data['yes_bid'] + data['yes_ask']) / 2
            
            records.append(data)
    
    # Sort by time
    records.sort(key=lambda x: x['timestamp'])
    
    print(f"✅ Loaded {len(records)} data points")
    print(f"   Time range: {records[0]['timestamp']} → {records[-1]['timestamp']}")
    duration_hours = (records[-1]['timestamp'] - records[0]['timestamp']).total_seconds() / 3600
    print(f"   Duration: {duration_hours:.1f} hours")
    
    return records


def calculate_indicators(data: List[Dict]) -> List[Dict]:
    """Calculate technical indicators for all data"""
    print("\n📊 Calculating indicators...")
    
    prices = [d['brti'] for d in data]
    
    # Calculate indicators
    indicators = SimpleIndicators()
    
    rsi_values = indicators.calculate_rsi(prices, CONFIG['lookback_rsi'])
    macd, macd_signal, macd_hist = indicators.calculate_macd(
        prices,
        CONFIG['lookback_macd_fast'],
        CONFIG['lookback_macd_slow'],
        CONFIG['lookback_macd_signal']
    )
    roc_fast = indicators.calculate_roc(prices, CONFIG['roc_fast_period'])
    roc_medium = indicators.calculate_roc(prices, CONFIG['roc_medium_period'])
    
    # Add to data
    for i, record in enumerate(data):
        record['rsi'] = rsi_values[i]
        record['macd'] = macd[i]
        record['macd_signal'] = macd_signal[i]
        record['macd_histogram'] = macd_hist[i]
        record['roc_fast'] = roc_fast[i]
        record['roc_medium'] = roc_medium[i]
    
    # Calculate time to close
    for record in data:
        try:
            ticker = record['ticker']
            parts = ticker.split('-')
            if len(parts) >= 2:
                time_str = parts[1][-6:]
                hour = int(time_str[:2])
                minute = int(time_str[2:4])
                
                date_part = parts[1][:-6]
                day = int(date_part[:2])
                month_map = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 
                            'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
                            'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12}
                month = month_map.get(date_part[2:], 2)
                
                close_time = datetime(2026, month, day, hour, minute)
                record['time_to_close'] = (close_time - record['timestamp']).total_seconds()
            else:
                record['time_to_close'] = 999
        except:
            record['time_to_close'] = 999
    
    print(f"✅ Indicators calculated")
    
    # Print some stats
    valid_rsi = [r for r in rsi_values if r is not None]
    valid_roc = [r for r in roc_fast if r is not None]
    if valid_rsi:
        print(f"   RSI range: {min(valid_rsi):.1f} - {max(valid_rsi):.1f}")
    if valid_roc:
        print(f"   ROC fast range: {min(valid_roc):.2f}% - {max(valid_roc):.2f}%")
    
    return data


def generate_signal(record: Dict) -> Dict:
    """Generate trading signal"""
    rsi = record.get('rsi')
    macd = record.get('macd')
    macd_signal = record.get('macd_signal')
    macd_hist = record.get('macd_histogram')
    roc_fast = record.get('roc_fast')
    roc_medium = record.get('roc_medium')
    spread = record['spread']
    time_to_close = record.get('time_to_close', 999)
    
    signal = {
        'action': None,
        'confidence': 0,
        'reason': []
    }
    
    # Filters
    if time_to_close < CONFIG['min_time_remaining']:
        signal['reason'].append('Too close to market close')
        return signal
    
    if spread > CONFIG['max_spread']:
        signal['reason'].append(f'Spread too wide: ${spread:.3f}')
        return signal
    
    # Check for None values
    if any(v is None for v in [rsi, macd, macd_signal, roc_fast, roc_medium]):
        signal['reason'].append('Insufficient data')
        return signal
    
    # BULLISH SIGNALS
    if roc_fast > 0.2 and 60 < rsi < 75 and macd > macd_signal:
        signal['action'] = 'BUY_YES'
        signal['confidence'] = 3
        signal['reason'].append('Strong upward momentum')
    elif roc_fast > CONFIG['entry_threshold_roc'] and roc_medium > 0.08:
        signal['action'] = 'BUY_YES'
        signal['confidence'] = 2
        signal['reason'].append('Fast + medium ROC positive')
    elif rsi < 30 and roc_fast > 0.08:
        signal['action'] = 'BUY_YES'
        signal['confidence'] = 2
        signal['reason'].append('Oversold bounce')
    elif roc_fast > 0.25:  # Strong momentum alone
        signal['action'] = 'BUY_YES'
        signal['confidence'] = 2
        signal['reason'].append('Very strong upward move')
    
    # BEARISH SIGNALS
    elif roc_fast < -0.2 and 25 < rsi < 40 and macd < macd_signal:
        signal['action'] = 'BUY_NO'
        signal['confidence'] = 3
        signal['reason'].append('Strong downward momentum')
    elif roc_fast < -CONFIG['entry_threshold_roc'] and roc_medium < -0.08:
        signal['action'] = 'BUY_NO'
        signal['confidence'] = 2
        signal['reason'].append('Fast + medium ROC negative')
    elif rsi > 70 and roc_fast < -0.08:
        signal['action'] = 'BUY_NO'
        signal['confidence'] = 2
        signal['reason'].append('Overbought reversal')
    elif roc_fast < -0.25:  # Strong momentum alone
        signal['action'] = 'BUY_NO'
        signal['confidence'] = 2
        signal['reason'].append('Very strong downward move')
    
    return signal


def simulate_trade(entry_record: Dict, future_data: List[Dict], action: str) -> Dict:
    """Simulate a trade"""
    entry_time = entry_record['timestamp']
    
    if action == 'BUY_YES':
        entry_side = 'YES'
        entry_price = entry_record['yes_ask']
    else:
        entry_side = 'NO'
        entry_price = 1.0 - entry_record['yes_bid']
    
    trade = {
        'entry_time': entry_time,
        'entry_price': entry_price,
        'entry_side': entry_side,
        'ticker': entry_record['ticker'],
        'exit_time': None,
        'exit_price': None,
        'exit_reason': None,
        'pnl': 0,
        'roi': 0,
        'win': False
    }
    
    # Simulate holding
    for record in future_data:
        time_elapsed = (record['timestamp'] - entry_time).total_seconds()
        
        # Market close approaching
        if record.get('time_to_close', 0) < 60:
            exit_price = record['yes_bid'] if entry_side == 'YES' else (1.0 - record['yes_ask'])
            trade['exit_time'] = record['timestamp']
            trade['exit_price'] = exit_price
            trade['exit_reason'] = 'Market close'
            break
        
        # Current price
        current_price = record['yes_bid'] if entry_side == 'YES' else (1.0 - record['yes_ask'])
        unrealized_roi = (current_price - entry_price) / entry_price if entry_price > 0 else 0
        
        # Profit target
        if unrealized_roi >= CONFIG['profit_target']:
            trade['exit_time'] = record['timestamp']
            trade['exit_price'] = current_price
            trade['exit_reason'] = 'Profit target'
            break
        
        # Stop loss
        if unrealized_roi <= -CONFIG['stop_loss']:
            trade['exit_time'] = record['timestamp']
            trade['exit_price'] = current_price
            trade['exit_reason'] = 'Stop loss'
            break
        
        # Momentum reversal
        rsi = record.get('rsi')
        roc_fast = record.get('roc_fast')
        if rsi is not None and roc_fast is not None:
            if entry_side == 'YES' and rsi < 45 and roc_fast < -0.1:
                trade['exit_time'] = record['timestamp']
                trade['exit_price'] = current_price
                trade['exit_reason'] = 'Momentum reversal'
                break
            elif entry_side == 'NO' and rsi > 55 and roc_fast > 0.1:
                trade['exit_time'] = record['timestamp']
                trade['exit_price'] = current_price
                trade['exit_reason'] = 'Momentum reversal'
                break
    
    # Calculate PnL
    if trade['exit_price'] is not None:
        trade['pnl'] = (trade['exit_price'] - trade['entry_price']) * CONFIG['position_size']
        trade['roi'] = (trade['exit_price'] - trade['entry_price']) / entry_price if entry_price > 0 else 0
        trade['win'] = trade['pnl'] > 0
    
    return trade


def run_backtest(data: List[Dict]) -> List[Dict]:
    """Run backtest"""
    print("\n🚀 Running backtest...")
    
    trades = []
    last_exit_time = None
    signals_generated = 0
    signals_traded = 0
    
    for i, record in enumerate(data):
        signal = generate_signal(record)
        
        if signal['action'] is not None:
            signals_generated += 1
            
            # Don't enter new trade if last one just exited (wait at least 1 minute)
            if last_exit_time and (record['timestamp'] - last_exit_time).total_seconds() < 60:
                continue
            
            # Get future data for same market
            future_data = [
                d for d in data[i+1:] 
                if d['ticker'] == record['ticker']
            ]
            
            if len(future_data) >= 5:
                signals_traded += 1
                
                print(f"\n📡 Signal #{signals_traded} at {record['timestamp']}: {signal['action']} "
                      f"(confidence={signal['confidence']})")
                print(f"   Reason: {', '.join(signal['reason'])}")
                
                trade = simulate_trade(record, future_data, signal['action'])
                trade['signal_confidence'] = signal['confidence']
                trade['signal_reason'] = ', '.join(signal['reason'])
                
                trades.append(trade)
                
                print(f"   Entry: ${trade['entry_price']:.3f} ({trade['entry_side']})")
                if trade['exit_price']:
                    print(f"   Exit: ${trade['exit_price']:.3f} ({trade['exit_reason']})")
                    print(f"   PnL: ${trade['pnl']:.2f} ({trade['roi']*100:.1f}%) "
                          f"{'✅ WIN' if trade['win'] else '❌ LOSS'}")
                    last_exit_time = trade['exit_time']
    
    print(f"\n✅ Backtest complete:")
    print(f"   Signals generated: {signals_generated}")
    print(f"   Signals traded: {signals_traded}")
    print(f"   Completed trades: {len([t for t in trades if t['exit_price'] is not None])}")
    return trades


def analyze_results(trades: List[Dict]):
    """Analyze and print results"""
    if not trades:
        print("\n⚠️ No trades executed")
        return
    
    complete_trades = [t for t in trades if t['exit_price'] is not None]
    
    if not complete_trades:
        print("\n⚠️ No complete trades")
        return
    
    total = len(complete_trades)
    wins = sum(1 for t in complete_trades if t['win'])
    losses = total - wins
    win_rate = wins / total if total > 0 else 0
    
    total_pnl = sum(t['pnl'] for t in complete_trades)
    avg_pnl = total_pnl / total if total > 0 else 0
    avg_roi = sum(t['roi'] for t in complete_trades) / total if total > 0 else 0
    
    winning_pnl = [t['pnl'] for t in complete_trades if t['win']]
    losing_pnl = [t['pnl'] for t in complete_trades if not t['win']]
    
    avg_win = sum(winning_pnl) / len(winning_pnl) if winning_pnl else 0
    avg_loss = sum(losing_pnl) / len(losing_pnl) if losing_pnl else 0
    
    # Calculate sharpe (simplified)
    roi_values = [t['roi'] for t in complete_trades]
    mean_roi = sum(roi_values) / len(roi_values)
    variance = sum((r - mean_roi) ** 2 for r in roi_values) / len(roi_values)
    std_roi = variance ** 0.5
    sharpe = (mean_roi / std_roi * (252 ** 0.5)) if std_roi > 0 else 0
    
    # Max drawdown
    cumulative = 0
    max_seen = 0
    max_dd = 0
    for t in complete_trades:
        cumulative += t['pnl']
        max_seen = max(max_seen, cumulative)
        drawdown = cumulative - max_seen
        max_dd = min(max_dd, drawdown)
    
    max_dd_pct = max_dd / CONFIG['position_size'] if CONFIG['position_size'] > 0 else 0
    
    # Print report
    print("\n" + "="*60)
    print("📊 MOMENTUM STRATEGY BACKTEST RESULTS")
    print("="*60)
    
    print(f"\n🎯 Trade Summary:")
    print(f"   Total Trades: {total}")
    print(f"   Winners: {wins} ({win_rate*100:.1f}%)")
    print(f"   Losers: {losses} ({(1-win_rate)*100:.1f}%)")
    
    print(f"\n💰 P&L:")
    print(f"   Total PnL: ${total_pnl:.2f}")
    print(f"   Avg PnL/Trade: ${avg_pnl:.2f}")
    print(f"   Avg ROI: {avg_roi*100:.2f}%")
    print(f"   Avg Win: ${avg_win:.2f}")
    print(f"   Avg Loss: ${avg_loss:.2f}")
    
    print(f"\n📈 Risk Metrics:")
    print(f"   Sharpe Ratio: {sharpe:.2f}")
    print(f"   Max Drawdown: ${max_dd:.2f} ({max_dd_pct*100:.1f}%)")
    
    # Trade frequency
    if complete_trades:
        time_span = (complete_trades[-1]['exit_time'] - complete_trades[0]['entry_time']).total_seconds() / 3600
        trades_per_day = (total / time_span * 24) if time_span > 0 else 0
    else:
        trades_per_day = 0
    
    print(f"\n✅ Success Criteria:")
    print(f"   Win Rate >55%: {'✅' if win_rate > 0.55 else '❌'} ({win_rate*100:.1f}%)")
    print(f"   Avg ROI >5%: {'✅' if avg_roi > 0.05 else '❌'} ({avg_roi*100:.1f}%)")
    print(f"   Sharpe >1.0: {'✅' if sharpe > 1.0 else '❌'} ({sharpe:.2f})")
    print(f"   Max DD <20%: {'✅' if max_dd_pct > -0.20 else '❌'} ({max_dd_pct*100:.1f}%)")
    print(f"   Trades >5/day: {'✅' if trades_per_day > 5 else '❌'} ({trades_per_day:.1f}/day)")
    
    print("\n" + "="*60)
    
    return {
        'total_trades': total,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_roi': avg_roi,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': max_dd_pct,
        'trades_per_day': trades_per_day,
        'trades': complete_trades
    }


def main():
    """Main execution"""
    print("🚀 Momentum Strategy Backtest (Simple Version)\n")
    
    # Paths
    data_path = Path(__file__).parent.parent / "data" / "collection_20260202_024420.jsonl"
    output_dir = Path(__file__).parent.parent / "backtest_results"
    output_dir.mkdir(exist_ok=True)
    
    # Load data
    data = load_data(data_path)
    
    # Calculate indicators
    data = calculate_indicators(data)
    
    # Run backtest
    trades = run_backtest(data)
    
    # Analyze
    results = analyze_results(trades)
    
    # Save results
    if results:
        output_file = output_dir / 'backtest_results.json'
        with open(output_file, 'w') as f:
            json.dump({
                'config': CONFIG,
                'summary': {
                    'total_trades': results['total_trades'],
                    'win_rate': results['win_rate'],
                    'total_pnl': results['total_pnl'],
                    'avg_roi': results['avg_roi'],
                    'sharpe_ratio': results['sharpe_ratio'],
                    'max_drawdown_pct': results['max_drawdown_pct'],
                    'trades_per_day': results['trades_per_day']
                },
                'trades': [
                    {
                        'entry_time': t['entry_time'].isoformat(),
                        'exit_time': t['exit_time'].isoformat(),
                        'entry_price': t['entry_price'],
                        'exit_price': t['exit_price'],
                        'pnl': t['pnl'],
                        'roi': t['roi'],
                        'win': t['win'],
                        'exit_reason': t['exit_reason']
                    }
                    for t in results['trades']
                ]
            }, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")
    
    print("\n✅ Backtest complete!")


if __name__ == "__main__":
    main()
