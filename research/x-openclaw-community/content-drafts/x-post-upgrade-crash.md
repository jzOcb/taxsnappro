# X Post: OpenClaw升级翻车记录（我们的版本）

---

OpenClaw升级翻车记录。

从v2026.1.24直接跳到v2026.2.3。跨了9个版本。

让AI跑update.run，然后整个服务器挂了。

修了7个问题才活过来：

1⃣ browser.profiles缺color字段
AI加了cdpPort但漏了必填的color。而且color必须是hex格式（"0066FF"），写"blue"直接报错。

2⃣ 无效配置键
AI猜着加了auth、fallbacks这些根本不存在的字段。clawdbot doctor --fix才清掉。

3⃣ Model名称格式错
写成claude-sonnet-4.5（点号），正确是claude-sonnet-4-5（连字符）。一个标点，模型找不到。

4⃣ Telegram channel丢失
配置过程中channel设置被清除。发消息没反应，日志都没记录。最阴的bug——静默失败。

5⃣ 插件文件名不匹配
系统找clawdbot.plugin.json，文件实际叫openclaw.plugin.json。改名遗留问题。
修复：ln -s openclaw.plugin.json clawdbot.plugin.json

6⃣ 插件SDK模块找不到
Cannot find module 'openclaw/plugin-sdk'。
修复：git pull + pnpm install

7⃣ 依赖导出不匹配
discoverAuthStorage这个export消失了。
修复：rm -rf node_modules + pnpm install + pnpm run build

跟 @ohxiyu 踩的坑一模一样的核心问题：AI不知道正确的配置格式。它猜。猜错系统就崩。

我的踩坑总结比他多一条：

1. 改配置前先备份
2. 每次只改一个字段
3. 不确定就查文档，别让AI猜
4. 大版本跳跃别用update.run，手动三步走：git pull → pnpm install → pnpm run build
5. 更新后检查文件名兼容性——改名期的项目，旧名新名可能混着用
6. Telegram channel静默丢失是最难debug的——记得更新后第一时间测试消息通道
7. ⚠️ 新增：跨多个版本更新时，先读每个版本的release notes。9个版本的breaking changes叠在一起，一个update.run根本扛不住。

现在的状态：
- v2026.2.3 ✅ 运行正常
- 配置 ✅ 已备份+验证
- 教训 ✅ 写进了AGENTS.md的Iron Law

多Agent系统最怕的不是功能不够，是配置改崩了全军覆没。

深有同感 @ohxiyu 🤝
