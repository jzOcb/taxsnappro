#!/usr/bin/env python3
"""Fast real-time monitoring"""
import json, time
from datetime import datetime
from urllib import request

def get_btc():
    req = request.Request("https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT")
    req.add_header('User-Agent', 'Mozilla/5.0')
    try:
        with request.urlopen(req, timeout=2) as r:
            return float(json.loads(r.read())['price'])
    except: return None

def get_kalshi():
    req = request.Request("https://api.elections.kalshi.com/trade-api/v2/markets?limit=10&series_ticker=KXBTC15M&status=open")
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    try:
        with request.urlopen(req, timeout=2) as r:
            d = json.loads(r.read())
        if d.get('markets'):
            m = d['markets'][0]
            return {'ticker': m['ticker'], 'yes_bid': m.get('yes_bid',0)/100, 'yes_ask': m.get('yes_ask',0)/100}
    except: pass
    return None

def monitor(dur=300, ms=1000):
    print(f"\n{'='*70}\nFAST MONITOR {dur}s @ {ms}ms\n{'='*70}\n")
    start = time.time()
    last_b, last_k = None, None
    sigs = []
    
    while time.time() < start + dur:
        t = time.time()
        btc, kal = get_btc(), get_kalshi()
        
        if btc and kal:
            bc = ((btc-last_b)/last_b*100) if last_b else None
            kc = ((kal['yes_bid']-last_k)/last_k*100) if last_k and last_k>0 else None
            sig = None
            
            if bc and kc and abs(bc)>0.05 and abs(kc)<0.03:
                sig = "STRONG" if abs(bc)>0.1 else "WEAK"
                sigs.append({'time': datetime.now().isoformat(), 'btc':btc, 'btc_chg':bc, 
                            'kalshi_bid':kal['yes_bid'], 'kalshi_chg':kc, 'signal':sig})
            
            e = int(time.time()-start)
            if sig:
                print(f"⚡ [{e:3d}s] ${btc:,.2f} ({bc:+.3f}%) | {kal['yes_bid']:.2f} ({kc:+.3f}%) [{sig}]")
            elif e%10==0:
                bs = f"{bc:+.3f}%" if bc else "---"
                ks = f"{kc:+.3f}%" if kc else "---"
                print(f"   [{e:3d}s] ${btc:,.2f} ({bs}) | {kal['yes_bid']:.2f} ({ks})")
            
            last_b, last_k = btc, kal['yes_bid']
        
        time.sleep(max(0, ms/1000-(time.time()-t)))
    
    print(f"\n{'='*70}\nSignals: {len(sigs)}")
    if sigs:
        for i,s in enumerate(sigs[:10],1):
            print(f"  {i}. BTC {s['btc_chg']:+.3f}%, Kalshi {s['kalshi_chg']:+.3f}% [{s['signal']}]")
        import os
        os.makedirs('../data', exist_ok=True)
        fn = f"../data/signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(fn,'w') as f: json.dump(sigs,f,indent=2)
        print(f"\n{fn}")

if __name__=="__main__":
    import sys
    try: monitor(int(sys.argv[1]) if len(sys.argv)>1 else 300, int(sys.argv[2]) if len(sys.argv)>2 else 1000)
    except KeyboardInterrupt: print("\n⚠️  Stopped")
