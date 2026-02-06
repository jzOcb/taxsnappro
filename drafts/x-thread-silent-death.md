# X Thread Draft: AI Agent基础设施的两个静默死亡

## 🧵1/6
用AI Agent跑量化交易两天，踩了两个坑。

两个坑有一个共同特点：没有任何报错。

不是crash，不是exception，不是OOM。
是系统"正常运行"，但你的东西悄悄死了。

## 🧵2/6
【第一个坑 — 定时任务静默失效】

Day 1，我发现我的12个定时任务（交易报告、持仓监控、市场扫描）8.5小时没有执行过一次。

OpenClaw的cron scheduler有个bug：timer倒计时到0 → 跳过执行 → 重新排期。循环往复。

没有error log。Gateway显示"running"。job列表显示"next run in 30 min"。一切看起来正常。

只是没有一个job真正跑过。

## 🧵3/6
【第二个坑 — 6个进程同时被杀】

Day 2，我的6个交易机器人全部死亡。

不是一个个挂的 — 是同一毫秒：14:30:24.541 UTC。

排查过程：
- ps日志：6个进程同时收到SIGTERM
- dmesg：不是OOM  
- 没有人手动kill

凶手是谁？我自己的AI Agent。

OpenClaw的sub-agent完成任务后做session cleanup → 对exec产生的子进程广播SIGTERM → 我的bot恰好是sub-agent启动的 → 全灭。

## 🧵4/6
【为什么翻遍文档也找不到】

这两个问题有个共同点：它们不是"bug"，是"设计行为的副作用"。

cron跳过执行 → scheduler的边界条件
session cleanup杀子进程 → Unix进程组的正常行为

没有人会写文档说"我们的定时任务可能静默不执行"或"sub-agent结束会杀你的后台进程"。

这类问题只能靠踩坑发现。

## 🧵5/6
【修了三层防线】

Day 1修：
- 整个cron scheduler弃用，写了cron-dispatcher.sh走系统crontab
- 直接调Telegram Bot API发报告，零依赖OpenClaw

Day 2修：
- setsid：进程脱离Agent进程组，不再被连带kill
- managed-process.sh：统一进程管理，5分钟healthcheck自动拉起
- pre-commit hook：git层面强制所有trader必须通过managed-process启动

不靠自觉，靠机制。代码即法律。

## 🧵6/6
经验总结：

用AI Agent做任何需要"持续运行"的事情时：

1. 不要信任Agent的基础设施 — 它的定时任务、进程管理都可能有静默失败模式
2. 建立独立的监控 — 不依赖Agent本身的健康检查
3. "没有报错"≠"没有问题" — 最危险的bug不crash
4. 5分钟发现 vs 8小时发现，差的是真金白银

AI Agent很强大，但它的基础设施还很年轻。

Trust but verify, on a 5-minute loop.
