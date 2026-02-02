# WebSocket Infrastructure - Usage Guide

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Option 1: System package (recommended)
sudo apt-get install -y python3-websockets

# Option 2: pip (if available)
pip install websockets
```

### 2. Test WebSocket Connection

```bash
cd /home/clawdbot/clawd/btc-arbitrage/src

# Run comprehensive test suite (60 seconds)
python3 test_websocket.py 60

# Quick test (30 seconds)
python3 test_websocket.py 30
```

This will test:
- ✅ Kalshi WebSocket connection
- ✅ Latency measurements (target: <1s)
- ✅ Data quality validation

### 3. Test Enhanced BRTI Proxy

```bash
# One-shot calculation (with Bitstamp + volume weighting)
python3 brti_proxy_enhanced.py

# Stream mode (updates every 5 seconds)
python3 brti_proxy_enhanced.py stream 5

# Stream for 10 minutes
python3 brti_proxy_enhanced.py stream 5 10
```

### 4. Run Real-Time Pipeline

```bash
# Full pipeline: Kalshi WebSocket + BRTI Proxy
python3 realtime_pipeline.py

# With custom BRTI interval (3 seconds)
python3 realtime_pipeline.py KXBTC15M 3

# Monitor specific series
python3 realtime_pipeline.py KXBTCHR 2
```

## 📂 Components

### 1. `kalshi_websocket.py`

**Kalshi WebSocket Client** - Real-time orderbook and ticker data

**Features:**
- Auto-reconnect with exponential backoff
- Market/series subscription
- Connection health monitoring
- Latency tracking

**Usage:**
```python
from kalshi_websocket import KalshiWebSocketClient

def on_orderbook(data):
    print(f"YES: {data['yes_bid']}/{data['yes_ask']}")

client = KalshiWebSocketClient(on_orderbook=on_orderbook)
await client.start(series="KXBTC15M")
```

**Key Methods:**
- `connect()` - Establish connection
- `subscribe_market(ticker)` - Subscribe to specific market
- `subscribe_series(series)` - Subscribe to all markets in series
- `get_stats()` - Connection statistics

### 2. `brti_proxy_enhanced.py`

**Enhanced BRTI Proxy** - Volume-weighted BTC price calculation

**Improvements over original:**
- ✅ Bitstamp added (BRTI constituent)
- ✅ Volume-weighted calculation (more accurate)
- ✅ Async streaming support
- ✅ Better error handling

**Exchanges:**
- Coinbase (30%)
- Kraken (25%)
- Bitstamp (25%)
- Binance.US (20%)

**Usage:**
```python
from brti_proxy_enhanced import BTRIProxyEnhanced

proxy = BTRIProxyEnhanced(use_volume_weights=True)
result = proxy.calculate()

print(f"BRTI Proxy: ${result['proxy_brti']:,.2f}")
print(f"Spread: {result['spread_pct']:.3f}%")
```

### 3. `realtime_pipeline.py`

**Unified Real-Time Pipeline** - Integrated data pipeline

**Features:**
- Parallel Kalshi WebSocket + BRTI updates
- Signal detection
- Session logging
- Latency monitoring

**Data Flow:**
```
Kalshi WebSocket ──┐
                   ├──> Signal Detection ──> Data Logging
BRTI Proxy ────────┘
```

**Usage:**
```python
from realtime_pipeline import RealtimePipeline

pipeline = RealtimePipeline(
    series_ticker="KXBTC15M",
    brti_interval=2.0,
    enable_logging=True,
)

await pipeline.start()
```

**Output:**
- Real-time console updates
- Session JSON logs in `data/`
- Statistics summary on exit

### 4. `test_websocket.py`

**Test Suite** - Validation and benchmarking

**Tests:**
1. Connection test - Verify WebSocket connectivity
2. Latency test - Measure Kalshi + BRTI latencies
3. Data quality test - Validate message format

**Usage:**
```bash
# 60-second test
python3 test_websocket.py 60

# Quick 30-second test
python3 test_websocket.py 30
```

## 🎯 Performance Targets

### Latency Goals
- **Kalshi WebSocket:** <1 second (vs REST: 20-30s)
- **BRTI Proxy:** <500ms
- **End-to-end pipeline:** <2 seconds

### Expected Improvements
| Metric | Before (REST) | After (WebSocket) | Improvement |
|--------|---------------|-------------------|-------------|
| Kalshi Data Latency | 20-30s | <1s | **20-30x faster** |
| Update Frequency | ~3/min | Real-time | **Continuous** |
| Arbitrage Window Detection | Delayed | Instant | **Critical** |

## 🔧 Configuration

### WebSocket Endpoint

If the default Kalshi WebSocket URL changes, update in `kalshi_websocket.py`:

```python
WS_URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"
```

### BRTI Weights

Adjust exchange weights in `brti_proxy_enhanced.py`:

```python
DEFAULT_WEIGHTS = {
    'coinbase': 0.30,
    'kraken': 0.25,
    'bitstamp': 0.25,
    'binance_us': 0.20,
}
```

### Pipeline Settings

In `realtime_pipeline.py`:

```python
pipeline = RealtimePipeline(
    series_ticker="KXBTC15M",     # Market series
    brti_interval=2.0,            # BRTI update interval (seconds)
    log_dir="./data",             # Log directory
    enable_logging=True,          # Enable file logging
)
```

## 🐛 Troubleshooting

### "websockets library not installed"

```bash
# Solution 1: System package
sudo apt-get install python3-websockets

# Solution 2: Check if already installed
python3 -c "import websockets; print('installed')"
```

### "Connection failed" or "Connection timeout"

**Possible causes:**
1. Network connectivity issue
2. Kalshi WebSocket endpoint changed
3. Authentication required (not implemented yet)

**Debug:**
```bash
# Test basic connectivity
curl -I https://api.elections.kalshi.com

# Check if WebSocket endpoint is accessible
# (May need to verify current endpoint URL)
```

### No messages received

**Possible causes:**
1. No active markets in series
2. Markets closed (outside trading hours)
3. Subscription failed

**Debug:**
```python
# Check available markets first
import requests
resp = requests.get("https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXBTC15M&status=open")
print(resp.json())
```

### High latency

**Check:**
1. Server load (use `top` or `htop`)
2. Network latency (`ping api.elections.kalshi.com`)
3. System resources

## 📊 Data Format

### Orderbook Update
```json
{
  "type": "orderbook",
  "market_ticker": "KXBTC15M-26FEB0417-T106000",
  "yes_bid": 0.52,
  "yes_ask": 0.54,
  "no_bid": 0.46,
  "no_ask": 0.48,
  "timestamp": "2026-02-02T17:00:00Z"
}
```

### BRTI Proxy Result
```json
{
  "timestamp": "2026-02-02T17:00:00Z",
  "proxy_brti": 105234.56,
  "prices": {
    "coinbase": 105230.00,
    "kraken": 105240.00,
    "bitstamp": 105235.00,
    "binance_us": 105233.00
  },
  "volumes": {
    "kraken": 1234.5,
    "bitstamp": 987.3
  },
  "weights": {
    "coinbase": 0.30,
    "kraken": 0.25,
    "bitstamp": 0.25,
    "binance_us": 0.20
  },
  "spread": 10.00,
  "spread_pct": 0.009
}
```

## 🔐 Authentication

**Current Implementation:** Public endpoints only (no auth)

**If Kalshi WebSocket requires authentication:**

1. Obtain API credentials from Kalshi
2. Update `kalshi_websocket.py`:

```python
class KalshiWebSocketClient:
    def __init__(self, api_key=None, api_secret=None, ...):
        self.api_key = api_key
        self.api_secret = api_secret
    
    async def connect(self):
        # Add authentication headers
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        
        self.ws = await websockets.connect(
            self.WS_URL,
            extra_headers=headers
        )
```

## 📈 Next Steps

After validating WebSocket infrastructure:

1. **Integration** - Connect to existing arbitrage strategy
2. **Signal Refinement** - Improve detection algorithm
3. **Backtesting** - Replay captured data
4. **Paper Trading** - Test with live data
5. **Production** - Deploy with monitoring

## 🔗 References

- [Kalshi API Docs](https://docs.kalshi.com)
- [CF Benchmarks BRTI](https://www.cfbenchmarks.com/data/indices/BRTI)
- [WebSockets Python Library](https://websockets.readthedocs.io/)

---

**Status:** ✅ Ready for testing  
**Last Updated:** 2026-02-02  
**Dependencies:** python3-websockets
