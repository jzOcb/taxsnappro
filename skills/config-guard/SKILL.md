---
name: config-guard
description: Prevent OpenClaw config changes from crashing the gateway. Auto-backup, schema validation, critical field checks, and auto-rollback. Use before any config.apply, config.patch, or openclaw.json edit.
metadata:
  openclaw:
    emoji: "🛡️"
---

# Config Guard 🛡️

**Stop AI agents from killing themselves by editing their own config wrong.**

OpenClaw agents have full access to `openclaw.json` — the file that controls the gateway, channels, models, and tools. One bad edit and the gateway crashes. The agent goes offline. Nobody can fix it remotely.

This skill prevents that.

## The Problem

Real incidents (all from 2026-02-04, same day):

| What happened | Root cause |
|---|---|
| Gateway crashed after update | AI added unknown config fields (`auth`, `fallbacks`) |
| Model not found | AI wrote `claude-sonnet-4.5` (dots) instead of `claude-sonnet-4-5` (hyphens) |
| Telegram stopped working | Config change silently wiped the channel section |
| browser.profiles error | AI forgot the required `color` field (must be hex) |
| Plugin SDK missing | Update broke module paths, no validation caught it |

**Core truth: AI doesn't know correct config formats. It guesses. Wrong guesses crash systems.**

## What Config Guard Does

### Before config changes:
1. **Auto-backup** — `cp openclaw.json` to timestamped backup
2. **JSON syntax check** — catches malformed JSON before it hits the gateway
3. **Schema validation** — checks required fields, correct types, valid values
4. **Semantic checks** — catches AI-specific mistakes:
   - Model names with dots instead of hyphens
   - Missing required fields (browser.profiles.color)
   - Unknown top-level keys
   - Placeholder values in sensitive fields
5. **Critical field diff** — warns if Telegram channel, auth tokens, or tool deny lists changed

### After config changes (with `--restart`):
6. **Gateway health check** — polls gateway for up to 30s
7. **Auto-rollback** — if gateway doesn't recover, restores backup automatically

## Usage

### As a script (recommended):
```bash
# Validate current config
bash scripts/config-guard.sh check

# Validate → backup → apply → verify
bash scripts/config-guard.sh apply --restart

# Show what changed vs last backup
bash scripts/config-guard.sh diff

# Emergency rollback
bash scripts/config-guard.sh rollback
```

### As a git hook:
```bash
# Install the pre-commit hook
cp scripts/pre-config-hook.sh /path/to/repo/.git/hooks/pre-commit
# Or chain it in your existing hook
```

### For AI agents:

## ⛔ CRITICAL: DO NOT USE `gateway config.patch` DIRECTLY

The `gateway` tool's `config.patch` action **bypasses all validation**. One wrong model name, one invalid field, and the gateway crashes. You go offline. Nobody can fix you remotely.

**Use `safe-config-patch.sh` instead:**

```bash
# ✅ CORRECT: Validates before applying
bash scripts/safe-config-patch.sh '{"agents":{"defaults":{"model":"anthropic/claude-opus-4-5"}}}'

# ❌ WRONG: No validation, will crash on bad input  
gateway config.patch raw='{"agents":{"defaults":{"model":"claude-opus-4.5"}}}'  # dots = crash
```

## MANDATORY WORKFLOW

1. **Use the safe wrapper** (validates → backs up → applies → verifies):
   ```bash
   bash /path/to/config-guard/scripts/safe-config-patch.sh '<json-patch>'
   ```

2. **Never guess config field names or values.** If unsure:
   - Use `gateway config.schema` to check valid fields
   - Use `gateway config.get` to see current values
   - Change ONE field at a time

3. **For complex changes**, validate first:
   ```bash
   bash /path/to/config-guard/scripts/config-guard.sh check ~/.openclaw/openclaw.json
   ```

4. **If gateway dies**, rollback:
   ```bash
   bash /path/to/config-guard/scripts/config-guard.sh rollback
   ```

## Why This Matters

On 2026-02-05, the agent used `gateway config.patch` to upgrade to Claude Opus 4.6. The model ID was wrong (`claude-opus-4-6-20260205` doesn't exist yet). Gateway kept crashing and falling back to 4.5. Human had to manually fix.

**config-guard existed but was bypassed** because the agent used the raw gateway tool instead of the validated wrapper. This is exactly the failure mode this skill was designed to prevent.

## Checks Performed

| Check | What it catches |
|---|---|
| JSON syntax | Malformed JSON, trailing commas, unquoted keys |
| Unknown top-level keys | AI inventing fields like `fallbacks`, `auth` at wrong level |
| Model name format | `claude-sonnet-4.5` → should be `claude-sonnet-4-5` |
| browser.profiles.color | Missing required field, non-hex values |
| commands.native | Missing required fields |
| Placeholder values | `your-token-here`, `sk-xxx` in sensitive fields |
| Empty primary model | No model configured = agent can't think |
| Telegram channel wipe | Silent removal of channel config |
| Auth token removal | Gateway auth accidentally deleted |
| Tool deny list changes | Security-critical tools removed from deny |

## Philosophy

**Prompts are suggestions. Code is law.**

This skill doesn't ask the AI to "please validate before changing config." It provides executable scripts that enforce validation. The pre-commit hook blocks bad configs from being committed. The apply script auto-rollbacks on failure.

The AI doesn't need to cooperate. The code runs regardless.

## Install

```bash
clawdhub install config-guard
# or copy the scripts/ directory to your workspace
```

## Requirements

- `python3` (for JSON parsing and validation)
- `curl` (for gateway health checks)
- `bash` 4+
