#!/usr/bin/env python3
"""Process one item from x-queue.json and post it via X API.
Run by cron every 10 minutes. Posts first item, removes it from queue.
Logs results to x-queue-log.json."""

import json
import os
import sys
from datetime import datetime, timezone

QUEUE_FILE = "/home/clawdbot/clawd/scripts/x-queue.json"
LOG_FILE = "/home/clawdbot/clawd/scripts/x-queue-log.json"
ENV_FILE = "/home/clawdbot/clawd/.env.x-api"

def load_creds():
    creds = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                creds[k] = v
    return creds

def post_tweet(text, reply_to=None):
    from requests_oauthlib import OAuth1Session
    creds = load_creds()
    oauth = OAuth1Session(
        creds['X_API_KEY'],
        client_secret=creds['X_API_SECRET'],
        resource_owner_key=creds['X_ACCESS_TOKEN'],
        resource_owner_secret=creds['X_ACCESS_TOKEN_SECRET'],
    )
    payload = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": str(reply_to)}
    
    response = oauth.post("https://api.x.com/2/tweets", json=payload)
    result = response.json()
    
    if response.status_code == 201:
        tweet_id = result['data']['id']
        return {"ok": True, "id": tweet_id, "url": f"https://x.com/xxx111god/status/{tweet_id}"}
    else:
        return {"ok": False, "status": response.status_code, "error": result}

def main():
    # Load queue
    if not os.path.exists(QUEUE_FILE):
        print("No queue file found.")
        return
    
    with open(QUEUE_FILE) as f:
        queue = json.load(f)
    
    if not queue:
        print("Queue empty, nothing to post.")
        return
    
    # Pop first item
    item = queue.pop(0)
    text = item["text"]
    reply_to = item.get("reply_to")
    target = item.get("target", "unknown")
    
    # Post
    result = post_tweet(text, reply_to)
    now = datetime.now(timezone.utc).isoformat()
    
    # Save remaining queue
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
    
    # Log result
    log_entry = {
        "time": now,
        "target": target,
        "reply_to": reply_to,
        "text": text[:80] + "..." if len(text) > 80 else text,
        "result": result
    }
    
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            log = json.load(f)
    log.append(log_entry)
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    
    remaining = len(queue)
    if result["ok"]:
        print(f"✅ Posted to {target}: {result['url']} ({remaining} remaining in queue)")
    else:
        print(f"❌ Failed for {target}: {result['error']} ({remaining} remaining in queue)")

if __name__ == "__main__":
    main()
