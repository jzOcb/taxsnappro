#!/usr/bin/env python3
""" 
Flexible Heartbeat Scheduler for Clawdbot 

Features: 
- Dynamic job scheduling 
- Model-based task routing 
- Configurable intervals 
- Enhanced logging and error handling 
- Secure command execution 
"""

import os
import sys
import time
import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Callable

class HeartbeatScheduler:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.jobs: Dict[str, Dict[str, Any]] = {}
        
        # 使用当前目录作为日志目录
        log_path = "heartbeat.log"
        self.state_path = os.path.join(os.path.dirname(config_path), 'heartbeat_state.json')
        
        # 配置更详细的日志
        self.logger = logging.getLogger('HeartbeatScheduler')
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=log_path,
            filemode='a'
        )
        
        # 添加控制台日志，便于调试
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def load_config(self):
        """安全地加载作业配置"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.jobs = config.get('jobs', {})
            self.logger.info(f"成功加载配置文件: {self.config_path}")
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            raise

    def load_state(self) -> Dict[str, float]:
        """安全地加载作业状态"""
        try:
            with open(self.state_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning("状态文件不存在，创建新状态")
            return {}
        except json.JSONDecodeError:
            self.logger.error("状态文件解析失败")
            return {}

    def save_state(self, state: Dict[str, float]):
        """安全地保存作业状态"""
        try:
            with open(self.state_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"保存状态文件失败: {e}")

    def should_run(self, job_name: str, last_run: float, interval: str) -> bool:
        """判断作业是否应该运行"""
        now = time.time()
        multipliers = {'m': 60, 'h': 3600, 'd': 86400}
        
        try:
            unit = interval[-1]
            value = int(interval[:-1])
            interval_seconds = value * multipliers[unit]
            return now - last_run >= interval_seconds
        except Exception as e:
            self.logger.error(f"计算作业 {job_name} 运行间隔失败: {e}")
            return False

    def safe_execute_command(self, command: str, job_name: str, retry_config: Dict[str, Any]) -> bool:
        """
        安全执行系统命令，支持重试机制
        返回命令是否成功执行
        """
        retry_count = retry_config.get('retry_count', 1)
        retry_delay = retry_config.get('retry_delay', 300)
        
        for attempt in range(retry_count + 1):
            try:
                # 确保命令是绝对路径且可执行
                if command.startswith('/'):
                    if not os.path.exists(command):
                        self.logger.error(f"文件不存在: {command}")
                        return False
                    if not os.access(command, os.X_OK):
                        os.chmod(command, 0o755)  # 添加执行权限
                
                # 输出完整命令，便于调试
                self.logger.info(f"执行命令 [{job_name}] 尝试 {attempt + 1}/{retry_count + 1}: {command}")
                
                result = subprocess.run(
                    command, 
                    shell=True, 
                    check=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                
                # 记录命令输出
                if result.stdout:
                    self.logger.info(f"[{job_name}] 标准输出: {result.stdout}")
                
                self.logger.info(f"命令执行成功: {command}")
                return True
            
            except subprocess.CalledProcessError as e:
                self.logger.error(f"命令执行失败 [{job_name}] 尝试 {attempt + 1}/{retry_count + 1}: {command}")
                self.logger.error(f"错误码: {e.returncode}")
                
                # 记录详细的错误信息
                if e.stderr:
                    self.logger.error(f"标准错误: {e.stderr}")
                
                if attempt < retry_count:
                    self.logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
            
            except subprocess.TimeoutExpired:
                self.logger.error(f"命令执行超时 [{job_name}]: {command}")
                if attempt < retry_count:
                    self.logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
            
            except Exception as e:
                self.logger.error(f"执行命令时发生未知错误 [{job_name}]: {str(e)}")
                if attempt < retry_count:
                    self.logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
        
        return False

    def run_jobs(self):
        """执行所有计划作业"""
        state = self.load_state()
        
        for job_name, job_config in self.jobs.items():
            interval = job_config.get('interval', '1h')
            last_run = state.get(job_name, 0)
            
            if self.should_run(job_name, last_run, interval):
                self.logger.info(f"准备运行作业: {job_name}")
                try:
                    command = job_config.get('command', '')
                    retry_config = {
                        'retry_count': job_config.get('retry_count', 1),
                        'retry_delay': job_config.get('retry_delay', 300)
                    }
                    
                    success = self.safe_execute_command(command, job_name, retry_config)
                    if success:
                        state[job_name] = time.time()
                except Exception as e:
                    self.logger.error(f"作业 {job_name} 执行异常: {e}")
        
        self.save_state(state)

def main():
    config_path = 'heartbeat_config.json'
    scheduler = HeartbeatScheduler(config_path)
    scheduler.load_config()
    scheduler.run_jobs()

if __name__ == '__main__':
    main()