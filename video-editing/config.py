#!/usr/bin/env python3
"""配置文件"""
import os

# 火山引擎API配置
VOLCENGINE_API_KEY = os.getenv('VOLCENGINE_API_KEY', '')
VOLCENGINE_APPID = os.getenv('VOLCENGINE_APPID', '')

# 输出目录
OUTPUT_DIR = 'output'

# 审核界面端口
WEB_SERVER_PORT = 5678

# 识别参数
MIN_SILENCE_DURATION = 1.0  # 最小静音时长（秒）
FILLER_WORDS = ['嗯', '啊', '呃', '额', '那个', '就是', '然后']
PAUSE_WORDS = ['呃', '额', '嗯嗯', '啊啊']
