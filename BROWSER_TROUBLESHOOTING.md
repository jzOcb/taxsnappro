# Browser Troubleshooting Guide

## Common Issues & Solutions

### Issue 1: Browser Doesn't Auto-Open

**Symptoms:**
- `browser` tool doesn't automatically open browser
- Get permission errors
- Need to manually click extension/plugin
- "No browser found" errors

**Root Cause:**
OpenClaw tries to use system browser by default, which may:
- Require user interaction (extension click)
- Have permission issues on headless servers
- Not have required extensions installed

**Solution:**

Add this to your `~/.clawdbot/clawdbot.json` (root level):

```json
{
  "browser": {
    "defaultProfile": "openclaw"
  }
}
```

**What this does:**
- Uses OpenClaw's dedicated browser profile
- Browser starts automatically without user interaction
- Sessions persist in the dedicated profile
- No extension/permission issues

**Full example config:**
```json
{
  "browser": {
    "enabled": true,
    "defaultProfile": "openclaw",
    "headless": true,
    "noSandbox": true,
    "profiles": {
      "openclaw": {
        "cdpPort": 18800,
        "color": "0066FF"
      }
    }
  }
}
```

### Issue 2: Snap Chromium Not Working

**Symptom:**
```
Error: Browser doesn't support CDP
```

**Solution:**
Install Google Chrome (not Chromium snap):

```bash
# Remove snap chromium
sudo snap remove chromium

# Install Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f

# Update config
# Set executablePath: "/usr/bin/google-chrome"
```

### Issue 3: Headless Server Issues

**Symptom:**
- Browser crashes on server
- Display errors
- "Cannot open display" errors

**Solution:**
Ensure `headless: true` and `noSandbox: true`:

```json
{
  "browser": {
    "headless": true,
    "noSandbox": true
  }
}
```

### Issue 4: Port Already in Use

**Symptom:**
```
Error: CDP port 18800 already in use
```

**Solution:**

```bash
# Find and kill existing process
lsof -ti:18800 | xargs kill -9

# Or change port in config
# "cdpPort": 18801
```

### Issue 5: Profile Not Persisting

**Symptom:**
- Need to login every time
- Sessions don't persist
- Cookies lost between runs

**Solution:**

Check profile directory exists and has permissions:

```bash
ls -la ~/.clawdbot/browser/openclaw/user-data/

# If doesn't exist or wrong permissions:
mkdir -p ~/.clawdbot/browser/openclaw/user-data
chmod 755 ~/.clawdbot/browser/openclaw/user-data
```

---

## Best Practices

### For Servers (Headless)

```json
{
  "browser": {
    "enabled": true,
    "executablePath": "/usr/bin/google-chrome",
    "headless": true,
    "noSandbox": true,
    "defaultProfile": "openclaw"
  }
}
```

### For Desktop (Interactive)

```json
{
  "browser": {
    "enabled": true,
    "headless": false,
    "defaultProfile": "openclaw"
  }
}
```

### Multiple Profiles

```json
{
  "browser": {
    "defaultProfile": "openclaw",
    "profiles": {
      "openclaw": {
        "cdpPort": 18800
      },
      "testing": {
        "cdpPort": 18801
      }
    }
  }
}
```

Then switch profiles:
```javascript
browser action=start profile=testing
```

---

## Verification

After configuration changes:

```bash
# 1. Restart clawdbot
clawdbot gateway restart

# 2. Test browser
clawdbot message send --target YOUR_ID --message "Test browser"
# Then use browser tool

# 3. Check browser started
lsof -i:18800  # Should show chrome process
```

---

## Community Tips

**Shared by @jzOcb (2026-02-02):**
> 很多人用openclaw遇到浏览器有一个问题，他不给你主动打开浏览器，要么是没权限，要么是让你手动点一下插件，很麻烦。
> 
> 分享一个配置，在你的openclaw.json的根节点中加入：
> ```json
> "browser": {
>   "defaultProfile": "openclaw"
> }
> ```
> openclaw就会默认用他独立的浏览器启动，后续只需要在这里登录各类会话就行，也不会报错

---

## Still Having Issues?

1. Check logs: `tail -f ~/.clawdbot/logs/browser.log`
2. Verify Chrome installed: `google-chrome --version`
3. Test CDP manually: `google-chrome --remote-debugging-port=18800 --headless`
4. Ask in Discord: https://discord.com/invite/clawd

---

**Last Updated:** 2026-02-02  
**Contributors:** @jzOcb, community feedback
