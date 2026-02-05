#!/usr/bin/env python3
"""X/Twitter API v2 posting script using OAuth 1.0a
Usage: 
  python3 x-post.py "tweet text"
  python3 x-post.py --reply-to <tweet_id> "reply text"
"""
import sys
import os
import json
from requests_oauthlib import OAuth1Session

# Load credentials
ENV_FILE = "/home/clawdbot/clawd/.env.x-api"
creds = {}
with open(ENV_FILE) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            creds[k] = v

API_KEY = creds['X_API_KEY']
API_SECRET = creds['X_API_SECRET']
ACCESS_TOKEN = creds['X_ACCESS_TOKEN']
ACCESS_TOKEN_SECRET = creds['X_ACCESS_TOKEN_SECRET']

def post_tweet(text, reply_to=None):
    oauth = OAuth1Session(
        API_KEY,
        client_secret=API_SECRET,
        resource_owner_key=ACCESS_TOKEN,
        resource_owner_secret=ACCESS_TOKEN_SECRET,
    )
    
    payload = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": str(reply_to)}
    
    response = oauth.post(
        "https://api.x.com/2/tweets",
        json=payload,
    )
    
    result = response.json()
    
    if response.status_code == 201:
        tweet_id = result['data']['id']
        print(f"✅ Tweet posted! ID: {tweet_id}")
        print(f"🔗 https://x.com/xxx111god/status/{tweet_id}")
        return tweet_id
    else:
        print(f"❌ Error {response.status_code}: {json.dumps(result, indent=2)}")
        return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Post to X/Twitter via API v2")
    parser.add_argument("text", help="Tweet text")
    parser.add_argument("--reply-to", help="Tweet ID to reply to")
    parser.add_argument("--dry-run", action="store_true", help="Print but don't post")
    args = parser.parse_args()
    
    if args.dry_run:
        print(f"🔍 DRY RUN — would post:")
        print(f"  Text: {args.text}")
        if args.reply_to:
            print(f"  Reply to: {args.reply_to}")
    else:
        post_tweet(args.text, args.reply_to)
