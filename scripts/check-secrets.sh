#!/bin/bash
# check-secrets.sh — 扫描代码中可疑的硬编码secrets
# 用法: bash scripts/check-secrets.sh [directory]

set -uo pipefail

TARGET_DIR="${1:-.}"
FOUND=0

echo "🔍 Scanning for potential hardcoded secrets in: $TARGET_DIR"
echo ""

# 搜索模式（按危险程度排序）
declare -A PATTERNS=(
    # GitHub tokens
    ["GitHub Personal Access Token"]='ghp_[a-zA-Z0-9]{36,}'
    
    # Common API keys
    ["Stripe API Key"]='sk_(live|test)_[a-zA-Z0-9]{24,}'
    ["Notion API Token"]='ntn_[a-zA-Z0-9]{36,}'
    ["OpenAI API Key"]='sk-[a-zA-Z0-9]{48,}'
    
    # Generic patterns
    ["API Key Assignment"]='api[_-]?key\s*=\s*["\x27][a-zA-Z0-9_-]{20,}["\x27]'
    ["Token Assignment"]='token\s*=\s*["\x27][a-zA-Z0-9_-]{20,}["\x27]'
    ["Secret Assignment"]='secret\s*=\s*["\x27][a-zA-Z0-9_-]{20,}["\x27]'
    ["Password in Code"]='password\s*=\s*["\x27][^"\x27]{8,}["\x27]'
    
    # Environment variable defaults (dangerous pattern)
    ["Hardcoded Default in getenv"]='getenv\([^)]+,\s*["\x27][a-zA-Z0-9_-]{20,}["\x27]\)'
)

# 文件类型
FILE_PATTERNS="*.py *.js *.ts *.sh *.bash *.json *.yaml *.yml *.env"

# 排除目录
EXCLUDE_DIRS=(
    ".git"
    "node_modules"
    "__pycache__"
    ".venv"
    "venv"
    ".pytest_cache"
    "dist"
    "build"
)

# 构建排除参数
EXCLUDE_ARGS=""
for dir in "${EXCLUDE_DIRS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude-dir=$dir"
done

# 扫描每个模式
for desc in "${!PATTERNS[@]}"; do
    pattern="${PATTERNS[$desc]}"
    
    results=$(grep -rn -E "$pattern" "$TARGET_DIR" \
        --include="*.py" --include="*.js" --include="*.sh" --include="*.ts" \
        --include="*.json" --include="*.yaml" --include="*.yml" \
        $EXCLUDE_ARGS \
        2>/dev/null || true)
    
    if [ -n "$results" ]; then
        echo "⚠️  $desc:"
        echo "$results" | sed 's/^/  /'
        echo ""
        FOUND=1
    fi
done

# 特殊检查：.env 文件在git里（不应该commit）
if git -C "$TARGET_DIR" ls-files --error-unmatch '*.env' 2>/dev/null | grep -q .; then
    echo "🚨 .env files tracked in git:"
    git -C "$TARGET_DIR" ls-files '*.env' | sed 's/^/  /'
    echo ""
    FOUND=1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FOUND -eq 0 ]; then
    echo "✅ No obvious secrets found"
    exit 0
else
    echo "❌ Found potential secrets!"
    echo ""
    echo "⚠️  WARNING:"
    echo "  - Review files above before committing"
    echo "  - Never hardcode secrets — use environment variables"
    echo "  - See SECURITY.md for proper patterns"
    echo ""
    exit 1
fi
