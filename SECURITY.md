# SECURITY.md — Secrets管理标准

**所有sessions、agents和项目必须遵守此标准**

## 🚨 为什么重要

**2026-02-02 Notion Token泄露事故：**
- ❌ Notion API token被硬编码在 `notion_sync.py` 里
- ❌ Commit到git历史（`52f7cb34`）
- ❌ Push到GitHub被secret scanning拦截
- ❌ 需要撤销token、清理git历史、重新配置

**后果：**
- 🔐 Token泄露 = 任何人都能访问你的Notion数据库
- 💰 API滥用 = 可能产生费用
- 🚨 GitHub blocking = push失败，工作流中断
- ⏰ 修复成本 = 浪费大量时间

**这是完全可以避免的错误。**

---

## ✅ 标准方法：环境变量

**唯一批准的方式：从环境变量读取secrets**

### 配置文件位置

```
/opt/clawdbot.env  — 系统级配置（所有sessions共享）
```

**权限要求：**
```bash
chmod 600 /opt/clawdbot.env
chown clawdbot:clawdbot /opt/clawdbot.env
```

### 正确的代码写法

#### Python

```python
import os

# ✅ 正确：只从环境变量读取，无默认值
API_KEY = os.getenv('SERVICE_API_KEY')
if not API_KEY:
    raise ValueError("SERVICE_API_KEY not set. Add to /opt/clawdbot.env")

# ❌ 错误：有默认值（硬编码）
API_KEY = os.getenv('SERVICE_API_KEY', 'sk_live_abc123...')  # 永远不要这样！
```

#### Bash

```bash
# ✅ 正确：source环境变量文件
source /opt/clawdbot.env

if [ -z "$API_KEY" ]; then
    echo "❌ API_KEY not set" >&2
    exit 1
fi

# 使用 $API_KEY
```

#### Node.js

```javascript
// ✅ 正确：从环境变量读取
const API_KEY = process.env.SERVICE_API_KEY;
if (!API_KEY) {
    throw new Error('SERVICE_API_KEY not set. Add to /opt/clawdbot.env');
}

// 使用前验证
```

---

## ❌ 禁止事项

### 1. 硬编码Secrets（绝对禁止）

```python
# ❌ 永远不要这样
API_KEY = "sk_live_abc123xyz..."
NOTION_TOKEN = "ntn_45583973184..."
DATABASE_PASSWORD = "mypassword123"
```

**即使在以下情况也不行：**
- "只是测试代码"
- "这个文件在 .gitignore 里"
- "我待会改"
- "只有我能看到这个repo"

**为什么？**
- 容易忘记删除
- `.gitignore` 不影响已commit的历史
- Private repo也可能意外公开
- 代码可能被复制到其他地方

### 2. 文件内的Secrets

```python
# ❌ 不要从未加密的文件读取
with open('secrets.json') as f:
    secrets = json.load(f)
```

**除非文件：**
- 权限严格（600）
- 在 `.gitignore` 里
- 从环境变量生成（临时使用后删除）

### 3. 日志或输出Secrets

```python
# ❌ 不要记录完整的secret
print(f"API Key: {API_KEY}")
logger.info(f"Token: {token}")

# ✅ 可以记录前几个字符（用于调试）
print(f"API Key: {API_KEY[:8]}...")
logger.info(f"Using token: {token[:12]}***")
```

---

## 📝 添加新Secret的流程

### 1. 获取Secret

从服务提供商获取API key/token

### 2. 添加到环境变量文件

```bash
# SSH到服务器
sudo nano /opt/clawdbot.env

# 添加新行（使用描述性名称）
SERVICE_NAME_API_KEY=your_token_here
DATABASE_PASSWORD=your_password_here

# 保存并确保权限
sudo chmod 600 /opt/clawdbot.env
sudo chown clawdbot:clawdbot /opt/clawdbot.env
```

**命名规范：**
- 大写字母 + 下划线
- 前缀服务名称（如 `NOTION_`, `GITHUB_`, `OPENAI_`）
- 清晰表明用途（`API_KEY`, `TOKEN`, `SECRET`, `PASSWORD`）

### 3. 重启Gateway（如果需要）

```bash
clawdbot gateway restart
```

或者等待下次自动重启（heartbeat/cron会重载环境）

### 4. 在代码中使用

```python
import os

API_KEY = os.getenv('SERVICE_NAME_API_KEY')
if not API_KEY:
    raise ValueError("SERVICE_NAME_API_KEY not set in /opt/clawdbot.env")
```

### 5. 添加到 .gitignore（防御性）

```bash
# .gitignore
.env
*.env
secrets.*
config.json  # 如果包含secrets
```

---

## 🔍 代码审查Checklist

**创建新项目前：**
- [ ] 查看所有代码文件
- [ ] 搜索可能的secrets模式：
  - `sk_`, `ghp_`, `ntn_`, `api_key`, `token`, `password`
  - 长随机字符串（>20字符）
  - Base64编码的数据
- [ ] 确认所有secrets从环境变量读取
- [ ] 确认有验证逻辑（缺失时报错）

**Push到GitHub前：**
```bash
# 扫描secrets（手动检查）
git diff --cached | grep -iE '(token|key|secret|password|api).*=.*["\x27]'

# 如果有匹配，仔细检查！
```

**定期审计：**
```bash
# 搜索可疑的硬编码
cd /workspace
grep -rn --include="*.py" --include="*.js" --include="*.sh" \
  -E '(token|key|secret|password|api).*=.*["'"'"'][a-zA-Z0-9_-]{20,}' .
```

---

## 🔄 迁移现有代码

如果发现硬编码的secrets：

### 步骤1：评估影响

- ✅ Secret已在git历史里？
- ✅ 已push到GitHub/远程？
- ✅ Repo是public还是private？

### 步骤2：立即撤销Secret

去服务提供商：
- 撤销/删除旧的API key/token
- 生成新的替换

**即使repo是private，也要撤销！**

### 步骤3：清理代码

```python
# 之前（硬编码）
API_KEY = "sk_live_abc123xyz"

# 之后（环境变量）
API_KEY = os.getenv('SERVICE_API_KEY')
if not API_KEY:
    raise ValueError("SERVICE_API_KEY not set")
```

### 步骤4：配置环境变量

```bash
sudo bash -c "echo 'SERVICE_API_KEY=新的token' >> /opt/clawdbot.env"
sudo chmod 600 /opt/clawdbot.env
```

### 步骤5：清理Git历史（如果已commit）

```bash
# 使用 git-filter-repo（推荐）或 filter-branch
# 详见 GitHub secret scanning 的指导

# 例子（删除包含secret的文件）
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/file.py" \
  --prune-empty -- --all
```

### 步骤6：Force push

```bash
git push origin main --force
```

---

## 📋 项目模板

**新项目必须包含的文件：**

### `.gitignore`

```gitignore
# Secrets
.env
*.env
.env.*
secrets.*
*_secret.*
credentials.*

# Config files that may contain secrets
config.json
settings.json

# Logs (may contain sensitive data)
*.log
logs/

# Python
__pycache__/
*.pyc

# Node
node_modules/
```

### `README.md`（安全配置部分）

```markdown
## Configuration

This project requires the following environment variables in `/opt/clawdbot.env`:

- `SERVICE_NAME_API_KEY` — API key from Service Name (required)
- `DATABASE_URL` — Database connection string (required)

Never commit secrets to git. See [SECURITY.md](../SECURITY.md) for details.
```

### 代码模板（Python）

```python
#!/usr/bin/env python3
"""
Project Name

Security: All secrets must be in environment variables.
See /workspace/SECURITY.md for standards.
"""

import os
import sys

# Required environment variables
REQUIRED_ENV_VARS = [
    'SERVICE_API_KEY',
    'DATABASE_URL',
]

def validate_environment():
    """Validate all required environment variables are set."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nAdd them to /opt/clawdbot.env and restart.")
        sys.exit(1)

# Run validation on import
validate_environment()

# Now safe to use
API_KEY = os.getenv('SERVICE_API_KEY')
DB_URL = os.getenv('DATABASE_URL')
```

---

## 🎓 教育所有Sessions

**AGENTS.md已更新** — 所有session启动时会读到此标准

**强制规则：**
1. 创建新项目时，必须先读 `SECURITY.md`
2. 写代码前，先配置环境变量
3. Commit前，审查是否有硬编码secrets
4. 发现问题，立即报告并修复

**在spawn sub-agent时提醒：**
```
Task: 创建XYZ项目

⚠️ 安全要求：
- 所有secrets必须从环境变量读取（参考 SECURITY.md）
- 禁止硬编码API keys, tokens, passwords
- 新的环境变量需添加到 /opt/clawdbot.env
```

---

## 🛠 工具和脚本

### 快速检查脚本

```bash
#!/bin/bash
# scripts/check-secrets.sh — 扫描可疑的硬编码secrets

echo "🔍 Scanning for potential hardcoded secrets..."

# 搜索模式
PATTERNS=(
    'api[_-]?key.*=.*["\x27][a-zA-Z0-9_-]{20,}'
    'token.*=.*["\x27][a-zA-Z0-9_-]{20,}'
    'secret.*=.*["\x27][a-zA-Z0-9_-]{20,}'
    'password.*=.*["\x27][^"\x27]+["\x27]'
    'sk_[a-z]+_[a-zA-Z0-9]{24,}'
    'ghp_[a-zA-Z0-9]{36,}'
    'ntn_[a-zA-Z0-9]{36,}'
)

FOUND=0

for pattern in "${PATTERNS[@]}"; do
    results=$(grep -rn -E "$pattern" . \
        --include="*.py" --include="*.js" --include="*.sh" --include="*.ts" \
        --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=__pycache__ \
        2>/dev/null)
    
    if [ -n "$results" ]; then
        echo "⚠️  Found potential secrets:"
        echo "$results"
        FOUND=1
    fi
done

if [ $FOUND -eq 0 ]; then
    echo "✅ No obvious secrets found"
else
    echo ""
    echo "❌ Review the above files before committing!"
fi
```

### Git Pre-commit Hook（可选）

```bash
#!/bin/bash
# .git/hooks/pre-commit
# 阻止commit包含明显secrets的文件

bash scripts/check-secrets.sh
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Commit blocked: potential secrets detected"
    echo "Review your changes and remove hardcoded secrets"
    exit 1
fi
```

---

## 📚 延伸阅读

- GitHub: [Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [git-filter-repo](https://github.com/newren/git-filter-repo) — 推荐的git历史清理工具
- [gitleaks](https://github.com/gitleaks/gitleaks) — 自动扫描secrets
- OWASP: [Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)

---

## ❓ FAQ

**Q: 测试代码可以硬编码吗？**
A: 不行。用测试专用的环境变量或mock数据。

**Q: 如果secret很短（比如密码）怎么办？**
A: 依然用环境变量。长度不是判断标准。

**Q: 我可以把secrets加密后放代码里吗？**
A: 不推荐。解密密钥又要放哪里？还是用环境变量。

**Q: Private repo可以放secrets吗？**
A: 不行。Repo可能变public，代码可能被复制。

**Q: 配置文件（config.json）包含secrets怎么办？**
A: 要么用环境变量覆盖，要么把config.json加到 .gitignore（运行时生成）。

**Q: 怎么在本地开发时测试？**
A: 创建 `.env.local`（在 .gitignore 里），用 `python-dotenv` 或手动source。

---

## 版本历史

- **2026-02-02**: 初始版本，基于Notion token泄露事故教训
- 标准化所有项目的secrets管理方式
- 强制环境变量唯一方案
