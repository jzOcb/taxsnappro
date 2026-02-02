#!/usr/bin/env python3
"""
Gabagool Arbitrage Detector
检测Kalshi BTC市场中YES+NO<$1的无风险套利机会
"""
import json
import sys
from datetime import datetime
from collections import defaultdict

def load_data(filepath):
    """Load JSONL data"""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def find_gabagool_opportunities(data):
    """
    查找YES ask + NO ask < $1.00的机会
    
    Returns: list of opportunities with details
    """
    opportunities = []
    
    for entry in data:
        timestamp = entry.get('timestamp')
        markets = entry.get('markets', {})
        
        for market_id, market_data in markets.items():
            ticker = market_data.get('ticker', '')
            yes_ask = market_data.get('yes_ask')
            no_ask = market_data.get('no_ask')
            yes_bid = market_data.get('yes_bid')
            no_bid = market_data.get('no_bid')
            
            # Skip if missing data
            if yes_ask is None or no_ask is None:
                continue
            
            # Gabagool condition: YES ask + NO ask < 1.00
            total_cost = yes_ask + no_ask
            
            if total_cost < 1.00:
                profit = 1.00 - total_cost
                profit_pct = profit / total_cost * 100
                
                opportunities.append({
                    'timestamp': timestamp,
                    'market_id': market_id,
                    'ticker': ticker,
                    'yes_ask': yes_ask,
                    'no_ask': no_ask,
                    'yes_bid': yes_bid,
                    'no_bid': no_bid,
                    'total_cost': total_cost,
                    'profit': profit,
                    'profit_pct': profit_pct
                })
    
    return opportunities

def analyze_opportunities(opportunities):
    """Analyze and summarize opportunities"""
    if not opportunities:
        return {
            'total_count': 0,
            'total_profit': 0,
            'avg_profit': 0,
            'max_profit': 0,
            'min_profit': 0,
            'avg_profit_pct': 0,
            'conclusion': 'NO GABAGOOL OPPORTUNITIES FOUND'
        }
    
    total_count = len(opportunities)
    profits = [opp['profit'] for opp in opportunities]
    profit_pcts = [opp['profit_pct'] for opp in opportunities]
    
    # Group by market to find persistence
    market_counts = defaultdict(int)
    for opp in opportunities:
        market_counts[opp['market_id']] += 1
    
    return {
        'total_count': total_count,
        'total_profit': sum(profits),
        'avg_profit': sum(profits) / total_count,
        'max_profit': max(profits),
        'min_profit': min(profits),
        'avg_profit_pct': sum(profit_pcts) / total_count,
        'max_profit_pct': max(profit_pcts),
        'unique_markets': len(market_counts),
        'most_frequent_market': max(market_counts.items(), key=lambda x: x[1]) if market_counts else None,
        'conclusion': 'GABAGOOL VIABLE' if total_count > 10 else 'RARE BUT EXISTS'
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python gabagool_detector.py <data_file.jsonl>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    print(f"Loading data from {filepath}...")
    data = load_data(filepath)
    print(f"Loaded {len(data)} data points")
    
    print("\nSearching for Gabagool opportunities (YES ask + NO ask < $1.00)...")
    opportunities = find_gabagool_opportunities(data)
    
    print(f"\n{'='*80}")
    print(f"GABAGOOL DETECTION RESULTS")
    print(f"{'='*80}\n")
    
    if not opportunities:
        print("❌ NO GABAGOOL OPPORTUNITIES FOUND")
        print("\nKalshi BTC 15分钟市场定价高效，YES+NO始终≈$1.00")
        print("Gabagool策略在Kalshi不可行。")
        return
    
    # Analysis
    analysis = analyze_opportunities(opportunities)
    
    print(f"✅ Found {analysis['total_count']} Gabagool opportunities")
    print(f"\n📊 Statistics:")
    print(f"  Total profit potential: ${analysis['total_profit']:.4f}")
    print(f"  Average profit: ${analysis['avg_profit']:.4f} ({analysis['avg_profit_pct']:.2f}%)")
    print(f"  Max profit: ${analysis['max_profit']:.4f} ({analysis['max_profit_pct']:.2f}%)")
    print(f"  Min profit: ${analysis['min_profit']:.4f}")
    print(f"  Unique markets: {analysis['unique_markets']}")
    
    if analysis.get('most_frequent_market'):
        market_id, count = analysis['most_frequent_market']
        print(f"  Most frequent market: {market_id} ({count} times)")
    
    print(f"\n🎯 Conclusion: {analysis['conclusion']}")
    
    # Show top 10 opportunities
    print(f"\n📋 Top 10 Opportunities (by profit %):")
    print(f"{'Timestamp':<20} {'Ticker':<30} {'YES ask':<10} {'NO ask':<10} {'Total':<10} {'Profit':<10} {'Profit %':<10}")
    print("-" * 110)
    
    sorted_opps = sorted(opportunities, key=lambda x: x['profit_pct'], reverse=True)[:10]
    for opp in sorted_opps:
        print(f"{opp['timestamp']:<20} {opp['ticker']:<30} ${opp['yes_ask']:<9.2f} ${opp['no_ask']:<9.2f} ${opp['total_cost']:<9.2f} ${opp['profit']:<9.4f} {opp['profit_pct']:<9.2f}%")
    
    # Save detailed results
    output_file = filepath.replace('.jsonl', '_gabagool_results.json')
    with open(output_file, 'w') as f:
        json.dump({
            'analysis': analysis,
            'opportunities': opportunities
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")

if __name__ == "__main__":
    main()
