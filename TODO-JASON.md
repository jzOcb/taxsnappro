# Jason TODO — 回电脑后操作

## 1. 安装Skills（1分钟）✅ 已完成
```bash
bash ~/clawd/setup/install-skills.sh
clawdbot gateway restart
```

## 2. 服务器安全加固（5分钟）✅ 已完成
```bash
cd ~/clawd/security
bash audit.sh          # 先看当前状况
sudo bash harden.sh    # 交互式加固（UFW+SSH+fail2ban+Tailscale）
```
⚠️ 跑harden.sh时**不要关当前SSH窗口**，先开第二个窗口测试新端口能连

## 3. 给我开host权限（1分钟）✅ 已完成
编辑 `~/.openclaw/openclaw.json`，加入：
```json5
{
  tools: {
    elevated: {
      enabled: true,
      allowFrom: { telegram: true }
    }
  }
}
```
然后 `clawdbot gateway restart`

## 4. Token优化配置（1分钟）✅ 已完成
同一个 `openclaw.json` 里加：
```json5
{
  agents: {
    defaults: {
      heartbeat: { every: "55m" },
      contextPruning: { mode: "cache-ttl", ttl: "1h" },
      subagents: { model: "anthropic/claude-sonnet-4" }
    }
  }
}
```

## 5. Git commit（30秒）✅ 已完成
```bash
cd ~/clawd && git add -A && git commit -m "security + kalshi tools + token optimization"
```

## 6. Telegram Topics 群配置（2分钟）✅ 已完成
在服务器上跑：
```bash
# 查看 gateway 日志，看群消息有没有进来
clawdbot gateway logs --tail 30

# 查看当前 telegram channel 配置
cat ~/.clawdbot/clawdbot.json | python3 -m json.tool | grep -A 30 telegram
```
把输出发给我，我来告诉你怎么把新群加进 channel routing。
目标：Chat / Work / Monitor 三个 Topic 各自独立 session，互不串台。

---
**顺序建议：** 2 → 3 → 1 → 4 → 6 → 5（先加固再开权限，最后 commit）
