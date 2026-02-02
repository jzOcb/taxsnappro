#!/usr/bin/env python3
"""
GitHub Token 安全管理工具

特性：
- 通过 1Password CLI 管理 GitHub Token
- 安全获取和轮换 Token
- 集成 Git 推送工作流
"""

import os
import subprocess
import logging
from typing import Optional

class GitHubTokenManager:
    def __init__(self, 
                 vault: str = "Private", 
                 token_item: str = "GitHub Personal Access Token"):
        self.vault = vault
        self.token_item = token_item
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """配置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='/home/clawdbot/clawd/logs/github_token_manager.log',
            filemode='a'
        )
        return logging.getLogger('GitHubTokenManager')

    def _run_op_command(self, command: list) -> str:
        """
        执行 1Password CLI 命令
        """
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"1Password CLI 命令失败: {e}")
            self.logger.error(f"错误输出: {e.stderr}")
            raise

    def get_github_token(self) -> Optional[str]:
        """
        从 1Password 获取 GitHub Token
        """
        try:
            token = self._run_op_command([
                'op', 'item', 'get', 
                self.token_item, 
                '--vault', self.vault, 
                '--fields', 'password'
            ])
            
            # 基本验证
            if not token or len(token) < 20:
                self.logger.warning("获取的 Token 看起来不正确")
                return None
            
            self.logger.info("成功获取 GitHub Token")
            return token
        
        except Exception as e:
            self.logger.error(f"获取 GitHub Token 失败: {e}")
            return None

    def rotate_github_token(self) -> bool:
        """
        轮换 GitHub Token
        注意：实际轮换需要在 GitHub 网站手动操作
        """
        try:
            # 生成新 Token 的占位逻辑
            new_token = subprocess.check_output([
                'openssl', 'rand', '-hex', '20'
            ]).decode().strip()
            
            # 更新 1Password 中的 Token
            self._run_op_command([
                'op', 'item', 'edit', 
                self.token_item, 
                '--vault', self.vault,
                f'password={new_token}'
            ])
            
            self.logger.info("GitHub Token 已在 1Password 中更新")
            return True
        
        except Exception as e:
            self.logger.error(f"Token 轮换失败: {e}")
            return False

    def configure_git_credential(self) -> bool:
        """
        配置 Git 使用获取的 Token
        """
        try:
            token = self.get_github_token()
            if not token:
                return False
            
            # 配置 Git 凭证助手
            subprocess.run([
                'git', 'config', '--global', 
                'credential.helper', 
                '!op run -- git credential fill'
            ], check=True)
            
            # 设置远程仓库 URL
            subprocess.run([
                'git', 'config', '--global', 
                'url."https://oauth2:{token}@github.com".insteadOf'.format(token=token),
                'https://github.com'
            ], check=True)
            
            self.logger.info("Git 凭证配置成功")
            return True
        
        except Exception as e:
            self.logger.error(f"Git 凭证配置失败: {e}")
            return False

def main():
    token_manager = GitHubTokenManager()
    
    # 配置 Git 凭证
    if token_manager.configure_git_credential():
        print("GitHub Token 管理已就绪")
    else:
        print("GitHub Token 管理配置失败")

if __name__ == '__main__':
    main()