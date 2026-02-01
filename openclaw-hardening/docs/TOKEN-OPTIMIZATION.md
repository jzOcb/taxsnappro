# 💰 Token Optimization Guide

## The Problem

Running Claude Opus for **everything** — main chat, heartbeats, sub-agents — burns tokens fast. Users report hitting rate limits after just 20-30 messages.

## The Solution: Model Layering

Use expensive models only where they matter. Route everything else to cheaper models.

### Cost Comparison (Anthropic, per 1M tokens)

| Model | Input | Output | Relative |
|-------|-------|--------|----------|
| Claude Opus 4.5 | $15 | $75 | 5x |
| Claude Sonnet 4 | $3 | $15 | 1x |

### Recommended Routing

| Task | Model | Why |
|------|-------|-----|
| Main conversation | Opus | You want the best reasoning |
| Sub-agents | Sonnet | Background work, bulk processing |
| Heartbeats | Sonnet | Periodic checks, simple logic |
| Fallback | Sonnet | When Opus is rate-limited |

### Config

```json5
// Add to ~/.openclaw/openclaw.json
{
  agents: {
    defaults: {
      model: { primary: "anthropic/claude-opus-4-5" },
      subagents: { model: "anthropic/claude-sonnet-4" },
      fallbacks: ["anthropic/claude-sonnet-4"],
      heartbeat: { every: "55m" },
      contextPruning: { mode: "cache-ttl", ttl: "1h" },
    }
  }
}
```

## Cache Warming

Anthropic caches your system prompt for ~1 hour. After that, the next request re-caches everything (expensive). 

**Fix:** Set heartbeat to 55 minutes. Each heartbeat keeps the cache warm, so you never pay the full re-cache cost.

```
Cache TTL: 1 hour
Heartbeat: 55 minutes
→ Cache never expires → cheaper subsequent requests
```

## Context Pruning

Old tool outputs (file reads, command results) accumulate in context. `cache-ttl` pruning trims them after idle periods, reducing cache write costs.

## Manual Model Switching

In chat, use `/model` to switch on the fly:

```
/model              # browse available models
/model sonnet       # switch to Sonnet
/new                # start fresh session (recommended before switching)
```

**Pro tip:** Switch to Sonnet for exploratory work (brainstorming, research), switch back to Opus for critical decisions.

## Workspace File Budget

These files are injected into every prompt:
- `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`, `HEARTBEAT.md`

Keep them concise. Default limit: 20,000 chars total.

Check your current usage:
```
/context list       # see what's injected
/context detail     # per-file breakdown
/status             # overall token usage
```

## Expected Savings

With model layering + cache warming:
- **Heartbeat cost:** -80% (Opus → Sonnet)
- **Sub-agent cost:** -80% (Opus → Sonnet)  
- **Cache writes:** -30-50% (warm cache)
- **Overall:** ~30-50% reduction

## References

- [OpenClaw Token Use Docs](https://docs.clawd.bot)
- [歸藏's Model Config Tutorial](https://x.com/op7418/status/2017647987854610930)
- [GitHub #1594: Token usage discussion](https://github.com/openclaw/openclaw/issues/1594)
