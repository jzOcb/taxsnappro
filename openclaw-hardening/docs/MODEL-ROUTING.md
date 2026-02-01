# 🔀 Model Routing Guide

## Available Models

OpenClaw supports multiple model providers. Configure via `openclaw configure` or edit `~/.openclaw/openclaw.json`.

### Anthropic (Primary)
- `anthropic/claude-opus-4-5` — Best reasoning, most expensive
- `anthropic/claude-sonnet-4` — Great balance, 5x cheaper

### Chinese Models (Alternative)
Tested and confirmed working by the community:

| Model | Provider | Notes |
|-------|----------|-------|
| Kimi K2.5 | Moonshot AI | Has coding plan option |
| Minimax M2.1 | Minimax | No coding plan in selector, choose Minimax directly |
| GLM | Zhipu AI | Works with overseas version |

### ⚠️ Common Gotchas

1. **国内 vs 海外 URL** — This is the #1 setup failure
   - Minimax 国内: `api.minimaxi.com`
   - Minimax 海外: `api.minimax.io`
   - If it doesn't work, check the URL first

2. **"no output" problem** — Output is going to a different environment (Web, Telegram, etc). Check other surfaces.

3. **`agents.fallbacks`** — Must list models here for switching to work

## Setup via CLI

```bash
openclaw configure
# Select: local → models → pick your model → enter API key
```

## Setup via Config

Edit `~/.openclaw/openclaw.json`:

```json5
{
  agents: {
    defaults: {
      model: {
        primary: "anthropic/claude-opus-4-5"
      },
      fallbacks: [
        "anthropic/claude-sonnet-4",
        // Add more fallbacks here
      ],
      subagents: {
        model: "anthropic/claude-sonnet-4"
      }
    }
  }
}
```

## Switching in Chat

```
/model              # Interactive model picker
/model <name>       # Direct switch
/new                # New session (recommended before switching)
/status             # Check current model + usage
```

## Future: Rule-Based Routing

Coming soon (PR #5873): automatic routing based on rules:

```json5
// Not yet available — watch the PR
models: {
  routing: {
    rules: [
      { match: { isCron: true }, model: "anthropic/claude-sonnet-4" },
      { match: { sessionKeyPrefix: "subagent:" }, model: "anthropic/claude-sonnet-4" },
    ]
  }
}
```

## References

- [歸藏's Model Config Tutorial](https://x.com/op7418/status/2017647987854610930) (Chinese)
- [OpenClaw Model Docs](https://docs.clawd.bot)
