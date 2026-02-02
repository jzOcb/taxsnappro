#!/usr/bin/env python3
"""
Momentum/Logic Arbitrage Backtest
Validates momentum strategy on historical BTC-Kalshi data
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns

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


class MomentumIndicators:
    """Calculate technical indicators for momentum trading"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(prices: pd.Series, 
                       fast: int = 12, 
                       slow: int = 26, 
                       signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, Signal Line, and Histogram"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        
        return macd, signal_line, histogram
    
    @staticmethod
    def calculate_roc(prices: pd.Series, period: int) -> pd.Series:
        """Calculate Rate of Change"""
        roc = ((prices - prices.shift(period)) / prices.shift(period)) * 100
        return roc


class MomentumStrategy:
    """Momentum arbitrage strategy logic"""
    
    def __init__(self, config: Dict):
        self.config = config
        
    def generate_signal(self, row: pd.Series) -> Dict:
        """Generate trading signal based on indicators"""
        
        # Extract indicators
        rsi = row['rsi']
        macd = row['macd']
        macd_signal = row['macd_signal']
        macd_hist = row['macd_histogram']
        roc_fast = row['roc_fast']
        roc_medium = row['roc_medium']
        spread = row['spread']
        time_to_close = row.get('time_to_close', 999)
        
        # Initialize signal
        signal = {
            'action': None,  # 'BUY_YES', 'BUY_NO', or None
            'confidence': 0,
            'reason': []
        }
        
        # Filter: Time remaining
        if time_to_close < self.config['min_time_remaining']:
            signal['reason'].append('Too close to market close')
            return signal
        
        # Filter: Spread too wide
        if spread > self.config['max_spread']:
            signal['reason'].append(f'Spread too wide: ${spread:.3f}')
            return signal
        
        # Check for NaN values
        if pd.isna([rsi, macd, macd_signal, roc_fast, roc_medium]).any():
            signal['reason'].append('Insufficient data for indicators')
            return signal
        
        # --- BULLISH SIGNALS ---
        
        # High confidence bullish
        if (roc_fast > 0.2 and 
            rsi > 60 and rsi < 75 and 
            macd > macd_signal):
            signal['action'] = 'BUY_YES'
            signal['confidence'] = 3
            signal['reason'].append('Strong upward momentum + RSI bullish + MACD cross')
        
        # Medium confidence bullish
        elif (roc_fast > self.config['entry_threshold_roc'] and 
              roc_medium > 0.1):
            signal['action'] = 'BUY_YES'
            signal['confidence'] = 2
            signal['reason'].append('Fast + medium ROC both positive')
        
        # Oversold bounce
        elif rsi < 30 and roc_fast > 0.1 and macd_hist > 0:
            signal['action'] = 'BUY_YES'
            signal['confidence'] = 2
            signal['reason'].append('Oversold RSI + momentum reversal')
        
        # --- BEARISH SIGNALS ---
        
        # High confidence bearish
        elif (roc_fast < -0.2 and 
              rsi > 25 and rsi < 40 and 
              macd < macd_signal):
            signal['action'] = 'BUY_NO'
            signal['confidence'] = 3
            signal['reason'].append('Strong downward momentum + RSI bearish + MACD cross')
        
        # Medium confidence bearish
        elif (roc_fast < -self.config['entry_threshold_roc'] and 
              roc_medium < -0.1):
            signal['action'] = 'BUY_NO'
            signal['confidence'] = 2
            signal['reason'].append('Fast + medium ROC both negative')
        
        # Overbought reversal
        elif rsi > 70 and roc_fast < -0.1 and macd_hist < 0:
            signal['action'] = 'BUY_NO'
            signal['confidence'] = 2
            signal['reason'].append('Overbought RSI + momentum reversal')
        
        return signal
    
    def simulate_trade(self, entry_row: pd.Series, 
                       future_data: pd.DataFrame,
                       action: str) -> Dict:
        """Simulate a single trade from entry to exit"""
        
        entry_price = entry_row['mid_price']
        entry_time = entry_row['timestamp']
        market_ticker = entry_row['ticker']
        
        # Determine entry side and target
        if action == 'BUY_YES':
            entry_side = 'YES'
            # Buy at ask
            entry_price = entry_row['yes_ask']
        else:  # BUY_NO
            entry_side = 'NO'
            # Buy NO = sell YES, so enter at bid
            entry_price = 1.0 - entry_row['yes_bid']
        
        # Track trade
        trade = {
            'entry_time': entry_time,
            'entry_price': entry_price,
            'entry_side': entry_side,
            'ticker': market_ticker,
            'exit_time': None,
            'exit_price': None,
            'exit_reason': None,
            'pnl': 0,
            'roi': 0,
            'win': False
        }
        
        # Simulate holding period
        for idx, row in future_data.iterrows():
            time_elapsed = (row['timestamp'] - entry_time).total_seconds()
            
            # Check exit conditions
            
            # 1. Market close approaching (1 minute before)
            if row.get('time_to_close', 0) < 60:
                if entry_side == 'YES':
                    exit_price = row['yes_bid']  # Sell at bid
                else:
                    exit_price = 1.0 - row['yes_ask']  # Buy back at ask
                
                trade['exit_time'] = row['timestamp']
                trade['exit_price'] = exit_price
                trade['exit_reason'] = 'Market close approaching'
                break
            
            # 2. Profit target hit (+10%)
            current_price = row['yes_bid'] if entry_side == 'YES' else (1.0 - row['yes_ask'])
            unrealized_roi = (current_price - entry_price) / entry_price
            
            if unrealized_roi >= self.config['profit_target']:
                trade['exit_time'] = row['timestamp']
                trade['exit_price'] = current_price
                trade['exit_reason'] = 'Profit target hit'
                break
            
            # 3. Stop loss hit (-15%)
            if unrealized_roi <= -self.config['stop_loss']:
                trade['exit_time'] = row['timestamp']
                trade['exit_price'] = current_price
                trade['exit_reason'] = 'Stop loss hit'
                break
            
            # 4. Momentum reversal
            if not pd.isna(row['rsi']):
                if entry_side == 'YES' and row['rsi'] < 45 and row['roc_fast'] < -0.1:
                    trade['exit_time'] = row['timestamp']
                    trade['exit_price'] = current_price
                    trade['exit_reason'] = 'Momentum reversal (bearish)'
                    break
                elif entry_side == 'NO' and row['rsi'] > 55 and row['roc_fast'] > 0.1:
                    trade['exit_time'] = row['timestamp']
                    trade['exit_price'] = current_price
                    trade['exit_reason'] = 'Momentum reversal (bullish)'
                    break
        
        # Calculate PnL
        if trade['exit_price'] is not None:
            trade['pnl'] = (trade['exit_price'] - trade['entry_price']) * self.config['position_size']
            trade['roi'] = (trade['exit_price'] - trade['entry_price']) / trade['entry_price']
            trade['win'] = trade['pnl'] > 0
        
        return trade


class BacktestEngine:
    """Main backtest engine"""
    
    def __init__(self, data_path: str, config: Dict):
        self.data_path = Path(data_path)
        self.config = config
        self.strategy = MomentumStrategy(config)
        self.indicators = MomentumIndicators()
        
    def load_data(self) -> pd.DataFrame:
        """Load and preprocess JSONL data"""
        print(f"📂 Loading data from {self.data_path}")
        
        records = []
        with open(self.data_path, 'r') as f:
            for line in f:
                records.append(json.loads(line))
        
        df = pd.DataFrame(records)
        
        # Parse timestamp
        df['timestamp'] = pd.to_datetime(df['t'])
        
        # Extract Kalshi fields
        df['ticker'] = df['kalshi'].apply(lambda x: x['ticker'])
        df['yes_bid'] = df['kalshi'].apply(lambda x: x['yes_bid'])
        df['yes_ask'] = df['kalshi'].apply(lambda x: x['yes_ask'])
        df['volume'] = df['kalshi'].apply(lambda x: x['volume'])
        
        # Calculate derived fields
        df['spread'] = df['yes_ask'] - df['yes_bid']
        df['mid_price'] = (df['yes_bid'] + df['yes_ask']) / 2
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"✅ Loaded {len(df)} data points")
        print(f"   Time range: {df['timestamp'].min()} → {df['timestamp'].max()}")
        print(f"   Duration: {(df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600:.1f} hours")
        
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        print("\n📊 Calculating indicators...")
        
        # RSI
        df['rsi'] = self.indicators.calculate_rsi(
            df['brti'], 
            period=self.config['lookback_rsi']
        )
        
        # MACD
        macd, signal, hist = self.indicators.calculate_macd(
            df['brti'],
            fast=self.config['lookback_macd_fast'],
            slow=self.config['lookback_macd_slow'],
            signal=self.config['lookback_macd_signal']
        )
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_histogram'] = hist
        
        # ROC
        df['roc_fast'] = self.indicators.calculate_roc(
            df['brti'], 
            period=self.config['roc_fast_period']
        )
        df['roc_medium'] = self.indicators.calculate_roc(
            df['brti'], 
            period=self.config['roc_medium_period']
        )
        
        # Calculate time to market close (estimate from ticker)
        # Ticker format: KXBTC15M-26FEB020300-00 → closes at 03:00
        def extract_close_time(ticker):
            try:
                # Extract time part: "020300" → 02:03:00
                parts = ticker.split('-')
                if len(parts) >= 2:
                    time_str = parts[1]  # "26FEB020300"
                    time_part = time_str[-6:]  # "020300"
                    hour = int(time_part[:2])
                    minute = int(time_part[2:4])
                    
                    # Parse date
                    date_part = time_str[:-6]  # "26FEB"
                    day = int(date_part[:2])
                    month_str = date_part[2:]
                    
                    month_map = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 
                                'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
                                'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12}
                    month = month_map.get(month_str, 1)
                    
                    close_time = datetime(2026, month, day, hour, minute)
                    return close_time
            except:
                pass
            return None
        
        df['market_close_time'] = df['ticker'].apply(extract_close_time)
        df['time_to_close'] = (df['market_close_time'] - df['timestamp']).dt.total_seconds()
        
        print(f"✅ Indicators calculated")
        print(f"   RSI range: {df['rsi'].min():.1f} - {df['rsi'].max():.1f}")
        print(f"   ROC fast range: {df['roc_fast'].min():.2f}% - {df['roc_fast'].max():.2f}%")
        
        return df
    
    def run_backtest(self, df: pd.DataFrame) -> List[Dict]:
        """Execute backtest: generate signals and simulate trades"""
        print("\n🚀 Running backtest...")
        
        trades = []
        in_position = False
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            
            # Skip if already in position
            if in_position:
                continue
            
            # Generate signal
            signal = self.strategy.generate_signal(row)
            
            if signal['action'] is not None:
                print(f"\n📡 Signal at {row['timestamp']}: {signal['action']} "
                      f"(confidence={signal['confidence']}, reason={', '.join(signal['reason'])})")
                
                # Get future data for this market (same ticker)
                same_market = df[
                    (df['ticker'] == row['ticker']) & 
                    (df['timestamp'] > row['timestamp'])
                ]
                
                if len(same_market) > 5:  # Need at least 5 future ticks
                    # Simulate trade
                    trade = self.strategy.simulate_trade(row, same_market, signal['action'])
                    trade['signal_confidence'] = signal['confidence']
                    trade['signal_reason'] = ', '.join(signal['reason'])
                    
                    trades.append(trade)
                    
                    print(f"   ├─ Entry: ${trade['entry_price']:.3f} ({trade['entry_side']})")
                    if trade['exit_price']:
                        print(f"   ├─ Exit: ${trade['exit_price']:.3f} ({trade['exit_reason']})")
                        print(f"   └─ PnL: ${trade['pnl']:.2f} ({trade['roi']*100:.1f}%) "
                              f"{'✅ WIN' if trade['win'] else '❌ LOSS'}")
                    
                    in_position = True
                    
                    # Wait for market to close before next trade
                    if trade['exit_time']:
                        # Find next market
                        next_market_idx = df[
                            (df['timestamp'] > trade['exit_time']) & 
                            (df['ticker'] != row['ticker'])
                        ].index
                        if len(next_market_idx) > 0:
                            in_position = False
        
        print(f"\n✅ Backtest complete: {len(trades)} trades executed")
        return trades
    
    def analyze_results(self, trades: List[Dict]) -> Dict:
        """Analyze backtest results"""
        if not trades:
            print("\n⚠️ No trades executed")
            return {}
        
        trades_df = pd.DataFrame(trades)
        
        # Filter out trades without exits (incomplete)
        complete_trades = trades_df[trades_df['exit_price'].notna()]
        
        if len(complete_trades) == 0:
            print("\n⚠️ No complete trades")
            return {}
        
        # Calculate metrics
        total_trades = len(complete_trades)
        winning_trades = complete_trades['win'].sum()
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = complete_trades['pnl'].sum()
        avg_pnl = complete_trades['pnl'].mean()
        avg_roi = complete_trades['roi'].mean()
        
        avg_win = complete_trades[complete_trades['win']]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = complete_trades[~complete_trades['win']]['pnl'].mean() if losing_trades > 0 else 0
        
        # Calculate Sharpe ratio (annualized)
        if complete_trades['roi'].std() > 0:
            sharpe = (avg_roi / complete_trades['roi'].std()) * np.sqrt(252)  # Assume daily trading
        else:
            sharpe = 0
        
        # Calculate max drawdown
        cumulative_pnl = complete_trades['pnl'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        max_drawdown = drawdown.min()
        max_drawdown_pct = (max_drawdown / self.config['position_size']) if self.config['position_size'] > 0 else 0
        
        results = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'avg_roi': avg_roi,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'trades': complete_trades
        }
        
        return results
    
    def print_report(self, results: Dict):
        """Print formatted backtest report"""
        if not results:
            return
        
        print("\n" + "="*60)
        print("📊 MOMENTUM STRATEGY BACKTEST RESULTS")
        print("="*60)
        
        print(f"\n🎯 Trade Summary:")
        print(f"   Total Trades: {results['total_trades']}")
        print(f"   Winners: {results['winning_trades']} ({results['win_rate']*100:.1f}%)")
        print(f"   Losers: {results['losing_trades']} ({(1-results['win_rate'])*100:.1f}%)")
        
        print(f"\n💰 P&L:")
        print(f"   Total PnL: ${results['total_pnl']:.2f}")
        print(f"   Avg PnL/Trade: ${results['avg_pnl']:.2f}")
        print(f"   Avg ROI: {results['avg_roi']*100:.2f}%")
        print(f"   Avg Win: ${results['avg_win']:.2f}")
        print(f"   Avg Loss: ${results['avg_loss']:.2f}")
        
        print(f"\n📈 Risk Metrics:")
        print(f"   Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"   Max Drawdown: ${results['max_drawdown']:.2f} ({results['max_drawdown_pct']*100:.1f}%)")
        
        print(f"\n✅ Success Criteria Check:")
        print(f"   Win Rate >55%: {'✅' if results['win_rate'] > 0.55 else '❌'} ({results['win_rate']*100:.1f}%)")
        print(f"   Avg ROI >5%: {'✅' if results['avg_roi'] > 0.05 else '❌'} ({results['avg_roi']*100:.1f}%)")
        print(f"   Sharpe >1.0: {'✅' if results['sharpe_ratio'] > 1.0 else '❌'} ({results['sharpe_ratio']:.2f})")
        print(f"   Max DD <20%: {'✅' if results['max_drawdown_pct'] > -0.20 else '❌'} ({results['max_drawdown_pct']*100:.1f}%)")
        
        # Calculate daily trade frequency (estimated)
        trades_df = results['trades']
        duration_hours = (trades_df['exit_time'].max() - trades_df['entry_time'].min()).total_seconds() / 3600
        trades_per_day = (results['total_trades'] / duration_hours) * 24 if duration_hours > 0 else 0
        print(f"   Trades >5/day: {'✅' if trades_per_day > 5 else '❌'} ({trades_per_day:.1f}/day)")
        
        print("\n" + "="*60)
    
    def plot_results(self, df: pd.DataFrame, trades: List[Dict], output_dir: Path):
        """Generate visualization charts"""
        if not trades:
            return
        
        trades_df = pd.DataFrame(trades)
        complete_trades = trades_df[trades_df['exit_price'].notna()]
        
        if len(complete_trades) == 0:
            return
        
        print("\n📊 Generating charts...")
        
        # Create output directory
        output_dir.mkdir(exist_ok=True)
        
        # Set style
        sns.set_style("darkgrid")
        
        # 1. Price and Indicators
        fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
        
        # BTC Price
        axes[0].plot(df['timestamp'], df['brti'], label='BTC Price', color='blue', linewidth=1)
        axes[0].set_ylabel('BTC Price ($)')
        axes[0].set_title('BTC Price Movement')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # RSI
        axes[1].plot(df['timestamp'], df['rsi'], label='RSI', color='purple', linewidth=1)
        axes[1].axhline(y=70, color='r', linestyle='--', alpha=0.5, label='Overbought')
        axes[1].axhline(y=30, color='g', linestyle='--', alpha=0.5, label='Oversold')
        axes[1].set_ylabel('RSI')
        axes[1].set_ylim(0, 100)
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # MACD
        axes[2].plot(df['timestamp'], df['macd'], label='MACD', color='blue', linewidth=1)
        axes[2].plot(df['timestamp'], df['macd_signal'], label='Signal', color='red', linewidth=1)
        axes[2].bar(df['timestamp'], df['macd_histogram'], label='Histogram', color='gray', alpha=0.3)
        axes[2].set_ylabel('MACD')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        # ROC
        axes[3].plot(df['timestamp'], df['roc_fast'], label='ROC Fast (2min)', color='orange', linewidth=1)
        axes[3].plot(df['timestamp'], df['roc_medium'], label='ROC Medium (5min)', color='green', linewidth=1)
        axes[3].axhline(y=0, color='black', linestyle='-', alpha=0.5)
        axes[3].set_ylabel('ROC (%)')
        axes[3].set_xlabel('Time')
        axes[3].legend()
        axes[3].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'indicators.png', dpi=150)
        print(f"   ✅ Saved: indicators.png")
        plt.close()
        
        # 2. Cumulative PnL
        fig, ax = plt.subplots(figsize=(12, 6))
        cumulative_pnl = complete_trades['pnl'].cumsum()
        ax.plot(range(len(cumulative_pnl)), cumulative_pnl, marker='o', linewidth=2, markersize=4)
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax.set_xlabel('Trade Number')
        ax.set_ylabel('Cumulative PnL ($)')
        ax.set_title('Cumulative P&L Over Time')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'cumulative_pnl.png', dpi=150)
        print(f"   ✅ Saved: cumulative_pnl.png")
        plt.close()
        
        # 3. Win/Loss Distribution
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # PnL histogram
        axes[0].hist(complete_trades['pnl'], bins=20, edgecolor='black', alpha=0.7)
        axes[0].axvline(x=0, color='red', linestyle='--', linewidth=2)
        axes[0].set_xlabel('PnL ($)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('PnL Distribution')
        axes[0].grid(True, alpha=0.3)
        
        # Win/Loss pie chart
        win_counts = [complete_trades['win'].sum(), (~complete_trades['win']).sum()]
        axes[1].pie(win_counts, labels=['Wins', 'Losses'], autopct='%1.1f%%', 
                   colors=['green', 'red'], startangle=90)
        axes[1].set_title('Win Rate')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'win_loss_distribution.png', dpi=150)
        print(f"   ✅ Saved: win_loss_distribution.png")
        plt.close()


def main():
    """Main execution"""
    print("🚀 Momentum Strategy Backtest\n")
    
    # Paths
    data_path = Path(__file__).parent.parent / "data" / "collection_20260202_024420.jsonl"
    output_dir = Path(__file__).parent.parent / "backtest_results"
    output_dir.mkdir(exist_ok=True)
    
    # Initialize backtest
    engine = BacktestEngine(str(data_path), CONFIG)
    
    # Load data
    df = engine.load_data()
    
    # Calculate indicators
    df = engine.calculate_indicators(df)
    
    # Run backtest
    trades = engine.run_backtest(df)
    
    # Analyze results
    results = engine.analyze_results(trades)
    
    # Print report
    engine.print_report(results)
    
    # Generate charts
    if results:
        engine.plot_results(df, trades, output_dir)
    
    # Save results to JSON
    if results:
        results_to_save = {
            'config': CONFIG,
            'summary': {
                'total_trades': results['total_trades'],
                'win_rate': results['win_rate'],
                'total_pnl': results['total_pnl'],
                'avg_roi': results['avg_roi'],
                'sharpe_ratio': results['sharpe_ratio'],
                'max_drawdown_pct': results['max_drawdown_pct']
            },
            'trades': [
                {
                    'entry_time': str(t['entry_time']),
                    'exit_time': str(t['exit_time']),
                    'entry_price': float(t['entry_price']),
                    'exit_price': float(t['exit_price']),
                    'pnl': float(t['pnl']),
                    'roi': float(t['roi']),
                    'win': bool(t['win']),
                    'exit_reason': t['exit_reason']
                }
                for t in trades if t['exit_price'] is not None
            ]
        }
        
        output_file = output_dir / 'backtest_results.json'
        with open(output_file, 'w') as f:
            json.dump(results_to_save, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")
    
    print("\n✅ Backtest complete!")


if __name__ == "__main__":
    main()
