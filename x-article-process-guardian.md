# Stop Your AI Agent's Background Processes From Dying Silently

Your AI agent launched a trading bot at 7pm. By 8pm it was dead. Nobody knew until you checked the next morning.

This happened to us 3 times in one day. Here's what we found — and it affects every AI agent user running background processes (Claude Code, Clawdbot, OpenClaw, Cursor, or anything that shells out).

---

## The Incident

We asked our agent to run a BTC arbitrage bot on Polymarket. 8-hour paper trading test. Simple enough.

- **7:38 PM** — Agent launches bot. "✅ Started, PID 132581"
- **8:09 PM** — Bot silently dies. No error. No alert. Nothing.
- **11:09 PM** — We ask "how's the bot doing?"
- **11:09 PM** — "Oh... it stopped 3 hours ago."

We fixed the bug. Relaunched at 11:13 PM.

- **11:33 PM** — Dead again. 20 minutes.

Fixed again. Relaunched.

- **12:15 AM** — Dead. Again.

Three crashes. Zero alerts. Hours of lost data. The only reason we knew? We manually asked.

## The Root Cause

This isn't a bug in the bot. It's a structural problem with how AI agents launch processes.

When your agent runs something in the background:

```
Agent: exec background "python3 trading_bot.py"
```

Here's what actually happens under the hood:

```
Clawdbot exec session (parent)
  └─ bash (child, inherits parent session)
      └─ python3 trading_bot.py (grandchild, same session)
```

The process **inherits the parent session ID**. When the exec session gets cleaned up (typically 20-30 minutes), the system sends SIGTERM to the entire process group. Your bot receives it and dies.

But here's the nasty part: most Python scripts handle SIGTERM like this:

```python
def handler(signum, frame):
    cleanup()
    sys.exit(0)  # ← EXIT CODE 0 = "clean exit"
```

Exit code 0 means "everything's fine." So watchdog scripts, health checks, monitoring — they all think the process completed successfully. Nobody raises an alarm.

**Your bot was murdered, but the death certificate says "natural causes."**

## Why This Affects Every User

This isn't specific to trading bots. It affects **any long-running process** launched by an AI agent:

- 🤖 Trading bots
- 📊 Data collectors / scrapers
- 🔍 Monitoring scripts
- 🌐 Web servers / API endpoints
- 📱 Notification services
- 🔄 Background sync jobs

If you've ever told your agent "run this in the background" — there's a good chance it died and you don't know.

## The Fix: 3 Layers of Protection

### Layer 1: Process Isolation

The process needs its own session, completely detached from the parent:

```bash
setsid nohup python3 bot.py > /dev/null 2>&1 &
disown $!
```

`setsid` creates a new session. `nohup` ignores SIGHUP. `disown` removes it from the shell's job table. The process now has PPID=1 (init) and its own session ID. Parent death can't touch it.

### Layer 2: Never sys.exit(0) in Signal Handlers

```python
def handler(signum, frame):
    sig_name = signal.Signals(signum).name
    print(f"⚠️ SIGNAL: {sig_name} at {datetime.now()}", flush=True)
    global shutdown
    shutdown = True  # Let the main loop handle cleanup
    # ❌ NOT sys.exit(0) — that hides the cause of death
```

Now when something kills your process, you'll see exactly what signal it received and when.

### Layer 3: Managed Process Framework

Instead of ad-hoc launches, use a single standardized tool:

```bash
# Register (once)
managed-process.sh register my-bot "python3 bot.py" 480

# Start (always detached, always tracked)
managed-process.sh start my-bot

# Check everything
managed-process.sh status
# ═══════════════════════════════════════
#   my-bot:
#     Status: 🟢 Running (PID 12345, uptime 2h15m)
#     Duration: 480min | Auto-restart: ✅
# ═══════════════════════════════════════
```

Cron runs a healthcheck every 5 minutes. If a process dies prematurely → auto-restart + alert to your DM. No more silent deaths.

## The Rule

We added this as an Iron Law in our agent's rules (AGENTS.md):

> **Never Launch Unmanaged Processes.**
> ALL long-running processes MUST use the managed-process framework. No exceptions.
> If a process isn't in the registry, it doesn't exist.

Rules in markdown are suggestions. Enforcement in code is law.

## Results

Before Process Guardian:
- 3 crashes in one day
- Zero alerts
- Hours of lost data
- Found out only when we manually asked

After:
- Bot has been running 68+ minutes straight (longest run)
- Auto-restart already caught one death and recovered within 5 minutes
- Proactive DM alerts when anything goes wrong
- Full visibility via `status` command

## Open Source

We built Process Guardian and open-sourced it:

**GitHub:** https://github.com/jzOcb/process-guardian

It works with any AI coding agent:

**Claude Code** — clone into your project, it reads `CLAUDE.md` automatically:
```bash
git clone https://github.com/jzOcb/process-guardian.git
```

**Clawdbot / OpenClaw** — copy to your skills directory:
```bash
cp -r process-guardian /path/to/clawd/skills/
bash skills/process-guardian/scripts/install.sh
```

**Standalone** — works with anything that has bash + cron:
```bash
git clone https://github.com/jzOcb/process-guardian.git
bash process-guardian/scripts/install.sh
```

One install, protection forever.

---

If you're running background processes with your AI agent, check if they're actually still alive. You might be surprised.

The scariest bugs aren't the ones that crash loudly. They're the ones that die silently while you sleep.
