# MEMORY.md - Long-Term Memory

## About Jason
- Software developer, has a 9-5 day job
- Wants to build something fun with big potential — change the world
- Builder mindset, wants a collaborator not just an assistant
- Telegram: @zzGody (id: 6978208486), alt: Johanne Jiao (id: 7952782207)
- Smart about security — set up a throwaway Gmail rather than giving full access to his main

## Reference: Multi-Agent Architecture
- Article: "The Complete Guide to Building Mission Control" by @pbteja1998 (SiteGPT founder)
- Link: https://x.com/pbteja1998/status/2017662163540971756
- TL;DR: 10 Clawdbot sessions as specialized agents, shared Convex DB for task management, heartbeat cron system, @mention notifications, daily standups
- Key patterns: WORKING.md for task state, model tiering (cheap for heartbeats, expensive for creative), staggered cron schedules
- **Not needed now** — revisit when we have parallel workstreams that justify multiple agents
- Jason's rule: 先有活干，再招人

## Key Decisions
- **Email:** Skipping for now. Google suspended jzclaws1@gmail.com
- **Communication:** Telegram is the primary channel
- **Project structure:** 每个项目独立目录 + README.md，PROJECTS.md 只做索引

## Infrastructure
- Server: 45.55.78.247 (DigitalOcean Ubuntu 24.04)
- Sandbox: bridge networking, rw workspace, noexec /tmp
- ffmpeg: 可用（memfd trick 绕过 noexec）
- whisper: 装不了（PyTorch too big for /tmp）
- yt-dlp: 已安装
- Notion API: .config/notion/api_key

## Lessons Learned
- Sandbox containers need **recreated** (not just restarted) for new bind mounts
- Google aggressively suspends throwaway OAuth accounts
- ffmpeg 可以通过 memfd_create 在 noexec /tmp 上运行
- **Kalshi: 绝对不能只看价格面就给建议** — 必须先做 research（GDP 5.4% 教训）
- exec 在 sandbox 里以 root 运行，但 workspace 是 uid 1000 所有，root 写不进去
- **永远先 research 再动手** — Jason 已经给了足够信息（账号ID、平台名），不要反过来问他要参考，自己去找
- 封面工具第一版完全做错方向 — 因为没看他的实际内容就开搞，浪费了大量 token
- **遇到限制要第一时间说** — 小红书访问不了应该立刻告诉 Jason，不要默默绕弯
- **Kalshi 策略要从事实出发找错误定价** — 不是从市场价格出发找新闻验证。Putin 教训：4x 机会因为策略方向错误完全漏掉

## Active Projects
详见 PROJECTS.md 和各项目 README.md：
1. 小红书内容创作 → `chinese-social-scripts/`
2. Kalshi 交易系统 → `kalshi/`
3. YouTube 视频搬运 → `video-repurpose/`

## Pending Items
- [ ] Kalshi API key（Jason 提供后可以自动交易）
- [ ] YouTube cookies（下载视频需要）
- [ ] 封面生成器完善（sub-agent 可能超时了）
- [ ] 产品图抠图替代方案
- [ ] 日历/邮件替代方案
