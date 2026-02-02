#!/usr/bin/env python3
"""
Kalshi API Integration
Handles authentication and order placement for real trading
"""

import json
import os
from urllib import request, parse
from datetime import datetime
import hmac
import hashlib

class KalshiAPI:
    """Kalshi API client"""
    
    def __init__(self, email=None, password=None, api_key=None):
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.email = email or os.getenv('KALSHI_EMAIL')
        self.password = password or os.getenv('KALSHI_PASSWORD')
        self.api_key = api_key or os.getenv('KALSHI_API_KEY')
        self.token = None
        
    def login(self):
        """
        Login and get auth token
        Note: For demo purposes, we'll use public endpoints
        Real trading requires actual credentials
        """
        if not self.email or not self.password:
            print("⚠️  No credentials - using public endpoints only")
            return False
        
        url = f"{self.base_url}/login"
        data = json.dumps({
            'email': self.email,
            'password': self.password
        }).encode()
        
        req = request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        
        try:
            with request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read())
            
            self.token = result.get('token')
            print("✅ Logged in to Kalshi")
            return True
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
    
    def get_markets(self, series_ticker='KXBTC15M', status='open', limit=200):
        """Get markets"""
        params = {
            'limit': limit,
            'series_ticker': series_ticker,
            'status': status,
        }
        
        url = f"{self.base_url}/markets?{parse.urlencode(params)}"
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')
        
        try:
            with request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
            return data.get('markets', [])
        except Exception as e:
            print(f"❌ Error fetching markets: {e}")
            return []
    
    def get_market(self, ticker):
        """Get specific market details"""
        url = f"{self.base_url}/markets/{ticker}"
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')
        
        try:
            with request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
            return data.get('market')
        except Exception as e:
            print(f"❌ Error fetching market: {e}")
            return None
    
    def place_order(self, ticker, action, side, count, yes_price=None):
        """
        Place order (requires authentication)
        
        ticker: market ticker
        action: 'buy' or 'sell'
        side: 'yes' or 'no'
        count: number of contracts
        yes_price: limit price (in cents)
        """
        if not self.token:
            print("❌ Not authenticated - cannot place orders")
            return None
        
        url = f"{self.base_url}/portfolio/orders"
        
        order = {
            'ticker': ticker,
            'action': action,
            'side': side,
            'count': count,
            'type': 'limit',
        }
        
        if yes_price:
            order['yes_price'] = int(yes_price * 100)  # Convert to cents
        
        data = json.dumps(order).encode()
        
        req = request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {self.token}')
        
        try:
            with request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read())
            print(f"✅ Order placed: {result}")
            return result
        except Exception as e:
            print(f"❌ Order failed: {e}")
            return None
    
    def get_balance(self):
        """Get account balance (requires authentication)"""
        if not self.token:
            print("❌ Not authenticated")
            return None
        
        url = f"{self.base_url}/portfolio/balance"
        req = request.Request(url)
        req.add_header('Authorization', f'Bearer {self.token}')
        
        try:
            with request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
            return data.get('balance')
        except Exception as e:
            print(f"❌ Error fetching balance: {e}")
            return None
    
    def get_positions(self):
        """Get current positions (requires authentication)"""
        if not self.token:
            print("❌ Not authenticated")
            return None
        
        url = f"{self.base_url}/portfolio/positions"
        req = request.Request(url)
        req.add_header('Authorization', f'Bearer {self.token}')
        
        try:
            with request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
            return data.get('positions', [])
        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            return []


if __name__ == "__main__":
    # Demo - test public endpoints
    print("\n" + "="*70)
    print("KALSHI API DEMO - Public Endpoints")
    print("="*70 + "\n")
    
    api = KalshiAPI()
    
    # Get current markets
    print("Fetching KXBTC15M markets...\n")
    markets = api.get_markets('KXBTC15M', 'open', 5)
    
    if markets:
        print(f"Found {len(markets)} open markets:\n")
        for i, m in enumerate(markets[:3], 1):
            print(f"{i}. {m['ticker']}")
            print(f"   YES: ${m.get('yes_bid', 0)/100:.2f} / ${m.get('yes_ask', 0)/100:.2f}")
            print(f"   Volume: {m.get('volume', 0)} | Close: {m.get('close_time')}")
            print()
        
        # Get details of first market
        if markets:
            ticker = markets[0]['ticker']
            print(f"Fetching details for {ticker}...\n")
            market = api.get_market(ticker)
            
            if market:
                print(f"Market Details:")
                print(f"  Title: {market.get('title')}")
                print(f"  Open: {market.get('open_time')}")
                print(f"  Close: {market.get('close_time')}")
                print(f"  Volume: {market.get('volume')} contracts")
                print(f"  Liquidity: ${market.get('liquidity', 0)/100:,.2f}")
    else:
        print("No markets found")
    
    print("\n" + "="*70)
    print("Note: Order placement requires authentication")
    print("Set KALSHI_EMAIL and KALSHI_PASSWORD environment variables")
    print("="*70 + "\n")
