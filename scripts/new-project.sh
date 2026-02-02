#!/bin/bash
# new-project.sh — Bootstrap a new project with proper structure
# Usage: bash scripts/new-project.sh project-name "Project Display Name"

set -uo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: bash scripts/new-project.sh project-name [\"Project Display Name\"]"
    echo ""
    echo "Examples:"
    echo "  bash scripts/new-project.sh my-bot"
    echo "  bash scripts/new-project.sh trading-algo \"Trading Algorithm\""
    exit 1
fi

PROJECT_DIR="$1"
PROJECT_NAME="${2:-$1}"
WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"

# Validate project name (kebab-case)
if ! echo "$PROJECT_DIR" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*$'; then
    echo "❌ Error: Project directory must be lowercase kebab-case (e.g., my-project)"
    exit 1
fi

PROJECT_PATH="$WORKSPACE/$PROJECT_DIR"

# Check if project already exists
if [ -d "$PROJECT_PATH" ]; then
    echo "❌ Error: Project directory already exists: $PROJECT_PATH"
    exit 1
fi

echo "Creating new project: $PROJECT_NAME"
echo "Directory: $PROJECT_PATH"
echo ""

# Create project structure
mkdir -p "$PROJECT_PATH"
mkdir -p "$PROJECT_PATH/src"
mkdir -p "$PROJECT_PATH/docs"

# Get current UTC timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%MZ")

# Create STATUS.md
cat > "$PROJECT_PATH/STATUS.md" << EOF
# STATUS.md — $PROJECT_NAME

Last updated: $TIMESTAMP

## 当前状态: 规划中

## 最后做了什么
- 项目初始化

## Blockers
无

## 下一步
1. 定义项目目标和范围
2. 设计架构
3. 开始实现

## 关键决策记录
- $TIMESTAMP: 项目创建
EOF

# Create README.md
cat > "$PROJECT_PATH/README.md" << EOF
# $PROJECT_NAME

[项目简短描述]

## 目标

[项目目标和目的]

## 状态

详见 [STATUS.md](./STATUS.md)

## 快速开始

\`\`\`bash
# [安装/运行指令]
\`\`\`

## 架构

[技术架构说明]

## 文档

- [STATUS.md](./STATUS.md) - 项目状态
- [docs/](./docs/) - 详细文档
EOF

# Create .gitignore
cat > "$PROJECT_PATH/.gitignore" << EOF
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/
venv/
env/

# Logs
*.log
logs/

# Config (may contain secrets)
config.json
*.env
.env*

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
EOF

echo "✅ Project structure created:"
echo ""
tree -L 2 "$PROJECT_PATH" 2>/dev/null || ls -la "$PROJECT_PATH"
echo ""
echo "📝 Next steps:"
echo "1. Edit $PROJECT_PATH/STATUS.md with project details"
echo "2. Edit $PROJECT_PATH/README.md with project overview"
echo "3. Run: bash scripts/sync-status-to-kanban.sh"
echo "4. Verify at: http://45.55.78.247:8090"
echo ""
echo "📚 See PROJECT-WORKFLOW.md for complete workflow documentation"
