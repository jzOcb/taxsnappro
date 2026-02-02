#!/usr/bin/env python3
"""Test Binance.US API accessibility"""

import requests
import json
from datetime import datetime

BASE_URL = "https://api.binance.us"

def test_btc_price():
    endpoint = f"{BASE_URL}/api/v3/ticker/price"
    params = {"symbol": "BTCUSDT"}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    print(f"Testing: {endpoint}?symbol=BTCUSDT")
    response = requests.get(endpoint, params=params, headers=headers, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS - BTC Price: ${data['price']}")
        return True
    else:
        print(f"❌ FAILED - Status: {response.status_code}")
        return False

if __name__ == "__main__":
    test_btc_price()
