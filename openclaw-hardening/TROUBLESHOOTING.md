# Troubleshooting

Common issues encountered during setup and their solutions.

---

## Installation Issues

### `clawdhub: command not found`

**Problem:** After `npm install -g clawdhub`, the command is not found.

**Solution:**
```bash
# Add npm global bin to PATH
export PATH="$(npm config get prefix)/bin:$PATH"

# Make it permanent
echo 'export PATH="$(npm config get prefix)/bin:$PATH"' >> ~/.bashrc
```

### `Cannot find package 'undici'` when running clawdhub

**Problem:** `clawdhub` fails with missing `undici` dependency.

**Solution:**
```bash
cd $(npm config get prefix)/lib/node_modules/clawdhub
npm install undici
```

---

## Configuration Issues

### Invalid config: `Unrecognized key: "fallbacks"`

**Problem:** After adding `fallbacks` to config, `clawdbot doctor` reports it as invalid.

**Status:** `agents.fallbacks` is **not supported** in Clawdbot 2026.1.24-1 and earlier versions.

**Workaround:** Use manual model switching instead:
- In chat: `/model sonnet` or `/model haiku`
- For sub-agents: `subagents.model` works fine
- For cron jobs: specify model when spawning

**Future:** Model routing rules are coming in a future release (see [#5873](https://github.com/clawdbot/clawdbot/pull/5873)).

### Wrong model name format

**Problem:** Config uses `anthropic/claude-sonnet-4` but model fails to load.

**Solution:** Use the correct model identifiers with dashes:
```json5
{
  agents: {
    defaults: {
      model: { primary: "anthropic/claude-sonnet-4-5" },  // ✅ Correct
      subagents: { model: "anthropic/claude-sonnet-4-5" }
    }
  }
}
```

**Valid model names:**
- `anthropic/claude-opus-4-5`
- `anthropic/claude-sonnet-4-5`
- `anthropic/claude-3-5-haiku-latest`

Check available models: `/model` in chat or `clawdbot model list`

---

## Security Issues

### `Bad port` error when running harden.sh

**Problem:** `ufw allow "$CURRENT_SSH_PORT"/tcp` fails with "ERROR: Bad port"

**Cause:** The script's SSH port detection returned an empty value.

**Fixed in:** Latest version uses `${VAR:-22}` fallback.

**Manual fix:**
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

### `integer expression expected` in audit.sh

**Problem:** `Failed attempts: 0 0` causes bash comparison error.

**Cause:** `sudo` password prompt contaminated the grep output.

**Fixed in:** Latest version strips whitespace.

---

## Gateway Issues

### `systemctl --user unavailable`

**Problem:** `clawdbot gateway restart` fails with "No medium found"

**Solution:** Use system-level systemd:
```bash
sudo systemctl restart clawdbot
```

### Claude auth expiring

**Problem:** `clawdbot doctor` shows "expiring (2h)"

**Solution:**
```bash
claude setup-token
sudo systemctl restart clawdbot
```

**Note:** OAuth tokens refresh automatically. You only need this once unless fully expired.

---

## Token Optimization

### Still burning through Opus tokens

**Check:**
1. Primary model still Opus? `cat ~/.clawdbot/clawdbot.json | grep primary`
2. Gateway restarted? `sudo systemctl status clawdbot`
3. Old sessions? Start new: `/new` or switch: `/model sonnet`

---

## Getting Help

- **Docs:** https://docs.clawd.bot
- **Issues:** https://github.com/clawdbot/clawdbot/issues
- **Discord:** https://discord.com/invite/clawd
