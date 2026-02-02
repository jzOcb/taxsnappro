#!/usr/bin/env python3
"""
Quick analysis of existing delay measurement data
"""

import json
import sys
from statistics import mean, stdev

def analyze_delay_data(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    
    measurements = data['measurements']
    
    print(f"\n{'='*70}")
    print(f"QUICK ANALYSIS: {filename}")
    print(f"{'='*70}\n")
    
    # Extract prices
    btc_prices = [m['binance']['price'] for m in measurements]
    kalshi_yes_bids = [m['kalshi']['yes_bid'] for m in measurements]
    kalshi_yes_asks = [m['kalshi']['yes_ask'] for m in measurements]
    
    print(f"📊 SUMMARY")
    print(f"Total measurements: {len(measurements)}")
    print(f"Duration: {data['summary']['duration_seconds']}s")
    print(f"Interval: {data['summary']['interval_seconds']}s")
    
    print(f"\n💰 BTC PRICE MOVEMENT")
    print(f"Start: ${btc_prices[0]:,.2f}")
    print(f"End: ${btc_prices[-1]:,.2f}")
    print(f"Change: ${btc_prices[-1] - btc_prices[0]:+,.2f} ({((btc_prices[-1]/btc_prices[0])-1)*100:+.3f}%)")
    print(f"Min: ${min(btc_prices):,.2f}")
    print(f"Max: ${max(btc_prices):,.2f}")
    print(f"Range: ${max(btc_prices) - min(btc_prices):,.2f}")
    
    print(f"\n📈 KALSHI YES MARKET")
    print(f"Bid range: ${min(kalshi_yes_bids):.2f} - ${max(kalshi_yes_bids):.2f}")
    print(f"Ask range: ${min(kalshi_yes_asks):.2f} - ${max(kalshi_yes_asks):.2f}")
    print(f"Spread: ${mean(kalshi_yes_asks) - mean(kalshi_yes_bids):.3f} average")
    
    # Detect when BTC moved but Kalshi didn't
    btc_changes = []
    kalshi_changes = []
    
    for i in range(1, len(measurements)):
        btc_chg = ((btc_prices[i] - btc_prices[i-1]) / btc_prices[i-1]) * 100
        kalshi_chg = ((kalshi_yes_bids[i] - kalshi_yes_bids[i-1]) / kalshi_yes_bids[i-1] * 100) if kalshi_yes_bids[i-1] > 0 else 0
        
        btc_changes.append(btc_chg)
        kalshi_changes.append(kalshi_chg)
    
    # Find potential arbitrage windows
    windows = []
    for i, (btc_chg, kalshi_chg) in enumerate(zip(btc_changes, kalshi_changes)):
        if abs(btc_chg) > 0.05 and abs(kalshi_chg) < 0.05:  # BTC moved >0.05%, Kalshi didn't
            windows.append({
                'index': i+1,
                'btc_change': btc_chg,
                'kalshi_change': kalshi_chg,
                'btc_price': btc_prices[i+1],
                'kalshi_bid': kalshi_yes_bids[i+1],
            })
    
    print(f"\n⚡ POTENTIAL ARBITRAGE WINDOWS")
    print(f"Total windows detected: {len(windows)}")
    
    if windows:
        print(f"\nTop 5 opportunities:")
        for i, w in enumerate(windows[:5], 1):
            print(f"  {i}. [{w['index']:2d}] BTC: {w['btc_change']:+.3f}%, Kalshi: {w['kalshi_change']:+.3f}% | "
                  f"BTC=${w['btc_price']:,.2f}, YES=${w['kalshi_bid']:.2f}")
    
    print(f"\n📊 STATISTICS")
    if btc_changes:
        print(f"BTC avg change: {mean([abs(c) for c in btc_changes]):.4f}%")
        print(f"BTC volatility: {stdev(btc_changes):.4f}%")
    if kalshi_changes:
        print(f"Kalshi avg change: {mean([abs(c) for c in kalshi_changes]):.4f}%")
    
    print(f"\n🎯 INSIGHTS")
    btc_moved_significantly = sum(1 for c in btc_changes if abs(c) > 0.05)
    print(f"Times BTC moved >0.05%: {btc_moved_significantly}/{len(btc_changes)} ({btc_moved_significantly/len(btc_changes)*100:.1f}%)")
    print(f"Arbitrage windows: {len(windows)}/{len(btc_changes)} ({len(windows)/len(btc_changes)*100:.1f}%)")
    
    if len(windows) > 0:
        print(f"\n✅ VERDICT: Arbitrage windows exist! ({len(windows)} detected in {data['summary']['duration_seconds']}s)")
    else:
        print(f"\n⚠️  VERDICT: No clear windows in this sample (need more data)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 quick_analysis.py <data_file.json>")
        sys.exit(1)
    
    analyze_delay_data(sys.argv[1])
