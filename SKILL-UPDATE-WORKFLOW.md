# Skill Update Workflow - Automatic Feedback Loop

**Problem:** When we improve enforcement in a project, we often forget to update the skill itself.

**Example (2026-02-02):**
1. ✅ Discovered deployment gap in Kalshi
2. ✅ Built .deployment-check.sh to fix it
3. ⚠️ Almost forgot to update agent-guardrails skill
4. ✅ Updated only after user reminded us

**Goal:** Automate the feedback loop so improvements always flow back to skills.

---

## Current Workflow (Manual)

```
Project issue → Fix in project → [Remember?] → Update skill
                                       ↑
                                  Often breaks here
```

**Problems:**
- Relies on human memory
- Easy to forget during busy work
- Skills become stale
- Other projects don't benefit

---

## Target Workflow (Automated)

```
Project issue → Fix in project → [Auto-detect] → Pending task → [Auto-update] → Skill updated
                                        ↓
                                   No memory needed
```

**Benefits:**
- Can't forget (mechanical)
- Skills stay current
- Knowledge compounds
- Other projects auto-benefit

---

## Implementation (3 Phases)

### Phase 1: Detection (✅ DONE)

**Script:** `scripts/detect-enforcement-improvement.sh`

**Triggers:**
- Git post-commit hook
- Or: CI/CD pipeline
- Or: Daily cron scan

**What it does:**
1. Scans last commit for enforcement-related changes
2. Identifies which skill should be updated
3. Creates task in `.pending-skill-updates.txt`

**Patterns detected:**
- Deployment checks (`.deployment-check.sh`, `DEPLOYMENT-CHECKLIST.md`)
- Pre/post-creation hooks
- Secret scanning
- Any file matching "enforcement", "guardrails", "mechanical"

**Example output:**
```
Date: 2026-02-02 21:00 UTC
Commit: abc123
Skill: agent-guardrails
Files: kalshi/.deployment-check.sh kalshi/DEPLOYMENT-CHECKLIST.md

Commit Message:
Add deployment verification for Kalshi

Action needed:
1. Review the enforcement improvement
2. Extract reusable patterns/scripts
3. Update skills/agent-guardrails/
4. Commit skill changes
```

### Phase 2: Semi-Automatic (CURRENT - RECOMMENDED)

**Scripts:**
- `scripts/auto-update-skills.sh` - Show pending tasks
- `scripts/auto-commit-skill-updates.sh` - Auto-commit with confirmation

**Workflow:**
1. ✅ **Detection (automatic):** Git hook detects improvement → creates task
2. 👤 **Update (manual):** Review task → update skill files
3. ✅ **Commit (automatic with confirmation):** Run script → review changes → confirm → auto-commit

**Steps:**
```bash
# 1. Check pending tasks
cat .pending-skill-updates.txt

# 2. Review and update skill files
# (e.g., add script to agent-guardrails/)

# 3. Auto-commit with confirmation
bash scripts/auto-commit-skill-updates.sh
# → Shows what will be committed
# → Asks for confirmation (y/N)
# → Commits and cleans up task
```

**Benefits:**
- ✅ Can't forget to commit (script reminds you)
- ✅ Safe (confirmation step before commit)
- ✅ Auto-generates commit message from task
- ✅ Archives processed tasks

**Why semi-automatic:**
- Need human judgment on what's reusable
- Some improvements are project-specific
- Quality control on skill changes
- But removes manual commit busywork

### Phase 3: Autonomous Update (TODO)

**Vision:** AI agent automatically updates skills

**How it would work:**
```bash
# Triggered automatically when task detected
python3 scripts/ai-skill-updater.py

# Agent does:
1. Read pending task
2. Analyze project files that changed
3. Extract reusable patterns
4. Generate skill updates (scripts, docs, examples)
5. Run tests on updated skill
6. If tests pass → Commit
7. If tests fail → Create manual review task
8. Notify user of update
```

**Requirements:**
- AI capable of code analysis
- Template system for skill updates
- Automated testing for skills
- Safety rails (human review for breaking changes)

---

## Installation

### 1. Install Detection Hook

**Option A: Git post-commit hook**
```bash
cat >> .git/hooks/post-commit << 'EOF'
#!/bin/bash
bash scripts/detect-enforcement-improvement.sh
EOF
chmod +x .git/hooks/post-commit
```

**Option B: Daily cron**
```bash
# Check for new enforcement improvements daily
0 9 * * * cd /home/clawdbot/clawd && bash scripts/detect-enforcement-improvement.sh
```

### 2. Review Pending Updates

Manually or via cron:
```bash
bash scripts/auto-update-skills.sh
```

### 3. Process Updates

When you see pending tasks:
1. Read `.pending-skill-updates.txt`
2. Review the improvement
3. Update the skill
4. Delete the task entry

---

## Examples

### Example 1: Deployment Check

**Project commit:**
```
kalshi/.deployment-check.sh
kalshi/DEPLOYMENT-CHECKLIST.md
```

**Detection:**
```
✅ Detected enforcement improvement
→ Created task for agent-guardrails skill
```

**Update applied:**
```
skills/agent-guardrails/scripts/create-deployment-check.sh
skills/agent-guardrails/references/deployment-verification-guide.md
skills/agent-guardrails/SKILL.md
```

**Result:** Other projects can now use `create-deployment-check.sh`

### Example 2: New Bypass Pattern

**Project commit:**
```
# Blocked pattern: "temporary fix"
scripts/pre-commit hook updated
```

**Detection:**
```
✅ Detected enforcement improvement
→ Created task for agent-guardrails skill
```

**Update applied:**
```
skills/agent-guardrails/scripts/post-create-validate.sh
# Added "temporary fix" to blocked patterns
```

**Result:** All projects now block "temporary fix" pattern

---

## Monitoring

### Check for Pending Tasks

```bash
cat .pending-skill-updates.txt
```

### Count Pending Updates

```bash
grep -c "^---$" .pending-skill-updates.txt | awk '{print $1/2 " pending updates"}'
```

### Review Update History

```bash
git log --all --grep="skill update" --oneline
```

---

## Metrics (Future)

Track improvement velocity:
- **Detection rate:** How many improvements caught?
- **Update latency:** Time from detection to skill update
- **Application rate:** How many projects using updated skills?
- **Issue prevention:** How many issues avoided by updated skills?

---

## Future Enhancements

### Auto-Categorization

AI determines skill category:
```python
def categorize_improvement(files, commit_msg):
    if "deployment" in commit_msg:
        return "agent-guardrails"
    elif "trading" in files:
        return "kalshi" or "trading-strategy"
    # etc.
```

### Cross-Project Learning

Scan ALL projects for similar improvements:
```bash
# If project A adds deployment check
# → Suggest to project B, C, D
```

### Skill Version Management

```json
{
  "skill": "agent-guardrails",
  "version": "1.2.0",
  "changes": [
    "Added deployment verification",
    "Updated bypass patterns"
  ],
  "breaking": false
}
```

### Auto-Testing

Before updating skill:
```bash
# Run skill tests
bash skills/agent-guardrails/tests/run-all.sh

# If pass → Auto-commit
# If fail → Flag for review
```

---

## Guardrails for the Guardrails

**Meta-problem:** What if we forget to update the skill-update system?

**Solution:** Make it self-documenting:

1. ✅ This document (SKILL-UPDATE-WORKFLOW.md)
2. ✅ Detection script with clear patterns
3. ✅ Pending tasks file as reminder
4. TODO: Cron reminder if tasks > 7 days old
5. TODO: Dashboard showing update health

**Iron rule:** If you improve enforcement, the system should nag you until skill is updated.

---

## TL;DR

**Old way:**
```
Fix problem → Hope you remember to update skill
```

**New way:**
```
Fix problem → System detects → Creates task → Nags until updated
```

**Phase 1 (Now):** Automatic detection + manual update
**Phase 2 (Soon):** Automatic detection + semi-automatic update
**Phase 3 (Future):** Fully autonomous skill improvement

**Remember:** Skills are living knowledge. Keep them current or they rot.
