# Kanban 自动化同步系统

## 📋 系统组件

### 1. `parse-status.py`
解析STATUS.md文件，提取项目信息为JSON格式。

**用法：**
```bash
# 解析单个文件
python3 scripts/parse-status.py kalshi/STATUS.md

# 扫描所有项目
python3 scripts/parse-status.py
```

### 2. `validate-status.py`
校验STATUS.md格式，自动修复常见错误。

**用法：**
```bash
# 仅校验
python3 scripts/validate-status.py

# 校验并自动修复
python3 scripts/validate-status.py --fix
```

**检查项：**
- ✅ 第一行格式：`# STATUS.md — 项目名`
- ✅ 更新时间：`Last updated: YYYY-MM-DDTHH:MMZ`
- ✅ 必需章节：当前状态、最后做了什么、Blockers、下一步
- ✅ 状态值标准化：进行中/卡住/完成/规划中

### 3. `sync-status-to-kanban.sh`
主同步脚本，自动将STATUS.md同步到kanban看板。

**用法：**
```bash
bash scripts/sync-status-to-kanban.sh
```

**工作流程：**
1. 自动校验格式 (`validate-status.py --fix`)
2. 扫描所有STATUS.md (`parse-status.py`)
3. 创建/更新kanban卡片
4. 状态变化时移动卡片
5. 记录日志到 `memory/kanban-sync.log`

## 🔄 自动化机制

### 实时触发
Agent完成工作时自动调用：
```bash
# 更新项目STATUS.md后
bash scripts/sync-status-to-kanban.sh
```

### 定期检查（Heartbeat）
每2小时自动运行一次作为兜底。

## 📊 看板地址

http://45.55.78.247:8090

## 🎯 STATUS.md 标准格式

```markdown
# STATUS.md — 项目名
Last updated: YYYY-MM-DDTHH:MMZ

## 当前状态: [进行中/卡住/完成/规划中]

## 最后做了什么
...

## Blockers
...

## 下一步
...

## 关键决策记录
...
```

## 🚨 常见问题

**Q: 为什么看板没更新？**
A: 运行 `bash scripts/sync-status-to-kanban.sh` 手动同步

**Q: 格式校验失败怎么办？**
A: 运行 `python3 scripts/validate-status.py --fix` 自动修复

**Q: 如何添加新项目？**
A: 在项目目录创建STATUS.md，格式遵循标准模板，下次sync自动同步

## 📝 日志位置

- 同步日志: `memory/kanban-sync.log`
- Heartbeat状态: `memory/heartbeat-state.json`
