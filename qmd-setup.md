# qmd Setup - Local Semantic Search for Token Optimization

**Status:** ✅ In Progress (embedding models downloading)  
**Source:** https://x.com/wangray/status/2017624068997189807 (Ray Wang, 200K views)  
**Date:** 2026-02-02

## What is qmd?

Local semantic search engine by Shopify founder Tobi, designed for AI agents.

**Benefits:**
- 90% token savings (search vs. full context dump)
- 95%+ accuracy with hybrid search
- Zero API cost (runs locally)
- MCP integration (agents auto-recall)

**Models:**
- Embedding: embeddinggemma-300M (328MB)
- Reranker: qwen3-reranker-0.6b-q8_0
- Generation: Qwen3-0.6B-Q8_0

## Installation

```bash
# 1. Install bun
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc

# 2. Install qmd
bun install -g https://github.com/tobi/qmd

# 3. Verify
qmd status
```

## Setup for clawd workspace

```bash
cd ~/clawd

# Create memory collection
qmd collection add memory --name daily-logs --mask "*.md"
qmd embed -c daily-logs

# Create workspace collection
qmd collection add . --name workspace --mask "*.md"
qmd embed -c workspace

# List collections
qmd collection list
```

## Usage

```bash
# Hybrid search (93% accuracy - recommended)
qmd query "keyword" -c daily-logs

# Pure semantic search
qmd vsearch "keyword" -c daily-logs

# Full-text search
qmd search "keyword" -c daily-logs

# Get document
qmd get memory/2026-02-02.md

# Status
qmd status
```

## MCP Integration

Create `config/mcporter.json`:

```json
{
  "mcpServers": {
    "qmd": {
      "command": "/home/clawdbot/.bun/bin/qmd",
      "args": ["mcp"]
    }
  }
}
```

**Available tools:**
- `query` — hybrid search (most accurate)
- `vsearch` — semantic search
- `search` — keyword search
- `get / multi_get` — document extraction
- `status` — health check

## Maintenance

Add to heartbeat or cron:

```bash
# Update indexes when memory files change
qmd embed -c daily-logs
qmd embed -c workspace
```

## Performance

**Traditional approach:**
- Dump entire MEMORY.md (2000 tokens)
- 90% irrelevant content
- Hit token limits

**qmd approach:**
- Search returns relevant snippets (~200 tokens)
- 90% token savings
- Higher precision

## Current Status

✅ bun installed (v1.3.8)  
✅ qmd installed  
✅ daily-logs collection created (8 files)  
🔄 Embedding in progress (25 chunks, 55.8KB)  
⏳ workspace collection (pending)  
⏳ MCP integration (pending)

## Next Steps

1. ✅ Wait for embedding to complete
2. Create workspace collection
3. Test search accuracy
4. Configure MCP integration
5. Add to heartbeat automation
6. Document token savings

## Files

- Setup doc: `/home/clawdbot/clawd/qmd-setup.md`
- Index: `~/.cache/qmd/index.sqlite`
- Models: `~/.cache/qmd/models/`

## References

- Article: https://x.com/wangray/status/2017624068997189807
- GitHub: https://github.com/tobi/qmd
- Ray Wang (200K views, 2.2K bookmarks)
