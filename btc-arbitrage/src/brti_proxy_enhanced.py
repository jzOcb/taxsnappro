#!/usr/bin/env python3
"""
Enhanced BRTI Proxy with Bitstamp and Volume-Weighted Calculation

CF Benchmarks BRTI uses volume-weighted prices from multiple exchanges.
This enhanced version:
- Adds Bitstamp (BRTI constituent)
- Implements volume-weighted price calculation
- Provides real-time streaming via async
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Optional, Tuple
from urllib import request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BTRIProxyEnhanced:
    """
    Enhanced BRTI proxy with volume-weighted calculation
    
    BRTI constituents (approximate):
    - Coinbase
    - Kraken  
    - Bitstamp
    - Binance.US (when available)
    """
    
    # Exchange API endpoints
    EXCHANGES = {
        'coinbase': 'https://api.coinbase.com/v2/prices/BTC-USD/spot',
        'kraken': 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD',
        'bitstamp': 'https://www.bitstamp.net/api/v2/ticker/btcusd/',
        'binance_us': 'https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT',
    }
    
    # Default weights (equal weight if volume not available)
    DEFAULT_WEIGHTS = {
        'coinbase': 0.30,
        'kraken': 0.25,
        'bitstamp': 0.25,
        'binance_us': 0.20,
    }
    
    def __init__(self, use_volume_weights: bool = True):
        """
        Initialize BRTI proxy
        
        Args:
            use_volume_weights: Use volume-based weighting (more accurate)
        """
        self.use_volume_weights = use_volume_weights
        self.last_prices = {}
        self.last_volumes = {}
        self.last_update = None
    
    def _fetch_exchange(self, exchange: str, url: str) -> Optional[Tuple[float, float]]:
        """
        Fetch price and volume from an exchange
        
        Returns:
            (price, volume) or None if error
        """
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        try:
            with request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
            
            price = None
            volume = None
            
            # Parse response based on exchange
            if exchange == 'coinbase':
                price = float(data['data']['amount'])
                # Coinbase doesn't provide volume in spot endpoint
                volume = 1.0  # Use default weight
            
            elif exchange == 'kraken':
                pair_data = data['result']['XXBTZUSD']
                price = float(pair_data['c'][0])  # Last trade price
                volume = float(pair_data['v'][1])  # 24h volume
            
            elif exchange == 'bitstamp':
                price = float(data['last'])
                volume = float(data['volume'])  # 24h volume
            
            elif exchange == 'binance_us':
                price = float(data['price'])
                # Binance price endpoint doesn't include volume
                # Need to use 24hr ticker instead
                volume = 1.0  # Default weight
            
            return (price, volume) if price else None
            
        except Exception as e:
            logger.debug(f"Error fetching {exchange}: {e}")
            return None
    
    def _fetch_binance_us_with_volume(self) -> Optional[Tuple[float, float]]:
        """Fetch Binance.US with 24hr ticker for volume"""
        url = 'https://api.binance.us/api/v3/ticker/24hr?symbol=BTCUSDT'
        
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        try:
            with request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
            
            price = float(data['lastPrice'])
            volume = float(data['volume'])  # 24h volume in BTC
            
            return (price, volume)
        except:
            return None
    
    def calculate(self) -> Optional[Dict]:
        """
        Calculate BRTI proxy with volume weighting
        
        Returns:
            Dict with price, volumes, weights, and metadata
        """
        prices = {}
        volumes = {}
        
        logger.info("Fetching BTC prices from exchanges...")
        
        # Fetch from all exchanges
        for exchange, url in self.EXCHANGES.items():
            if exchange == 'binance_us' and self.use_volume_weights:
                # Use 24hr ticker for volume
                result = self._fetch_binance_us_with_volume()
            else:
                result = self._fetch_exchange(exchange, url)
            
            if result:
                price, volume = result
                prices[exchange] = price
                volumes[exchange] = volume
                logger.info(f"  {exchange:12s}: ${price:,.2f} (vol: {volume:,.0f})")
        
        if not prices:
            logger.error("❌ Failed to fetch any prices")
            return None
        
        # Calculate weights
        weights = {}
        
        if self.use_volume_weights and any(v > 1 for v in volumes.values()):
            # Volume-weighted
            total_volume = sum(volumes.values())
            
            if total_volume > 0:
                for exchange in prices.keys():
                    weights[exchange] = volumes[exchange] / total_volume
                
                logger.info("\nUsing volume-weighted calculation:")
                for exchange, weight in weights.items():
                    logger.info(f"  {exchange}: {weight:.1%}")
            else:
                # Fallback to default weights
                weights = {ex: self.DEFAULT_WEIGHTS.get(ex, 0.25) 
                          for ex in prices.keys()}
                logger.info("Using default weights (volume unavailable)")
        else:
            # Use default weights
            total_weight = sum(self.DEFAULT_WEIGHTS.get(ex, 0.25) 
                             for ex in prices.keys())
            for exchange in prices.keys():
                weights[exchange] = self.DEFAULT_WEIGHTS.get(exchange, 0.25) / total_weight
            
            logger.info("\nUsing equal/default weights")
        
        # Calculate weighted average
        weighted_sum = sum(prices[ex] * weights[ex] for ex in prices.keys())
        proxy_price = weighted_sum
        
        # Calculate metrics
        price_values = list(prices.values())
        spread = max(price_values) - min(price_values)
        spread_pct = (spread / proxy_price) * 100
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'proxy_brti': proxy_price,
            'prices': prices,
            'volumes': volumes if self.use_volume_weights else {},
            'weights': weights,
            'spread': spread,
            'spread_pct': spread_pct,
            'num_exchanges': len(prices),
        }
        
        # Update cache
        self.last_prices = prices
        self.last_volumes = volumes
        self.last_update = time.time()
        
        logger.info(f"\n✅ BRTI Proxy: ${proxy_price:,.2f}")
        logger.info(f"Spread: ${spread:.2f} ({spread_pct:.3f}%)")
        logger.info(f"Exchanges: {len(prices)}")
        
        return result
    
    def get_price(self) -> Optional[float]:
        """Get just the proxy price (quick)"""
        result = self.calculate()
        return result['proxy_brti'] if result else None


async def stream_brti(interval_seconds: float = 5.0, duration_minutes: Optional[int] = None):
    """
    Stream BRTI proxy updates
    
    Args:
        interval_seconds: Update interval
        duration_minutes: Run duration (None = infinite)
    """
    proxy = BTRIProxyEnhanced(use_volume_weights=True)
    
    print("="*70)
    print("BRTI Proxy Streaming (Enhanced)")
    print("="*70)
    print(f"Interval: {interval_seconds}s")
    if duration_minutes:
        print(f"Duration: {duration_minutes} minutes")
    else:
        print("Duration: Infinite (Ctrl+C to stop)")
    print("="*70)
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60) if duration_minutes else float('inf')
    
    count = 0
    last_price = None
    
    try:
        while time.time() < end_time:
            result = proxy.calculate()
            
            if result:
                count += 1
                current_price = result['proxy_brti']
                
                # Calculate change
                change_str = ""
                if last_price:
                    change = current_price - last_price
                    change_pct = (change / last_price) * 100
                    change_str = f" ({change:+.2f}, {change_pct:+.3f}%)"
                
                elapsed = int(time.time() - start_time)
                print(f"\n[{elapsed:4d}s] #{count}")
                print(f"BRTI Proxy: ${current_price:,.2f}{change_str}")
                print(f"Spread: ${result['spread']:.2f} ({result['spread_pct']:.3f}%)")
                
                last_price = current_price
            
            await asyncio.sleep(interval_seconds)
    
    except KeyboardInterrupt:
        print("\n⚠️  Stopped by user")
    
    print(f"\nTotal updates: {count}")


def main():
    """CLI interface"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'stream':
        # Stream mode
        interval = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else None
        
        asyncio.run(stream_brti(interval, duration))
    else:
        # One-shot mode
        proxy = BTRIProxyEnhanced(use_volume_weights=True)
        result = proxy.calculate()
        
        if result:
            print("\n" + json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
