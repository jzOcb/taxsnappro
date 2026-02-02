# PROJECTS.md — 项目总览

> 每个项目有自己的目录和 README.md + STATUS.md，这里只放摘要和链接。
> 新项目必须遵循同样的结构：独立目录 + README.md + STATUS.md。

---

## 活跃项目

### 1. 小红书内容创作 `chinese-social-scripts/`
- **状态:** ✅ 核心闭环完成，待积累内容
- **进度:** Phase 2完成（目录重构+AI工作流+Notion集成），首次测试成功
- **目标:** 系统化内容创作（从选题→文稿→标题→发布→数据分析）
- **详情:** [chinese-social-scripts/STATUS.md](chinese-social-scripts/STATUS.md)
- **下一步:** 
  - Jason实际使用产出第一个视频
  - 测试生成标题功能
  - 开始积累素材库
- **关键成果:**
  - ✅ Notion双向同步（本地↔小红书选题库）
  - ✅ 首个文稿生成："屏障受损与闭口的关系"
  - ✅ 4个AI工作流定义完成

### 2. AI视频粗剪工具 `video-editing/`
- **状态:** ✅ 代码完成，等待测试视频
- **进度:** 全部代码完成，火山引擎API已配置
- **目标:** 自动识别并删除视频口误/静音/重复，生成紧凑视频
- **详情:** [video-editing/STATUS.md](video-editing/STATUS.md)
- **下一步:**
  - Jason提供测试视频（3-5分钟口播）
  - 测试火山引擎API识别效果
  - 测试审核界面
  - 完整剪辑流程验证
- **技术栈:**
  - 火山引擎API（豆包）— 字幕识别
  - Python分析器 — 口误检测
  - Flask — Web审核界面
  - ffmpeg — 视频剪辑

### 3. Kalshi 预测市场交易 `kalshi/`
- **状态:** 🔧 工具可用，策略迭代中
- **目标:** 自动监控政治预测市场，辅助交易决策
- **⚠️ 铁律：每个建议必须经过深度 research**
- **详情:** [kalshi/STATUS.md](kalshi/STATUS.md)

### 4. YouTube 视频搬运 `video-repurpose/`
- **状态:** 📋 规划中
- **目标:** AI健身视频搬运到抖音/小红书，长期转向AI原创
- **详情:** [video-repurpose/STATUS.md](video-repurpose/STATUS.md)

---

## 项目关系图

```
小红书内容创作
    ↓ 选题 + 文稿
    ↓
录制视频（Jason）
    ↓
AI视频粗剪 ←─── 自动删除口误/静音
    ↓
剪映精修（Jason）
    ↓
发布小红书
    ↓
记录数据 ────→ 反哺方法论
```

---

## 项目规范

新建项目时必须：
1. 创建独立目录 `project-name/`
2. 写 `README.md`（项目介绍、快速开始）
3. 写 `STATUS.md`（当前状态、Blockers、下一步、关键决策）
4. 在本文件添加索引条目
5. **不要在 PROJECTS.md 里写详细内容**

---

*Last updated: 2026-02-02T04:18Z*
