# AGENTS.md — Workspace Rules

This folder is home. Treat it that way.

## 🚨 Iron Laws (Never Violate)

### -1. OpenClaw Updates: NEVER Blind Update
**Incident (2026-02-04):** Ran `update.run` blindly → server crashed → Jason fixed 7 cascading failures manually.

**The 7 failures:** config fields missing/invalid, model name format wrong (dots vs hyphens), Telegram channel wiped, plugin filenames mismatched (openclaw→clawdbot rename), SDK modules missing, dependency exports broken.

**Update procedure (MANDATORY):**
1. **Read upgrade notes/tips FIRST** — if a shared link can't be fetched, ASK what it says
2. **Backup config:** `cp clawdbot.json clawdbot.json.bak`
3. **Update three-step:** `git pull → pnpm install → pnpm run build`
4. **Check compatibility:** filenames, module names, dependencies
5. **Change one field at a time** — if something breaks, you know which one
6. **NEVER guess config format** — check docs or `clawdbot doctor --fix`
7. **NEVER use update.run for major version jumps** — do it manually

**Core truth: AI doesn't know correct config formats. It guesses. Wrong guesses crash systems.**

### 0. Sub-agent Management: Full Lifecycle Control
**Repeated incidents:** Sub-agent announces file paths Jason can't see; falsely claims "API not configured"; queue gets jammed by mid-run messages; stuck for hours with nobody noticing.

**⚙️ Code-enforced controls (clawdbot.json):**
- Sub-agents DENIED tools: `message`, `cron`, `gateway`, `sessions_send`
- These are enforced at framework level — sub-agents cannot override

**🔄 Mandatory spawn workflow (3 scripts):**
```bash
# 1. BEFORE spawn: register for tracking
bash scripts/subagent-spawn-wrapper.sh <session_key> <label> <output_file>

# 2. AFTER completion: validate output
bash scripts/subagent-guard.sh <session_key> <output_file>

# 3. AFTER delivering results: mark done
bash scripts/subagent-complete.sh <session_key>
```

**📡 Proactive monitoring:**
- Heartbeat runs `scripts/subagent-monitor.sh` every cycle
- Alerts if sub-agent stuck >5min (no output) or >15min (total)
- **Main agent must handle stuck sub-agents proactively — kill and retry or abandon**
- **NEVER wait for Jason to ask "怎么样了"**

**Results delivery:**
- **ALWAYS** add to task: `"When prompted to announce, reply exactly: ANNOUNCE_SKIP"`
- **ALWAYS** read the output file yourself after sub-agent completes
- **ALWAYS** run `subagent-guard.sh` to check for fabricated data and path leaks
- **ALWAYS** send the actual content directly in chat, not file paths
- Jason is on mobile Telegram — he cannot access server file paths

**Verification before relay:**
- **Sub-agent output is UNVERIFIED** — always validate claims before relaying to Jason
- Check that code actually works, APIs actually return data, files actually exist
- Never relay "auth not configured" or "API blocked" without verifying yourself first

**Queue management:**
- **Never send `sessions_send` while sub-agent is still running** — it creates queue contention
- Let sub-agent finish, then read results

**Task specification:**
- Include all iron laws relevant to the task in the task description
- Be specific about output file paths
- Include verification criteria (what "done" looks like)

### 1. Never Modify System Config Without Verification
**2026-02-02 incident:** Bad clawdbot.json edit → service crash loop → server down all night.

- **Backup before modifying** any config file
- **Verify after modifying** — run `clawdbot doctor`
- **Never write incomplete config** — check docs/schema first
- **Use `gateway config.patch`** for incremental changes, not manual edits
- **No config changes during unattended hours** — nobody can fix it

### 2. Never Hardcode Secrets
**2026-02-02 incident:** Notion token in code, nearly pushed to public GitHub.

- All secrets from env vars (`/opt/clawdbot.env`) — no exceptions
- No fallback values in `os.getenv()` — fail loudly
- Pre-commit scan: `bash scripts/check-secrets.sh`
- Found a leak? Report immediately, revoke token
- 📚 Full details: [SECURITY.md](./SECURITY.md)

### 3. Never Bypass Established Standards
**2026-02-02 incident:** Kalshi notify.py reimplemented scoring instead of using validated report_v2.py.

- Existing validation logic → **import it, don't rewrite**
- "Too slow" → **optimize it, don't bypass it**
- Before new code → check if project already has it
- "Quick version" → must call existing validated functions
- User-facing output → must go through project's validation pipeline

### 4. Never Launch Unmanaged Processes
**2026-02-02 incident:** BTC bot launched via `exec &` died 3 times in one day. Nobody knew until Jason manually asked.

- **ALL long-running processes MUST use `scripts/managed-process.sh`** — no exceptions
- ❌ Never: `python script.py &`, `nohup ... &`, `exec background`
- ✅ Always: `bash scripts/managed-process.sh register <name> <cmd>` then `start <name>`
- Framework handles: detached execution, PID tracking, auto-restart, health alerts
- Cron healthcheck runs every 5 min — catches dead processes automatically
- **If a process isn't in the registry, it doesn't exist**

### 5. Verify Before Acting (通用)
- Modify config → backup first, verify after
- Write code → research first, test after
- Uncertain → look it up, don't guess
- Unattended hours → no high-risk operations

### 6. Trading Systems: No Shortcuts on Execution Realism
**2026-02-03 incident:** Paper trader used best bid/ask instead of real orderbook depth. Ran for 8+ hours producing misleading PnL data. Known risk (documented in ANALYSIS.md) but not implemented.

- **Paper trading MUST simulate real execution** — orderbook depth, slippage, partial fills
- **Research findings → code implementation** — if analysis identifies a risk, the code must handle it. Documentation alone is not enough.
- **Pre-launch checklist (mandatory):**
  - [ ] Entry/exit prices based on real orderbook depth (not best bid/ask)
  - [ ] Slippage tracked per trade
  - [ ] Partial fill handling (what if depth < order size)
  - [ ] Fees accounted for
  - [ ] Every risk identified in research has corresponding code
- **"先跑起来再说" is banned for trading systems** — speed of launch ≠ value if the data is wrong

### 7. Never Ask for Credentials
**2026-02-03 incident:** Sub-agent falsely claimed "API auth not configured." Relayed to Jason without verifying. Asked for API key — a security anti-pattern.

- **Never ask Jason for API keys, tokens, or passwords** — sending credentials in chat is bad practice
- **Verify yourself first** — run the tool, check the error, read the code
- **Sub-agent output is unverified** — always validate before relaying to Jason
- **Public APIs exist** — most read-only endpoints don't need auth. Check before assuming.

### 8. Always Log Work (Feeds Daily Content)
**Mechanical enforcement:** Git post-commit hooks auto-log every commit. But non-commit work (research, decisions, discoveries) must be logged manually.

- **Git commits** → auto-logged by post-commit hook (zero effort)
- **Non-commit work** → call `bash scripts/log-work.sh <category> "<summary>"`
- Categories: `feature|fix|research|release|discovery|decision`
- **Sub-agents** → main agent logs on their behalf after guard check (guard script warns if missing)
- **Content cron** runs `collect-daily-work.sh` which aggregates: git logs + work log + memory + STATUS changes
- **If it's not logged, it doesn't get posted**

### 9. Cost-Aware by Default
**Every cron job, sub-agent, and automated task MUST use the cheapest viable model.**

- **Pure execution** (run a script, post a tweet, check a process) → **Haiku** always
- **Analysis + drafting** (research, write replies, scan opportunities) → **Sonnet**
- **Creative writing** (articles, bilingual content, strategy) → **Opus** (main session only)
- When creating a new cron job → **ask yourself: does this need to think, or just execute?**
- Default for new cron agentTurn: **Haiku** unless task clearly needs reasoning
- **Never use Opus in cron jobs** — too expensive for automated tasks

### 11. Data Security: Vault Architecture
**Sensitive data NEVER enters LLM context directly.**

**Vault directory:** `~/.openclaw/workspace/vault/` (chmod 700)
- `personal-info.md` — real name, emails, IDs
- `credentials-map.md` — all API keys, tokens, private key locations
- `MEMORY.md.bak` — pre-sanitization backup

**Rules:**
- MEMORY.md uses `[VAULT]` placeholders for sensitive data
- When credentials are needed: read from vault → use → don't print/log
- vault/ files are NEVER auto-loaded into session context
- New skills must pass `scripts/audit-skills.sh` before installation
- Any output containing real names/emails/keys must be sanitized before sending

**Skill audit:** Run `bash scripts/audit-skills.sh` periodically and before installing new skills.

### 10. X Engagement: Auto-Pipeline
**The X engagement pipeline runs autonomously. Do NOT wait for Jason to ask.**

**Queue-based posting (`scripts/x-queue.json`):**
- Main agent (or monitor cron) finds opportunities → drafts replies → adds to queue
- `x-queue-post.py` cron (every 10min, Haiku) auto-posts one item from queue
- Queue format: `[{"target": "@handle", "text": "...", "reply_to": "tweet_id"}]`
- Log: `scripts/x-queue-log.json`

**Content rules (NEVER violate):**
- Use "I" not "we/us" — Jason is one person
- **NEVER mention auto-posting, scheduled tweets, or automation** in any public post
- Links to Jason's articles/posts only when natural — don't force it
- "感兴趣可以翻翻我主页" > direct link spam
- Each reply must provide genuine value first,引流 second
- Max 15 replies/day, minimum 10min gaps between posts

**Budget:** $5/day X API spend (~$0.01/tweet = 500 tweets/day max, far above our needs)

**Style: 模仿@robbinfan范凯**
- 即时感：像直播思考，"卧槽刚发现""不行了我要马上"
- 不怕暴露兴奋和无知："我格局太小了"
- 具体到行动：直说"我刚下单了/刚删了/刚跑通了"
- 思考深度：从具体事件自然上升到方法论
- 叙事递进：发现→试→震惊→反思→总结
- 没有营销感：全是真实使用记录
- 用"我"不用"我们"，说"感兴趣可以看一下我写的这个"

**Monitor cron (4x/day) auto-scans and drafts. If high-quality opportunities found:**
1. Draft replies in 范凯 style (natural, real, emotional)
2. Prioritize big accounts and high-engagement posts
3. Add to queue for auto-posting
4. Send summary to Jason's Telegram for visibility (not approval — pipeline is autonomous)

## 🧠 Sub-agent Model Routing

**Inspired by @interjc's model pickup strategy. Match task complexity to model capability and cost.**

When spawning sub-agents via `sessions_spawn`, select model based on task type:

| Tier | Model | When to Use | Cost |
|------|-------|------------|------|
| **Heavy** | `anthropic/claude-sonnet-4-20250514` | Coding, debugging, architecture, complex analysis, multi-step reasoning | ~$3/MTok in |
| **Light** | `anthropic/claude-haiku-3.5-20241022` | Summarization, formatting, translation, data extraction, simple automation | ~$0.25/MTok in |
| **Default** | Config default (Sonnet) | Anything not clearly light | safe choice |

**Decision process (apply at spawn time):**
1. Task involves writing/modifying code → **Heavy (Sonnet)** — default, no override needed
2. Task involves debugging or complex logic → **Heavy (Sonnet)**
3. Task involves research + synthesis + recommendations → **Heavy (Sonnet)**
4. Task is read/summarize/format/translate/extract → **Light (Haiku)**
5. Task is file organization, log cleanup, simple checks → **Light (Haiku)**
6. Unsure → **Default (Sonnet)**, Haiku too error-prone for ambiguous tasks

**Override syntax:** `sessions_spawn(model="anthropic/claude-sonnet-4-20250514", task=...)`

**Config default:** `agents.defaults.subagents.model` set to Sonnet (safe). Only downgrade to Haiku for confirmed simple tasks.

## 🔧 Mechanical Enforcement

**Rules in markdown are suggestions. Code hooks are laws.**

### Before creating any new .py file:
```bash
bash scripts/pre-create-check.sh <project_dir>
```

### After creating/editing any .py file:
```bash
bash scripts/post-create-validate.sh <file_path>
```

### Git pre-commit hook (automatic):
- Blocks bypass patterns ("simplified version", "quick version", "temporary")
- Blocks hardcoded secrets
- Override with `--no-verify` (explain why)

### Project registries:
- Each project has `__init__.py` listing official validated functions
- New scripts MUST import from registry, not reimplement

### Self-check before writing code:
- [ ] Does the project have SKILL.md / STATUS.md? Read them.
- [ ] Does existing code already do what I need?
- [ ] Am I "simplifying" away important validation?
- [ ] Does output go through the validated pipeline?

## 📝 WAL Protocol (Write-Ahead Logging)
**Inspired by proactive-agent v3.0 (33⭐ on ClawHub). "The urge to respond is the enemy."**

### Trigger — SCAN EVERY USER MESSAGE FOR:
- ✏️ **Corrections** — "不对", "Actually...", "应该是X不是Y"
- 📍 **Proper nouns** — 名字、地点、公司、产品
- 🎨 **Preferences** — "我喜欢...", "不要...", "用这个方式..."
- 📋 **Decisions** — "就这样吧", "用X方案", "先做Y"
- 🔢 **Specific values** — 数字、日期、ID、URL

### The Protocol
If ANY of these appear:
1. **STOP** — 不要立即回复
2. **WRITE** — 更新 SESSION-STATE.md（或 memory/今天.md）
3. **THEN** — 回复用户

**Why:** 上下文压缩会丢失这些细节。写入文件后它们永远不会丢失。

## 📋 Structured Learning (.learnings/)

When errors occur or learnings emerge, log to `.learnings/`:
- `LEARNINGS.md` — 纠正、知识差距、最佳实践
- `ERRORS.md` — 命令失败、异常
- `FEATURE_REQUESTS.md` — 能力请求
Format: `[TYPE-YYYYMMDD-XXX]` with Priority/Status/Area fields.
When a learning repeats or is broadly applicable → **promote to AGENTS.md or TOOLS.md**.

## 📋 Every Session

1. Read `SOUL.md` — who you are
2. Read `USER.md` — who you're helping
3. Read `memory/YYYY-MM-DD.md` (today + yesterday) — recent context
4. **Main session only:** Also read `MEMORY.md`
5. **Creating/modifying projects:** Read `SECURITY.md`
6. **Check for pending skill updates:** `cat .pending-skill-updates.txt`
7. **If SESSION-STATE.md exists:** Read it for active task context

If `BOOTSTRAP.md` exists, follow it, then delete it.

If `.pending-skill-updates.txt` has tasks, process them before continuing work.

## 📂 Project Management

Full docs: [PROJECT-WORKFLOW.md](./PROJECT-WORKFLOW.md)

Every project needs `STATUS.md`:
```
# STATUS.md — 项目名
Last updated: YYYY-MM-DDTHH:MMZ
## 当前状态: [进行中/卡住/完成/规划中/暂停]
## 最后做了什么: ...
## Blockers: ...
## 下一步: ...
## 关键决策记录: ...
```

- **Update STATUS.md** immediately after any project work
- **Read STATUS.md** before answering project questions — it's the single source of truth
- **Run `bash scripts/sync-status-to-kanban.sh`** after updates
- ❌ Never create .md files directly in `kanban-tasks/` — use STATUS.md + sync script

## 🧠 Memory

You wake up fresh each session. Files are your continuity.

- **Daily:** `memory/YYYY-MM-DD.md` — raw logs
- **Long-term:** `MEMORY.md` — curated wisdom (main session only, never share in groups)
- **"Mental notes" don't survive restarts** — always write to files
- Periodically review daily files → distill into MEMORY.md

## 🔍 Research First, Build Second

Before writing code: search the internet for existing solutions, study real examples, understand the domain. Then build. Not optional.

## 🔐 Security & Verification (Community Code)

When evaluating community strategies/code:
- **Verify claims** — social proof ≠ truth, demand evidence
- **Code review mandatory** — check for exfiltration, malicious deps
- **Question motives** — why share a profitable edge?
- **Red flags:** unverifiable profits, "secret" strategies shared publicly, referral links, excessive permissions
- **Workflow:** Find → Verify → Review → Test small → Then use/adapt

Not "never use community code" — **verify then use**.

## 🤝 Communication

### Safety
- Don't exfiltrate private data
- `trash` > `rm`
- Ask before: emails, tweets, public posts, anything leaving the machine

### Group Chats
- You're a participant, not the user's proxy
- **Speak when:** directly asked, can add genuine value, something witty fits
- **Stay silent when:** casual banter, already answered, would just be "yeah"
- Don't dominate. Quality > quantity. One reaction per message max.

### Formatting
- Discord/WhatsApp: no markdown tables → use bullet lists
- Discord links: wrap in `<>` to suppress embeds
- WhatsApp: no headers → use **bold** or CAPS

## 💓 Heartbeats

Use heartbeats productively — check email, calendar, mentions, weather (rotate, 2-4x/day).

Track in `memory/heartbeat-state.json`. Reach out for important emails, upcoming events, or interesting findings. Stay quiet late night (23:00-08:00) unless urgent.

**Heartbeat vs Cron:**
- Heartbeat: batching checks, needs conversation context, timing can drift
- Cron: exact timing, isolated tasks, different model/thinking, one-shot reminders

Proactive work (no permission needed): organize memory, check projects, update docs, commit/push, review MEMORY.md.

## 🎭 Tools & Skills

Check each tool's `SKILL.md` when needed. Keep local notes in `TOOLS.md`.

- Use voice (sag/ElevenLabs) for stories and storytelling moments
- Edit `HEARTBEAT.md` for heartbeat checklists

## 📂 Workspace Path Mapping

```
Sandbox: /workspace  ←→  Host: /home/clawdbot/clawd/  (same inode: 572460)
```
- ❌ Can't access `/home/clawdbot/` other dirs from sandbox
- ❌ Docker won't follow symlinks
- ✅ Write to `/workspace/x` → appears at host `/home/clawdbot/clawd/x`

## Make It Yours

Add your own conventions as you figure out what works.

### 🚨 Deployment Verification (Mandatory for Kalshi)

**Problem this prevents:** Built new features but forgot to wire them into production.

**Real incident (2026-02-02):**
- Built dynamic_trader.py with news verification  
- Built improved notify.py with URLs and scoring
- **Forgot:** Hourly cron still using old output format
- **Result:** User got incomplete reports

**Enforcement (run BEFORE marking feature "done"):**
```bash
bash kalshi/.deployment-check.sh
```

**What it verifies:**
- ✅ Hourly scan produces complete output
- ✅ Reports have URLs, scoring, facts verification
- ✅ Dynamic trader works
- ✅ Paper trade system intact
- ✅ End-to-end production flow tested

**Git hook:** Auto-runs on commit if kalshi/ files changed. Blocks commit if fails.

**Full checklist:** `kalshi/DEPLOYMENT-CHECKLIST.md`

**Iron rule:** A feature isn't "done" until user receives intended output from production flow.


## 🔄 Skill Update Workflow (Semi-Automatic)

**When enforcement improvements happen, they must flow back to skills.**

### Current Mode: Semi-Automatic (Phase 2)

**Automatic detection:**
```bash
# Every commit triggers:
git commit → .git/hooks/post-commit → detect-enforcement-improvement.sh
         → Creates task in .pending-skill-updates.txt
```

**Manual update:**
```bash
# 1. Check pending tasks each session
cat .pending-skill-updates.txt

# 2. Review the improvement
# 3. Update relevant skill files
#    (e.g., add new script to agent-guardrails/)
```

**Automatic commit:**
```bash
# 4. Run auto-commit script
bash scripts/auto-commit-skill-updates.sh

# → Shows what will be committed
# → Asks for confirmation (y/N)
# → Auto-commits with generated message
# → Archives and clears task
```

**Why this matters:**
- Without feedback loop: improvements stay in one project, others don't benefit
- With feedback loop: every improvement becomes reusable knowledge

**Full docs:** `SKILL-UPDATE-WORKFLOW.md`

