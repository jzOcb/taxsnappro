#!/bin/bash
# audit-skills.sh — Scan OpenClaw skills for security concerns
# Usage: ./audit-skills.sh [--verbose]
#
# Checks:
# 1. External HTTP requests (outbound data risk)
# 2. Vault directory access attempts
# 3. Credential/secret file reads
# 4. Shell command execution (exec/spawn/system)
# 5. Environment variable access

set -uo pipefail

VERBOSE="${1:-}"
VAULT_DIR="$HOME/.openclaw/workspace/vault"
SKILL_DIRS=(
  "$HOME/clawd/skills"
  "/opt/clawdbot/skills"
)

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

total_skills=0
clean_skills=0
warning_skills=0
high_risk_skills=0

echo "========================================"
echo "  OpenClaw Skill Security Audit"
echo "  $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "========================================"
echo ""

for base_dir in "${SKILL_DIRS[@]}"; do
  [ -d "$base_dir" ] || continue
  
  for skill_dir in "$base_dir"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    total_skills=$((total_skills + 1))
    
    issues=()
    risk_level="clean"
    
    # Check 1: External HTTP requests
    http_files=$(grep -rl "https\?://" "$skill_dir" \
      --include="*.sh" --include="*.py" --include="*.js" --include="*.ts" \
      2>/dev/null | wc -l)
    
    if [ "$http_files" -gt 0 ]; then
      # Filter out documentation-only URLs (comments, README refs)
      real_http=$(grep -rn "https\?://" "$skill_dir" \
        --include="*.sh" --include="*.py" --include="*.js" --include="*.ts" \
        2>/dev/null | grep -v "^.*#.*http" | grep -v "example\.com" | grep -v "localhost" | grep -v "127\.0\.0\.1" | wc -l)
      
      if [ "$real_http" -gt 0 ]; then
        issues+=("⚠️  External HTTP: ${real_http} calls in ${http_files} files")
        [ "$risk_level" = "clean" ] && risk_level="warning"
      fi
    fi
    
    # Check 2: Vault access attempts
    vault_access=$(grep -rl "vault\|VAULT" "$skill_dir" \
      --include="*.sh" --include="*.py" --include="*.js" --include="*.ts" \
      2>/dev/null | wc -l)
    
    if [ "$vault_access" -gt 0 ]; then
      issues+=("🔴 VAULT ACCESS: ${vault_access} files reference vault/")
      risk_level="high"
    fi
    
    # Check 3: Credential/secret file reads
    cred_access=$(grep -rn "private_key\|\.env\|credentials\|passwd\|shadow\|/etc/ssh" "$skill_dir" \
      --include="*.sh" --include="*.py" --include="*.js" --include="*.ts" \
      2>/dev/null | grep -v "^.*#" | wc -l)
    
    if [ "$cred_access" -gt 0 ]; then
      issues+=("🔴 CREDENTIAL ACCESS: ${cred_access} references to sensitive files")
      risk_level="high"
    fi
    
    # Check 4: Arbitrary command execution
    exec_patterns=$(grep -rn "subprocess\|os\.system\|exec(\|spawn(\|eval(" "$skill_dir" \
      --include="*.py" --include="*.js" --include="*.ts" \
      2>/dev/null | grep -v "^.*#" | wc -l)
    
    if [ "$exec_patterns" -gt 0 ]; then
      issues+=("⚠️  Command execution: ${exec_patterns} exec/spawn/system calls")
      [ "$risk_level" = "clean" ] && risk_level="warning"
    fi
    
    # Check 5: Environment variable harvesting
    env_harvest=$(grep -rn "os\.environ\|process\.env\|printenv\|\$[A-Z_]*TOKEN\|\$[A-Z_]*KEY\|\$[A-Z_]*SECRET" "$skill_dir" \
      --include="*.sh" --include="*.py" --include="*.js" --include="*.ts" \
      2>/dev/null | grep -v "^.*#" | wc -l)
    
    if [ "$env_harvest" -gt 0 ]; then
      issues+=("⚠️  Env access: ${env_harvest} references to env vars (TOKEN/KEY/SECRET)")
      [ "$risk_level" = "clean" ] && risk_level="warning"
    fi
    
    # Report
    if [ ${#issues[@]} -eq 0 ]; then
      clean_skills=$((clean_skills + 1))
      [ "$VERBOSE" = "--verbose" ] && echo -e "${GREEN}✅ ${skill_name}${NC} — clean"
    else
      case "$risk_level" in
        high)
          high_risk_skills=$((high_risk_skills + 1))
          echo -e "${RED}🔴 ${skill_name}${NC} — HIGH RISK"
          ;;
        warning)
          warning_skills=$((warning_skills + 1))
          echo -e "${YELLOW}⚠️  ${skill_name}${NC} — needs review"
          ;;
      esac
      for issue in "${issues[@]}"; do
        echo "   $issue"
      done
      
      if [ "$VERBOSE" = "--verbose" ]; then
        echo "   --- Details ---"
        grep -rn "https\?://" "$skill_dir" \
          --include="*.sh" --include="*.py" --include="*.js" --include="*.ts" \
          2>/dev/null | grep -v "example\.com\|localhost\|127\.0\.0\.1" | head -5
        echo ""
      fi
    fi
  done
done

echo ""
echo "========================================"
echo "  SUMMARY"
echo "========================================"
echo -e "  Total skills scanned: ${CYAN}${total_skills}${NC}"
echo -e "  ${GREEN}✅ Clean:${NC}    ${clean_skills}"
echo -e "  ${YELLOW}⚠️  Warning:${NC}  ${warning_skills}"
echo -e "  ${RED}🔴 High risk:${NC} ${high_risk_skills}"
echo ""

if [ "$high_risk_skills" -gt 0 ]; then
  echo -e "${RED}ACTION REQUIRED: Review high-risk skills before use.${NC}"
fi

echo "Vault directory: $VAULT_DIR"
echo "Run with --verbose for detailed output."
