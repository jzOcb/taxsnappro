#!/usr/bin/env python3
"""
Live Paper Trader - Runs for hours executing paper trades based on signals
"""

import json
import time
import os
import sys
from datetime import datetime
from urllib import request

class PaperTrader:
    """Paper trading engine"""
    
    def __init__(self, initial_balance=1000):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.positions = []
        self.trades = []
        self.pnl = 0
        
    def can_trade(self, size, price):
        cost = size * price
        return cost <= self.balance
    
    def open_position(self, direction, size, entry_price, market_ticker):
        cost = size * entry_price
        
        if not self.can_trade(size, entry_price):
            return None
        
        position = {
            'id': len(self.positions),
            'direction': direction,
            'size': size,
            'entry_price': entry_price,
            'entry_time': datetime.now().isoformat(),
            'market': market_ticker,
            'status': 'open',
        }
        
        self.positions.append(position)
        self.balance -= cost
        
        print(f"  ✅ OPEN {direction} {size} @ ${entry_price:.2f} | Cost: ${cost:.2f}")
        
        return position['id']
    
    def close_position(self, position_id, exit_price):
        position = next((p for p in self.positions if p['id'] == position_id and p['status'] == 'open'), None)
        
        if not position:
            return None
        
        entry_cost = position['size'] * position['entry_price']
        exit_value = position['size'] * exit_price
        pnl = exit_value - entry_cost
        
        if position['direction'] == 'NO':
            pnl = -pnl
        
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now().isoformat()
        position['pnl'] = pnl
        position['status'] = 'closed'
        
        self.balance += exit_value
        self.pnl += pnl
        
        self.trades.append(position.copy())
        
        win_loss = "WIN" if pnl > 0 else "LOSS"
        print(f"  {'✅' if pnl > 0 else '❌'} CLOSE {position['direction']} {position['size']} @ ${exit_price:.2f} | "
              f"P&L: ${pnl:+.2f} [{win_loss}]")
        
        return pnl
    
    def get_open_positions(self):
        return [p for p in self.positions if p['status'] == 'open']


def get_brti_proxy():
    """Quick BRTI proxy - average of 3 exchanges"""
    exchanges = {
        'binance_us': 'https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT',
        'coinbase': 'https://api.coinbase.com/v2/prices/BTC-USD/spot',
        'kraken': 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD',
    }
    
    prices = []
    
    for name, url in exchanges.items():
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        try:
            with request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
            
            if name == 'binance_us':
                prices.append(float(data['price']))
            elif name == 'coinbase':
                prices.append(float(data['data']['amount']))
            elif name == 'kraken':
                prices.append(float(data['result']['XXBTZUSD']['c'][0]))
        except:
            pass
    
    if prices:
        return sum(prices) / len(prices)
    return None


def get_kalshi_market():
    """Get current active KXBTC15M market"""
    url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=200&series_ticker=KXBTC15M&status=open"
    
    req = request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    
    try:
        with request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        
        if data.get('markets') and len(data['markets']) > 0:
            market = data['markets'][0]
            return {
                'ticker': market['ticker'],
                'yes_bid': market.get('yes_bid', 0) / 100,
                'yes_ask': market.get('yes_ask', 0) / 100,
                'volume': market.get('volume', 0),
                'close_time': market.get('close_time'),
            }
    except Exception as e:
        pass
    
    return None


def run_live_paper_trading(duration_minutes=480, interval_seconds=60, trade_size=10):
    """
    Run live paper trading for extended period
    
    Strategy:
    - Monitor BRTI vs Kalshi
    - When BRTI moves >0.2% but Kalshi lags (<0.1% move)
    - Open position betting Kalshi will follow
    - Close after 3-5 minutes or when profit target hit
    """
    print(f"\n{'='*70}")
    print(f"LIVE PAPER TRADING")
    print(f"{'='*70}")
    print(f"Duration: {duration_minutes} minutes")
    print(f"Interval: {interval_seconds} seconds")
    print(f"Trade Size: {trade_size} contracts")
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*70}\n")
    
    trader = PaperTrader(initial_balance=1000)
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    last_brti = None
    last_kalshi_bid = None
    
    measurements = []
    
    while time.time() < end_time:
        measurement_time = datetime.now()
        elapsed = int(time.time() - start_time)
        
        brti = get_brti_proxy()
        kalshi = get_kalshi_market()
        
        if not brti or not kalshi:
            print(f"[{elapsed:4d}s] ⚠️  Data fetch failed, retrying...")
            time.sleep(interval_seconds)
            continue
        
        brti_chg = None
        kalshi_chg = None
        
        if last_brti:
            brti_chg = ((brti - last_brti) / last_brti) * 100
        
        if last_kalshi_bid and last_kalshi_bid > 0:
            kalshi_chg = ((kalshi['yes_bid'] - last_kalshi_bid) / last_kalshi_bid) * 100
        
        # Trading logic
        signal = None
        action_taken = False
        
        if brti_chg is not None and kalshi_chg is not None:
            # WINDOW: BRTI moved but Kalshi didn't follow yet
            if abs(brti_chg) > 0.2 and abs(kalshi_chg) < 0.1:
                signal = "WINDOW"
                
                # Open position if we don't have one
                open_positions = trader.get_open_positions()
                if len(open_positions) == 0:
                    # Bet YES if BRTI went up (Kalshi should follow)
                    # Bet NO if BRTI went down
                    direction = 'YES' if brti_chg > 0 else 'NO'
                    entry_price = kalshi['yes_ask'] if direction == 'YES' else (1 - kalshi['yes_bid'])
                    
                    pos_id = trader.open_position(direction, trade_size, entry_price, kalshi['ticker'])
                    if pos_id is not None:
                        print(f"[{elapsed:4d}s] 🎯 SIGNAL: BRTI {brti_chg:+.3f}%, Kalshi {kalshi_chg:+.2f}%")
                        action_taken = True
        
        # Check open positions - close after 3-5 cycles or profit target
        for position in trader.get_open_positions():
            entry_time = datetime.fromisoformat(position['entry_time'])
            hold_time = (datetime.now() - entry_time).total_seconds()
            
            # Close conditions:
            # 1. Held for 3+ minutes
            # 2. Profit target hit (>2% gain)
            should_close = False
            
            if hold_time > 180:  # 3 minutes
                should_close = True
            
            # Calculate current profit
            current_price = kalshi['yes_bid'] if position['direction'] == 'YES' else (1 - kalshi['yes_ask'])
            unrealized_pnl = (current_price - position['entry_price']) * position['size']
            
            if position['direction'] == 'NO':
                unrealized_pnl = -unrealized_pnl
            
            pnl_pct = (unrealized_pnl / (position['entry_price'] * position['size'])) * 100
            
            if pnl_pct > 2:  # 2% profit target
                should_close = True
            
            if should_close:
                trader.close_position(position['id'], current_price)
                action_taken = True
        
        # Status line
        brti_str = f"{brti_chg:+.3f}%" if brti_chg else "N/A"
        kalshi_str = f"{kalshi_chg:+.2f}%" if kalshi_chg else "N/A"
        sig_str = f" [{signal}]" if signal else ""
        pos_str = f" | Positions: {len(trader.get_open_positions())}" if trader.get_open_positions() else ""
        pnl_str = f" | P&L: ${trader.pnl:+.2f}" if trader.trades else ""
        
        if not action_taken:
            print(f"[{elapsed:4d}s] BRTI: ${brti:,.2f} ({brti_str}) | "
                  f"Kalshi: {kalshi['yes_bid']:.2f}/{kalshi['yes_ask']:.2f} ({kalshi_str}){sig_str}{pos_str}{pnl_str}")
        
        measurements.append({
            'timestamp': measurement_time.isoformat(),
            'elapsed': elapsed,
            'brti': brti,
            'brti_chg': brti_chg,
            'kalshi': kalshi,
            'kalshi_chg': kalshi_chg,
            'signal': signal,
            'balance': trader.balance,
            'pnl': trader.pnl,
        })
        
        last_brti = brti
        last_kalshi_bid = kalshi['yes_bid']
        
        time.sleep(interval_seconds)
    
    # Summary
    print(f"\n{'='*70}")
    print("PAPER TRADING SUMMARY")
    print(f"{'='*70}")
    print(f"Initial Balance: ${trader.initial_balance:,.2f}")
    print(f"Final Balance: ${trader.balance:,.2f}")
    print(f"Total P&L: ${trader.pnl:+,.2f} ({(trader.pnl/trader.initial_balance)*100:+.2f}% ROI)")
    print(f"\nTotal Trades: {len(trader.trades)}")
    
    if trader.trades:
        wins = [t for t in trader.trades if t['pnl'] > 0]
        print(f"Wins: {len(wins)} | Losses: {len(trader.trades) - len(wins)}")
        print(f"Win Rate: {len(wins)/len(trader.trades)*100:.1f}%")
        print(f"Best Trade: ${max(t['pnl'] for t in trader.trades):+.2f}")
        print(f"Worst Trade: ${min(t['pnl'] for t in trader.trades):+.2f}")
    
    # Save results
    os.makedirs('data', exist_ok=True)
    filename = f"data/paper_trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            'duration_minutes': duration_minutes,
            'initial_balance': trader.initial_balance,
            'final_balance': trader.balance,
            'pnl': trader.pnl,
            'trades': trader.trades,
            'measurements': measurements,
        }, f, indent=2)
    
    print(f"\nSaved: {filename}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 480  # 8 hours default
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60   # 1 minute
    trade_size = int(sys.argv[3]) if len(sys.argv) > 3 else 10  # 10 contracts
    
    try:
        run_live_paper_trading(duration, interval, trade_size)
    except KeyboardInterrupt:
        print("\n⚠️  Stopped by user")
