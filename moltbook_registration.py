#!/usr/bin/env python3
"""
Moltbook Agent Registration Script
使用 Sonnet 模型处理更复杂的注册逻辑
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/home/clawdbot/clawd/moltbook_registration.log'
)

def check_registration_eligibility():
    """检查是否可以进行注册"""
    cooldown_end = datetime(2026, 2, 2, 12, 41)
    current_time = datetime.now()
    
    if current_time < cooldown_end:
        logging.info(f"当前处于冷却期，距离可注册还有 {cooldown_end - current_time}")
        return False
    return True

def register_agent():
    """注册 agent"""
    agent_name = "jz-agent"
    api_url = "https://www.moltbook.com/api/v1/agents/register"
    
    # 从环境变量读取敏感信息
    api_key = os.getenv('MOLTBOOK_API_KEY')
    if not api_key:
        logging.error("未找到 MOLTBOOK_API_KEY")
        return None
    
    try:
        response = requests.post(api_url, json={
            'name': agent_name,
            'api_key': api_key
        }, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        })
        
        if response.status_code == 200:
            registration_data = response.json()
            claim_url = registration_data.get('claim_url')
            
            # 使用 sessions_spawn 发送通知，指定 Sonnet 模型
            notification = f"Moltbook Agent 注册成功！\nClaim URL: {claim_url}"
            os.system(f"clawdbot sessions_spawn --task 'Moltbook Registration' --model 'anthropic/claude-3-sonnet-20k' --message '{notification}'")
            
            return claim_url
        else:
            logging.error(f"注册失败：{response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logging.error(f"注册过程中发生错误: {e}")
        return None

def main():
    if check_registration_eligibility():
        claim_url = register_agent()
        if claim_url:
            logging.info(f"成功获取 Claim URL: {claim_url}")
    else:
        logging.info("当前不满足注册条件")

if __name__ == '__main__':
    main()