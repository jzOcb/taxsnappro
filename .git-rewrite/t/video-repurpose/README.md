# YouTube 视频搬运项目

## 目标
将 YouTube 上的 AI 健身动画视频搬运到中文平台（抖音、小红书），长期转向 AI 原创内容。

## 目标频道
- **GymHybrids** — https://www.youtube.com/@GymHybrids.
- AI 动画风格健身科普
- 测试视频: https://youtu.be/OG3nekTnQlA (Drop Sets vs Supersets)

## 流程设计

### 阶段1 — 搬运+字幕（快速验证）
1. YouTube 下载视频 + 提取字幕
2. 翻译/重写中文文案（适合国内受众）
3. ffmpeg 切片成短视频
4. 烧录中文字幕
5. 生成封面图

### 阶段2 — 深度本地化
- 重写脚本，配中文 AI 配音
- 适配平台规则（抖音竖屏、小红书3:4）

### 阶段3 — AI 原创（长期）
- 分析原视频动作/场景描述
- 用视频生成模型（Kling、Pika、Runway）重新生成
- 完全原创，无版权问题

## 技术栈
- **yt-dlp** ✅ 已安装（YouTube 下载需要 cookies）
- **ffmpeg** ✅ 可用（通过 memfd 绕过 sandbox noexec）
- **whisper** ❌ 装不了（PyTorch 900MB+，sandbox /tmp 空间不足）
- **字幕方案:** YouTube 自带字幕 > Whisper API > 手动

## 待解决
- [ ] YouTube cookies（sandbox IP 被 bot 检测拦截）
- [ ] 语音转文字方案（whisper 替代方案）
- [ ] 中文 TTS 配音工具选型
- [ ] 视频生成模型调研（阶段3）

## 状态
📋 规划中 — 等待 Jason 提供视频文件或 YouTube cookies

*Created: 2026-02-01*
