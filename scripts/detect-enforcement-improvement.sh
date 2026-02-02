#!/bin/bash
# Detect when enforcement improvements happen and trigger skill updates
# Run this as git post-commit hook or CI step

WORKSPACE=/home/clawdbot/clawd
SKILLS_DIR=$WORKSPACE/skills

# Patterns that indicate enforcement improvements
ENFORCEMENT_PATTERNS=(
    "\.deployment-check\.sh"
    "DEPLOYMENT-CHECKLIST\.md"
    "pre-commit"
    "post-create"
    "check-secrets"
    "\.guardrails"
    "enforcement"
    "mechanical"
)

# Check last commit for enforcement-related changes
LAST_COMMIT=$(git log -1 --name-only --pretty=format:"")

echo "🔍 Checking for enforcement improvements in last commit..."

FOUND_IMPROVEMENTS=()

for file in $LAST_COMMIT; do
    for pattern in "${ENFORCEMENT_PATTERNS[@]}"; do
        if echo "$file" | grep -q "$pattern"; then
            FOUND_IMPROVEMENTS+=("$file")
            break
        fi
    done
done

if [ ${#FOUND_IMPROVEMENTS[@]} -eq 0 ]; then
    echo "   No enforcement improvements detected"
    exit 0
fi

echo ""
echo "🎯 Detected ${#FOUND_IMPROVEMENTS[@]} enforcement improvements:"
for file in "${FOUND_IMPROVEMENTS[@]}"; do
    echo "   - $file"
done
echo ""

# Extract lesson from commit message
COMMIT_MSG=$(git log -1 --pretty=format:"%B")
COMMIT_HASH=$(git log -1 --pretty=format:"%h")

# Determine which skill should be updated
SKILL_TO_UPDATE=""

if echo "$COMMIT_MSG" | grep -qi "deployment\|integration\|production"; then
    SKILL_TO_UPDATE="agent-guardrails"
elif echo "$COMMIT_MSG" | grep -qi "bypass\|reimplementation\|duplicate"; then
    SKILL_TO_UPDATE="agent-guardrails"
elif echo "$COMMIT_MSG" | grep -qi "secret\|token\|password\|key"; then
    SKILL_TO_UPDATE="agent-guardrails"
fi

if [ -z "$SKILL_TO_UPDATE" ]; then
    echo "⚠️ Couldn't determine which skill to update"
    echo "   Review manually: skills/agent-guardrails/"
    exit 0
fi

echo "📝 Should update skill: $SKILL_TO_UPDATE"
echo ""

# Create update task
TASK_FILE="$WORKSPACE/.pending-skill-updates.txt"

cat >> "$TASK_FILE" << EOF
---
Date: $(date -u +"%Y-%m-%d %H:%M UTC")
Commit: $COMMIT_HASH
Skill: $SKILL_TO_UPDATE
Files: ${FOUND_IMPROVEMENTS[@]}

Commit Message:
$COMMIT_MSG

Action needed:
1. Review the enforcement improvement
2. Extract reusable patterns/scripts
3. Update skills/$SKILL_TO_UPDATE/
4. Commit skill changes
5. Mark this task done

---
EOF

echo "✅ Created update task in .pending-skill-updates.txt"
echo ""
echo "Next step: Review and apply the improvement to $SKILL_TO_UPDATE skill"
