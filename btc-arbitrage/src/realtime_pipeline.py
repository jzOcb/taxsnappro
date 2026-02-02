#!/usr/bin/env python3
"""
Unified Real-Time Data Pipeline
Integrates Kalshi WebSocket + Enhanced BRTI Proxy for low-latency arbitrage

Features:
- <1s latency on Kalshi orderbook updates
- Real-time BRTI proxy calculation
- Arbitrage signal detection
- Data logging for analysis
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Optional, List
import logging
from pathlib import Path

# Import our components
try:
    from kalshi_websocket import KalshiWebSocketClient
    from brti_proxy_enhanced import BTRIProxyEnhanced
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from kalshi_websocket import KalshiWebSocketClient
    from brti_proxy_enhanced import BTRIProxyEnhanced

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class RealtimePipeline:
    """
    Unified real-time data pipeline for BTC arbitrage
    
    Combines:
    - Kalshi WebSocket (orderbook updates)
    - Enhanced BRTI Proxy (volume-weighted BTC price)
    - Signal detection
    - Data logging
    """
    
    def __init__(
        self,
        series_ticker: str = "KXBTC15M",
        brti_interval: float = 2.0,
        log_dir: str = "./data",
        enable_logging: bool = True,
    ):
        """
        Initialize pipeline
        
        Args:
            series_ticker: Kalshi series to monitor
            brti_interval: BRTI update interval (seconds)
            log_dir: Directory for data logs
            enable_logging: Enable file logging
        """
        self.series_ticker = series_ticker
        self.brti_interval = brti_interval
        self.log_dir = Path(log_dir)
        self.enable_logging = enable_logging
        
        # Components
        self.kalshi_client = None
        self.brti_proxy = BTRIProxyEnhanced(use_volume_weights=True)
        
        # State
        self.running = False
        self.current_market = None
        self.latest_orderbook = {}
        self.latest_brti = None
        self.last_brti_update = 0
        
        # Data storage
        self.events = []
        self.signals = []
        
        # Stats
        self.stats = {
            'start_time': None,
            'orderbook_updates': 0,
            'brti_updates': 0,
            'signals_detected': 0,
            'kalshi_latency_ms': [],
            'brti_latency_ms': [],
        }
        
        # Setup logging directory
        if self.enable_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _on_orderbook(self, data: Dict):
        """Handle Kalshi orderbook update"""
        try:
            self.stats['orderbook_updates'] += 1
            
            ticker = data.get('market_ticker') or data.get('ticker')
            
            if not ticker:
                return
            
            # Extract orderbook data
            orderbook = {
                'timestamp': datetime.now().isoformat(),
                'ticker': ticker,
                'yes_bid': data.get('yes_bid', 0),
                'yes_ask': data.get('yes_ask', 0),
                'no_bid': data.get('no_bid', 0),
                'no_ask': data.get('no_ask', 0),
            }
            
            # Calculate latency (if timestamp available)
            if 'timestamp' in data:
                try:
                    server_time = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                    latency_ms = (datetime.now() - server_time.replace(tzinfo=None)).total_seconds() * 1000
                    self.stats['kalshi_latency_ms'].append(latency_ms)
                except:
                    pass
            
            self.latest_orderbook[ticker] = orderbook
            self.current_market = ticker
            
            # Log event
            event = {
                'type': 'orderbook',
                'data': orderbook,
            }
            
            if self.enable_logging:
                self.events.append(event)
            
            # Detect signals
            self._detect_signals(orderbook)
            
            # Console output
            logger.info(f"📊 {ticker}: YES {orderbook['yes_bid']:.2f}/{orderbook['yes_ask']:.2f}")
        
        except Exception as e:
            logger.error(f"Error handling orderbook: {e}")
    
    def _on_ticker(self, data: Dict):
        """Handle Kalshi ticker update"""
        # For now, just log
        logger.debug(f"Ticker update: {data.get('market_ticker')}")
    
    def _on_error(self, error: Exception):
        """Handle WebSocket error"""
        logger.error(f"WebSocket error: {error}")
    
    async def _brti_update_loop(self):
        """Background loop for BRTI proxy updates"""
        logger.info(f"Starting BRTI update loop (interval: {self.brti_interval}s)")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Calculate BRTI proxy
                result = self.brti_proxy.calculate()
                
                if result:
                    self.stats['brti_updates'] += 1
                    self.latest_brti = result
                    self.last_brti_update = time.time()
                    
                    # Calculate latency
                    latency_ms = (time.time() - start_time) * 1000
                    self.stats['brti_latency_ms'].append(latency_ms)
                    
                    # Log event
                    event = {
                        'type': 'brti',
                        'data': result,
                    }
                    
                    if self.enable_logging:
                        self.events.append(event)
                    
                    logger.info(f"💰 BRTI: ${result['proxy_brti']:,.2f} ({latency_ms:.0f}ms)")
                
                await asyncio.sleep(self.brti_interval)
            
            except Exception as e:
                logger.error(f"BRTI update error: {e}")
                await asyncio.sleep(self.brti_interval)
    
    def _detect_signals(self, orderbook: Dict):
        """
        Detect arbitrage signals
        
        Strategy: Look for BRTI movement vs Kalshi price lag
        """
        if not self.latest_brti:
            return
        
        # Get BRTI price and Kalshi market price
        brti_price = self.latest_brti['proxy_brti']
        yes_mid = (orderbook['yes_bid'] + orderbook['yes_ask']) / 2
        
        # Calculate implied probability
        # This is simplified - real strategy would be more sophisticated
        
        # Check for signal conditions
        # Example: BRTI moved >0.2% but Kalshi hasn't updated
        
        # For now, just log potential windows
        signal = {
            'timestamp': datetime.now().isoformat(),
            'ticker': orderbook['ticker'],
            'brti_price': brti_price,
            'kalshi_yes_mid': yes_mid,
            'signal_type': 'potential_window',
        }
        
        self.signals.append(signal)
        self.stats['signals_detected'] += 1
        
        # Console alert for significant signals
        # (Add more sophisticated logic here)
    
    async def start(self):
        """Start the pipeline"""
        logger.info("="*70)
        logger.info("Starting Real-Time Pipeline")
        logger.info("="*70)
        logger.info(f"Series: {self.series_ticker}")
        logger.info(f"BRTI Interval: {self.brti_interval}s")
        logger.info(f"Logging: {'Enabled' if self.enable_logging else 'Disabled'}")
        logger.info("="*70)
        
        self.running = True
        self.stats['start_time'] = time.time()
        
        # Initialize Kalshi WebSocket client
        self.kalshi_client = KalshiWebSocketClient(
            on_orderbook=self._on_orderbook,
            on_ticker=self._on_ticker,
            on_error=self._on_error,
        )
        
        # Start both components concurrently
        try:
            await asyncio.gather(
                self.kalshi_client.start(series=self.series_ticker),
                self._brti_update_loop(),
            )
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the pipeline"""
        logger.info("Stopping pipeline...")
        
        self.running = False
        
        if self.kalshi_client:
            await self.kalshi_client.stop()
        
        # Save data
        if self.enable_logging and self.events:
            self._save_session_data()
        
        # Print stats
        self._print_stats()
        
        logger.info("Pipeline stopped")
    
    def _save_session_data(self):
        """Save session data to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        session_data = {
            'session_info': {
                'start_time': datetime.fromtimestamp(self.stats['start_time']).isoformat(),
                'duration_seconds': time.time() - self.stats['start_time'],
                'series_ticker': self.series_ticker,
            },
            'stats': self.stats,
            'events': self.events,
            'signals': self.signals,
        }
        
        filename = self.log_dir / f"realtime_session_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        logger.info(f"📁 Session data saved: {filename}")
    
    def _print_stats(self):
        """Print session statistics"""
        if not self.stats['start_time']:
            return
        
        duration = time.time() - self.stats['start_time']
        
        print("\n" + "="*70)
        print("Session Statistics")
        print("="*70)
        print(f"Duration: {duration:.1f}s")
        print(f"Orderbook updates: {self.stats['orderbook_updates']}")
        print(f"BRTI updates: {self.stats['brti_updates']}")
        print(f"Signals detected: {self.stats['signals_detected']}")
        
        if self.stats['kalshi_latency_ms']:
            avg_latency = sum(self.stats['kalshi_latency_ms']) / len(self.stats['kalshi_latency_ms'])
            print(f"Avg Kalshi latency: {avg_latency:.1f}ms")
        
        if self.stats['brti_latency_ms']:
            avg_latency = sum(self.stats['brti_latency_ms']) / len(self.stats['brti_latency_ms'])
            print(f"Avg BRTI latency: {avg_latency:.1f}ms")
        
        print("="*70)


async def main():
    """CLI interface"""
    import sys
    
    series = sys.argv[1] if len(sys.argv) > 1 else "KXBTC15M"
    brti_interval = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    
    pipeline = RealtimePipeline(
        series_ticker=series,
        brti_interval=brti_interval,
        enable_logging=True,
    )
    
    try:
        await pipeline.start()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
    finally:
        await pipeline.stop()


if __name__ == "__main__":
    asyncio.run(main())
