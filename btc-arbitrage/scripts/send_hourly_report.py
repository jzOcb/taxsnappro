#!/usr/bin/env python3
"""
BTC 每小时报告发送脚本
使用 message 工具发送通知
"""

import os
import sys
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/home/clawdbot/clawd/btc_hourly_report.log'
)

def generate_report():
    """生成BTC策略报告"""
    report_script = "/home/clawdbot/clawd/btc-arbitrage/scripts/hourly_report.sh"
    
    try:
        # 执行报告生成脚本
        with os.popen(f"bash {report_script}") as pipe:
            report = pipe.read()
        
        # 保存到临时文件
        with open("/tmp/btc_hourly_report.txt", "w") as f:
            f.write(report)
        
        # 标记给heartbeat检测
        open("/tmp/btc_hourly_report_ready.flag", "w").close()
        
        return report
    except Exception as e:
        logging.error(f"生成报告失败: {e}")
        return None

def send_report(report):
    """发送报告"""
    if not report:
        logging.error("无法发送空报告")
        return
    
    try:
        from message import send
        send(
            action="send", 
            channel="telegram", 
            to="-1003548880054", 
            message=f"📊 BTC 交易策略 v3 - 每小时详细报告：\n\n{report}\n\n📊 本报告提供全面的交易洞察。"
        )
        logging.info("报告发送成功")
    except ImportError:
        # 如果导入失败，使用系统命令
        os.system(f"message action=send channel=telegram to=-1003548880054 message='📊 BTC 交易策略 v3 - 每小时详细报告：\n\n{report}\n\n📊 本报告提供全面的交易洞察。'")

def main():
    report = generate_report()
    send_report(report)

if __name__ == "__main__":
    main()