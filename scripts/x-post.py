#!/usr/bin/env python3
"""X/Twitter API v2 posting script using OAuth 1.0a
Usage: 
  python3 x-post.py "tweet text"
  python3 x-post.py --reply-to <tweet_id> "reply text"
  python3 x-post.py --quote <tweet_id> "quote tweet text"

Safety checks (enforced, not advisory):
  1. --reply-to: verifies target tweet is NOT by @xxx111god (prevents self-reply)
  2. --reply-to: checks if @xxx111god already replied to that tweet (prevents duplicate)
"""
import sys
import os
import json
import subprocess
from requests_oauthlib import OAuth1Session

MY_USERNAME = "xxx111god"

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


def _bird_env():
    """Build env dict with bird cookie auth from bashrc."""
    env = os.environ.copy()
    # Read AUTH_TOKEN and CT0 from bashrc if not already set
    if not env.get("AUTH_TOKEN") or not env.get("CT0"):
        try:
            bashrc = os.path.expanduser("~/.bashrc")
            with open(bashrc) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("export AUTH_TOKEN="):
                        env["AUTH_TOKEN"] = line.split("=", 1)[1].strip('"\'')
                    elif line.startswith("export CT0="):
                        env["CT0"] = line.split("=", 1)[1].strip('"\'')
        except Exception:
            pass
    return env


def check_tweet_author(tweet_id):
    """Check who authored a tweet. Returns username or None."""
    try:
        result = subprocess.run(
            ["bird", "read", str(tweet_id), "--json-full"],
            capture_output=True, text=True, timeout=15,
            env=_bird_env()
        )
        if result.returncode != 0:
            # If bird fails, try parsing the API response directly
            # FAIL CLOSED: if we can't verify, block the action
            print(f"⚠️  Could not verify tweet author (bird failed). Blocking to be safe.")
            return MY_USERNAME  # assume self to block
        data = json.loads(result.stdout)
        if isinstance(data, list):
            data = data[0]
        author = data.get("author", {})
        return author.get("username", None)
    except Exception as e:
        print(f"⚠️  Could not verify tweet author ({e}). Blocking to be safe.")
        return MY_USERNAME  # fail closed


def check_already_replied(tweet_id):
    """Check if @xxx111god already replied to this tweet. Returns True if already replied."""
    try:
        result = subprocess.run(
            ["bird", "replies", str(tweet_id), "--json"],
            capture_output=True, text=True, timeout=15,
            env=_bird_env()
        )
        if result.returncode != 0:
            return False  # can't check replies, allow posting (less critical)
        data = json.loads(result.stdout)
        tweets = data if isinstance(data, list) else data.get("tweets", [])
        for t in tweets:
            author = t.get("author", {})
            if author.get("username", "").lower() == MY_USERNAME.lower():
                return True
        return False
    except Exception:
        return False  # can't check, allow posting


def upload_media(image_path):
    """Upload image to Twitter and return media_id."""
    import base64
    
    oauth = OAuth1Session(
        API_KEY,
        client_secret=API_SECRET,
        resource_owner_key=ACCESS_TOKEN,
        resource_owner_secret=ACCESS_TOKEN_SECRET,
    )
    
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # v1.1 media upload endpoint
    response = oauth.post(
        "https://upload.twitter.com/1.1/media/upload.json",
        data={"media_data": image_data}
    )
    
    if response.status_code == 200:
        media_id = response.json()['media_id_string']
        print(f"📷 Image uploaded: {media_id}")
        return media_id
    else:
        print(f"❌ Media upload failed: {response.status_code} - {response.text[:200]}")
        return None


def post_tweet(text, reply_to=None, quote_tweet_id=None, skip_checks=False, media_ids=None):
    oauth = OAuth1Session(
        API_KEY,
        client_secret=API_SECRET,
        resource_owner_key=ACCESS_TOKEN,
        resource_owner_secret=ACCESS_TOKEN_SECRET,
    )
    
    # === SAFETY CHECKS (code is law) ===
    if reply_to and not skip_checks:
        # Check 1: Don't reply to own tweets
        author = check_tweet_author(reply_to)
        if author and author.lower() == MY_USERNAME.lower():
            print(f"🚫 BLOCKED: Tweet {reply_to} is by @{MY_USERNAME} — self-reply prevented")
            print(f"   If this is intentional (thread continuation), use --skip-checks")
            return None
        
        # Check 2: Don't reply if already replied
        if check_already_replied(reply_to):
            print(f"🚫 BLOCKED: @{MY_USERNAME} already replied to {reply_to} — duplicate prevented")
            print(f"   If this is intentional, use --skip-checks")
            return None
    
    payload = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": str(reply_to)}
    if quote_tweet_id:
        payload["quote_tweet_id"] = str(quote_tweet_id)
    if media_ids:
        payload["media"] = {"media_ids": media_ids}
    
    response = oauth.post(
        "https://api.x.com/2/tweets",
        json=payload,
    )
    
    result = response.json()
    
    if response.status_code == 201:
        tweet_id = result['data']['id']
        print(f"✅ Tweet posted! ID: {tweet_id}")
        print(f"🔗 https://x.com/{MY_USERNAME}/status/{tweet_id}")
        return tweet_id
    else:
        print(f"❌ Error {response.status_code}: {json.dumps(result, indent=2)}")
        return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Post to X/Twitter via API v2")
    parser.add_argument("text", help="Tweet text")
    parser.add_argument("--reply-to", help="Tweet ID to reply to")
    parser.add_argument("--quote", help="Tweet ID to quote (proper quote tweet, not just URL)")
    parser.add_argument("--image", help="Path to image file to attach")
    parser.add_argument("--dry-run", action="store_true", help="Print but don't post")
    parser.add_argument("--skip-checks", action="store_true", 
                        help="Skip self-reply and duplicate checks (for intentional threads)")
    args = parser.parse_args()
    
    if args.dry_run:
        print(f"🔍 DRY RUN — would post:")
        print(f"  Text: {args.text}")
        if args.reply_to:
            print(f"  Reply to: {args.reply_to}")
        if args.quote:
            print(f"  Quote tweet: {args.quote}")
        if args.image:
            print(f"  Image: {args.image}")
    else:
        media_ids = None
        if args.image:
            media_id = upload_media(args.image)
            if media_id:
                media_ids = [media_id]
            else:
                print("⚠️  Proceeding without image due to upload failure")
        post_tweet(args.text, args.reply_to, args.quote, args.skip_checks, media_ids)
