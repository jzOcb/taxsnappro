#!/usr/bin/env python3
"""
A/B Test Tracker — Compare performance across all bot variants.

Reads state files from V10, V11, V12, V13, V14, and Maker V1,
then displays a side-by-side comparison table.

Usage:
    python3 src/ab_test_tracker.py

IRON RULES compliance:
  - Rule #3: Only change one variable at a time (A/B test). This tool helps verify.
  - Rule #6: Record everything. This tool reads the records.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = '/home/clawdbot/clawd/btc-arbitrage'
DATA_DIR = os.path.join(BASE_DIR, 'data')


def load_json(path):
    """Safely load a JSON file, return None on failure"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def extract_taker_metrics(state, bot_name):
    """Extract metrics from taker bot (V10-V14) state files"""
    if not state:
        return None
    
    trader = state.get('trader', {})
    positions = trader.get('positions', [])
    
    # Count closed trades
    closed = [p for p in positions if not p.get('open', True)]
    total_trades = len(closed)
    
    if total_trades == 0:
        return {
            'bot': bot_name,
            'trades': 0,
            'win_pct': None,
            'net_pnl': trader.get('pnl', 0.0),
            'avg_win': None,
            'avg_loss': None,
            'best_strategy': '-',
            'ev_per_trade': None,
            'elapsed_sec': state.get('elapsed_sec', 0),
        }
    
    # Calculate wins/losses
    wins = [p for p in closed if p.get('pnl', 0) > 0]
    losses = [p for p in closed if p.get('pnl', 0) <= 0]
    
    win_pct = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    avg_win = (sum(p.get('pnl', 0) for p in wins) / len(wins)) if wins else None
    avg_loss = (sum(p.get('pnl', 0) for p in losses) / len(losses)) if losses else None
    
    net_pnl = trader.get('pnl', 0.0)
    ev_per_trade = net_pnl / total_trades if total_trades > 0 else None
    
    # Find best strategy
    strategy_pnl = {}
    for p in closed:
        strat = p.get('strategy', 'unknown')
        if strat not in strategy_pnl:
            strategy_pnl[strat] = {'pnl': 0, 'count': 0}
        strategy_pnl[strat]['pnl'] += p.get('pnl', 0)
        strategy_pnl[strat]['count'] += 1
    
    best_strategy = '-'
    if strategy_pnl:
        best = max(strategy_pnl.items(), key=lambda x: x[1]['pnl'])
        best_strategy = best[0]
    
    return {
        'bot': bot_name,
        'trades': total_trades,
        'win_pct': win_pct,
        'net_pnl': net_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'best_strategy': best_strategy,
        'ev_per_trade': ev_per_trade,
        'elapsed_sec': state.get('elapsed_sec', 0),
    }


def extract_maker_metrics(state):
    """Extract metrics from Maker V1 state file"""
    if not state:
        return None
    
    perf = state.get('performance', {})
    inv = state.get('inventory', {})
    
    total_fills = perf.get('total_fills', 0)
    spreads = perf.get('spreads_captured', 0)
    total_pnl = perf.get('total_pnl', 0.0)
    spread_pnl = perf.get('total_spread_pnl', 0.0)
    
    # For maker, "win" = spread capture, "loss" = unsettled inventory loss
    # Simplified: if we have fills, calculate averages
    if total_fills == 0:
        return {
            'bot': 'Maker',
            'trades': 0,
            'win_pct': None,
            'net_pnl': total_pnl,
            'avg_win': None,
            'avg_loss': None,
            'best_strategy': 'two_sided_mm',
            'ev_per_trade': None,
            'elapsed_sec': state.get('elapsed_sec', 0),
            'extra': {
                'spreads_captured': spreads,
                'spread_pnl': spread_pnl,
                'yes_fills': perf.get('yes_fills', 0),
                'no_fills': perf.get('no_fills', 0),
                'quote_cycles': perf.get('quote_cycles', 0),
                'inventory_yes': inv.get('yes', 0),
                'inventory_no': inv.get('no', 0),
            }
        }
    
    # Approximate win rate from spread captures vs total fill pairs
    fill_pairs = min(perf.get('yes_fills', 0), perf.get('no_fills', 0))
    win_pct = (spreads / fill_pairs * 100) if fill_pairs > 0 else None
    
    avg_spread = spread_pnl / spreads if spreads > 0 else None
    ev_per_trade = total_pnl / total_fills if total_fills > 0 else None
    
    return {
        'bot': 'Maker',
        'trades': total_fills,
        'win_pct': win_pct,
        'net_pnl': total_pnl,
        'avg_win': avg_spread,
        'avg_loss': None,
        'best_strategy': 'two_sided_mm',
        'ev_per_trade': ev_per_trade,
        'elapsed_sec': state.get('elapsed_sec', 0),
        'extra': {
            'spreads_captured': spreads,
            'spread_pnl': spread_pnl,
            'yes_fills': perf.get('yes_fills', 0),
            'no_fills': perf.get('no_fills', 0),
            'quote_cycles': perf.get('quote_cycles', 0),
            'inventory_yes': inv.get('yes', 0),
            'inventory_no': inv.get('no', 0),
        }
    }


def format_dollar(val):
    """Format a dollar value or return '-' if None"""
    if val is None:
        return '-'
    if val >= 0:
        return f"${val:.2f}"
    return f"-${abs(val):.2f}"


def format_pct(val):
    """Format a percentage or return '-' if None"""
    if val is None:
        return '-'
    return f"{val:.1f}"


def format_elapsed(sec):
    """Format elapsed seconds as human-readable"""
    if sec < 60:
        return f"{sec:.0f}s"
    if sec < 3600:
        return f"{sec/60:.0f}m"
    return f"{sec/3600:.1f}h"


def print_dashboard(metrics_list):
    """Print the A/B test dashboard table"""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    print(f"\n=== A/B Test Dashboard ({now}) ===\n")
    
    # Header
    header = f"{'Bot':<8} | {'Trades':>6} | {'Win%':>5} | {'Net P&L':>9} | {'Avg Win':>8} | {'Avg Loss':>9} | {'Best Strategy':<16} | {'EV/Trade':>9} | {'Uptime':>7}"
    print(header)
    print("-" * len(header))
    
    # Rows
    for m in metrics_list:
        if m is None:
            continue
        
        bot = m['bot']
        trades = str(m['trades'])
        win_pct = format_pct(m['win_pct'])
        net_pnl = format_dollar(m['net_pnl'])
        avg_win = format_dollar(m['avg_win'])
        avg_loss = format_dollar(m['avg_loss'])
        best_strat = m['best_strategy'][:16]
        ev = format_dollar(m['ev_per_trade'])
        uptime = format_elapsed(m['elapsed_sec'])
        
        print(f"{bot:<8} | {trades:>6} | {win_pct:>5} | {net_pnl:>9} | {avg_win:>8} | {avg_loss:>9} | {best_strat:<16} | {ev:>9} | {uptime:>7}")
    
    print()
    
    # Maker-specific extras
    for m in metrics_list:
        if m and m.get('extra'):
            ex = m['extra']
            print(f"  📊 Maker Details: spreads_captured={ex['spreads_captured']} | "
                  f"spread_pnl={format_dollar(ex['spread_pnl'])} | "
                  f"fills: YES={ex['yes_fills']} NO={ex['no_fills']} | "
                  f"quotes={ex['quote_cycles']} | "
                  f"inventory: YES={ex['inventory_yes']} NO={ex['inventory_no']}")
    
    print()


def main():
    """Load all bot states and display comparison"""
    
    # Define bot state files
    bots = [
        ('V10', os.path.join(DATA_DIR, 'rt_v10_state.json'), 'taker'),
        ('V11', os.path.join(DATA_DIR, 'rt_v11_state.json'), 'taker'),
        ('V12', os.path.join(DATA_DIR, 'rt_v12_state.json'), 'taker'),
        ('V13', os.path.join(DATA_DIR, 'rt_v13_state.json'), 'taker'),
        ('V14', os.path.join(DATA_DIR, 'rt_v14_state.json'), 'taker'),
        ('Maker', os.path.join(DATA_DIR, 'maker_v1_state.json'), 'maker'),
    ]
    
    metrics_list = []
    
    for bot_name, state_path, bot_type in bots:
        state = load_json(state_path)
        
        if state is None:
            # Bot has no state file — show as inactive
            metrics_list.append({
                'bot': bot_name,
                'trades': 0,
                'win_pct': None,
                'net_pnl': 0.0,
                'avg_win': None,
                'avg_loss': None,
                'best_strategy': '-',
                'ev_per_trade': None,
                'elapsed_sec': 0,
            })
            continue
        
        if bot_type == 'maker':
            m = extract_maker_metrics(state)
        else:
            m = extract_taker_metrics(state, bot_name)
        
        if m:
            metrics_list.append(m)
        else:
            metrics_list.append({
                'bot': bot_name,
                'trades': 0,
                'win_pct': None,
                'net_pnl': 0.0,
                'avg_win': None,
                'avg_loss': None,
                'best_strategy': '-',
                'ev_per_trade': None,
                'elapsed_sec': 0,
            })
    
    print_dashboard(metrics_list)
    
    # Summary
    active = [m for m in metrics_list if m and m['trades'] > 0]
    if active:
        best = max(active, key=lambda x: x['net_pnl'])
        worst = min(active, key=lambda x: x['net_pnl'])
        total_pnl = sum(m['net_pnl'] for m in active)
        total_trades = sum(m['trades'] for m in active)
        
        print(f"  📈 Summary: {len(active)} active bots | {total_trades} total trades | Net P&L: {format_dollar(total_pnl)}")
        print(f"  🏆 Best: {best['bot']} ({format_dollar(best['net_pnl'])})")
        print(f"  💀 Worst: {worst['bot']} ({format_dollar(worst['net_pnl'])})")
    else:
        print("  ⚠️ No active bots with trades found.")
    
    print()


if __name__ == '__main__':
    main()
