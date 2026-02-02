#!/usr/bin/env python3
"""
Flash Crash Parameter Sweep
测试不同参数组合找到最优配置
"""
import json
import sys
from flash_crash_backtest import FlashCrashStrategy, load_data, analyze_results

def run_backtest(data, drop_threshold, lookback_ticks, take_profit, stop_loss):
    """Run backtest with given parameters"""
    strategy = FlashCrashStrategy(
        drop_threshold=drop_threshold,
        lookback_ticks=lookback_ticks,
        take_profit=take_profit,
        stop_loss=stop_loss,
        trade_size=10.0
    )
    
    for data_point in data:
        strategy.on_data(data_point)
    
    strategy.finalize()
    return analyze_results(strategy.completed_trades)

def main():
    if len(sys.argv) < 2:
        print("Usage: python flash_crash_param_sweep.py <data_file.jsonl>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    print(f"Loading data from {filepath}...")
    data = load_data(filepath)
    print(f"Loaded {len(data)} data points\n")
    
    print("Running Parameter Sweep...")
    print("="*120)
    
    # Parameter ranges
    drop_thresholds = [0.10, 0.15, 0.20, 0.25, 0.30]
    lookback_options = [3, 5, 10]
    take_profit_options = [0.08, 0.10, 0.15]
    stop_loss_options = [0.05, 0.10]
    
    results_summary = []
    
    for drop in drop_thresholds:
        for lookback in lookback_options:
            for tp in take_profit_options:
                for sl in stop_loss_options:
                    results = run_backtest(data, drop, lookback, tp, sl)
                    
                    results_summary.append({
                        'params': {
                            'drop_threshold': drop,
                            'lookback_ticks': lookback,
                            'take_profit': tp,
                            'stop_loss': sl
                        },
                        'results': results
                    })
                    
                    # Print if any signals
                    if results['total_trades'] > 0:
                        print(f"Drop={drop*100:>4.0f}% Lookback={lookback:>2} TP={tp*100:>4.0f}% SL={sl*100:>4.0f}% | "
                              f"Signals={results['total_trades']:>3} WinRate={results['win_rate']:>5.1f}% "
                              f"PnL=${results['total_pnl']:>8.2f} | {results['conclusion']}")
    
    # Find best configuration
    viable_results = [r for r in results_summary if r['results']['total_trades'] > 0]
    
    if not viable_results:
        print("\n❌ NO VIABLE PARAMETERS FOUND")
        print("   Kalshi BTC市场极少出现flash crash（即使10%阈值）")
        print("   建议：")
        print("   1. 获取更多数据（目前只有13小时）")
        print("   2. 使用WebSocket获取更高频数据")
        print("   3. 考虑其他策略")
        return
    
    # Sort by PnL
    best_by_pnl = max(viable_results, key=lambda x: x['results']['total_pnl'])
    best_by_winrate = max(viable_results, key=lambda x: x['results']['win_rate'])
    
    print("\n" + "="*120)
    print("BEST CONFIGURATIONS")
    print("="*120)
    
    print("\n🏆 Best by Total PnL:")
    p = best_by_pnl['params']
    r = best_by_pnl['results']
    print(f"  Drop={p['drop_threshold']*100:.0f}% Lookback={p['lookback_ticks']} TP={p['take_profit']*100:.0f}% SL={p['stop_loss']*100:.0f}%")
    print(f"  Signals: {r['total_trades']}")
    print(f"  Win Rate: {r['win_rate']:.1f}%")
    print(f"  Total PnL: ${r['total_pnl']:.2f}")
    print(f"  Conclusion: {r['conclusion']}")
    
    print("\n🎯 Best by Win Rate:")
    p = best_by_winrate['params']
    r = best_by_winrate['results']
    print(f"  Drop={p['drop_threshold']*100:.0f}% Lookback={p['lookback_ticks']} TP={p['take_profit']*100:.0f}% SL={p['stop_loss']*100:.0f}%")
    print(f"  Signals: {r['total_trades']}")
    print(f"  Win Rate: {r['win_rate']:.1f}%")
    print(f"  Total PnL: ${r['total_pnl']:.2f}")
    print(f"  Conclusion: {r['conclusion']}")
    
    # Save all results
    output_file = filepath.replace('.jsonl', '_flash_crash_sweep.json')
    with open(output_file, 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    print(f"\n💾 Full sweep results saved to: {output_file}")

if __name__ == "__main__":
    main()
