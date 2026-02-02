# Kanban修复总结

## 问题根源
**文件格式不对** — Tasks.md期望简单markdown，我生成的格式太复杂。

## 已修复
✅ 重写同步脚本，生成Tasks.md格式  
✅ 所有项目卡片已重新生成（时间戳03:10）  
✅ 文件在 `/workspace/kanban-tasks/` (= host `/home/clawdbot/clawd/kanban-tasks/`)

## 新格式示例
```markdown
# 小红书内容创作

## 状态
✅ 系统搭建完成，待试用

## 最近进展
...

## 当前Blockers
...

## 下一步
...
```

## 你需要做的
如果软链接 `/home/clawdbot/kanban/tasks -> /home/clawdbot/clawd/kanban-tasks` 已存在：

**选项1：直接刷新看板**  
http://45.55.78.247:8090 （可能需要硬刷新 Ctrl+Shift+R）

**选项2：重启容器（如果还是空）**  
```bash
docker restart 808c0d52b2b2
```

## 验证命令
```bash
# 1. 检查文件时间戳（应该显示03:10）
ls -la /home/clawdbot/clawd/kanban-tasks/*/

# 2. 检查容器能否看到文件
docker exec 808c0d52b2b2 ls -la /tasks/

# 3. 检查文件内容格式
head -15 /home/clawdbot/clawd/kanban-tasks/完成/chinese-social-scripts.md
```

## 如果还不行
可能还有其他问题（权限、路径、容器配置），需要进一步诊断。
