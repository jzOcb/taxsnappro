# ✅ Kanban看板 - 最终配置

## 当前状态
✅ **看板正常工作**: http://45.55.78.247:8090  
✅ 显示5个项目（TODO/进行中/完成三列）

## 问题根源
**Docker不能follow symlinks** — 这是Docker的设计限制。容器挂载的路径如果是symlink，只看到空目录。

## 解决方案
用 `cp` 代替 `ln -s`，然后定期rsync同步。

## 文件路径说明
```
Agent (sandbox) 写入:
  /workspace/kanban-tasks/
       ↓ (自动映射)
Host 实际路径:
  /home/clawdbot/clawd/kanban-tasks/
       ↓ (需要rsync复制)
容器读取位置:
  /home/clawdbot/kanban/tasks/
       ↓ (Docker挂载)
Tasks.md容器 → 看板显示
```

## 🔄 保持同步（重要！）

Agent每次更新项目STATUS.md后会自动同步到 `/workspace/kanban-tasks/`，但**需要你在host上设置cron定期复制**：

```bash
# 编辑cron
crontab -e

# 添加这一行（每5分钟同步）
*/5 * * * * rsync -a --delete /home/clawdbot/clawd/kanban-tasks/ /home/clawdbot/kanban/tasks/
```

**或者手动同步（任何时候）：**
```bash
rsync -a --delete /home/clawdbot/clawd/kanban-tasks/ /home/clawdbot/kanban/tasks/
```

## 验证同步
```bash
# 检查文件时间戳是否一致
ls -la /home/clawdbot/clawd/kanban-tasks/进行中/
ls -la /home/clawdbot/kanban/tasks/进行中/
```

## Agent工作流（自动）
```
1. Agent完成工作 → 更新项目STATUS.md
2. sync-status-to-kanban.sh → 更新 /workspace/kanban-tasks/
3. (等待cron) → rsync到 /home/clawdbot/kanban/tasks/
4. 刷新看板 → 显示最新状态
```

## 如果看板没更新
1. 检查 `/home/clawdbot/clawd/kanban-tasks/` 是否有最新文件
2. 手动运行 rsync 命令
3. 刷新浏览器（可能需要 Ctrl+Shift+R 硬刷新）

---
*Last updated: 2026-02-02T04:29Z*
