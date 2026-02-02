#!/usr/bin/env python3
"""
Notion ↔ 本地选题双向同步
- Notion → 本地：从Notion拉取新/更新的选题
- 本地 → Notion：把本地记录的选题推送到Notion
"""

import os
import json
from datetime import datetime
from pathlib import Path

API_KEY = os.getenv('NOTION_API_KEY')  # Set via environment variable
DATABASE_ID = '2faa9d04-3b40-81c7-a39d-c5271357cfe9'
NOTION_VERSION = '2022-06-28'

BASE_DIR = Path(__file__).parent.parent
LOCAL_IDEAS_FILE = BASE_DIR / '01-选题/想法记录.md'
SYNC_STATE_FILE = BASE_DIR / '.notion_sync_state.json'

def load_sync_state():
    """加载上次同步状态"""
    if SYNC_STATE_FILE.exists():
        with open(SYNC_STATE_FILE) as f:
            return json.load(f)
    return {'last_sync': None, 'notion_pages': {}}

def save_sync_state(state):
    """保存同步状态"""
    with open(SYNC_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def notion_request(method, endpoint, data=None):
    """发送Notion API请求"""
    import subprocess
    
    url = f"https://api.notion.com/v1/{endpoint}"
    headers = [
        f"Authorization: Bearer {API_KEY}",
        f"Notion-Version: {NOTION_VERSION}",
        "Content-Type: application/json"
    ]
    
    cmd = ['curl', '-s', '-X', method, url]
    for h in headers:
        cmd.extend(['-H', h])
    if data:
        cmd.extend(['-d', json.dumps(data)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    
    try:
        return json.loads(result.stdout)
    except:
        print(f"Failed to parse JSON: {result.stdout[:200]}")
        return None

def fetch_notion_ideas():
    """从Notion拉取所有选题"""
    data = notion_request('POST', f'databases/{DATABASE_ID}/query', {
        'sorts': [{'property': '创建日期', 'direction': 'descending'}]
    })
    
    if not data or 'results' not in data:
        print("Failed to fetch Notion database")
        return []
    
    ideas = []
    for page in data['results']:
        props = page['properties']
        
        # 提取各个字段
        title = props.get('选题标题', {}).get('title', [{}])[0].get('plain_text', '')
        direction = props.get('选题方向', {}).get('select', {}).get('name', '')
        description = ''.join([t['plain_text'] for t in props.get('想法描述', {}).get('rich_text', [])])
        status = props.get('状态', {}).get('select', {}).get('name', '')
        priority = props.get('优先级', {}).get('select', {}).get('name', '')
        products = ''.join([t['plain_text'] for t in props.get('相关产品', {}).get('rich_text', [])])
        created = props.get('创建日期', {}).get('created_time', '')
        
        ideas.append({
            'id': page['id'],
            'title': title,
            'direction': direction,
            'description': description,
            'status': status,
            'priority': priority,
            'products': products,
            'created': created
        })
    
    return ideas

def sync_notion_to_local():
    """Notion → 本地同步"""
    print("📥 从Notion拉取选题...")
    
    ideas = fetch_notion_ideas()
    if not ideas:
        print("没有找到选题")
        return
    
    state = load_sync_state()
    
    # 读取本地文件
    if LOCAL_IDEAS_FILE.exists():
        with open(LOCAL_IDEAS_FILE) as f:
            local_content = f.read()
    else:
        local_content = "# 想法记录 — 碎片想法收集箱\n\n> 有什么选题想法？随时记下来。\n> 格式：日期 | 选题方向 | 简要描述\n\n---\n\n"
    
    # 添加新的想法
    new_count = 0
    for idea in ideas:
        if idea['id'] not in state['notion_pages']:
            # 新选题，添加到本地
            date = idea['created'][:10] if idea['created'] else datetime.now().strftime('%Y-%m-%d')
            line = f"\n## {date} - {idea['title']}\n"
            line += f"- 方向: {idea['direction']}\n"
            if idea['description']:
                line += f"- 描述: {idea['description']}\n"
            if idea['products']:
                line += f"- 产品: {idea['products']}\n"
            line += f"- 状态: {idea['status']} | 优先级: {idea['priority']}\n"
            line += f"- Notion ID: {idea['id']}\n"
            
            local_content += line
            state['notion_pages'][idea['id']] = idea['title']
            new_count += 1
    
    # 保存
    with open(LOCAL_IDEAS_FILE, 'w') as f:
        f.write(local_content)
    
    state['last_sync'] = datetime.now().isoformat()
    save_sync_state(state)
    
    print(f"✅ 同步完成！新增 {new_count} 条选题")

def create_notion_idea(title, direction='', description='', priority='⚡中'):
    """创建Notion选题"""
    print(f"📤 推送到Notion: {title}")
    
    properties = {
        '选题标题': {'title': [{'text': {'content': title}}]},
        '状态': {'select': {'name': '💡想法'}}
    }
    
    if direction:
        properties['选题方向'] = {'select': {'name': direction}}
    if description:
        properties['想法描述'] = {'rich_text': [{'text': {'content': description}}]}
    if priority:
        properties['优先级'] = {'select': {'name': priority}}
    
    data = notion_request('POST', 'pages', {
        'parent': {'database_id': DATABASE_ID},
        'properties': properties
    })
    
    if data and 'id' in data:
        print(f"✅ 创建成功！Notion ID: {data['id']}")
        
        # 更新sync state
        state = load_sync_state()
        state['notion_pages'][data['id']] = title
        save_sync_state(state)
        
        return data['id']
    else:
        print("❌ 创建失败")
        return None

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'pull':
            sync_notion_to_local()
        elif cmd == 'push' and len(sys.argv) > 2:
            title = sys.argv[2]
            direction = sys.argv[3] if len(sys.argv) > 3 else ''
            description = sys.argv[4] if len(sys.argv) > 4 else ''
            create_notion_idea(title, direction, description)
        else:
            print("Usage: notion_sync.py [pull|push <title> [direction] [description]]")
    else:
        # 默认pull
        sync_notion_to_local()
