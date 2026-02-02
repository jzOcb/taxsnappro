# Claude 账户切换系统

多账户自动切换机制，优化Token使用，避免单账户额度耗尽。

## 项目目标

实现一个灵活的Claude账户管理和自动切换系统：
- 监控多个Claude账户的Token使用情况
- 根据策略自动切换账户
- 确保服务连续性（不因单账户耗尽而中断）
- 安全存储和管理API密钥

## 核心特性

- ✅ 多账户管理
- ✅ Token使用追踪
- ✅ 灵活切换策略
- ✅ 日志记录
- ⏳ 安全的API Key存储
- ⏳ 实时监控和告警
- ⏳ Claude API集成

## 技术架构

```
claude-account-switcher/
├── src/
│   ├── account_manager.py    # 账户管理核心逻辑
│   └── switcher.py            # 切换策略实现
├── scripts/
│   └── switch.sh              # 快速切换脚本
├── config/
│   └── accounts.json          # 账户配置（不提交到git）
└── logs/
    └── switcher.log           # 运行日志
```

## 使用场景

1. **预防性切换**: Token使用超过阈值时自动切换
2. **时间窗口切换**: 不同时段使用不同账户
3. **成本优化**: 优先使用免费额度，付费账户做备份
4. **故障恢复**: 主账户失败时自动fallback

## 安全考虑

- API密钥加密存储（考虑1Password集成）
- 配置文件不提交到版本控制
- 访问日志记录
- 定期密钥轮换提醒

## 状态

详见 [STATUS.md](./STATUS.md)
