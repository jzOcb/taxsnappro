#!/bin/bash
# sync-status-to-kanban.sh
# 自动同步 STATUS.md 到 kanban board

set -euo pipefail

WORKSPACE=${WORKSPACE:-/workspace}
KANBAN_DIR="$WORKSPACE/kanban-tasks"
PARSER="$WORKSPACE/scripts/parse-status.py"
LOG_FILE="$WORKSPACE/memory/kanban-sync.log"
TEMP_JSON="/tmp/kanban-sync-$$.json"

mkdir -p "$WORKSPACE/memory"
touch "$LOG_FILE"

log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"
}

# 创建或更新kanban卡片
update_kanban_card() {
    local json="$1"
    
    local project_name=$(echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin)['project_name'])")
    local project_dir=$(echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin)['project_dir'])")
    local column=$(echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin)['kanban_column'])")
    local last_work=$(echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin)['last_work'])")
    local blockers=$(echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin)['blockers'])")
    local next_steps=$(echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin)['next_steps'])")
    local last_updated=$(echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin)['last_updated'])")
    
    # 使用project_dir作为文件名（已经是安全的英文目录名）
    local card_name="$project_dir"
    
    # 确保column目录存在
    mkdir -p "$KANBAN_DIR/$column"
    
    # 查找卡片是否在其他列
    local existing_card=""
    local existing_col=""
    for col in TODO 进行中 完成 暂停; do
        if [ -f "$KANBAN_DIR/$col/$card_name.md" ]; then
            existing_card="$KANBAN_DIR/$col/$card_name.md"
            existing_col="$col"
            break
        fi
    done
    
    local target_card="$KANBAN_DIR/$column/$card_name.md"
    
    # 如果卡片在不同列，移动它
    if [ -n "$existing_card" ] && [ "$existing_card" != "$target_card" ]; then
        log "移动卡片: $project_name ($existing_col → $column)"
        mv "$existing_card" "$target_card"
    elif [ -f "$target_card" ]; then
        log "更新卡片: $project_name @ $column"
    else
        log "创建卡片: $project_name @ $column"
    fi
    
    # 生成卡片内容
    cat > "$target_card" << EOFCARD
# $project_name

**项目目录**: \`$project_dir/\`  
**最后更新**: $last_updated  
**同步时间**: $(date -u +%Y-%m-%dT%H:%M:%SZ)

---

## 📝 最近进展

$last_work

---

## 🚧 当前Blockers

$blockers

---

## 🎯 下一步

$next_steps

---

*此卡片由 sync-status-to-kanban.sh 自动生成*  
*数据源: \`$project_dir/STATUS.md\`*
EOFCARD
}

main() {
    log "开始同步 STATUS.md → kanban..."
    
    if [ ! -f "$PARSER" ]; then
        log "❌ 错误: parse-status.py 不存在"
        exit 1
    fi
    
    python3 "$PARSER" > "$TEMP_JSON" 2>/dev/null || {
        log "❌ 错误: 解析STATUS.md失败"
        exit 1
    }
    
    local count=$(python3 -c "import sys,json; print(len(json.load(open('$TEMP_JSON'))))")
    
    if [ "$count" -eq 0 ]; then
        log "⚠️  未找到任何STATUS.md文件"
        rm -f "$TEMP_JSON"
        exit 0
    fi
    
    for i in $(seq 0 $((count - 1))); do
        local project_json=$(python3 -c "import sys,json; print(json.dumps(json.load(open('$TEMP_JSON'))[$i]))")
        update_kanban_card "$project_json"
    done
    
    log "✅ 同步完成，处理了 $count 个项目"
    rm -f "$TEMP_JSON"
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
