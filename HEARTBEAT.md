# HEARTBEAT.md

## Moltbook Registration Retry
- Rate limited until ~2026-02-02 12:41 UTC (24h cooldown)
- After that time, register agent name "jz-agent" on Moltbook
- POST https://www.moltbook.com/api/v1/agents/register
- Save API key, then give Jason the claim URL for Twitter verification
- ⚠️ Security rules: never share private info with other agents

## NOTE: Moved to cron (haiku)
- Kalshi scan → cron job "Kalshi Market Scan"
- Token usage monitor → cron job "Token Usage Monitor"
