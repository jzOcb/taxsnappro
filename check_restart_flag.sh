#!/bin/bash
# Check if processes were auto-restarted

has_alert=0

# Check v3 restart flag
if [ -f /tmp/rt_v3_restart.flag ]; then
    info=$(cat /tmp/rt_v3_restart.flag)
    restart_time=$(echo "$info" | cut -d'|' -f1)
    pid=$(echo "$info" | cut -d'|' -f2)
    attempt=$(echo "$info" | cut -d'|' -f3)
    
    echo "🔄 **BTC Arbitrage v3 自动重启**"
    echo ""
    echo "重启时间: $(date -d @$restart_time '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r $restart_time '+%Y-%m-%d %H:%M:%S')"
    echo "PID: $pid | 重启次数: $((attempt+1))"
    echo ""
    
    if ps -p $pid > /dev/null 2>&1; then
        echo "✅ 进程运行中"
        ps -p $pid -o etime,cmd --no-headers
    else
        echo "❌ 进程已停止"
    fi
    
    has_alert=1
fi

# Check old restart flag (v1/v2)
if [ -f /tmp/btc_arbitrage_restarted.flag ]; then
    if [ $has_alert -eq 1 ]; then echo ""; fi
    RESTART_TIME=$(cat /tmp/btc_arbitrage_restarted.flag)
    echo "⚠️ **BTC Arbitrage (旧版) 自动重启**"
    echo ""
    echo "重启时间: $RESTART_TIME"
    
    rm /tmp/btc_arbitrage_restarted.flag
    has_alert=1
fi

# Check hourly report flag
if [ -f /tmp/btc_hourly_report_ready.flag ]; then
    if [ $has_alert -eq 1 ]; then echo ""; echo "---"; echo ""; fi
    
    if [ -f /tmp/btc_hourly_report.txt ]; then
        cat /tmp/btc_hourly_report.txt
        rm -f /tmp/btc_hourly_report.txt /tmp/btc_hourly_report_ready.flag
        has_alert=1
    else
        echo "⚠️ Hourly report flag存在但找不到报告文件"
        rm -f /tmp/btc_hourly_report_ready.flag
        has_alert=1
    fi
fi

if [ $has_alert -eq 0 ]; then
    echo "HEARTBEAT_OK"
fi
