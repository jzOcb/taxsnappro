#!/bin/bash

# Heartbeat Scheduler 测试脚本
echo "=== 开始 Heartbeat Scheduler 测试 ==="
date

# 测试 Python 调度器
echo "--- 运行调度器 ---"
python3 /workspace/heartbeat_scheduler.py

# 检查日志文件
echo "--- 最近日志 ---"
tail -n 20 /home/clawdbot/clawd/heartbeat.log

# 检查状态文件
echo "--- 状态文件 ---"
cat /workspace/heartbeat_state.json

echo "=== Heartbeat Scheduler 测试完成 ==="
