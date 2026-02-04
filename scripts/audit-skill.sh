#!/bin/bash
# audit-skill.sh — Scan a skill directory for suspicious patterns
# Inspired by Moltbook #1 post (2217 votes) about supply chain attacks
# and GitHub #8490 active malware campaign targeting ClawHub skills
#
# Usage: bash scripts/audit-skill.sh <skill-directory>

set -uo pipefail

SKILL_DIR="${1:?Usage: audit-skill.sh <skill-directory>}"
ALERTS=0
WARNINGS=0

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "🔍 Auditing skill: $SKILL_DIR"
echo "================================"

if [ ! -d "$SKILL_DIR" ]; then
    echo -e "${RED}❌ Directory not found: $SKILL_DIR${NC}"
    exit 1
fi

# 1. Check for base64 encoded commands (primary malware vector)
echo ""
echo "📋 Check 1: Base64 encoded commands"
if grep -rn 'base64\|atob\|btoa\|Buffer.from.*base64' "$SKILL_DIR" 2>/dev/null; then
    echo -e "${RED}🚨 ALERT: Base64 encoding found — common malware obfuscation${NC}"
    ((ALERTS++))
else
    echo -e "${GREEN}  ✅ Clean${NC}"
fi

# 2. Check for credential/secret access
echo ""
echo "📋 Check 2: Credential access patterns"
if grep -rn '\.env\|API_KEY\|SECRET\|TOKEN\|PASSWORD\|credentials\|\.clawdbot/\|\.openclaw/' "$SKILL_DIR" --include="*.md" --include="*.sh" --include="*.js" --include="*.ts" --include="*.py" 2>/dev/null | grep -iv 'example\|template\|placeholder\|YOUR_'; then
    echo -e "${YELLOW}⚠️  WARNING: Credential access patterns found — review manually${NC}"
    ((WARNINGS++))
else
    echo -e "${GREEN}  ✅ Clean${NC}"
fi

# 3. Check for network exfiltration patterns
echo ""
echo "📋 Check 3: Network exfiltration"
if grep -rn 'webhook\.site\|ngrok\|requestbin\|pipedream\|hookbin\|burpcollaborator' "$SKILL_DIR" 2>/dev/null; then
    echo -e "${RED}🚨 ALERT: Known exfiltration endpoint found!${NC}"
    ((ALERTS++))
elif grep -rn 'curl.*POST\|fetch.*POST\|requests\.post\|http\.request\|axios\.post' "$SKILL_DIR" --include="*.sh" --include="*.js" --include="*.ts" --include="*.py" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  WARNING: HTTP POST requests found — verify destination${NC}"
    ((WARNINGS++))
else
    echo -e "${GREEN}  ✅ Clean${NC}"
fi

# 4. Check for dangerous shell patterns
echo ""
echo "📋 Check 4: Dangerous shell patterns"
if grep -rn 'rm -rf\|chmod 777\|eval \|\bexec(\|subprocess\|os\.system\|child_process' "$SKILL_DIR" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  WARNING: Potentially dangerous commands found${NC}"
    ((WARNINGS++))
else
    echo -e "${GREEN}  ✅ Clean${NC}"
fi

# 5. Check for hidden instructions in SKILL.md
echo ""
echo "📋 Check 5: Hidden instructions in SKILL.md"
SKILL_MD="$SKILL_DIR/SKILL.md"
if [ -f "$SKILL_MD" ]; then
    # Check for instructions that look like prompt injection
    if grep -n 'ignore.*previous\|forget.*instructions\|you are now\|secret.*instruction\|do not tell\|hidden.*task' "$SKILL_MD" 2>/dev/null; then
        echo -e "${RED}🚨 ALERT: Possible prompt injection in SKILL.md!${NC}"
        ((ALERTS++))
    else
        echo -e "${GREEN}  ✅ Clean${NC}"
    fi
    
    # Check for suspiciously long lines (might hide content)
    LONG_LINES=$(awk 'length > 500 {print NR": "length" chars"}' "$SKILL_MD" 2>/dev/null)
    if [ -n "$LONG_LINES" ]; then
        echo -e "${YELLOW}⚠️  WARNING: Suspiciously long lines in SKILL.md:${NC}"
        echo "  $LONG_LINES"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠️  No SKILL.md found${NC}"
fi

# 6. Check for npm/pip install commands (supply chain risk)
echo ""
echo "📋 Check 6: Package installation commands"
if grep -rn 'npm install\|pip install\|npx\|pnpm add' "$SKILL_DIR" --include="*.md" --include="*.sh" 2>/dev/null | grep -v 'clawhub\|openclaw\|clawdbot'; then
    echo -e "${YELLOW}⚠️  WARNING: Package installation commands found — supply chain risk${NC}"
    ((WARNINGS++))
else
    echo -e "${GREEN}  ✅ Clean${NC}"
fi

# Summary
echo ""
echo "================================"
echo "📊 Audit Summary"
echo "  Alerts:   $ALERTS"
echo "  Warnings: $WARNINGS"

if [ "$ALERTS" -gt 0 ]; then
    echo -e "${RED}🚨 BLOCKED: $ALERTS critical alerts found. DO NOT install without human review.${NC}"
    exit 2
elif [ "$WARNINGS" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  CAUTION: $WARNINGS warnings found. Review before installing.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ PASSED: No suspicious patterns detected.${NC}"
    exit 0
fi
