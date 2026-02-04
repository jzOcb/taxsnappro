#!/bin/bash
# 包装脚本：生成报告并直接发送

# 生成报告
REPORT=$(bash /home/clawdbot/clawd/btc-arbitrage/scripts/hourly_report.sh 2>&1)

# 保存到临时文件
echo "$REPORT" > /tmp/btc_hourly_report.txt

# 标记给heartbeat检测
touch /tmp/btc_hourly_report_ready.flag

# 使用 message 工具发送消息
message action=send \
    channel=telegram \
    to="-1003548880054" \
    message="📊 BTC 交易策略 v3 - 每小时详细报告：

$REPORT

📊 本报告提供全面的交易洞察。"

# 输出报告以保留日志
echo "$REPORT"