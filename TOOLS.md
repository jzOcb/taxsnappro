# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Google / gog
- **Account:** jzclaws1@gmail.com
- **Services:** gmail, calendar, drive, contacts, docs, sheets
- **Keyring password:** clawdbot
- **Env vars:** GOG_KEYRING_PASSWORD=clawdbot, GOG_ACCOUNT=jzclaws1@gmail.com (in /opt/clawdbot.env)

## Server
- **IP:** 45.55.78.247
- **OS:** Ubuntu 24.04 (DigitalOcean)
- **User:** clawdbot (homebrew at $HOME/homebrew/bin)

## Telegram
- Jason: @zzGody (id: 6978208486)
- Jason alt: Johanne Jiao (id: 7952782207) — trusted, same person

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Workspace路径
- **Sandbox**: `/workspace`
- **Host**: `/home/clawdbot/clawd/`
- **映射**: 同一个目录（inode: 572460）

## Kanban看板
- **URL**: http://45.55.78.247:8090
- **容器**: 808c0d52b2b2 (Tasks.md)
- **挂载**: `/home/clawdbot/kanban/tasks/` (容器内 `/tasks`)
- **同步**: Cron每5分钟 rsync from `/home/clawdbot/clawd/kanban-tasks/`

## Browser / 浏览器自动化 🌐
- **状态**: ✅ 可用
- **浏览器**: Google Chrome 144.0.7559.109 (非snap版)
- **路径**: `/usr/bin/google-chrome`
- **模式**: Headless, noSandbox (服务器无GUI)
- **CDP端口**: 18800
- **Profile**: openclaw (默认)
- **控制服务**: http://127.0.0.1:18791

### 重要配置提示 💡
**问题：** 浏览器不自动打开/需要手动点击插件/权限报错

**解决方案：** 在 `~/.clawdbot/clawdbot.json` 根节点添加：
```json
"browser": {
  "defaultProfile": "openclaw"
}
```

这样OpenClaw会用独立浏览器启动，只需在该浏览器登录一次各类会话，后续不会报错。

**已设置：** ✅ 当前配置已正确

### 使用方法
所有session和agent都可以使用 `browser` 工具：
```
browser action=start profile=openclaw    # 启动浏览器
browser action=navigate targetUrl=URL    # 导航到URL
browser action=snapshot                  # 获取页面结构
browser action=screenshot                # 截图
browser action=act request={kind:click, ref:e1}  # 点击元素
```

### 能力
- ✅ 浏览任意网页
- ✅ 截图并发送
- ✅ 填写表单、点击按钮
- ✅ 登录网站（需要cookie/session管理）
- ✅ 爬取数据
- ✅ 自动化操作（注册、下单等）

### 注意事项
- 首次使用需要 `browser action=start profile=openclaw`
- Snap版Chromium不兼容，必须用Google Chrome deb包
- 服务器无GUI，只能headless模式

## Elevated权限
- **状态**: ✅ 已启用
- **模式**: full (auto-approve)
- **允许的Telegram用户**: 6978208486, 7952782207
- **能力**: 在host上执行任意命令，无需确认

## 环境注意事项
- **Sandbox模式**: user=root, pwd=/workspace, 无docker访问
- **Host模式**: user=clawdbot, pwd=/home/clawdbot/clawd, 有docker访问
- **权限冲突**: sandbox创建的文件属于root，host上clawdbot无法修改
- **解决方案**: `sudo chown -R clawdbot:clawdbot /home/clawdbot/clawd/`
