#!/usr/bin/env python3
"""
校验并修复 STATUS.md 格式
检测格式错误，自动修复或报告
"""

import sys
import re
from pathlib import Path
from datetime import datetime

REQUIRED_SECTIONS = [
    ("项目名", r'^#\s*STATUS\.md\s*—\s*(.+)$'),
    ("更新时间", r'^Last updated:\s*(.+)$'),
    ("当前状态", r'^##\s*当前状态[：:]\s*(.+)$'),
    ("最后做了什么", r'^##\s*最后做了什么'),
    ("Blockers", r'^##\s*Blockers'),
    ("下一步", r'^##\s*下一步'),
]

def validate_status(file_path):
    """校验STATUS.md格式，返回(is_valid, errors, warnings)"""
    if not Path(file_path).exists():
        return False, [f"文件不存在: {file_path}"], []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    errors = []
    warnings = []
    
    # 检查必需章节
    for section_name, pattern in REQUIRED_SECTIONS:
        if not re.search(pattern, content, re.MULTILINE):
            errors.append(f"缺少必需章节: {section_name} (正则: {pattern})")
    
    # 检查项目名格式
    if not re.search(r'^#\s*STATUS\.md\s*—\s*\S+', content, re.MULTILINE):
        errors.append("第一行格式错误，应为: # STATUS.md — 项目名")
    
    # 检查更新时间格式
    updated_match = re.search(r'^Last updated:\s*(.+)$', content, re.MULTILINE)
    if updated_match:
        timestamp = updated_match.group(1).strip()
        if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z?$', timestamp):
            warnings.append(f"时间戳格式不标准: {timestamp} (建议: YYYY-MM-DDTHH:MMZ)")
    
    # 检查状态是否为标准值
    status_match = re.search(r'^##\s*当前状态[：:]\s*(.+)$', content, re.MULTILINE)
    if status_match:
        status = status_match.group(1).strip()
        # 移除emoji
        status_clean = re.sub(r'[^\u4e00-\u9fa5]', '', status)
        valid_statuses = ['进行中', '卡住', '完成', '规划中', '未开始']
        if not any(s in status_clean for s in valid_statuses):
            warnings.append(f"状态值不标准: {status} (建议: 进行中/卡住/完成/规划中)")
    
    is_valid = len(errors) == 0
    return is_valid, errors, warnings

def auto_fix_status(file_path):
    """尝试自动修复常见格式问题"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed = False
    
    # 修复第一行（如果不是标准格式）
    if lines and not re.match(r'^#\s*STATUS\.md\s*—\s*', lines[0]):
        # 尝试提取项目名
        first_line = lines[0].strip()
        if first_line.startswith('#'):
            project_name = re.sub(r'^#+\s*', '', first_line)
            project_name = re.sub(r'\s*-\s*Project Status$', '', project_name, flags=re.IGNORECASE)
            project_name = re.sub(r'\s*Status$', '', project_name, flags=re.IGNORECASE)
            lines[0] = f"# STATUS.md — {project_name}\n"
            fixed = True
    
    if fixed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    
    return False

def scan_and_validate_all(workspace='/workspace'):
    """扫描所有STATUS.md并验证"""
    status_files = Path(workspace).glob('*/STATUS.md')
    results = []
    
    for status_file in status_files:
        is_valid, errors, warnings = validate_status(status_file)
        results.append({
            'file': str(status_file),
            'project': status_file.parent.name,
            'valid': is_valid,
            'errors': errors,
            'warnings': warnings
        })
    
    return results

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fix':
        # 自动修复模式
        results = scan_and_validate_all()
        fixed_count = 0
        for r in results:
            if not r['valid']:
                if auto_fix_status(r['file']):
                    print(f"✅ 已修复: {r['project']}")
                    fixed_count += 1
                else:
                    print(f"❌ 无法自动修复: {r['project']}")
                    for err in r['errors']:
                        print(f"   - {err}")
        
        if fixed_count > 0:
            print(f"\n✅ 共修复 {fixed_count} 个文件，重新验证中...")
            results = scan_and_validate_all()
    
    # 验证并报告
    results = scan_and_validate_all()
    
    invalid_count = sum(1 for r in results if not r['valid'])
    warning_count = sum(len(r['warnings']) for r in results)
    
    if invalid_count == 0 and warning_count == 0:
        print(f"✅ 所有 {len(results)} 个STATUS.md格式正确")
        sys.exit(0)
    else:
        print(f"⚠️  发现问题: {invalid_count} 个错误, {warning_count} 个警告\n")
        
        for r in results:
            if not r['valid'] or r['warnings']:
                print(f"📁 {r['project']}/STATUS.md")
                for err in r['errors']:
                    print(f"  ❌ {err}")
                for warn in r['warnings']:
                    print(f"  ⚠️  {warn}")
                print()
        
        sys.exit(1 if invalid_count > 0 else 0)
