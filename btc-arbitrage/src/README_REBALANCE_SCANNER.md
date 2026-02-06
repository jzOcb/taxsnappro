# Kalshi Market Rebalancing Arbitrage Scanner

## Overview

The Rebalancing Arbitrage Scanner identifies risk-free profit opportunities in Kalshi BTC markets where YES + NO prices don't sum to exactly $1.00.

## How It Works

### Arbitrage Types Detected

1. **Buy Both Strategy** (YES + NO < $1.00)
   - Buy YES at ask price + Buy NO at ask price
   - Total cost < $1.00, guaranteed $1.00 payout at settlement
   - **Risk-free profit = $1.00 - total_cost**

2. **Sell Both Strategy** (YES + NO > $1.00)  
   - Sell YES at bid price + Sell NO at bid price
   - Total revenue > $1.00, must pay $1.00 at settlement
   - **Risk-free profit = total_revenue - $1.00**

### Market Series Scanned

- **KXBTC15M**: 15-minute BTC price resolution windows
- **KXBTC1H**: 1-hour BTC price resolution windows

## Usage

### Basic Scan
```bash
python3 src/rebalance_scanner.py
```

### Integration Example
```python
from rebalance_scanner import scan_all_btc_markets

opportunities, all_results = scan_all_btc_markets()
for opp in opportunities:
    print(f"Found {opp['opportunity_type']} opportunity in {opp['ticker']}")
    print(f"Profit: ${opp['max_profit']:.3f} ({opp['profit_margin']:.2f}%)")
```

## Output Files

Results are saved to: `/home/clawdbot/clawd/btc-arbitrage/data/rebalance_scan_YYYYMMDD_HHMMSS.json`

### JSON Structure
```json
{
  "scan_time": "2026-02-04T14:27:01.201824+00:00",
  "opportunities_found": 0,
  "total_markets": 1,
  "opportunities": [
    {
      "ticker": "KXBTC15M-26FEB040930-30", 
      "opportunity_type": "buy_both",
      "max_profit": 0.015,
      "profit_margin": 1.52,
      "details": "Buy YES@$0.420 + NO@$0.565 = $0.985 < $1.00. Profit: $0.015"
    }
  ]
}
```

## Current Scan Results (2026-02-04 14:27 UTC)

**✅ Scanner Status: OPERATIONAL**

**📊 Live Scan Results:**
- **Markets Scanned:** 1 (KXBTC15M-26FEB040930-30)
- **Arbitrage Opportunities:** 0
- **Market Efficiency:** KXBTC15M is efficiently priced (YES+NO = $1.030, only $0.030 from perfect)

**🎯 No live arbitrage opportunities detected** - Kalshi BTC markets are currently well-arbitraged and efficient.

## Configuration

### Key Parameters
- `MIN_ARBITRAGE_PROFIT = 0.005` (minimum $0.005 profit to flag)
- `KALSHI_FEE_RATE = 0.00` (needs verification of actual fee structure)
- `API_BASE = "https://api.elections.kalshi.com/trade-api/v2"`

### Fee Considerations
Current implementation assumes no fees for simplicity. In practice, should verify:
- Kalshi transaction fees
- Market maker vs. taker fees  
- Withdrawal fees
- Minimum order sizes and slippage impact

## Testing

Run the test suite to verify scanner logic:
```bash
python3 src/test_rebalance_scanner.py
```

Test cases verify detection of:
- ✅ Buy both arbitrage (YES+NO < $1.00)
- ✅ Sell both arbitrage (YES+NO > $1.00)
- ✅ Efficient markets (YES+NO ≈ $1.00)

## Implementation Notes

### API Access
- Uses public Kalshi API endpoints (no authentication required for market data)
- Fallback implementation when kalshi module not available
- Rate limiting: Conservative request spacing to avoid API limits

### Market Data Sources
- Live market prices from `/markets` endpoint
- Orderbook data from `/markets/{ticker}/orderbook` endpoint  
- Only scans active ("open") markets

### Limitations
- Does not account for slippage on large orders
- Assumes perfect order execution at displayed prices
- Does not consider market depth or liquidity constraints
- Fee structure needs verification against actual Kalshi fees

## Future Enhancements

1. **Real-time Monitoring**: WebSocket integration for live opportunity detection
2. **Order Execution**: Integration with authenticated Kalshi trading API
3. **Position Sizing**: Dynamic sizing based on market depth and account balance
4. **Risk Management**: Stop-loss and position limits
5. **Fee Integration**: Accurate fee modeling based on actual Kalshi fee structure
6. **Alerting**: Telegram/Discord notifications when opportunities detected

## Exit Codes

- `0`: Scan successful with arbitrage opportunities found
- `1`: Scan successful but no opportunities found  
- `130`: User interrupt (Ctrl+C)
- Other: Fatal errors