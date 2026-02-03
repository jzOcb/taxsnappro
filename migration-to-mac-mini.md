# Migration Plan: VPS → Mac Mini

**Status:** Planning Phase  
**Date:** 2026-02-03  
**Current:** DigitalOcean VPS (Ubuntu 24.04, 1 vCPU, 1GB RAM)  
**Target:** Mac Mini (macOS, better specs, local hardware)

## Critical Requirements

**Must preserve:**
1. All project data and code
2. Configuration and credentials
3. Memory and context
4. Agent identity/continuity
5. Running services and cron jobs
6. Git history and uncommitted work

**Must verify:**
1. All services start correctly
2. All integrations work (Telegram, etc.)
3. All skills function
4. No data loss
5. Performance improvements realized

---

## Current State Inventory

### 1. Files & Projects
```bash
# Workspace
/home/clawdbot/clawd/
├── Projects (kalshi, openclaw-hardening, etc.)
├── Memory (memory/*.md)
├── Scripts (scripts/*.sh)
├── Skills (skills/*)
├── Config (*.md, *.json)
└── Git repos (multiple)

# Clawdbot config
~/.clawdbot/
├── clawdbot.json
├── agents/
├── browser/
├── credentials/
├── telegram/
└── identity/

# System
/opt/clawdbot/        # Installation
/opt/clawdbot.env     # Environment variables
```

### 2. Running Services
```bash
# Check what's running
ps aux | grep -E "clawdbot|gateway|bun|node" | grep -v grep

# Cron jobs
crontab -l

# Systemd services
systemctl --user list-units | grep clawdbot
```

### 3. Credentials & Secrets
```bash
# Environment variables
/opt/clawdbot.env

# SSH keys
~/.ssh/

# Git credentials
git config --list

# API keys (need inventory)
```

### 4. Network & External Services
```bash
# Telegram bot
# GitHub authentication
# Tailscale (if configured)
# Domain/DNS (if any)
```

---

## Research Needed

### Mac Mini Specific
- [ ] Clawdbot official Mac installation
- [ ] macOS vs Linux differences
- [ ] Performance expectations
- [ ] GPU/Metal support for browser/ML
- [ ] Power management (sleep/wake behavior)

### Migration Strategies
- [ ] Full backup → restore approach
- [ ] Selective migration approach
- [ ] Parallel running (test before switchover)
- [ ] Rollback plan if issues

### Tools & Methods
- [ ] rsync for file transfer
- [ ] Git for code migration
- [ ] Config export/import
- [ ] Testing checklist

---

## Next Steps

1. **Inventory current state** (this doc)
2. **Research Mac Mini setup** (Clawdbot docs)
3. **Create backup plan**
4. **Create migration checklist**
5. **Create testing plan**
6. **Create rollback plan**

---

**Status:** Research in progress...
