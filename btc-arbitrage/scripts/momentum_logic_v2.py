#!/usr/bin/env python3
"""
Momentum + Logic Arbitrage V2
Combines BTC momentum with Kalshi market inefficiency logic
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Import indicators from simple version
import sys
sys.path.append(str(Path(__file__).parent))
from momentum_backtest_simple import SimpleIndicators, load_data, calculate_indicators

# Enhanced configuration
CONFIG = {
    # Indicators
    "lookback_rsi": 14,
    "roc_fast_period": 4,
    "roc_medium_period": 10,
    
    # Entry filters
    "min_time_remaining": 300,      # 5 minutes
    "max_spread": 0.05,
    "avoid_extremes": True,         # Don't trade if price already at 0.95+ or 0.05-
    "min_edge_threshold": 0.10,     # Min 10% edge required
    
    # Risk management
    "profit_target": 0.08,          # 8% (more realistic)
    "stop_loss": 0.10,              # 10% (tighter)
    "position_size": 100,
    
    # Logic arbitrage
    "use_strike_logic": True,       # Consider BTC price vs strike price
    "momentum_weight": 0.6,         # 60% momentum, 40% logic
    "logic_weight": 0.4,
}


def extract_strike_price(ticker: str) -> float:
    """Extract strike price from ticker
    Format: KXBTC15M-26FEB020300-00
    Last two digits are the strike in hundreds (00 = $XX,X00)
    """
    try:
        parts = ticker.split('-')
        if len(parts) >= 3:
            strike_code = parts[2]  # "00", "30", "45", etc.
            
            # This is the last 2 digits of strike price
            # Need to infer the full strike from BTC price context
            # For now, return the fractional part
            return float(strike_code)
    except:
        pass
    return None


def calculate_fair_value(btc_price: float, strike_approx: float, time_to_close: float) -> float:
    """
    Calculate fair value probability that BTC will be above strike
    
    This is a simplified model. Real version would use:
    - Black-Scholes-like option pricing
    - Historical volatility
    - Drift estimation
    
    For now: naive probability based on distance to strike and time
    """
    if time_to_close <= 0:
        return 1.0 if btc_price > strike_approx else 0.0
    
    # Very simplified: closer to strike = closer to 50/50
    # More time = more uncertainty
    
    # Estimate strike price (last 2 digits)
    # E.g., if strike_code is 30 and BTC is ~76,000
    # Strike is probably 76,030 or 76,730 etc
    
    # Round BTC price to nearest 100
    base = (btc_price // 100) * 100
    
    # Try different strike possibilities
    possible_strikes = [
        base + strike_approx,
        base - 100 + strike_approx,
        base + 100 + strike_approx
    ]
    
    # Pick the closest one
    strike = min(possible_strikes, key=lambda s: abs(s - btc_price))
    
    # Distance to strike (in % of BTC price)
    distance_pct = (btc_price - strike) / btc_price * 100
    
    # Time factor (more time = more mean reversion)
    time_minutes = time_to_close / 60
    time_factor = min(time_minutes / 15, 1.0)  # Normalize to 15 min
    
    # Probability estimate (sigmoid-like)
    # If BTC well above strike → high prob YES
    # If BTC well below strike → low prob YES
    
    if distance_pct > 0.3:  # BTC is 0.3%+ above strike
        base_prob = 0.85
    elif distance_pct > 0.1:
        base_prob = 0.70
    elif distance_pct > -0.1:
        base_prob = 0.50
    elif distance_pct > -0.3:
        base_prob = 0.30
    else:
        base_prob = 0.15
    
    # Adjust for time (less time = more certain)
    certainty = 1.0 - time_factor * 0.3  # Up to 30% uncertainty with full time
    
    if base_prob > 0.5:
        fair_value = 0.5 + (base_prob - 0.5) * certainty
    else:
        fair_value = 0.5 - (0.5 - base_prob) * certainty
    
    return fair_value


def generate_enhanced_signal(record: Dict) -> Dict:
    """Generate signal using momentum + logic"""
    
    signal = {
        'action': None,
        'confidence': 0,
        'reason': [],
        'momentum_score': 0,
        'logic_score': 0,
        'fair_value': None,
        'edge': 0
    }
    
    # Extract data
    rsi = record.get('rsi')
    roc_fast = record.get('roc_fast')
    roc_medium = record.get('roc_medium')
    spread = record['spread']
    time_to_close = record.get('time_to_close', 999)
    mid_price = record['mid_price']
    btc_price = record['brti']
    ticker = record['ticker']
    
    # Filters
    if time_to_close < CONFIG['min_time_remaining']:
        signal['reason'].append('Too close to close')
        return signal
    
    if spread > CONFIG['max_spread']:
        signal['reason'].append(f'Spread too wide: ${spread:.3f}')
        return signal
    
    # Avoid extreme prices (already decided)
    if CONFIG['avoid_extremes']:
        if mid_price > 0.95:
            signal['reason'].append('Price too high (>0.95)')
            return signal
        if mid_price < 0.05:
            signal['reason'].append('Price too low (<0.05)')
            return signal
    
    # Check for None values
    if any(v is None for v in [rsi, roc_fast, roc_medium]):
        signal['reason'].append('Insufficient data')
        return signal
    
    # --- MOMENTUM SCORE (-1 to +1) ---
    momentum_score = 0
    
    # ROC contribution
    if roc_fast > 0.3:
        momentum_score += 1.0
    elif roc_fast > 0.15:
        momentum_score += 0.5
    elif roc_fast < -0.3:
        momentum_score -= 1.0
    elif roc_fast < -0.15:
        momentum_score -= 0.5
    
    # RSI contribution
    if rsi < 25:
        momentum_score += 0.3  # Oversold, expect bounce
    elif rsi > 75:
        momentum_score -= 0.3  # Overbought, expect reversal
    
    # Medium ROC confirmation
    if roc_medium > 0.1 and momentum_score > 0:
        momentum_score += 0.3
    elif roc_medium < -0.1 and momentum_score < 0:
        momentum_score -= 0.3
    
    signal['momentum_score'] = momentum_score
    
    # --- LOGIC SCORE (market inefficiency) ---
    strike_code = extract_strike_price(ticker)
    
    if strike_code is not None and CONFIG['use_strike_logic']:
        fair_value = calculate_fair_value(btc_price, strike_code, time_to_close)
        signal['fair_value'] = fair_value
        
        # Edge = fair_value - mid_price
        edge = fair_value - mid_price
        signal['edge'] = edge
        
        # Convert edge to logic score
        if abs(edge) > CONFIG['min_edge_threshold']:
            logic_score = min(max(edge * 5, -1.0), 1.0)  # Scale to -1 to +1
        else:
            logic_score = 0  # Edge too small
        
        signal['logic_score'] = logic_score
    else:
        signal['logic_score'] = 0
    
    # --- COMBINED SCORE ---
    combined_score = (
        CONFIG['momentum_weight'] * momentum_score +
        CONFIG['logic_weight'] * signal['logic_score']
    )
    
    # Decision threshold
    BUY_THRESHOLD = 0.4  # Need strong combined signal
    
    if combined_score >= BUY_THRESHOLD:
        signal['action'] = 'BUY_YES'
        signal['confidence'] = min(int(combined_score * 5), 3)
        signal['reason'].append(f'Combined score: {combined_score:.2f} (mom={momentum_score:.2f}, logic={signal["logic_score"]:.2f})')
        
        if signal['edge'] > 0:
            signal['reason'].append(f'Edge: {signal["edge"]*100:.1f}% (FV={signal["fair_value"]:.2f} vs Mid={mid_price:.2f})')
    
    elif combined_score <= -BUY_THRESHOLD:
        signal['action'] = 'BUY_NO'
        signal['confidence'] = min(int(abs(combined_score) * 5), 3)
        signal['reason'].append(f'Combined score: {combined_score:.2f} (mom={momentum_score:.2f}, logic={signal["logic_score"]:.2f})')
        
        if signal['edge'] < 0:
            signal['reason'].append(f'Edge: {abs(signal["edge"])*100:.1f}% (FV={signal["fair_value"]:.2f} vs Mid={mid_price:.2f})')
    
    return signal


def simulate_trade_v2(entry_record: Dict, future_data: List[Dict], action: str) -> Dict:
    """Simulate trade with updated risk params"""
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
    
    for record in future_data:
        time_to_close = record.get('time_to_close', 0)
        
        # Exit before close
        if time_to_close < 60:
            exit_price = record['yes_bid'] if entry_side == 'YES' else (1.0 - record['yes_ask'])
            trade['exit_time'] = record['timestamp']
            trade['exit_price'] = exit_price
            trade['exit_reason'] = 'Market close'
            break
        
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
    
    # Calculate PnL
    if trade['exit_price'] is not None:
        trade['pnl'] = (trade['exit_price'] - trade['entry_price']) * CONFIG['position_size']
        trade['roi'] = (trade['exit_price'] - trade['entry_price']) / entry_price if entry_price > 0 else 0
        trade['win'] = trade['pnl'] > 0
    
    return trade


def run_enhanced_backtest(data: List[Dict]) -> List[Dict]:
    """Run enhanced backtest"""
    print("\n🚀 Running Enhanced Momentum + Logic Backtest...")
    
    trades = []
    last_exit_time = None
    signals_generated = 0
    signals_traded = 0
    
    for i, record in enumerate(data):
        signal = generate_enhanced_signal(record)
        
        if signal['action'] is not None:
            signals_generated += 1
            
            # Wait after last exit
            if last_exit_time and (record['timestamp'] - last_exit_time).total_seconds() < 60:
                continue
            
            future_data = [d for d in data[i+1:] if d['ticker'] == record['ticker']]
            
            if len(future_data) >= 5:
                signals_traded += 1
                
                if signals_traded <= 10 or signals_traded % 20 == 0:  # Print first 10 + every 20th
                    print(f"\n📡 Signal #{signals_traded} at {record['timestamp']}: {signal['action']}")
                    print(f"   {', '.join(signal['reason'])}")
                
                trade = simulate_trade_v2(record, future_data, signal['action'])
                trade.update({
                    'signal_confidence': signal['confidence'],
                    'signal_reason': ', '.join(signal['reason']),
                    'momentum_score': signal['momentum_score'],
                    'logic_score': signal['logic_score'],
                    'edge': signal['edge']
                })
                
                trades.append(trade)
                
                if signals_traded <= 10 or signals_traded % 20 == 0:
                    print(f"   Entry: ${trade['entry_price']:.3f} ({trade['entry_side']})")
                    if trade['exit_price']:
                        print(f"   Exit: ${trade['exit_price']:.3f} ({trade['exit_reason']})")
                        print(f"   PnL: ${trade['pnl']:.2f} ({trade['roi']*100:.1f}%) "
                              f"{'✅' if trade['win'] else '❌'}")
                
                if trade['exit_time']:
                    last_exit_time = trade['exit_time']
    
    print(f"\n✅ Backtest complete:")
    print(f"   Signals generated: {signals_generated}")
    print(f"   Signals traded: {signals_traded}")
    
    return trades


def analyze_results_v2(trades: List[Dict]):
    """Analyze enhanced backtest results"""
    if not trades:
        print("\n⚠️ No trades")
        return {}
    
    complete = [t for t in trades if t['exit_price'] is not None]
    
    if not complete:
        print("\n⚠️ No complete trades")
        return {}
    
    total = len(complete)
    wins = sum(1 for t in complete if t['win'])
    win_rate = wins / total
    
    total_pnl = sum(t['pnl'] for t in complete)
    avg_pnl = total_pnl / total
    avg_roi = sum(t['roi'] for t in complete) / total
    
    winning = [t['pnl'] for t in complete if t['win']]
    losing = [t['pnl'] for t in complete if not t['win']]
    
    avg_win = sum(winning) / len(winning) if winning else 0
    avg_loss = sum(losing) / len(losing) if losing else 0
    
    # Sharpe
    roi_vals = [t['roi'] for t in complete]
    mean_roi = sum(roi_vals) / len(roi_vals)
    variance = sum((r - mean_roi) ** 2 for r in roi_vals) / len(roi_vals)
    std_roi = variance ** 0.5
    sharpe = (mean_roi / std_roi * (252 ** 0.5)) if std_roi > 0 else 0
    
    # Max DD
    cumulative = 0
    max_seen = 0
    max_dd = 0
    for t in complete:
        cumulative += t['pnl']
        max_seen = max(max_seen, cumulative)
        max_dd = min(max_dd, cumulative - max_seen)
    
    max_dd_pct = max_dd / CONFIG['position_size']
    
    # Trade frequency
    time_span = (complete[-1]['exit_time'] - complete[0]['entry_time']).total_seconds() / 3600
    trades_per_day = (total / time_span * 24) if time_span > 0 else 0
    
    print("\n" + "="*60)
    print("📊 ENHANCED MOMENTUM + LOGIC BACKTEST RESULTS")
    print("="*60)
    
    print(f"\n🎯 Trade Summary:")
    print(f"   Total: {total} | Wins: {wins} ({win_rate*100:.1f}%) | Losses: {total-wins} ({(1-win_rate)*100:.1f}%)")
    
    print(f"\n💰 P&L:")
    print(f"   Total: ${total_pnl:.2f} | Avg: ${avg_pnl:.2f} | Avg ROI: {avg_roi*100:.2f}%")
    print(f"   Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f}")
    print(f"   Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}x" if avg_loss != 0 else "   Win/Loss Ratio: N/A")
    
    print(f"\n📈 Risk:")
    print(f"   Sharpe: {sharpe:.2f} | Max DD: ${max_dd:.2f} ({max_dd_pct*100:.1f}%)")
    print(f"   Trade Frequency: {trades_per_day:.1f}/day")
    
    print(f"\n✅ Success Criteria:")
    checks = [
        ("Win Rate >55%", win_rate > 0.55, f"{win_rate*100:.1f}%"),
        ("Avg ROI >5%", avg_roi > 0.05, f"{avg_roi*100:.1f}%"),
        ("Sharpe >1.0", sharpe > 1.0, f"{sharpe:.2f}"),
        ("Max DD <20%", max_dd_pct > -0.20, f"{max_dd_pct*100:.1f}%"),
        ("Trades 5-20/day", 5 <= trades_per_day <= 20, f"{trades_per_day:.1f}/day")
    ]
    
    for name, passed, value in checks:
        print(f"   {name}: {'✅' if passed else '❌'} ({value})")
    
    print("\n" + "="*60)
    
    return {
        'total_trades': total,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_roi': avg_roi,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': max_dd_pct,
        'trades_per_day': trades_per_day,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'trades': complete
    }


def main():
    print("🚀 Momentum + Logic Arbitrage V2\n")
    
    data_path = Path(__file__).parent.parent / "data" / "collection_20260202_024420.jsonl"
    
    # Load and prep data
    data = load_data(data_path)
    data = calculate_indicators(data)
    
    # Run enhanced backtest
    trades = run_enhanced_backtest(data)
    
    # Analyze
    results = analyze_results_v2(trades)
    
    # Save
    if results:
        output_dir = Path(__file__).parent.parent / "backtest_results"
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / 'backtest_v2_results.json'
        with open(output_file, 'w') as f:
            json.dump({
                'config': CONFIG,
                'summary': {k: v for k, v in results.items() if k != 'trades'},
                'trades': [
                    {
                        'entry_time': t['entry_time'].isoformat(),
                        'exit_time': t['exit_time'].isoformat(),
                        'entry_price': t['entry_price'],
                        'exit_price': t['exit_price'],
                        'pnl': t['pnl'],
                        'roi': t['roi'],
                        'win': t['win'],
                        'exit_reason': t['exit_reason'],
                        'momentum_score': t.get('momentum_score'),
                        'logic_score': t.get('logic_score'),
                        'edge': t.get('edge')
                    }
                    for t in results['trades']
                ]
            }, f, indent=2)
        print(f"\n💾 Saved: {output_file}")


if __name__ == "__main__":
    main()
