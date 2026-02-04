# X/Twitter 中文推文草稿 — 2026-02-03

## 推文1: Process Guardian

你的AI agent后台进程，可能早就死了你还不知道 💀

Claude Code启动的后台任务，20-30分钟后会被父session静默SIGTERM掉，exit code还是0——看起来一切正常，实际已经凉了。

搞了个process-guardian：setsid脱离session + 自动重启 + 死亡告警，再也不用手动去查进程还活着没。

https://github.com/jzOcb/process-guardian

#ClaudeCode #AIAgents #开源

---

## 推文2: OpenClaw Hardening

你的OpenClaw服务器，真的藏好了吗？🔒

更新了hardening kit（基于 @tomcrawshaw01 的安全指南）：

→ unattended-upgrades 自动安全更新
→ verify-hidden.sh 一条命令检测服务器是否暴露（查公网IP、Tailscale、防火墙、fail2ban）

跑一下就知道自己有没有裸奔。

https://github.com/jzOcb/openclaw-hardening

#OpenClaw #服务器安全 #自建服务

---

## 推文3: Token省钱指南

Opus账单看哭了？这5招帮我砍了50%成本 🪓

① 模型分层：Opus只做推理，日常杂活丢给Sonnet
② Cache warming：每55分钟heartbeat保活，别让cache白白过期
③ Context pruning：自动裁剪旧tool输出，别啥都往context塞
④ Workspace文件控制在20K字符以内
⑤ 没事别废话，一个token能回的就别写一段

感谢 @op7418 的教程和 @ClawdBot 社区的实践分享。

https://github.com/jzOcb/openclaw-hardening

#ClaudeCode #AI省钱 #OpenClaw
