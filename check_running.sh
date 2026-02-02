#!/bin/bash
echo "=== 进程检查 ==="
pgrep -fa "monitor_overnight\|paper_trade_overnight" || echo "没有找到进程"
echo ""
echo "=== 最新数据文件 ==="
ls -lht /workspace/btc-arbitrage/data/ | head -5
