# ERRORS.md — 命令失败和异常追踪

记录命令失败、异常、意外行为。用于避免重复踩坑。

---

## [ERR-20260204-001] nitter_all_instances_down

**Logged**: 2026-02-04T06:10:00Z
**Priority**: low
**Status**: resolved
**Area**: infra

### Summary
所有nitter实例不可用，无法通过代理读取X/Twitter内容

### Error
```
nitter.privacydev.net: SSL TLSV1_ALERT_INTERNAL_ERROR
nitter.poast.org: 503
nitter.1d4.us: DNS resolution failed
nitter.cz: 403 Cloudflare challenge
```

### Context
- 试图搜索OpenClaw相关X帖子
- 所有5个nitter实例全部不可用
- fxtwitter API也返回429 rate limit

### Suggested Fix
配置bird CLI的X cookie实现直接API访问

### Metadata
- Reproducible: yes
- Tags: twitter, nitter, research

---
