# Kalshi Toolkit

Political prediction market scanner and analyzer.

## Tools

| Script | Purpose | Speed |
|--------|---------|-------|
| `notify.py` | Heartbeat scanner → Telegram report | ~30s |
| `discovery.py` | Market discovery across all series | ~20s (quick) / ~5min (--full) |
| `crossplatform.py` | Kalshi vs Polymarket comparison | ~15s (--auto for fuzzy) |
| `rules_scanner.py` | Contract rules & gotcha finder | ~30s |
| `news_scanner.py` | News → market opportunity matching | ~20s |
| `research.py` | Deep research on specific market | ~10s |

## Usage

```bash
# Heartbeat scan (run by HEARTBEAT.md every 3-4h)
python3 kalshi/notify.py

# Discover new markets
python3 kalshi/discovery.py          # Priority series only
python3 kalshi/discovery.py --full   # Full 8000+ series scan

# Cross-platform arbitrage
python3 kalshi/crossplatform.py --auto

# Contract rules analysis
python3 kalshi/rules_scanner.py

# News-driven opportunities
python3 kalshi/news_scanner.py
python3 kalshi/news_scanner.py --brief
```

## Strategy (see STRATEGY-V2.md)

1. **Junk bonds** — 85-95¢ markets expiring soon (reliable 5-15% returns)
2. **News-driven** — Match breaking news to mispriced markets
3. **Cross-platform** — Find spreads between Kalshi and Polymarket
4. **Rules edge** — Read contract rules to find settlement gotchas

## API Notes

- Rate limit: ~10 req/sec (be gentle)
- Series endpoint: paginated, 200/page, ~8000+ total
- Markets: use `series_ticker` param, status `open` (but some are `active`)
- Cache: `cache/` dir stores series list (6h TTL) and rules

## ⚠️ Research Checklist

Before recommending ANY trade to Jason:
1. ✅ Read contract rules (what exactly triggers YES/NO?)
2. ✅ Check data sources (BLS/BEA/Fed schedule)
3. ✅ Search recent news
4. ✅ Check Polymarket for price comparison
5. ✅ Verify timeline (when does it close? any events before?)
