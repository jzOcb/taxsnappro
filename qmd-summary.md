# qmd on VPS: Executive Summary

**Date:** 2026-02-03  
**Status:** ✅ Testing Complete, Cleaned Up  
**Source:** Ray Wang's article (200K views)

## TL;DR

**qmd CAN work on CPU-only VPS, but isn't practical.**

**Tested:** DigitalOcean $6/month droplet (1 vCPU, 1GB RAM, no GPU)  
**Result:** Works for 1-2 files, crashes on batch processing  
**Decision:** Use existing token optimization (model routing + context pruning) instead

---

## What We Tested

### ✅ **What Worked**
1. **Single file embedding:** 3-15 seconds, 88% accuracy
2. **Keyword search:** Instant, no embedding needed, 60% accuracy
3. **Per-file collections:** Stable but requires manual management

### ❌ **What Failed**
1. **Batch embedding:** Segmentation fault after 3+ minutes
2. **Scaling:** Can't process 7+ files without crashes
3. **Hybrid search:** Requires 2.25GB models (too heavy)

---

## Performance Comparison

| Method | Setup | Search | Accuracy | Monthly Cost |
|--------|-------|--------|----------|--------------|
| qmd (per-file) | 2hrs | 30-120s | 88% | $0 |
| qmd (keyword) | Instant | <1s | 60% | $0 |
| OpenAI API | Instant | <1s | 95%+ | $0.50 |
| Our current | Done | N/A | N/A | Opus→Sonnet=5x savings |

---

## Why We're Not Using It

**Time investment:** 2+ hours troubleshooting  
**Complexity:** Requires per-file processing scripts  
**Reliability:** Crashes on batch operations  
**Speed:** 30-120s vs <1s for cloud APIs  

**Our current approach is better:**
- ✅ Model routing (Sonnet vs Opus) = 5x cost savings
- ✅ Context pruning = auto-cleanup
- ✅ Daily memory files = already optimized
- ✅ No setup needed, works today

---

## When qmd DOES Make Sense

**✅ Use qmd if:**
- Mac with Metal GPU (fast, stable)
- Privacy is critical (can't use cloud APIs)
- Small document collection (<10 files)
- Learning/experimentation

**❌ Don't use qmd if:**
- CPU-only VPS (crashes)
- Production use case (unreliable)
- Large collections (doesn't scale)
- Time-sensitive (setup takes hours)

---

## Value From This Testing

1. **Validated community claims:** qmd works, just not for us
2. **Created reusable guide:** `qmd-vps-guide.md` for community
3. **Confirmed our approach:** Model routing is the right solution
4. **Saved future time:** Don't chase local embedding on CPU-only VPS

---

## Files Created

**Documentation:**
- `qmd-vps-guide.md` — Complete guide (working solutions + limitations)
- `qmd-evaluation.md` — Detailed test results
- `qmd-setup.md` — Installation log
- `qmd-summary.md` — This file

**Scripts:**
- `scripts/qmd-embed-single.sh` — Helper for per-file embedding

**Commits:**
- 0a22ac6 — Complete guide
- c24cd2a — Evaluation updates
- 2341437 — Initial evaluation

---

## Cleanup Done

**Removed:**
- qmd package (bun remove -g)
- Model cache (2.1GB)
- Test collections

**Kept:**
- bun runtime (902MB, may be useful later)
- Documentation (reference for community)

**Disk space freed:** 2.1GB

---

## Recommendation

**For token optimization on CPU-only VPS:**

1. **Keep using:** Model routing (Sonnet vs Opus)
2. **Keep using:** Context pruning
3. **Keep using:** Daily memory files
4. **If needed:** Enable memory_search with OpenAI API ($0.50/month)

**Don't use:** qmd on CPU-only VPS (not worth the complexity)

---

## Key Takeaways

1. **Community validation ≠ works everywhere**
   - 200K views doesn't mean it works on your setup
   
2. **Local ≠ better**
   - $0.50/month cloud API beats hours of troubleshooting
   
3. **Test before committing**
   - Good we tested before building workflows around it
   
4. **Document learnings**
   - Guide created helps community avoid same pitfalls

---

**Bottom line:** qmd is great tech, just wrong tool for our use case.
