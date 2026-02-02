#!/usr/bin/env python3
"""
Git 安全推送工具 (1Password 集成版)

特性：
- 自动检测并屏蔽敏感 Token
- 通过 1Password CLI 管理 GitHub 凭证
- 安全过滤 Git 提交内容
"""

import os
import re
import subprocess
import logging
from typing import List, Dict, Pattern

class GitSafePusher:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.logger = self._setup_logger()
        self.sensitive_patterns = self._compile_patterns()

    def _setup_logger(self):
        """配置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='/home/clawdbot/clawd/logs/git_safe_push.log',
            filemode='a'
        )
        return logging.getLogger('GitSafePusher')

    def _compile_patterns(self) -> Dict[str, Pattern]:
        """编译敏感信息正则模式"""
        return {
            'notion_token': re.compile(r'secret_\w{48}', re.IGNORECASE),
            'github_token': re.compile(r'ghp_\w{36}', re.IGNORECASE),
            'openai_token': re.compile(r'sk-\w{48}', re.IGNORECASE),
            'stripe_token': re.compile(r'sk_live_\w{24}', re.IGNORECASE),
            'aws_token': re.compile(r'AKIA[0-9A-Z]{16}', re.IGNORECASE),
        }

    def mask_file_content(self, file_path: str) -> bool:
        """
        屏蔽文件中的敏感信息
        如果文件包含敏感信息，返回 True
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            modified = False
            for name, pattern in self.sensitive_patterns.items():
                if pattern.search(content):
                    # 替换敏感信息为 [REDACTED-{token_type}]
                    content = pattern.sub(f'[REDACTED-{name}]', content)
                    modified = True
                    self.logger.warning(f"在 {file_path} 中屏蔽了 {name} 类型的敏感信息")
            
            if modified:
                with open(file_path, 'w') as f:
                    f.write(content)
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"处理文件 {file_path} 时出错: {e}")
            return False

    def scan_repo(self) -> List[str]:
        """
        扫描仓库中所有文件，屏蔽敏感信息
        返回被修改的文件列表
        """
        modified_files = []
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                if self.mask_file_content(file_path):
                    modified_files.append(file_path)
        
        return modified_files

    def configure_github_token(self):
        """
        通过 1Password CLI 配置 GitHub Token
        """
        try:
            subprocess.run([
                'python3', 
                '/home/clawdbot/clawd/scripts/github_token_manager.py'
            ], check=True)
            self.logger.info("GitHub Token 配置成功")
            return True
        except Exception as e:
            self.logger.error(f"GitHub Token 配置失败: {e}")
            return False

    def git_commit_and_push(self, message: str):
        """
        执行 Git 提交和推送
        """
        try:
            os.chdir(self.repo_path)
            
            # 配置 GitHub Token
            if not self.configure_github_token():
                raise Exception("GitHub Token 配置失败")
            
            # 扫描并屏蔽敏感信息
            modified_files = self.scan_repo()
            
            if not modified_files:
                self.logger.info("未发现敏感信息，直接推送")
                subprocess.run(['git', 'add', '.'], check=True)
                subprocess.run(['git', 'commit', '-m', message], check=True)
                subprocess.run(['op', 'run', '--', 'git', 'push'], check=True)
                return
            
            # 如果有修改，额外记录
            modified_msg = f"{message}\n\n屏蔽的敏感文件:\n" + "\n".join(modified_files)
            
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', modified_msg], check=True)
            subprocess.run(['op', 'run', '--', 'git', 'push'], check=True)
            
            self.logger.info(f"成功推送，屏蔽了 {len(modified_files)} 个文件中的敏感信息")
        
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git 操作失败: {e}")
            raise
        except Exception as e:
            self.logger.error(f"推送过程中发生错误: {e}")
            raise

def main():
    pusher = GitSafePusher('/home/clawdbot/clawd')
    pusher.git_commit_and_push("Heartbeat 系统重构：自动屏蔽敏感信息 (1Password 集成)")

if __name__ == '__main__':
    main()