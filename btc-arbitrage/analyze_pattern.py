#!/usr/bin/env python3
import re

# Parse log
with open('/workspace/btc-arbitrage/logs/paper_trade.log', 'r') as f:
    lines = f.readlines()

# Find potential windows (BRTI moved >0.2%, Kalshi <0.1%)
windows = []
near_misses = []

for line in lines:
    match = re.search(r'\[(\d+)s\] BRTI: \$[\d,.]+ \(([^)]+)\) \| Kalshi: ([\d.]+)/([\d.]+) \(([^)]+)\)', line)
    if not match:
        continue
    
    time_s = int(match.group(1))
    brti_chg = match.group(2)
    kalshi_chg = match.group(5)
    
    if brti_chg == 'N/A' or kalshi_chg == 'N/A':
        continue
    
    try:
        brti_pct = float(brti_chg.strip('%'))
        kalshi_pct = float(kalshi_chg.strip('%'))
    except:
        continue
    
    # Window condition
    if abs(brti_pct) > 0.2 and abs(kalshi_pct) < 0.1:
        windows.append({
            'time': time_s,
            'brti': brti_pct,
            'kalshi': kalshi_pct,
        })
    
    # Near miss (BRTI>0.2% but Kalshi also moved)
    if abs(brti_pct) > 0.2:
        near_misses.append({
            'time': time_s,
            'brti': brti_pct,
            'kalshi': kalshi_pct,
        })

print("=== 策略分析 ===\n")
print(f"总数据点: {len([l for l in lines if 'BRTI:' in l])}")
print(f"触发窗口 (BRTI>0.2% & Kalshi<0.1%): {len(windows)}")
print(f"BRTI大波动 (>0.2%): {len(near_misses)}")
print()

if windows:
    print("✅ 触发窗口:")
    for w in windows[:10]:
        print(f"  [{w['time']:4d}s] BRTI: {w['brti']:+.3f}%, Kalshi: {w['kalshi']:+.2f}%")
else:
    print("❌ 未触发任何交易窗口")

print()
print("📊 BRTI大波动时Kalshi反应:")
for nm in near_misses[:15]:
    print(f"  [{nm['time']:4d}s] BRTI: {nm['brti']:+.3f}% → Kalshi: {nm['kalshi']:+.2f}%")

print()
print("=== 结论 ===")
if len(windows) == 0:
    print("⚠️  策略条件过严：Kalshi波动远大于BRTI，从未出现滞后窗口")
    print("💡 建议：调整策略或收集更多数据验证假设")
