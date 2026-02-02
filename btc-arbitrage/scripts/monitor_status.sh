#!/bin/bash
# Monitor status checker - shows all running monitors

echo "======================================================================"
echo "BTC ARBITRAGE MONITORING STATUS"
echo "======================================================================"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S UTC')"
echo ""

echo "📊 ACTIVE MONITORS:"
echo ""

# Check for Python processes
ps aux | grep -E "continuous_monitor|settlement_tracker|websocket_monitor" | grep -v grep | while read line; do
    pid=$(echo $line | awk '{print $2}')
    cmd=$(echo $line | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')
    echo "  PID $pid: $cmd"
done

echo ""
echo "📁 DATA COLLECTED:"
echo ""

# Count data files
if [ -d "data" ]; then
    continuous_count=$(ls data/continuous_*.json 2>/dev/null | wc -l)
    signals_count=$(ls data/signals_*.json 2>/dev/null | wc -l)
    settlements=$(ls data/settlements.json 2>/dev/null | wc -l)
    
    echo "  Continuous monitoring runs: $continuous_count"
    echo "  Signal detection runs: $signals_count"
    echo "  Settlements tracked: $settlements"
    
    # Show latest files
    echo ""
    echo "  Latest files:"
    ls -lth data/*.json 2>/dev/null | head -5 | awk '{print "    "$9" ("$5", "$6" "$7" "$8")"}'
fi

echo ""
echo "📈 QUICK STATS:"
echo ""

# If we have any signal files, show count
if [ -f "data/signals_"*.json ]; then
    latest_sig=$(ls -t data/signals_*.json 2>/dev/null | head -1)
    if [ -n "$latest_sig" ]; then
        sig_count=$(cat "$latest_sig" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null)
        echo "  Signals in latest run: ${sig_count:-0}"
    fi
fi

# Settlement count
if [ -f "data/settlements.json" ]; then
    settle_count=$(cat data/settlements.json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null)
    echo "  Settlements validated: ${settle_count:-0}"
fi

echo ""
echo "======================================================================"
