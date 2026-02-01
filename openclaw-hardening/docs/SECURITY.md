# 🛡️ Security Hardening Guide

## Overview

OpenClaw/Clawdbot runs an AI agent with shell access on your machine. The official docs acknowledge:

> *"There is no 'perfectly secure' setup."*

This guide covers the **practical minimum** to avoid getting owned.

## Threat Model

| Threat | Vector | Severity |
|--------|--------|----------|
| SSH brute force | Password auth enabled | 🔴 Critical |
| Gateway hijack | Port 18789 on 0.0.0.0 | 🔴 Critical |
| Credential leak | Plaintext API keys | 🟡 High |
| Prompt injection | Untrusted content | 🟡 High |
| Session log leak | World-readable files | 🟡 High |
| Browser control | Port 18791 exposed | 🔴 Critical |

## What the Scripts Do

### audit.sh (9 checks)

1. **Open ports** — anything on 0.0.0.0?
2. **SSH config** — password auth? root login?
3. **Firewall** — UFW enabled?
4. **Failed logins** — being scanned?
5. **fail2ban** — brute force protection?
6. **Gateway config** — auth? loopback binding?
7. **Tailscale** — secure remote access?
8. **Credentials** — plaintext keys? file permissions?
9. **Browser control** — port 18791 exposed?

### harden.sh (4 steps)

1. **UFW** — deny all incoming, allow only SSH
2. **SSH** — change port, disable password, disable root, limit retries
3. **fail2ban** — 3 failures → 1h ban
4. **Tailscale** — guided install for secure remote access

## Post-Hardening Checklist

After running `harden.sh`:

- [ ] Tested SSH on new port from second terminal
- [ ] Removed old SSH port from UFW
- [ ] Set Gateway to `bind: "loopback"`
- [ ] Generated auth token: `openssl rand -hex 32`
- [ ] Moved API keys to environment variables
- [ ] Set `chmod 600` on openclaw.json
- [ ] Set `chmod -R o-rwx` on sessions directory
- [ ] Installed Tailscale for remote access
- [ ] Ran `audit.sh` again to verify

## What This Doesn't Cover

- **Prompt injection** — no script can fix this; be careful with untrusted content
- **Supply chain** — audit skills before installing (`skills-audit`)
- **Physical access** — encrypt your disk
- **Backups** — set up regular backups of `~/.openclaw/`

## References

- [OpenClaw Security Docs](https://docs.clawd.bot)
- [huangserva's Security Analysis](https://x.com/servasyy_ai/status/2015677935039213876)
