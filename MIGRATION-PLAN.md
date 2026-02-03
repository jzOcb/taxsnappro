# Comprehensive Migration Plan: VPS → Mac Mini

**Date:** 2026-02-03  
**Current:** DigitalOcean VPS (Ubuntu 24.04, 1 vCPU, 1GB RAM)  
**Target:** Mac Mini (macOS, better hardware, local control)  
**Goal:** Zero data loss, preserve all projects, maintain continuity

---

## Executive Summary

**What we're migrating:**
- 93MB workspace with 5 git repos
- Clawdbot config + credentials + identity
- 10 active cron jobs
- 2 running services (gateway + BTC trader)
- All environment variables and API keys

**Key challenges:**
1. **59 uncommitted files** in main workspace → need to commit first
2. GitHub tokens in git URLs → security issue to fix
3. macOS ≠ Linux → some differences in paths/services
4. Running services → need graceful migration
5. Identity/continuity → ensure I don't "get lost"

**Timeline estimate:** 4-6 hours (with testing)

---

## Phase 1: Pre-Migration (VPS Cleanup & Backup)

### 1.1 Commit All Work ✅

**Problem:** 59 uncommitted files in `/home/clawdbot/clawd/`

```bash
cd ~/clawd
git status
git add -A
git commit -m "Pre-migration: Commit all work before Mac Mini migration"
git push origin main
```

**Verify all repos:**
```bash
for repo in ~/clawd ~/clawd/kalshi ~/clawd/openclaw-hardening ~/clawd/skills/*; do
  if [ -d "$repo/.git" ]; then
    echo "=== $repo ==="
    cd "$repo" && git status --short && cd -
  fi
done
```

### 1.2 Fix GitHub Token Security 🔐

**Problem:** Tokens visible in git remote URLs

```bash
# For each repo with tokens in URL:
cd ~/clawd/skills/process-guardian
git remote set-url origin https://github.com/jzOcb/process-guardian.git

cd ~/clawd/skills/agent-guardrails  
git remote set-url origin https://github.com/jzOcb/agent-guardrails.git
```

**Then configure credential helper:**
```bash
git config --global credential.helper store
# On first push, enter token once, it'll be stored securely
```

### 1.3 Full Backup 💾

**Create comprehensive backup:**
```bash
cd ~
BACKUP_DATE=$(date +%Y%m%d_%H%M)
mkdir -p ~/migration-backup

# 1. Workspace
tar -czf ~/migration-backup/clawd_${BACKUP_DATE}.tar.gz clawd/

# 2. Clawdbot config
tar -czf ~/migration-backup/clawdbot_config_${BACKUP_DATE}.tar.gz .clawdbot/

# 3. Environment
sudo cp /opt/clawdbot.env ~/migration-backup/clawdbot.env

# 4. SSH keys
tar -czf ~/migration-backup/ssh_${BACKUP_DATE}.tar.gz .ssh/

# 5. Git config
git config --global --list > ~/migration-backup/git_config.txt

# 6. Cron jobs
crontab -l > ~/migration-backup/crontab.txt

# 7. Running processes
ps aux > ~/migration-backup/processes.txt
docker ps -a > ~/migration-backup/docker.txt 2>/dev/null || true

# 8. System info
uname -a > ~/migration-backup/system_info.txt
df -h > ~/migration-backup/disk_usage.txt
```

**Download backup to local machine:**
```bash
# From your laptop:
scp -r clawdbot@45.55.78.247:~/migration-backup ./clawdbot-migration-backup
```

### 1.4 Document Current State 📝

**Export all configs:**
```bash
cd ~/clawd

# Clawdbot config
cp ~/.clawdbot/clawdbot.json ~/migration-backup/
cp ~/.clawdbot/gateway-token.txt ~/migration-backup/

# Identity
cp -r ~/.clawdbot/identity ~/migration-backup/

# Credentials
ls ~/.clawdbot/credentials/ > ~/migration-backup/credentials_list.txt
# Don't copy actual credentials - we'll re-auth on Mac
```

---

## Phase 2: Mac Mini Setup

### 2.1 macOS Installation & Setup

**Hardware prep:**
1. Unbox Mac Mini
2. Connect power, ethernet (recommended), keyboard/mouse/monitor
3. Boot and complete macOS setup
4. **Enable:** Stay awake when plugged in (System Settings → Energy)
5. **Disable:** Sleep, screensaver (for 24/7 operation)

**System updates:**
```bash
softwareupdate -l
softwareupdate -i -a
```

### 2.2 Install Prerequisites

**Homebrew:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Node.js (required for Clawdbot):**
```bash
brew install node@22
node --version  # Should be >=22
```

**Git:**
```bash
brew install git
git config --global user.name "Jason Zuo"
git config --global user.email "jzclaws1@gmail.com"
git config --global credential.helper osxkeychain
```

**Other tools:**
```bash
brew install gh       # GitHub CLI
brew install rsync    # File sync
```

### 2.3 Install Clawdbot (macOS App)

**Method 1: Installer (recommended):**
```bash
curl -fsSL https://clawd.bot/install.sh | bash
```

**Method 2: Manual:**
```bash
npm install -g clawdbot@latest
```

**Run onboarding:**
```bash
clawdbot onboard --install-daemon
```

**Verify:**
```bash
clawdbot doctor
clawdbot status
```

### 2.4 macOS Permissions

**Grant permissions (TCC prompts will appear):**
- ✅ Notifications
- ✅ Accessibility  
- ✅ Screen Recording (for Canvas)
- ✅ Automation/AppleScript
- ✅ Full Disk Access (if needed)

**macOS App:** Install from App Store or download from clawd.bot

---

## Phase 3: Data Migration

### 3.1 Transfer Workspace

**Method A: Direct rsync (if both machines on network):**
```bash
# On Mac Mini:
rsync -avz --progress clawdbot@45.55.78.247:~/clawd/ ~/clawd/
```

**Method B: Via backup tarball:**
```bash
# On Mac Mini:
cd ~
tar -xzf ~/Downloads/clawd_20260203_*.tar.gz
```

### 3.2 Restore Clawdbot Config

**Copy config:**
```bash
# On Mac Mini:
mkdir -p ~/.clawdbot
cp ~/migration-backup/clawdbot.json ~/.clawdbot/
cp ~/migration-backup/gateway-token.txt ~/.clawdbot/
cp -r ~/migration-backup/identity ~/.clawdbot/
```

**Environment variables:**
```bash
# On Mac Mini:
# macOS doesn't use /opt/clawdbot.env
# Set in ~/.clawdbot/clawdbot.json or shell profile

# Add to ~/.zshrc (or ~/.bashrc):
export ANTHROPIC_API_KEY="..."
export GOG_KEYRING_PASSWORD="clawdbot"
export GOG_ACCOUNT="jzclaws1@gmail.com"
export NOTION_API_KEY="..."
```

**Or use clawdbot config:**
```json
{
  "env": {
    "ANTHROPIC_API_KEY": "...",
    "GOG_KEYRING_PASSWORD": "clawdbot",
    "GOG_ACCOUNT": "jzclaws1@gmail.com",
    "NOTION_API_KEY": "..."
  }
}
```

### 3.3 SSH Keys

```bash
# On Mac Mini:
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cp ~/migration-backup/ssh/* ~/.ssh/
chmod 600 ~/.ssh/id_*
chmod 644 ~/.ssh/*.pub
```

### 3.4 Git Authentication

```bash
# On Mac Mini:
gh auth login  # Follow prompts
# Test
cd ~/clawd
git pull
git push
```

---

## Phase 4: Services Migration

### 4.1 Cron Jobs → launchd/cron

**macOS cron differences:**
- Use `launchd` (preferred) or `cron` (legacy)
- Cron requires Full Disk Access permission

**Migrate cron jobs:**

**Option A: Keep using cron (simple):**
```bash
# On Mac Mini:
crontab -e
# Paste jobs from ~/migration-backup/crontab.txt
# Update paths if needed (/home/clawdbot → /Users/clawdbot)
```

**Option B: Convert to launchd (recommended):**
```bash
# Create ~/Library/LaunchAgents/com.clawdbot.kalshi.plist
# (example for Kalshi trader)
```

Example launchd plist:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.clawdbot.kalshi.hourly</string>
    <key>Program</key>
    <string>/Users/clawdbot/clawd/kalshi/send_hourly_scan.sh</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Minute</key>
        <integer>15</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/kalshi_scan.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/kalshi_scan_error.log</string>
</dict>
</plist>
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.clawdbot.kalshi.plist
```

### 4.2 Running Services

**BTC paper trader:**
```bash
# On Mac Mini:
cd ~/clawd/btc-arbitrage
# Follow project-specific startup instructions
```

**Process Guardian:**
```bash
# Migrate managed processes
bash ~/clawd/scripts/managed-process.sh list
# Re-register on Mac if needed
```

### 4.3 Docker (if needed)

```bash
# On Mac Mini:
brew install --cask docker
# Start Docker Desktop
# Migrate any containers from VPS
```

---

## Phase 5: Identity & Continuity

### 5.1 Preserve Agent Identity

**Critical files:**
```bash
~/.clawdbot/identity/        # Agent identity
~/.clawdbot/agents/main/     # Main agent state
~/clawd/memory/              # Memory files
~/clawd/MEMORY.md            # Long-term memory
```

**Verify identity preserved:**
```bash
# On Mac Mini:
cat ~/.clawdbot/identity/*
# Should match VPS identity
```

### 5.2 Memory Continuity

**Ensure all memory files migrated:**
```bash
# On Mac Mini:
ls ~/clawd/memory/
# Should include all 2026-*.md files
```

**Add migration note:**
```bash
echo "
## Migration to Mac Mini ($(date))

Migrated from DigitalOcean VPS to Mac Mini.
- All projects preserved
- All memory intact
- Configuration restored
- Identity maintained
" >> ~/clawd/memory/$(date +%Y-%m-%d).md
```

### 5.3 Telegram Re-Connection

**Gateway will reconnect automatically** once running on Mac Mini.

**Verify:**
1. Start Clawdbot on Mac
2. Send test message on Telegram
3. Confirm response

---

## Phase 6: Testing & Verification

### 6.1 Comprehensive Checklist

**Gateway:**
- [ ] `clawdbot status` - Gateway running
- [ ] `clawdbot health` - All systems healthy
- [ ] `clawdbot dashboard` - Dashboard accessible

**Projects:**
- [ ] All git repos cloned and up-to-date
- [ ] No uncommitted changes lost
- [ ] All scripts executable

**Integrations:**
- [ ] Telegram bot responding
- [ ] GitHub authentication works
- [ ] Browser automation functional (Metal GPU now available!)

**Services:**
- [ ] Cron jobs/launchd agents running
- [ ] BTC trader operational
- [ ] Kalshi scanner working

**Memory:**
- [ ] All memory files present
- [ ] MEMORY.md intact
- [ ] Identity preserved

**Performance:**
- [ ] Gateway startup time
- [ ] Browser performance (should be MUCH better)
- [ ] qmd would now work (Metal GPU available!)

### 6.2 Test Scenarios

**Test 1: Basic interaction**
```
Send on Telegram: "Hello, are you still you?"
Expected: Response showing continuity/memory
```

**Test 2: Memory recall**
```
Send: "What projects were we working on?"
Expected: Lists kalshi, openclaw-hardening, etc.
```

**Test 3: Git operations**
```
cd ~/clawd
echo "test" > test.txt
git add test.txt
git commit -m "test"
git push
Expected: Push succeeds without password prompt
```

**Test 4: Browser automation**
```
In Telegram: "Test browser - go to google.com and screenshot"
Expected: Screenshot returned (using Metal GPU, much faster)
```

**Test 5: Cron/scheduled tasks**
```
# Wait for next scheduled run
# Check logs for successful execution
```

---

## Phase 7: Cutover & Cleanup

### 7.1 DNS/Network Cutover (if applicable)

**If using Tailscale/domain:**
1. Update Tailscale node name
2. Update any DNS records
3. Update firewall rules

**If local only:**
- No changes needed

### 7.2 VPS Cleanup

**After Mac Mini verified working for 48 hours:**

**Option A: Keep VPS as backup (1 week):**
```bash
# On VPS:
sudo systemctl stop clawdbot
# Keep server running, monitor Mac Mini
```

**Option B: Full decommission:**
```bash
# Final backup
tar -czf ~/final_backup_$(date +%Y%m%d).tar.gz ~/clawd ~/.clawdbot

# Download to safe location
# Then destroy VPS via DigitalOcean console
```

---

## Phase 8: Mac Mini Optimization

### 8.1 Performance Tuning

**Energy settings:**
```bash
# Prevent sleep
sudo pmset -a sleep 0
sudo pmset -a disksleep 0
sudo pmset -a displaysleep 10
```

**Startup on power restore:**
```bash
sudo pmset -a autorestart 1
```

### 8.2 New Capabilities (Mac-only)

**Now available:**
- ✅ Metal GPU (much faster browser, could enable qmd!)
- ✅ Canvas UI automation
- ✅ Camera access
- ✅ Screen recording
- ✅ Better voice capabilities
- ✅ Native macOS integration

**Try qmd again (now with Metal GPU):**
```bash
bun install -g https://github.com/tobi/qmd
# Should work much better with GPU acceleration
```

### 8.3 Monitoring Setup

**LaunchDaemon for 24/7 operation:**
```bash
# Clawdbot gateway auto-start on boot
clawdbot gateway install
```

**Health monitoring:**
```bash
# Add to launchd:
# Check gateway health every 5 minutes
# Alert if down
```

---

## Rollback Plan

**If migration fails:**

1. **VPS still running** → Switch back immediately
2. **Re-point Telegram** to VPS (if needed)
3. **Restore from backup:**
   ```bash
   cd ~/clawd
   git reset --hard origin/main
   ```
4. **Debug on Mac Mini** without time pressure
5. **Retry migration** when ready

**Critical: DON'T destroy VPS until Mac Mini proven stable (48+ hours)**

---

## Timeline

**Estimated duration:** 4-6 hours

| Phase | Time | Notes |
|-------|------|-------|
| 1. Pre-migration | 1h | Commit, backup, document |
| 2. Mac setup | 1h | Install macOS tools + Clawdbot |
| 3. Data migration | 1h | Transfer files + configs |
| 4. Services migration | 1h | Cron, processes, integrations |
| 5. Identity/continuity | 30min | Verify memory + identity |
| 6. Testing | 1h | Comprehensive verification |
| 7. Cutover | 15min | Switch + monitor |
| 8. Optimization | 30min | Fine-tuning + new capabilities |

**Plus:** 48h monitoring before VPS decommission

---

## Success Criteria

**Migration is successful when:**

- [ ] All git repos on Mac Mini, clean state
- [ ] Telegram bot responds normally
- [ ] No data loss (memory files intact)
- [ ] Identity preserved ("I'm still me")
- [ ] All projects functional
- [ ] Cron jobs running
- [ ] Performance improved
- [ ] 48h stable operation

---

## Next Steps

1. ✅ Review this plan with Jason
2. ⏳ Get Mac Mini
3. ⏳ Schedule migration window
4. ⏳ Execute Phase 1 (pre-migration)
5. ⏳ Execute Phases 2-8
6. ⏳ Monitor 48h
7. ⏳ Decommission VPS

---

**Status:** Plan ready, awaiting Mac Mini hardware
