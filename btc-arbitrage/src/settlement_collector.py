#!/usr/bin/env python3
"""
Settlement Data Collector - 持续收集市场结算结果验证BRTI proxy
"""
import json, time, os
from datetime import datetime
from urllib import request

def fetch_markets():
    """获取所有BTC 15分钟市场（包括已结算）"""
    url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=100&series_ticker=KXBTC15M"
    req = request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    try:
        with request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        return data.get('markets', [])
    except:
        return []

def fetch_brti_proxy():
    """获取当前BRTI proxy (简化版，只用Coinbase)"""
    try:
        req = request.Request('https://api.coinbase.com/v2/prices/BTC-USD/spot')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read())
        return float(data['data']['amount'])
    except:
        return None

def load_settlements():
    """加载已收集的settlements"""
    path = '/home/clawdbot/clawd/btc-arbitrage/data/settlements_v2.json'
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return []

def save_settlements(settlements):
    """保存settlements"""
    path = '/home/clawdbot/clawd/btc-arbitrage/data/settlements_v2.json'
    with open(path, 'w') as f:
        json.dump(settlements, f, indent=2)

def main():
    print(f"{'='*70}\nSettlement Collector\n{'='*70}\n", flush=True)
    
    settlements = load_settlements()
    known_tickers = {s['ticker'] for s in settlements}
    
    while True:
        markets = fetch_markets()
        brti = fetch_brti_proxy()
        
        for m in markets:
            ticker = m['ticker']
            status = m.get('status')
            result = m.get('result')
            
            # 新的已结算市场
            if status == 'closed' and result and ticker not in known_tickers:
                settlement = {
                    'ticker': ticker,
                    'result': result,
                    'close_time': m.get('close_time'),
                    'volume': m.get('volume', 0),
                    'brti_at_check': brti,
                    'check_time': datetime.now().isoformat(),
                }
                
                settlements.append(settlement)
                known_tickers.add(ticker)
                save_settlements(settlements)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ NEW: {ticker} → {result} | BRTI: ${brti:,.2f} | Vol: {m.get('volume',0)}", flush=True)
        
        # 每5分钟汇报一次
        if int(time.time()) % 300 < 60:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring... {len(settlements)} settlements collected", flush=True)
        
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Stopped", flush=True)
