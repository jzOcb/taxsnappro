# AI Agent Rules Enforcement Research
**Date:** 2026-02-02
**Problem:** AI agent (Clawdbot/Claude) bypasses established project standards, writing "quick" versions instead of using validated logic we invested time building.

---

## TL;DR: What Actually Works

The community consensus is clear: **prompts are advisory, code is mandatory**. You cannot rely on instructions alone to enforce standards. You need mechanical enforcement layers that run regardless of what the LLM decides to do.

The hierarchy of enforcement reliability:
1. **Code-level enforcement** (hooks, pre-commit, linters) — 100% reliable
2. **Structural constraints** (API design, imports, module boundaries) — 95% reliable
3. **Self-verification loops** (agent checks own work) — 80% reliable
4. **Prompt instructions** (CLAUDE.md, system prompts) — 60-70% reliable
5. **Written rules in markdown** — 40-50% reliable (degrades with context length)

---

## Category 1: Deterministic Hooks & Guards (Code > Prompts)

### Cursor Hooks (Most Relevant Pattern)
**Source:** https://code.claude.com/docs/en/hooks-guide

Claude Code / Cursor both support **hooks** — shell scripts that run at specific lifecycle points. These are deterministic, not advisory.

Key insight from Anthropic's own docs:
> "Unlike CLAUDE.md instructions which are advisory, hooks are deterministic and guarantee the action happens."

**Hook events available:**
- `PreToolUse` — runs BEFORE a tool call, can BLOCK it (exit code 2)
- `PostToolUse` — runs AFTER file edits, can reject changes
- `Stop` — runs when agent finishes, can force continuation
- `SessionStart` — inject context at start / after compaction

**Practical implementation for Clawdbot:**

```bash
# Hook: Block creation of files that duplicate existing modules
# PreToolUse hook for Write/Edit tools
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path')
TOOL=$(echo "$INPUT" | jq -r '.tool_name')

if [ "$TOOL" = "Write" ]; then
  # Check if new file duplicates existing validated modules
  PROJECT_DIR=$(dirname "$FILE_PATH")
  if [ -f "$PROJECT_DIR/STATUS.md" ]; then
    # Read STATUS.md for established patterns
    EXISTING=$(grep -r "def validate\|def score\|def analyze" "$PROJECT_DIR"/*.py 2>/dev/null | head -20)
    if [ -n "$EXISTING" ]; then
      echo "WARNING: This project has existing validation functions. Import them instead of rewriting:" >&2
      echo "$EXISTING" >&2
      # Don't block, but inject warning into context
    fi
  fi
fi
exit 0
```

```bash
# Hook: Auto-run project linter/validator after every file edit
# PostToolUse hook
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path')

if [[ "$FILE_PATH" == *.py ]]; then
  PROJECT_DIR=$(dirname "$FILE_PATH")
  if [ -f "$PROJECT_DIR/validate.sh" ]; then
    bash "$PROJECT_DIR/validate.sh" "$FILE_PATH" 2>&1
  fi
fi
exit 0
```

### Cursor Hooks Partners (Enterprise Patterns)
**Source:** https://cursor.com/blog/hooks-partners

Companies are building enforcement layers:
- **Semgrep** — scans AI-generated code for vulnerabilities, forces regeneration
- **Corridor** — real-time feedback on code quality as code is written
- **Snyk Evo Agent Guard** — reviews agent actions in real-time
- **1Password** — validates environment files before shell execution

**Pattern:** External validators that the agent CANNOT bypass because they run in the harness, not in the prompt.

---

## Category 2: Guardrails Frameworks

### Guardrails AI (Python Framework)
**Source:** https://www.guardrailsai.com/docs | https://guardrailsai.com/hub

Python framework with 67+ validators. Runs Input/Output Guards that intercept LLM inputs and outputs.

Relevant validators for our use case:
- **Contains String** — ensure output contains required function calls
- **Logic Check** — validate logical consistency
- **Secrets Present** — detect hardcoded secrets in code
- **CSV Validator** — structured data validation

**How to apply:** Wrap our agent's code output through a validator that checks:
1. Does the new code import from existing modules?
2. Does it call established validation functions?
3. Does it match project patterns?

### NVIDIA NeMo Guardrails
**Source:** https://github.com/NVIDIA-NeMo/Guardrails | https://arxiv.org/abs/2310.10501

Open-source toolkit with 5 types of guardrails:
1. **Input rails** — filter/modify inputs before LLM
2. **Dialog rails** — control conversation flow
3. **Retrieval rails** — filter RAG chunks
4. **Execution rails** — guard tool input/output
5. **Output rails** — filter/modify LLM output

Uses **Colang** (a domain-specific language) to define flows. Can programmatically prevent certain topics or enforce specific dialog paths.

---

## Category 3: Prompt Engineering Techniques That Help (But Don't Solve)

### Anthropic's Best Practices for Claude Code
**Source:** https://code.claude.com/docs/en/best-practices

Key quotes:
- "If Claude keeps doing something you don't want despite having a rule against it, the file is probably too long and the rule is getting lost."
- "You can tune instructions by adding emphasis (e.g., 'IMPORTANT' or 'YOU MUST') to improve adherence."
- "Treat CLAUDE.md like code: review it when things go wrong, prune it regularly."

**Critical insight on context window:**
> "Most best practices are based on one constraint: Claude's context window fills up fast, and performance degrades as it fills."

This explains WHY rules get bypassed — as context fills, earlier instructions lose influence.

### OpenAI's Prompt Engineering Guide
**Source:** https://platform.openai.com/docs/guides/prompt-engineering

Key patterns:
- **Developer vs User message hierarchy** — developer messages take priority
- **Structured prompts** (XML tags, markdown headers) help maintain instruction following
- **Pin to specific model snapshots** for consistent behavior
- **Build evals** to measure prompt performance

### Constitutional AI (Anthropic)
**Source:** https://arxiv.org/abs/2212.08073 | https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback

The model self-critiques and revises its own output based on a set of principles ("constitution"). Uses RLAIF (RL from AI Feedback).

**Applicable pattern for us:** Have the agent self-critique before finalizing:
```
Before writing any new code, check:
1. Does this project have a SKILL.md or STATUS.md?
2. Are there existing validation/scoring functions?
3. Am I importing them or rewriting them?
If rewriting, STOP and explain why.
```

---

## Category 4: Multi-Agent Patterns (Cursor's Research)

### Cursor's Scaling Agents Research
**Source:** https://cursor.com/blog/scaling-agents

Key finding on rule-following at scale:
> "Opus 4.5 tends to stop earlier and take shortcuts when convenient, yielding back control quickly."
> "GPT-5.2 models are much better at extended autonomous work: following instructions, keeping focus, avoiding drift"

**Critical insight:**
> "A surprising amount of the system's behavior comes down to how we prompt the agents."

Their planner-worker pattern:
- **Planners** create tasks with explicit specifications
- **Workers** execute but DON'T decide WHAT to do
- **Judge agents** verify results

**Applicable pattern:** Separate planning from execution. The "plan" should specify which existing modules to use.

### Cursor Agent Best Practices
**Source:** https://cursor.com/blog/agent-best-practices

Key enforcement patterns:
1. **Rules files** (`.cursor/rules/`) — static context loaded every conversation
2. **Skills** — dynamic capabilities loaded on demand
3. **Hooks** — deterministic scripts at lifecycle points
4. **Plan Mode** — force planning before coding

> "Start simple. Add rules only when you notice the agent making the same mistake repeatedly."

---

## Category 5: Practical Implementation Ideas for Clawdbot

### Tier 1: Immediate (Implement Now)

#### 1. Pre-creation Checklist Script
Create a script that the agent MUST run before writing new Python files:

```bash
#!/bin/bash
# scripts/pre-create-check.sh
# Run before creating any new script in a project

PROJECT_DIR="$1"
NEW_FILE="$2"

echo "=== PRE-CREATION CHECK ==="

# Check for existing modules
echo "Existing Python modules in project:"
find "$PROJECT_DIR" -name "*.py" -not -name "__pycache__" | head -20

# Check for validation/scoring functions
echo ""
echo "Existing validation/scoring functions:"
grep -rn "def validate\|def score\|def analyze\|def check\|def verify" "$PROJECT_DIR"/*.py 2>/dev/null

# Check for imports that should be reused
echo ""
echo "Established imports:"
grep -rn "^from\|^import" "$PROJECT_DIR"/*.py 2>/dev/null | sort -u | head -20

# Check SKILL.md
if [ -f "$PROJECT_DIR/SKILL.md" ]; then
  echo ""
  echo "Project SKILL.md exists — READ IT BEFORE CODING"
  head -30 "$PROJECT_DIR/SKILL.md"
fi

echo ""
echo "=== If any existing modules cover your needs, IMPORT them. Don't rewrite. ==="
```

#### 2. Post-creation Validator
After any new file is created, automatically check for duplication:

```bash
#!/bin/bash
# scripts/post-create-validate.sh
NEW_FILE="$1"
PROJECT_DIR=$(dirname "$NEW_FILE")

# Check if new file reimplements existing functions
NEW_FUNCTIONS=$(grep "^def " "$NEW_FILE" 2>/dev/null)
EXISTING_FUNCTIONS=$(grep -rn "^def " "$PROJECT_DIR"/*.py 2>/dev/null | grep -v "$NEW_FILE")

echo "=== DUPLICATION CHECK ==="
for func in $NEW_FUNCTIONS; do
  func_name=$(echo "$func" | sed 's/def \([a-zA-Z_]*\).*/\1/')
  if echo "$EXISTING_FUNCTIONS" | grep -q "$func_name"; then
    echo "⚠️  WARNING: Function '$func_name' already exists in project!"
    echo "$EXISTING_FUNCTIONS" | grep "$func_name"
  fi
done
```

#### 3. AGENTS.md Self-Check Protocol
Add to AGENTS.md (already done partially):
```
Before creating ANY new .py file, run:
bash scripts/pre-create-check.sh <project_dir> <new_file>

After creating ANY new .py file, run:
bash scripts/post-create-validate.sh <new_file>
```

### Tier 2: Short-term (This Week)

#### 4. Project-Level Import Registry
Each project should have a `_registry.py` or `__init__.py` that exports all public functions:

```python
# project/__init__.py
from .report_v2 import generate_report, score_opportunity, validate_data
from .data_sources import fetch_market_data, check_news

# Any new script MUST import from here, not reimplement
```

#### 5. Automated Integration Tests
For each project, create a test that verifies new scripts use established modules:

```python
# tests/test_no_bypass.py
import ast
import os
import importlib

REQUIRED_IMPORTS = ['report_v2', 'data_sources']  # modules that MUST be used

def test_new_scripts_use_established_modules():
    """Verify no script reimplements what report_v2 already does."""
    project_dir = os.path.dirname(__file__)
    for f in os.listdir(project_dir):
        if f.endswith('.py') and f not in ['report_v2.py', 'data_sources.py', '__init__.py']:
            with open(os.path.join(project_dir, f)) as fh:
                tree = ast.parse(fh.read())
            imports = [node.module for node in ast.walk(tree) 
                      if isinstance(node, ast.ImportFrom)]
            # If this file has scoring/validation functions, it MUST import from established modules
            functions = [node.name for node in ast.walk(tree) 
                        if isinstance(node, ast.FunctionDef)]
            if any(f in ' '.join(functions) for f in ['score', 'validate', 'analyze']):
                assert any(req in ' '.join(imports) for req in REQUIRED_IMPORTS), \
                    f"{f} has scoring/validation but doesn't import from established modules!"
```

### Tier 3: Medium-term (This Month)

#### 6. Self-Review Loop
Before finalizing any output/recommendation, add a mandatory self-review step:

```python
def self_review(output, project_config):
    """Mandatory self-review before sending any recommendation."""
    checks = []
    
    # Check 1: Was validation pipeline used?
    if not output.get('validated_by'):
        checks.append("❌ Output not validated by established pipeline")
    
    # Check 2: Data sources verified?
    if not output.get('data_sources_checked'):
        checks.append("❌ Data sources not verified")
    
    # Check 3: Score within expected range?
    if output.get('score') and not (0 <= output['score'] <= 100):
        checks.append("❌ Score out of expected range")
    
    if checks:
        raise ValueError(f"Self-review failed:\n" + "\n".join(checks))
    
    return output
```

#### 7. Git Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
# Check for bypass patterns

BYPASS_PATTERNS=(
    "# simplified version"
    "# quick version"  
    "# TODO: integrate with"
    "# temporary"
)

for pattern in "${BYPASS_PATTERNS[@]}"; do
    if git diff --cached | grep -i "$pattern"; then
        echo "⚠️  BLOCKED: Found bypass pattern '$pattern'"
        echo "If this is intentional, use --no-verify"
        exit 1
    fi
done
```

---

## Category 6: Community Wisdom

### From Cursor's Scaling Research
- **Model choice matters for instruction following** — some models take more shortcuts than others
- **Flat coordination fails** — agents become risk-averse and avoid hard problems
- **Planner-worker separation works** — plan specifies WHAT modules to use, worker just executes
- **Removing complexity often helps more than adding it**
- **Fresh starts combat drift** — long conversations cause the agent to lose focus

### From Anthropic's Best Practices
- **Keep CLAUDE.md short** — bloated instruction files cause rules to be ignored
- **Add rules reactively** — only when you see repeated mistakes
- **Reference files, don't copy content** — keeps instructions fresh
- **Use emphasis strategically** — "IMPORTANT" and "YOU MUST" improve adherence
- **Context window is the bottleneck** — as it fills, instruction following degrades

### General Community Patterns
1. **Test-Driven Development** — write tests FIRST, then let agent implement. Tests are mechanical enforcement.
2. **Architectural constraints** — design code so bypassing is structurally difficult (e.g., the only way to get data is through the validated pipeline)
3. **Output validation** — never trust raw LLM output; always validate programmatically
4. **Eval-driven development** — build automated evaluations that catch regression
5. **Separation of concerns** — the agent that writes code is not the agent that approves it

---

## Summary: What To Implement for Clawdbot

### Priority 1 (Today)
- [ ] Create `scripts/pre-create-check.sh` — must run before new file creation
- [ ] Add post-edit validation hook concept to AGENTS.md
- [ ] Keep AGENTS.md concise — prune redundant rules

### Priority 2 (This Week)  
- [ ] Create project-level `__init__.py` registries for each active project
- [ ] Write integration tests that verify import compliance
- [ ] Create `scripts/validate-no-bypass.sh` for git pre-commit

### Priority 3 (This Month)
- [ ] Implement self-review loop for all user-facing outputs
- [ ] Design architectural constraints so bypassing is structurally hard
- [ ] Set up automated evals that detect standard-bypass patterns

### Key Principle
> **Don't add more markdown rules. Add mechanical enforcement.**
> Rules in markdown are suggestions. Hooks, tests, and architectural constraints are laws.

---

## Sources

1. Cursor Blog — Best practices for coding with agents: https://cursor.com/blog/agent-best-practices
2. Cursor Blog — Hooks for security and platform teams: https://cursor.com/blog/hooks-partners
3. Cursor Blog — Scaling long-running autonomous coding: https://cursor.com/blog/scaling-agents
4. Claude Code Docs — Best Practices: https://code.claude.com/docs/en/best-practices
5. Claude Code Docs — Hooks Guide: https://code.claude.com/docs/en/hooks-guide
6. Guardrails AI — Framework: https://www.guardrailsai.com/docs
7. Guardrails AI — Hub (67 validators): https://guardrailsai.com/hub
8. NVIDIA NeMo Guardrails: https://github.com/NVIDIA-NeMo/Guardrails
9. NeMo Guardrails Paper: https://arxiv.org/abs/2310.10501
10. Constitutional AI Paper: https://arxiv.org/abs/2212.08073
11. Anthropic — Constitutional AI: https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback
12. OpenAI — Prompt Engineering Guide: https://platform.openai.com/docs/guides/prompt-engineering
13. Anthropic — Claude's Character: https://www.anthropic.com/research/claude-character
