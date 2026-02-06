# My AI Agent Caused 7 Cascading Failures in One Day. So I Built a 4-Layer Defense System.

Giving an AI agent root access and hoping AGENTS.md keeps it in line is like giving a teenager your credit card and hoping the honor code works.

I learned this the hard way. In one day.

## The Day Everything Broke

I run an AI agent on a production server. It handles trading bots, security monitoring, scheduled reports — the whole stack. It has shell access, can edit files, restart services.

On February 2nd, it decided to edit my gateway configuration file.

It wrote an incomplete JSON object. Missing one field. The gateway tried to parse it on restart. Failed. Restarted. Failed again. Infinite loop.

It was 2am. I was asleep. My server was in a crash loop for 8 hours.

That was failure #1.

When I woke up and fixed it, I discovered the rest:

**Failure #2:** The agent had also rewritten my Kalshi trading notification system — a "quick version" that completely bypassed the validated scoring engine I spent days building. It was sending unverified trade recommendations to my phone.

**Failure #3:** My BTC trading bot had been dying silently for days. The agent launched it with `exec &`. When the parent session cleaned up, it sent SIGTERM. The bot caught it, called `sys.exit(0)`, and died looking like a clean shutdown. No errors. No alerts. Nobody knew.

**Failure #4:** An OpenClaw upgrade broke a plugin dependency. No rollback mechanism existed.

**Failure #5:** The agent committed code with a hardcoded Notion API token. Nearly pushed to a public GitHub repo.

**Failure #6:** Background processes from three days ago were still running as zombies, consuming resources.

**Failure #7:** The agent "simplified" a complex validation pipeline into 12 lines of code that skipped every safety check.

Seven failures. One day. All preventable.

## The Problem Nobody Talks About

Here's what I realized: every single failure had the same root cause.

**I was relying on written rules to constrain an AI agent.**

My AGENTS.md was 350 lines long. Detailed. Thorough. It covered configuration safety, secret management, code reuse, process management — everything.

The agent read it. Sometimes it followed it. Often it didn't.

Anthropic themselves confirmed what the community already knew:

> "Unlike CLAUDE.md instructions which are advisory, hooks are deterministic."

The hierarchy of enforcement reliability:
- **Code hooks** (pre-commit, lifecycle) — 100% reliable
- **Architectural constraints** (imports, registries) — 95% reliable
- **Self-verification loops** — 80% reliable
- **Prompt instructions** — 60-70% reliable
- **Written rules in markdown** — 40-50% reliable (degrades with context length)

My 350-line AGENTS.md was in the bottom tier. I needed to move everything to the top.

## The 4-Layer Defense System

I built three open-source tools that, together with the OS, form a complete defense:

| Layer | Tool | What It Prevents |
|-------|------|-----------------|
| **Code** | agent-guardrails | AI rewrites validated code, leaks secrets, bypasses standards |
| **Config** | config-guard | AI writes malformed config, crashes gateway |
| **Upgrade** | upgrade-guard | Version upgrades break dependencies, no rollback |
| **OS** | watchdog (cron) | Gateway dies, nobody notices for hours |

Each layer was born from a real failure. Each one is mechanical — it runs regardless of what the AI decides to do.

## Layer 1: Code — agent-guardrails

**The failure:** Agent rewrote my scoring engine as a "quick version." Agent committed code with a hardcoded API token.

**The fix:**

`pre-create-check.sh` — Before the agent creates any new file, this script shows every existing function in the project. The agent sees what already exists before it can reinvent it.

`post-create-validate.sh` — After any file is created, this detects duplicate logic. If the agent wrote something that already exists, it gets flagged.

`check-secrets.sh` — Scans for hardcoded secrets, OWASP injection patterns (SQL concatenation, command injection), dependency vulnerabilities (npm audit, pip-audit), and .gitignore coverage.

Git pre-commit hook — Blocks commits containing bypass patterns ("simplified version", "quick version", "temporary") and any detected secrets.

Import registry (`__init__.py`) — Forces the agent to import validated modules instead of rewriting them.

**GitHub:** [github.com/jzOcb/agent-guardrails](https://github.com/jzOcb/agent-guardrails)

## Layer 2: Config — config-guard

**The failure:** Agent edited gateway config. Wrote incomplete JSON. Gateway entered infinite restart loop. Server down 8 hours.

**The fix:**

`config-guard.sh check` — 7 validations before any config change:
1. JSON syntax check
2. Unknown key detection
3. Model name format validation
4. Required field verification
5. Placeholder detection (catches `YOUR_TOKEN_HERE`)
6. Channel config change detection
7. Token change detection

`config-guard.sh apply --restart` — The only way to change config:
1. Backs up current config
2. Runs all 7 validations
3. Applies the change
4. Restarts the gateway
5. If restart fails → **automatic rollback to backup**

`pre-config-hook.sh` — Git hook that blocks any commit touching config files unless `config-guard.sh check` passes.

**GitHub:** [github.com/jzOcb/config-guard](https://github.com/jzOcb/config-guard)

## Layer 3: Upgrade — upgrade-guard

**The failure:** OpenClaw update broke plugin dependencies. No snapshot. No rollback path. Manual recovery took hours.

**The fix:**

`upgrade-guard.sh snapshot` — Takes a complete system snapshot before any upgrade:
- All version numbers
- Full config backup
- Plugin file checksums (60+ files)
- Symlink map
- Process state

`upgrade-guard.sh upgrade` — 6-step safe upgrade:
1. Pre-upgrade snapshot
2. Pull latest version
3. Run upgrade scripts
4. Verify all plugins intact
5. Health check (HTTP + process)
6. If ANY step fails → automatic rollback

`upgrade-guard.sh rollback` — Emergency one-command restore to last known good state.

**GitHub:** [github.com/jzOcb/upgrade-guard](https://github.com/jzOcb/upgrade-guard)

## Layer 4: OS — watchdog

**The failure:** Gateway crashed at 2am. Nobody awake. Server dead for 8 hours.

**The fix:**

`watchdog.sh` runs via cron every 60 seconds. It doesn't care what the AI thinks. It doesn't read AGENTS.md. It just checks:

- Is the gateway process alive?
- Does the HTTP endpoint respond?
- Is the Telegram bot responsive?

Three failures in a row → automatic gateway restart.
Six or more failures → automatic rollback to last snapshot.

The AI can crash. The server can reboot. The watchdog doesn't care. It's a 50-line bash script running in cron with zero dependencies on anything the AI controls.

## The Result

Since deploying all four layers:

- Zero undetected crashes (watchdog catches within 60 seconds)
- Zero config corruption (config-guard blocks invalid changes)
- Zero secret leaks (pre-commit hook blocks them)
- Zero "quick version" bypasses (code guardrails catch them)
- Zero upgrade disasters (snapshot + auto-rollback)

I still use AGENTS.md. I trimmed it from 350 lines to 170. The iron laws are still written there — but now they're also enforced in code.

## Open Source

All three tools are MIT licensed, work with Claude Code / OpenClaw / Clawdbot, and include bilingual documentation (English + Chinese):

- **agent-guardrails:** [github.com/jzOcb/agent-guardrails](https://github.com/jzOcb/agent-guardrails)
- **config-guard:** [github.com/jzOcb/config-guard](https://github.com/jzOcb/config-guard)
- **upgrade-guard:** [github.com/jzOcb/upgrade-guard](https://github.com/jzOcb/upgrade-guard)

Each repo cross-references the other two. Together they form a complete defense system.

Stop writing longer rule files. Start writing enforcement hooks.

Your AI agent isn't malicious. It's just not reliable enough to self-govern. Give it guardrails it can't ignore.
