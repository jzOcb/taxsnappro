# Config Guard 🛡️

[🇨🇳 中文文档](./README_CN.md)

[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://clawdhub.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](./SKILL.md)

## Stop AI agents from killing themselves by editing their own config wrong.

> Prompts are suggestions. Code is law.

OpenClaw agents have full access to `openclaw.json` — the file that controls the gateway, channels, models, and tools. One bad edit = gateway crash. Agent goes offline. Nobody can fix it remotely.

This skill prevents that.

## The Problem

Real incidents (all from the same day):

| What happened | Root cause |
|---|---|
| Gateway crashed after update | AI added unknown config fields (`auth`, `fallbacks`) |
| Model not found | AI wrote `claude-sonnet-4.5` (dots) instead of `claude-sonnet-4-5` (hyphens) |
| Telegram stopped working | Config change silently wiped the channel section |
| browser.profiles error | AI forgot the required `color` field (must be hex) |
| Plugin SDK missing | Update broke module paths, no validation caught it |

**7 cascading failures. 1 root cause: AI doesn't know correct config formats. It guesses.**

## What It Does

### Before config changes:
1. **Auto-backup** — timestamped copy before any change
2. **JSON syntax check** — catches malformed JSON
3. **Schema validation** — required fields, correct types, valid values
4. **Semantic checks** — catches AI-specific mistakes:
   - Model names with dots instead of hyphens
   - Missing required fields (`browser.profiles.color`)
   - Unknown top-level keys
   - Placeholder values in sensitive fields
5. **Critical field diff** — warns if Telegram channel, auth tokens, or tool deny lists changed

### After config changes:
6. **Gateway health check** — polls for up to 30s
7. **Auto-rollback** — if gateway doesn't recover, restores backup automatically

## Quick Start

```bash
# Install via ClawHub
clawdhub install config-guard

# Or clone directly
git clone https://github.com/jzOcb/config-guard
```

### Usage

```bash
# Validate current config
bash scripts/config-guard.sh check

# Validate → backup → apply → verify (with auto-rollback)
bash scripts/config-guard.sh apply --restart

# Show what changed vs last backup
bash scripts/config-guard.sh diff

# Emergency rollback
bash scripts/config-guard.sh rollback
```

### As a git hook

```bash
cp scripts/pre-config-hook.sh /path/to/repo/.git/hooks/pre-commit
```

## Checks Performed

| Check | What it catches |
|---|---|
| JSON syntax | Malformed JSON, trailing commas, unquoted keys |
| Unknown top-level keys | AI inventing fields like `fallbacks`, `auth` |
| Model name format | `claude-sonnet-4.5` → should be `claude-sonnet-4-5` |
| browser.profiles.color | Missing required field, non-hex values |
| Placeholder values | `your-token-here`, `sk-xxx` in sensitive fields |
| Empty primary model | No model configured = agent can't think |
| Telegram channel wipe | Silent removal of channel config |
| Auth token removal | Gateway auth accidentally deleted |
| Tool deny list changes | Security-critical tools removed from deny |

## For AI Agents

**MANDATORY WORKFLOW when editing openclaw.json:**

1. Run `config-guard.sh check` before ANY change
2. Never guess config field names — use `gateway config.schema`
3. Change ONE field at a time
4. Run `config-guard.sh apply --restart` after changes
5. If gateway dies → `config-guard.sh rollback`

## Requirements

- `bash` 4+
- `python3`
- `curl`

## 🛡️ Part of the AI Agent Security Suite

| Tool | What It Prevents |
|------|-----------------|
| **[agent-guardrails](https://github.com/jzOcb/agent-guardrails)** | AI rewrites validated code, leaks secrets, bypasses standards |
| **[config-guard](https://github.com/jzOcb/config-guard)** | AI writes malformed config, crashes gateway |
| **[upgrade-guard](https://github.com/jzOcb/upgrade-guard)** | Version upgrades break dependencies, no rollback |
| **[token-guard](https://github.com/jzOcb/token-guard)** | Runaway token costs, budget overruns |
| **[process-guardian](https://github.com/jzOcb/process-guardian)** | Background processes die silently, no auto-recovery |

📖 **Read the full story:** [I audited my own AI agent system and found it full of holes](https://x.com/xxx111god/status/2019455237048709336)

## License

MIT

## 🛡️ Part of the OpenClaw Security Suite

This skill is one of four guards in the hardening toolkit:

| Guard | Purpose | Protects Against |
|-------|---------|------------------|
| **[agent-guardrails](https://github.com/jzOcb/agent-guardrails)** | Pre-commit hooks + secret detection | Code leaks, unsafe commits |
| **[config-guard](https://github.com/jzOcb/config-guard)** | Config validation + auto-rollback | Gateway crashes from bad config |
| **[upgrade-guard](https://github.com/jzOcb/upgrade-guard)** | Safe upgrades + watchdog | Update failures, cascading breaks |
| **[token-guard](https://github.com/jzOcb/token-guard)** | Usage monitoring + cost alerts | Budget overruns, runaway costs |

📚 **Full writeup:** [4-Layer Defense System for AI Agents](https://x.com/xxx111god/status/2019096285853139083)
