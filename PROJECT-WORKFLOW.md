# PROJECT-WORKFLOW.md — 项目管理标准流程

**所有sessions和agents必须遵循此流程创建和管理项目**

## 铁律

❌ **禁止直接在 kanban-tasks/ 里手动创建.md文件**  
✅ **必须创建项目目录 + STATUS.md，由sync脚本自动生成kanban卡片**

## 为什么需要标准流程？

- **问题**: 之前有session直接在kanban文件夹里创建卡片，导致：
  - 项目没有代码/文档目录
  - 状态不同步
  - 无法追踪历史
  - 其他session找不到项目文件

- **解决**: 统一流程确保：
  - 项目结构完整
  - 状态自动同步到kanban
  - 所有人都能找到并更新项目

---

## 正确流程：创建新项目

### 1️⃣ 创建项目目录

```bash
cd /workspace
mkdir my-new-project
cd my-new-project
```

**目录命名规范：**
- 小写字母
- 用连字符分隔（kebab-case）
- 简洁但有意义
- 例如：`btc-arbitrage`, `video-editing`, `claude-account-switcher`

### 2️⃣ 创建 STATUS.md（必需）

这是项目在kanban系统中的唯一标识。格式**必须严格遵守**：

```markdown
# STATUS.md — 项目名称（中文或英文）

Last updated: YYYY-MM-DDTHH:MMZ

## 当前状态: [进行中/卡住/完成/规划中/暂停]

## 最后做了什么
- 简短描述最近完成的工作（1-3行）

## Blockers
- 列出阻塞因素（没有就写"无"）

## 下一步
1. 明确的下一步行动
2. 优先级排序

## 关键决策记录
- YYYY-MM-DD: 重要决策或里程碑
```

**状态映射到kanban列：**
- `进行中` / `In Progress` → "In Progress"
- `暂停` / `Paused` / `卡住` / `Blocked` → "Paused"
- `完成` / `Done` / `Completed` → "Done"
- `规划中` / `TODO` / `Planning` → "TODO"

### 3️⃣ 创建 README.md（推荐）

项目概述、目标、架构、使用方法等。

### 4️⃣ 同步到Kanban

```bash
# 方法1: 手动运行sync脚本
bash /workspace/scripts/sync-status-to-kanban.sh

# 方法2: 等待heartbeat自动同步（每2小时）
```

脚本会：
1. 扫描所有项目的STATUS.md
2. 解析状态
3. 在kanban-tasks/对应列中创建/更新卡片
4. 自动rsync到看板容器（每5分钟cron）

### 5️⃣ 验证

检查看板: http://45.55.78.247:8090

---

## 更新现有项目

### 修改项目状态

1. 编辑项目的 `STATUS.md`
2. 更新 `Last updated:` 时间戳
3. 修改 `## 当前状态:`
4. 更新 `## 最后做了什么` 和 `## 下一步`
5. 运行 sync 脚本（或等待自动同步）

**示例：**

```bash
cd /workspace/my-project
# 编辑STATUS.md
nano STATUS.md

# 同步到kanban
bash /workspace/scripts/sync-status-to-kanban.sh
```

### 移动项目到其他列

只需修改STATUS.md中的 `## 当前状态:` 即可：

- 暂停项目 → 改成 `暂停`
- 完成项目 → 改成 `完成`
- 重新启动 → 改成 `进行中`

sync脚本会自动把卡片从旧列移到新列。

---

## 自动同步机制

### Heartbeat自动检查

在 `HEARTBEAT.md` 中已配置：

```markdown
## Kanban 同步检查
- 每2小时检查一次
- 运行: bash scripts/sync-status-to-kanban.sh
- 更新 heartbeat-state.json 时间戳
```

### Host Cron rsync

看板容器无法直接访问 `/workspace`，通过cron同步：

```bash
# 每5分钟同步
*/5 * * * * rsync -a --delete /home/clawdbot/clawd/kanban-tasks/ /home/clawdbot/kanban/tasks/
```

---

## 项目目录结构示例

```
workspace/
├── btc-arbitrage/
│   ├── STATUS.md          ← 必需
│   ├── README.md          ← 推荐
│   ├── src/
│   │   └── main.py
│   └── data/
│
├── video-editing/
│   ├── STATUS.md
│   ├── README.md
│   └── scripts/
│
└── claude-account-switcher/
    ├── STATUS.md
    ├── README.md
    ├── src/
    ├── config/
    └── logs/
```

---

## 常见错误

### ❌ 错误做法

```bash
# 直接在kanban-tasks里创建文件
echo "# My Project" > /workspace/kanban-tasks/TODO/my-project.md
```

**后果：**
- 没有项目目录存放代码
- 下次sync会被覆盖
- 其他session找不到

### ✅ 正确做法

```bash
# 1. 创建项目目录
mkdir /workspace/my-project
cd /workspace/my-project

# 2. 写STATUS.md
cat > STATUS.md << 'EOF'
# STATUS.md — My Project
Last updated: 2026-02-02T17:50Z

## 当前状态: 进行中

## 最后做了什么
- 项目初始化

## Blockers
无

## 下一步
1. 实现核心功能

## 关键决策记录
- 2026-02-02: 项目启动
EOF

# 3. 同步
bash /workspace/scripts/sync-status-to-kanban.sh
```

---

## 检查清单

创建新项目前，确认：

- [ ] 项目目录已创建（在 /workspace/ 下）
- [ ] STATUS.md 格式正确（包含所有必需section）
- [ ] Last updated 时间戳是UTC时间
- [ ] 当前状态是允许的值（进行中/暂停/完成/规划中）
- [ ] 已运行 sync 脚本或等待heartbeat
- [ ] 在看板上验证卡片出现

更新项目前，确认：

- [ ] 修改了 STATUS.md
- [ ] 更新了 Last updated 时间戳
- [ ] 更新了 最后做了什么 和 下一步
- [ ] 已运行 sync 脚本

---

## 故障排查

### 卡片没有出现在看板上

1. 检查 STATUS.md 格式是否正确
2. 手动运行 sync 脚本查看输出
3. 检查 `/workspace/kanban-tasks/` 是否有对应文件
4. 等待5分钟让cron rsync同步
5. 强制刷新浏览器（Ctrl+Shift+R）

### 卡片在错误的列

检查 STATUS.md 中 `## 当前状态:` 后面的值，确保是：
- 进行中 / In Progress
- 暂停 / Paused
- 完成 / Done  
- 规划中 / TODO

### 卡片内容没更新

1. 确认修改了STATUS.md并保存
2. 确认运行了sync脚本
3. 等待rsync cron（最多5分钟）
4. 清除浏览器缓存

---

## 快速参考

**创建项目：**
```bash
mkdir /workspace/new-project && cd /workspace/new-project
# 写 STATUS.md（复制模板）
bash /workspace/scripts/sync-status-to-kanban.sh
```

**更新状态：**
```bash
cd /workspace/project-name
nano STATUS.md  # 修改状态
bash /workspace/scripts/sync-status-to-kanban.sh
```

**查看当前所有项目：**
```bash
find /workspace -maxdepth 2 -name "STATUS.md" -type f | sort
```

**看板地址：**
http://45.55.78.247:8090

---

## 版本历史

- **2026-02-02**: 创建此文档，修复kanban孤立卡片问题
  - 转换 claude-account-switcher, openclaw-hardening 为正规项目
  - 文档化标准流程
  - 添加自动同步到 HEARTBEAT.md
