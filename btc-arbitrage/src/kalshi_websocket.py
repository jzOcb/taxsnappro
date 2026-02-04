#!/usr/bin/env python3
"""
Kalshi WebSocket Client for Real-Time Market Data
Subscribes to orderbook updates for BTC 15-minute markets

Based on community implementation patterns and Kalshi WebSocket API
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any
import logging

# Note: Requires websockets library
# Install: sudo apt-get install python3-websockets
# Or: pip install websockets
try:
    import websockets
except ImportError:
    print("❌ websockets library not installed")
    print("Install with: sudo apt-get install python3-websockets")
    print("Or: pip install websockets")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KalshiWebSocketClient:
    """
    Real-time WebSocket client for Kalshi market data
    
    Features:
    - Auto-reconnect with exponential backoff
    - Orderbook subscription for BTC markets
    - Ticker updates
    - Connection health monitoring
    """
    
    # Kalshi WebSocket endpoints
    # Note: Based on community implementations, Kalshi uses WSS
    WS_URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"
    
    # Alternative demo/production endpoints (update as needed)
    # WS_URL = "wss://trading-api.kalshi.com/ws"
    
    def __init__(
        self,
        on_orderbook: Optional[Callable[[Dict], None]] = None,
        on_ticker: Optional[Callable[[Dict], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 60.0,
        api_key: Optional[str] = None,
        private_key_path: Optional[str] = None,
    ):
        """
        Initialize WebSocket client
        
        Args:
            on_orderbook: Callback for orderbook updates
            on_ticker: Callback for ticker updates
            on_error: Callback for errors
            reconnect_delay: Initial reconnect delay (seconds)
            max_reconnect_delay: Maximum reconnect delay (seconds)
            api_key: Kalshi API key ID (or from KALSHI_API_KEY env)
            private_key_path: Path to RSA private key PEM (or from KALSHI_PRIVATE_KEY_PATH env)
        """
        self.on_orderbook = on_orderbook
        self.on_ticker = on_ticker
        self.on_error = on_error
        
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.current_reconnect_delay = reconnect_delay
        
        self.ws = None
        self.running = False
        self.subscribed_tickers = set()
        
        # RSA auth
        import os
        self.api_key = api_key or os.getenv('KALSHI_API_KEY', '')
        self.private_key_path = private_key_path or os.getenv('KALSHI_PRIVATE_KEY_PATH', '')
        self._private_key = None
        self._load_auth()
        
        self._auth_headers_cache = None
        self.stats = {
            'messages_received': 0,
            'orderbook_updates': 0,
            'ticker_updates': 0,
            'reconnects': 0,
            'errors': 0,
            'last_message_time': None,
        }
    
    def _load_auth(self):
        """Load RSA private key for authentication"""
        if not self.api_key or not self.private_key_path:
            logger.warning("No Kalshi API credentials configured")
            return
        try:
            from cryptography.hazmat.primitives import serialization
            with open(self.private_key_path) as f:
                key_data = f.read()
            self._private_key = serialization.load_pem_private_key(key_data.encode(), password=None)
            logger.info(f"✅ Kalshi RSA key loaded (key: {self.api_key[:12]}...)")
        except Exception as e:
            logger.error(f"Failed to load RSA key: {e}")
    
    def _get_auth_headers(self) -> Dict:
        """Generate RSA-PSS signed auth headers for WebSocket"""
        if not self._private_key or not self.api_key:
            return {}
        try:
            import time as _time
            import base64
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            
            timestamp_ms = int(_time.time() * 1000)
            message = f"{timestamp_ms}GET/trade-api/ws/v2"
            signature = self._private_key.sign(
                message.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=hashes.SHA256.digest_size
                ),
                hashes.SHA256()
            )
            return {
                "KALSHI-ACCESS-KEY": self.api_key,
                "KALSHI-ACCESS-TIMESTAMP": str(timestamp_ms),
                "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode(),
            }
        except Exception as e:
            logger.error(f"Auth header generation failed: {e}")
            return {}
    
    async def connect(self):
        """Establish WebSocket connection with RSA auth"""
        try:
            logger.info(f"Connecting to {self.WS_URL}...")
            
            # Generate auth headers
            auth_headers = self._get_auth_headers()
            if not auth_headers:
                logger.error("No auth headers - cannot connect to Kalshi WebSocket")
                return False
            
            # Connect with timeout and auth
            self.ws = await asyncio.wait_for(
                websockets.connect(
                    self.WS_URL,
                    additional_headers=auth_headers,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                ),
                timeout=10.0
            )
            
            logger.info("✅ Connected to Kalshi WebSocket")
            self.current_reconnect_delay = self.reconnect_delay
            self.stats['reconnects'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            if self.on_error:
                self.on_error(e)
            return False
    
    async def subscribe_market(self, ticker: str):
        """
        Subscribe to orderbook updates for a specific market
        
        Args:
            ticker: Market ticker (e.g., "KXBTC15M-26FEB0417-T106000")
        """
        if not self.ws:
            logger.error("Not connected")
            return False
        
        try:
            # Subscription message format (based on typical WebSocket APIs)
            subscribe_msg = {
                "type": "subscribe",
                "channels": [
                    {
                        "name": "orderbook",
                        "market_ticker": ticker
                    },
                    {
                        "name": "ticker",
                        "market_ticker": ticker
                    }
                ]
            }
            
            await self.ws.send(json.dumps(subscribe_msg))
            self.subscribed_tickers.add(ticker)
            logger.info(f"📡 Subscribed to {ticker}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Subscribe failed: {e}")
            if self.on_error:
                self.on_error(e)
            return False
    
    async def subscribe_series(self, series_ticker: str = "KXBTC15M"):
        """
        Subscribe to all active markets in a series
        
        Args:
            series_ticker: Series ticker (e.g., "KXBTC15M")
        """
        if not self.ws:
            logger.error("Not connected")
            return False
        
        try:
            subscribe_msg = {
                "type": "subscribe",
                "channels": [
                    {
                        "name": "orderbook",
                        "series_ticker": series_ticker
                    },
                    {
                        "name": "ticker",
                        "series_ticker": series_ticker
                    }
                ]
            }
            
            await self.ws.send(json.dumps(subscribe_msg))
            logger.info(f"📡 Subscribed to series {series_ticker}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Series subscribe failed: {e}")
            if self.on_error:
                self.on_error(e)
            return False
    
    async def _handle_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = time.time()
            
            msg_type = data.get('type') or data.get('msg')
            
            # Handle different message types
            if msg_type == 'orderbook' or msg_type == 'orderbook_delta':
                self.stats['orderbook_updates'] += 1
                if self.on_orderbook:
                    self.on_orderbook(data)
            
            elif msg_type == 'ticker' or msg_type == 'market_update':
                self.stats['ticker_updates'] += 1
                if self.on_ticker:
                    self.on_ticker(data)
            
            elif msg_type == 'subscribed':
                logger.info(f"✅ Subscription confirmed")
            
            elif msg_type == 'error':
                logger.error(f"❌ Server error: {data.get('message')}")
                self.stats['errors'] += 1
            
            else:
                # Log unknown message types for debugging
                logger.debug(f"Unknown message type: {msg_type}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            if self.on_error:
                self.on_error(e)
    
    async def _receive_loop(self):
        """Main message receiving loop"""
        try:
            async for message in self.ws:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
            if self.on_error:
                self.on_error(e)
    
    async def _reconnect_loop(self):
        """Auto-reconnect loop with exponential backoff"""
        while self.running:
            if not self.ws or getattr(self.ws, "close_code", None) is not None:
                logger.info("Attempting to reconnect...")
                
                connected = await self.connect()
                
                if connected:
                    # Resubscribe to previous markets
                    for ticker in list(self.subscribed_tickers):
                        await self.subscribe_market(ticker)
                    
                    # Start receiving messages
                    try:
                        await self._receive_loop()
                    except Exception as e:
                        logger.error(f"Receive loop crashed: {e}")
                
                # Exponential backoff
                await asyncio.sleep(self.current_reconnect_delay)
                self.current_reconnect_delay = min(
                    self.current_reconnect_delay * 2,
                    self.max_reconnect_delay
                )
            else:
                await asyncio.sleep(1)
    
    async def start(self, ticker: Optional[str] = None, series: Optional[str] = None):
        """
        Start WebSocket client
        
        Args:
            ticker: Specific market ticker to subscribe to
            series: Series ticker to subscribe to (e.g., "KXBTC15M")
        """
        self.running = True
        
        # Initial connection
        connected = await self.connect()
        
        if connected:
            # Subscribe
            if ticker:
                await self.subscribe_market(ticker)
            elif series:
                await self.subscribe_series(series)
        
        # Start auto-reconnect loop
        await self._reconnect_loop()
    
    async def stop(self):
        """Stop WebSocket client"""
        logger.info("Stopping WebSocket client...")
        self.running = False
        
        if self.ws and getattr(self.ws, "close_code", None) is None:
            await self.ws.close()
        
        logger.info("WebSocket client stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        stats = self.stats.copy()
        
        if stats['last_message_time']:
            stats['seconds_since_last_message'] = time.time() - stats['last_message_time']
        
        return stats


async def demo():
    """Demo usage"""
    print("="*70)
    print("Kalshi WebSocket Client Demo")
    print("="*70)
    
    def on_orderbook(data):
        ticker = data.get('market_ticker', 'unknown')
        print(f"📊 Orderbook update: {ticker}")
        
        if 'yes_bid' in data:
            print(f"   YES: {data['yes_bid']:.2f} / {data['yes_ask']:.2f}")
        if 'no_bid' in data:
            print(f"   NO:  {data['no_bid']:.2f} / {data['no_ask']:.2f}")
    
    def on_ticker(data):
        ticker = data.get('market_ticker', 'unknown')
        print(f"📈 Ticker update: {ticker}")
        if 'last_price' in data:
            print(f"   Last: ${data['last_price']:.2f}")
    
    def on_error(error):
        print(f"❌ Error: {error}")
    
    client = KalshiWebSocketClient(
        on_orderbook=on_orderbook,
        on_ticker=on_ticker,
        on_error=on_error
    )
    
    try:
        # Subscribe to BTC 15-minute markets
        await client.start(series="KXBTC15M")
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    finally:
        await client.stop()
        
        # Print stats
        stats = client.get_stats()
        print("\n" + "="*70)
        print("Session Statistics:")
        print(f"  Messages received: {stats['messages_received']}")
        print(f"  Orderbook updates: {stats['orderbook_updates']}")
        print(f"  Ticker updates: {stats['ticker_updates']}")
        print(f"  Reconnects: {stats['reconnects']}")
        print(f"  Errors: {stats['errors']}")
        print("="*70)


if __name__ == "__main__":
    asyncio.run(demo())
