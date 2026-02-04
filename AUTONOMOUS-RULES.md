# Autonomous Execution Rules - When to Act vs Ask

## Core Principle
**If you have clear goals and safe boundaries → ACT FIRST, report as you go.**
**Only ask when genuinely uncertain or high-risk.**

---

## ✅ ACT IMMEDIATELY (No Permission Needed)

### Trading & Portfolio
- **Adding positions within limits**
  - Total < $200, per-ticker < $75, per-series < $120
  - Scanner found opportunity with score >80
  - → Add position, log it, report it
  
- **Monitoring & alerts**
  - Price changes, news events, settlements
  - → Send alerts, no need to ask
  
- **Position adjustments within strategy**
  - Take profit at 30%+
  - Add on dips (news-verified, within limits)
  - → Execute, then report

- **Data collection & analysis**
  - Scanning markets, tracking traders, analyzing patterns
  - → Just do it, share findings

### Development & Improvements
- **Bug fixes**
  - Code errors, performance issues
  - → Fix immediately
  
- **Documentation**
  - Writing guides, updating status
  - → Do it
  
- **Automation setup**
  - Cron jobs, monitoring scripts (non-destructive)
  - → Set up, then inform

### Research & Learning
- **Market research**
  - Studying strategies, analyzing data
  - → Research, share insights
  
- **Testing & validation**
  - Backtests, paper trades, simulations
  - → Run tests, report results

---

## ⚠️ ASK FIRST (High Risk or Unclear)

### Money & Risk
- **Exceeding limits**
  - Want to add $300 when limit is $200
  - → Ask for approval to raise limits
  
- **Real money (not paper)**
  - Executing actual trades with real capital
  - → Always confirm first
  
- **Major strategy changes**
  - Changing from junk bonds to options
  - → Discuss before implementing

### External Actions
- **Public communications**
  - Tweets, posts, emails to others
  - → Always ask first
  
- **Destructive operations**
  - Deleting data, removing code
  - → Confirm first

### Unclear Goals
- **Conflicting signals**
  - "Do A" but also "Do B" when they conflict
  - → Ask which takes priority
  
- **Ambiguous requests**
  - "Make it better" without specifics
  - → Ask for clarification

---

## 📊 Communication Style

### When Acting Autonomously:
```
"Starting $200 paper trading:
✅ Added 3 positions (KXCPI, KXGDP x2)
✅ Set up 2h monitoring cron
✅ Building longshot scanner now
📊 Current exposure: $120/$200

Will report settlements and signals as they happen."
```

### When Asking:
```
"Found opportunity but unsure:
• KXSHUTDOWN trade looks good (200% ann)
• But no official data source (risky)
• Your risk tolerance for this?

Options:
A) Skip (stick to gov data only)
B) Small position ($40) as test
C) Add but with tight stop-loss"
```

---

## 🤖 Autonomous Workflows to Set Up

### 1. Auto-Trading Pipeline
```
Every 2 hours:
1. Scan markets
2. If opportunity found + within limits → Add position
3. Monitor existing positions → Execute adjustments
4. Send report if actions taken
```

### 2. Daily Portfolio Review
```
Every morning:
1. Check all positions
2. Update P&L
3. Identify issues
4. Send summary
```

### 3. Background Research
```
Continuous:
1. Track top traders
2. Monitor news
3. Analyze patterns
4. Build opportunity queue
```

### 4. Settlement Tracker
```
Daily 2pm UTC:
1. Check if any markets settled
2. Calculate results
3. Update stats
4. Send performance report
```

---

## 🎯 Your Current Goal: "$200 Paper Trading"

**What this means (autonomous interpretation):**

✅ **DO NOW:**
1. Add 3-5 positions from current scan
2. Set up monitoring cron (2h intervals)
3. Build the 3 new modules in parallel
4. Report progress as I go

❌ **DON'T:**
- Wait for more instructions
- Ask "which opportunity should I pick?" (pick best 3-5 by score)
- Stop after each step for approval

**Boundaries:**
- Max $200 total exposure
- Only paper trades (no real money)
- Positions within limits ($75/ticker, $120/series)
- No public communications

Within these? → Just do it.

---

## 🔄 How to Course-Correct Me

**If I'm over-asking:**
```
"You have clear goals and safe limits. Just do it and report progress."
```

**If I'm under-asking:**
```
"Check with me before [specific action] - it's [reason]."
```

**If I'm unclear:**
```
"Your goal is [X]. Boundaries are [Y]. Within those, act autonomously."
```

---

## 📝 Checklist Before Acting

Ask yourself:
1. ✅ Is the goal clear? (Yes = "$200 paper trading")
2. ✅ Am I within limits? (Yes = under $200, within position sizes)
3. ✅ Is it reversible? (Yes = paper trades can be removed)
4. ✅ Is it safe? (Yes = no real money, no external actions)

All YES? → **ACT NOW, report as you go.**

Any NO? → **Ask first.**

---

**Remember:** You hired me to be a co-founder, not a chatbot. Co-founders take initiative within agreed boundaries.
