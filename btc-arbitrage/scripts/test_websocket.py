#!/usr/bin/env python3
"""Test Binance.US WebSocket connection"""

import json
import time
from datetime import datetime

try:
    import websocket
    HAS_WS = True
except ImportError:
    HAS_WS = False

def test_with_curl():
    """Fallback test using websocat if available"""
    import subprocess
    
    print("Testing with websocat (if available)...")
    try:
        # Try websocat for 5 seconds
        result = subprocess.run(
            ['timeout', '5', 'websocat', 'wss://stream.binance.us:9443/ws/btcusdt@trade'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.stdout:
            print("✅ WebSocket data received:")
            lines = result.stdout.strip().split('\n')
            for line in lines[:3]:  # First 3 messages
                data = json.loads(line)
                print(f"  Price: ${float(data['p']):,.2f} @ {datetime.fromtimestamp(data['T']/1000)}")
            return True
        else:
            print("No data received")
            return False
            
    except Exception as e:
        print(f"websocat not available: {e}")
        return False

if __name__ == "__main__":
    if not HAS_WS:
        print("⚠️  websocket-client not installed")
        print("Trying alternative method...")
        test_with_curl()
    else:
        print("websocket-client available - implement full test later")
