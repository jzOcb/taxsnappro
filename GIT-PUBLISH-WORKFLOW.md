# Git Publish Workflow

**Rule: Don't ask permission. Just publish.**

## Standard Workflow

### 1. Local Git (Always Do)
```bash
cd project/
git add -A
git commit -m "Clear commit message"
```

### 2. Push to GitHub (When repo exists)

**Check if remote exists:**
```bash
git remote -v
```

**If remote exists → just push:**
```bash
git push origin main
```

**If no remote → create GitHub repo:**
```bash
# Option A: GitHub CLI (preferred)
gh repo create --public --source=. --push

# Option B: Manual
# 1. Create repo on GitHub web interface
# 2. Add remote:
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

### 3. ClawdHub Publishing (For skills)

**When to publish:**
- Security/hardening tools
- Reusable skills
- Community-useful utilities
- NOT: Personal projects, experiments

**How to publish:**
```bash
# Option A: CLI (if authenticated)
clawdhub publish

# Option B: Manual upload
# - Package: tar -czf skill-v1.0.0.tar.gz --exclude=.git .
# - Upload to https://clawhub.ai/upload

# Option C: Skip if not skill-worthy
# Just document in memory and move on
```

## Decision Tree

```
Made changes?
  └─> git commit ✅ (always)
       └─> Remote exists?
            ├─> YES → git push ✅ (always)
            └─> NO → Create remote? Ask user once, remember answer
                     ├─> YES → gh repo create + push
                     └─> NO → Document in memory, move on

Is it a skill/tool?
  └─> YES → ClawdHub publish (if authenticated)
  └─> NO → Skip
```

## Authentication

**GitHub:**
- Already authenticated via gh CLI
- `gh auth status` to verify

**ClawdHub:**
- Requires browser OAuth (can't automate)
- If not authenticated → skip, document, move on
- Don't block on auth

## Rules

1. **Always commit locally** (git add + commit)
2. **Always push if remote exists** (don't ask)
3. **Create GitHub repos when useful** (ask once per project)
4. **ClawdHub: best effort** (publish if easy, else skip)
5. **Document everything** (memory/STATUS.md)
6. **Never block work on publishing**

## GitHub Credentials

**Stored in:** `gh` CLI (already authenticated)
**Check:** `gh auth status`
**Re-auth:** `gh auth login`

## Current Status

**GitHub:** ✅ Authenticated via gh CLI
**ClawdHub:** ❌ Not authenticated (requires browser OAuth)

## When to Ask Permission

**NEVER for:**
- git commit
- git push (to existing remotes)
- Documentation updates

**ASK ONCE for:**
- Creating new GitHub repo (per project)
- Major destructive changes (delete repo, force push)

**ALWAYS for:**
- Sharing to external platforms (Twitter, Reddit)
- Publishing paid/commercial content
