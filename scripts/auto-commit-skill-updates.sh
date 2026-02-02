#!/bin/bash
# Auto-commit skill updates after applying improvements
# CAUTION: This auto-commits to git. Use with care.

set -e

WORKSPACE=/home/clawdbot/clawd
SKILLS_DIR=$WORKSPACE/skills
TASK_FILE="$WORKSPACE/.pending-skill-updates.txt"

if [ ! -f "$TASK_FILE" ]; then
    echo "No pending skill updates to commit"
    exit 0
fi

echo "🔍 Checking for uncommitted skill changes..."
cd "$WORKSPACE"

# Check if skills/ has uncommitted changes
SKILL_CHANGES=$(git status --porcelain skills/ 2>/dev/null | wc -l)

if [ $SKILL_CHANGES -eq 0 ]; then
    echo "No uncommitted changes in skills/"
    exit 0
fi

echo "Found $SKILL_CHANGES change(s) in skills/"
echo ""

# Show what will be committed
git status --short skills/

echo ""
echo "=================================="
echo "🚨 AUTO-COMMIT MODE"
echo "=================================="
echo ""

# Parse pending tasks to generate commit message
TASKS=$(cat "$TASK_FILE")
SKILL_NAME=$(echo "$TASKS" | grep "^Skill:" | head -1 | cut -d: -f2 | xargs)
COMMIT_REF=$(echo "$TASKS" | grep "^Commit:" | head -1 | cut -d: -f2 | xargs)

if [ -z "$SKILL_NAME" ]; then
    echo "❌ Couldn't parse skill name from tasks"
    echo "Manual commit required"
    exit 1
fi

# Generate commit message
COMMIT_MSG="Update $SKILL_NAME skill from enforcement improvement

Auto-applied changes from commit $COMMIT_REF

Changes detected in pending tasks:
$(echo "$TASKS" | grep "^Files:" | head -1)

This update was automatically committed by auto-commit-skill-updates.sh
Review the changes before pushing.
"

echo "Generated commit message:"
echo "---"
echo "$COMMIT_MSG"
echo "---"
echo ""

# Safety check: Ask for confirmation (can be disabled for full automation)
if [ "$AUTO_COMMIT_NO_CONFIRM" != "true" ]; then
    read -p "Auto-commit these changes? (y/N): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Changes staged but not committed."
        exit 0
    fi
fi

# Commit the changes
git add skills/
git commit -m "$COMMIT_MSG"

echo "✅ Auto-committed skill updates"
echo ""

# Archive the processed task
ARCHIVE_FILE="$WORKSPACE/.skill-updates-archive.txt"
echo "===== Processed on $(date -u +"%Y-%m-%d %H:%M UTC") =====" >> "$ARCHIVE_FILE"
cat "$TASK_FILE" >> "$ARCHIVE_FILE"
echo "" >> "$ARCHIVE_FILE"

# Clear pending tasks
> "$TASK_FILE"

echo "✅ Pending tasks archived and cleared"
echo ""
echo "Next: Review the commit and push if satisfied:"
echo "  git log -1 --stat"
echo "  git push"
