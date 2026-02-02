#!/usr/bin/env python3
"""
解析 STATUS.md 文件，提取项目状态信息
输出JSON格式，方便shell脚本处理
"""

import sys
import json
import re
from pathlib import Path

def parse_status_file(file_path):
    """解析单个STATUS.md文件"""
    if not Path(file_path).exists():
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取项目名（第一行）
    project_name_match = re.search(r'^#\s*STATUS\.md\s*—\s*(.+)$', content, re.MULTILINE)
    project_name = project_name_match.group(1).strip() if project_name_match else "未命名项目"
    
    # 提取最后更新时间
    last_updated_match = re.search(r'Last updated:\s*(.+)$', content, re.MULTILINE)
    last_updated = last_updated_match.group(1).strip() if last_updated_match else ""
    
    # 提取当前状态（支持emoji和中文）
    status_match = re.search(r'##\s*当前状态[：:]\s*(.+)$', content, re.MULTILINE)
    status_raw = status_match.group(1).strip() if status_match else "未知"
    
    # 映射状态到kanban列名
    status_mapping = {
        '进行中': '进行中',
        '卡住': '暂停',
        '完成': '完成',
        '规划中': 'TODO',
        '未开始': 'TODO',
    }
    
    # 清理emoji，提取中文状态
    status_clean = re.sub(r'[^\u4e00-\u9fa5]', '', status_raw)
    kanban_column = 'TODO'  # 默认
    for key, value in status_mapping.items():
        if key in status_clean:
            kanban_column = value
            break
    
    # 提取"最后做了什么"
    last_work_match = re.search(r'##\s*最后做了什么\s*\n(.*?)(?=##|$)', content, re.DOTALL)
    last_work = last_work_match.group(1).strip() if last_work_match else ""
    
    # 提取Blockers
    blockers_match = re.search(r'##\s*Blockers\s*\n(.*?)(?=##|$)', content, re.DOTALL)
    blockers = blockers_match.group(1).strip() if blockers_match else ""
    
    # 提取下一步
    next_steps_match = re.search(r'##\s*下一步\s*\n(.*?)(?=##|$)', content, re.DOTALL)
    next_steps = next_steps_match.group(1).strip() if next_steps_match else ""
    
    return {
        'project_name': project_name,
        'project_dir': Path(file_path).parent.name,
        'last_updated': last_updated,
        'status_raw': status_raw,
        'kanban_column': kanban_column,
        'last_work': last_work[:200],
        'blockers': blockers[:200],
        'next_steps': next_steps[:200],
        'status_file': str(file_path)
    }

def scan_workspace(workspace_path='/workspace'):
    """扫描workspace所有STATUS.md"""
    status_files = Path(workspace_path).glob('*/STATUS.md')
    projects = []
    
    for status_file in status_files:
        parsed = parse_status_file(status_file)
        if parsed:
            projects.append(parsed)
    
    return projects

if __name__ == '__main__':
    if len(sys.argv) > 1:
        result = parse_status_file(sys.argv[1])
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({'error': 'File not found or invalid'}, ensure_ascii=False))
            sys.exit(1)
    else:
        projects = scan_workspace()
        print(json.dumps(projects, ensure_ascii=False, indent=2))
