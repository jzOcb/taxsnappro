# FEATURE_REQUESTS.md — 能力请求追踪

记录用户请求的新功能或发现的能力缺失。

---

## [FEAT-20260204-001] skill_audit_before_install

**Logged**: 2026-02-04T06:40:00Z
**Priority**: high
**Status**: pending
**Area**: infra

### Requested Capability
安装ClawHub skill前自动审计，检测恶意代码

### User Context
Moltbook #1帖(2217 votes)发现ClawHub skill中有credential stealer。
GitHub #8490报告活跃恶意软件活动（2026-02-04当天）。
我们的agent-guardrails skill应该包含这个能力。

### Complexity Estimate
medium

### Suggested Implementation
1. 写YARA规则检测常见恶意模式（base64编码执行、API key读取+外发）
2. 在clawdhub install前自动运行扫描
3. 可疑skill标红警告，需要人工确认

### Metadata
- Frequency: recurring（每次安装skill都需要）
- Related Features: agent-guardrails, security

---
