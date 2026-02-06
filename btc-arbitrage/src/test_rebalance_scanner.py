#!/usr/bin/env python3
"""
Test script for the Rebalancing Arbitrage Scanner
Demonstrates the scanner logic with mock arbitrage opportunities
"""

import sys
sys.path.insert(0, '.')
from rebalance_scanner import calculate_rebalance_opportunity

def test_arbitrage_detection():
    """Test the scanner's ability to detect arbitrage opportunities"""
    print("🧪 TESTING REBALANCE SCANNER LOGIC")
    print("=" * 50)
    
    # Test Case 1: Buy Both Arbitrage (YES + NO < $1.00)
    print("\n📉 Test Case 1: Buy Both Arbitrage")
    mock_market_1 = {
        "ticker": "TEST-BUYARB",
        "series_ticker": "TESTBTC",
        "yes_bid": 40,  # cents
        "yes_ask": 42,  # cents
        "no_bid": 55,   # cents
        "no_ask": 57,   # cents - Total: 42¢ + 57¢ = 99¢ < $1.00
        "volume": 1000,
        "close_time": "2026-02-04T15:00:00Z"
    }
    
    result_1 = calculate_rebalance_opportunity(mock_market_1)
    print(f"   Result: {result_1['opportunity_type']}")
    print(f"   Details: {result_1['details']}")
    print(f"   Max Profit: ${result_1['max_profit']:.3f}")
    print(f"   Profit Margin: {result_1['profit_margin']:.2f}%")
    
    # Test Case 2: Sell Both Arbitrage (YES + NO > $1.00)  
    print("\n📈 Test Case 2: Sell Both Arbitrage")
    mock_market_2 = {
        "ticker": "TEST-SELLARB", 
        "series_ticker": "TESTBTC",
        "yes_bid": 48,  # cents
        "yes_ask": 50,  # cents
        "no_bid": 53,   # cents  
        "no_ask": 55,   # cents - Total bids: 48¢ + 53¢ = 101¢ > $1.00
        "volume": 2000,
        "close_time": "2026-02-04T15:00:00Z"
    }
    
    result_2 = calculate_rebalance_opportunity(mock_market_2)
    print(f"   Result: {result_2['opportunity_type']}")
    print(f"   Details: {result_2['details']}")
    print(f"   Max Profit: ${result_2['max_profit']:.3f}")
    print(f"   Profit Margin: {result_2['profit_margin']:.2f}%")
    
    # Test Case 3: No Arbitrage (Efficient Market)
    print("\n⚖️ Test Case 3: Efficient Market (No Arbitrage)")
    mock_market_3 = {
        "ticker": "TEST-EFFICIENT",
        "series_ticker": "TESTBTC", 
        "yes_bid": 49,  # cents
        "yes_ask": 50,  # cents
        "no_bid": 49,   # cents
        "no_ask": 50,   # cents - Total: 50¢ + 50¢ = $1.00 (perfect)
        "volume": 5000,
        "close_time": "2026-02-04T15:00:00Z"
    }
    
    result_3 = calculate_rebalance_opportunity(mock_market_3)
    print(f"   Result: {result_3['opportunity_type']}")
    print(f"   Details: {result_3['details']}")
    
    # Summary
    print(f"\n✅ TEST SUMMARY:")
    print(f"   - Buy arbitrage detected: {result_1['opportunity_type'] == 'buy_both'}")
    print(f"   - Sell arbitrage detected: {result_2['opportunity_type'] == 'sell_both'}")
    print(f"   - Efficient market recognized: {result_3['opportunity_type'] == 'none'}")

if __name__ == "__main__":
    test_arbitrage_detection()