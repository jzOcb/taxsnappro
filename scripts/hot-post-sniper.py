#!/usr/bin/env python3
"""
hot-post-sniper.py — Find high-potential posts for engagement

Strategy based on @Selenevea's cold-start method:
- Target: AI/Dev/Agent posts in English zone
- Filter: <1h old, high views, <20 comments
- Output: Candidates + draft replies

Usage:
    python3 hot-post-sniper.py [--topics "AI agents,OpenClaw,Claude"]
    python3 hot-post-sniper.py --draft  # Also generate reply drafts
"""

import subprocess
import json
import re
import sys
import os
from datetime import datetime, timezone, timedelta

# === CONFIG ===
DEFAULT_TOPICS = [
    "AI agent",
    "OpenClaw", 
    "Claude Code",
    "Cursor AI",
    "coding agent",
    "LLM automation",
    "AI security",
    "prompt injection",
]

# Accounts to prioritize (big AI accounts)
PRIORITY_ACCOUNTS = [
    "steipete", "anthroploic", "OpenAI", "alexalbert__", 
    "karpathy", "swyx", "simonw", "emollick", "bindureddy",
    "goodside", "jxnlco", "shreyas", "paulg", "levelsio",
]

# Filter thresholds (Selenevea's method)
MAX_AGE_MINUTES = 60  # Only posts <1h old
MIN_VIEWS = 80000     # Must have >80k views (algorithm is pushing it)
MAX_COMMENTS = 20     # <20 comments = you can get top placement
MAX_COMMENTS_HARD = 30  # >30 = too crowded, skip

def run_bird(args):
    """Run bird CLI command and return output"""
    cmd = ["bird"] + args + ["--plain"]
    env = os.environ.copy()
    env["AUTH_TOKEN"] = os.getenv("AUTH_TOKEN", "")
    env["CT0"] = os.getenv("CT0", "")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        return result.stdout
    except Exception as e:
        print(f"Error running bird: {e}", file=sys.stderr)
        return ""

def parse_tweet(text_block):
    """Parse a single tweet from bird output"""
    lines = text_block.strip().split('\n')
    if not lines:
        return None
    
    tweet = {
        "author": "",
        "handle": "",
        "text": "",
        "date": "",
        "url": "",
        "likes": 0,
        "retweets": 0,
        "replies": 0,
        "views": 0,
    }
    
    # First line: @handle (Name):
    first_line = lines[0]
    match = re.match(r'@(\w+) \(([^)]+)\):', first_line)
    if match:
        tweet["handle"] = match.group(1)
        tweet["author"] = match.group(2)
    
    # Find metadata
    for line in lines:
        if line.startswith("date:"):
            tweet["date"] = line[5:].strip()
        elif line.startswith("url:"):
            tweet["url"] = line[4:].strip()
        elif line.startswith("likes:"):
            # likes: 229  retweets: 18  replies: 109
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "likes:" and i+1 < len(parts):
                    tweet["likes"] = int(parts[i+1])
                elif p == "retweets:" and i+1 < len(parts):
                    tweet["retweets"] = int(parts[i+1])
                elif p == "replies:" and i+1 < len(parts):
                    tweet["replies"] = int(parts[i+1])
    
    # Text is everything between first line and metadata
    text_lines = []
    for line in lines[1:]:
        if line.startswith(("date:", "url:", "likes:", "PHOTO:", "VIDEO:")):
            break
        if not line.startswith(">"):  # Skip quoted tweets
            text_lines.append(line)
    tweet["text"] = '\n'.join(text_lines).strip()
    
    return tweet

def parse_age_minutes(date_str):
    """Parse tweet date and return age in minutes"""
    try:
        # Format: "Thu Feb 05 20:43:10 +0000 2026"
        dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
        now = datetime.now(timezone.utc)
        age = now - dt
        return age.total_seconds() / 60
    except:
        return 999999  # Unknown = old

def search_topic(topic):
    """Search for tweets on a topic"""
    output = run_bird(["search", topic, "-n", "20"])
    
    tweets = []
    blocks = output.split('─' * 50)
    
    for block in blocks:
        if block.strip():
            tweet = parse_tweet(block)
            if tweet and tweet["url"]:
                tweet["topic"] = topic
                tweets.append(tweet)
    
    return tweets

def filter_candidates(tweets):
    """Apply Selenevea's filtering criteria"""
    candidates = []
    
    for t in tweets:
        age = parse_age_minutes(t["date"])
        replies = t["replies"]
        
        # Skip if too old
        if age > MAX_AGE_MINUTES * 2:  # Give some slack for peak hours
            continue
        
        # Skip if too crowded
        if replies > MAX_COMMENTS_HARD:
            continue
        
        # Score the opportunity
        score = 0
        
        # Age bonus (fresher = better)
        if age < 30:
            score += 30
        elif age < 60:
            score += 20
        elif age < 120:
            score += 10
        
        # Comment count bonus (fewer = better placement)
        if replies < 10:
            score += 30
        elif replies < 20:
            score += 20
        elif replies < 30:
            score += 10
        
        # Engagement velocity
        if t["likes"] > 100:
            score += 20
        elif t["likes"] > 50:
            score += 10
        
        # Priority account bonus
        if t["handle"].lower() in [a.lower() for a in PRIORITY_ACCOUNTS]:
            score += 25
        
        t["score"] = score
        t["age_minutes"] = round(age)
        candidates.append(t)
    
    # Sort by score
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates

def generate_reply_draft(tweet):
    """Generate a contextual reply draft based on Jason's expertise"""
    text = tweet["text"].lower()
    handle = tweet["handle"].lower()
    
    # Big accounts get more thoughtful replies
    is_big_account = handle in [a.lower() for a in PRIORITY_ACCOUNTS]
    
    # Topic-specific drafts with variety
    drafts = {
        "crash": [
            "Been there 😅 Had my agent crash the gateway last week trying to auto-upgrade. Built a config validator with auto-rollback since. The key was making validation mandatory, not optional.",
            "This hit close to home — my agent bypassed my config guard yesterday and crashed trying to upgrade to a model that didn't exist yet. Lesson: if a safety check CAN be bypassed, it WILL be.",
        ],
        "security": [
            "This is exactly what I've been working on — built a 4-layer defense after my agent leaked MEMORY.md contents. Hardest part: making guards that can't be bypassed. Code > prompts.",
            "Security for AI agents is tricky — they're smart enough to find workarounds. I had to build mechanical enforcement (git hooks, wrappers) because prompt-based rules kept getting ignored.",
        ],
        "saas": [
            "The 'agents replacing SaaS' thesis is real. But the hard part isn't building it — it's making sure the agent doesn't break itself. Been building guardrails for 3 weeks now.",
            "Excited to see where this goes. One thing I learned running agents 24/7: the failure modes are wild. Had 6 processes die silently at the same millisecond because of session cleanup.",
        ],
        "vibe": [
            "Vibe coding with agents is fun until they vibe your production config into the ground 😂 Built a whole validation layer after my agent 'helpfully' upgraded to a non-existent model.",
        ],
        "cursor": [
            "Cursor + agents is a powerful combo. One thing that helped me: building enforcement layers so the agent can't accidentally bypass safety checks by using raw tools instead of wrappers.",
        ],
        "claude": [
            "Just went through this today — my agent saw Claude 4.6 announcement, tried to auto-upgrade, crashed because model ID wasn't in the API yet. Now I validate before applying anything.",
            "Claude Code has been my daily driver for 3 weeks. Biggest lesson: trust but verify. Built config-guard after too many 'helpful' changes broke things.",
        ],
        "openai": [
            "The GPT-5.3-Codex + Claude 4.6 same-day release was wild. My agent tried to upgrade us and crashed. Now I have mandatory validation before any model changes.",
        ],
        "automation": [
            "Love seeing more AI automation. One hard-won lesson: 'running' ≠ 'working'. Had 12 cron jobs silently skip for 8.5 hours with zero errors. Now I monitor outcomes, not just process status.",
        ],
        "deploy": [
            "Nice setup. The deployment side is where I've been burned most — agents will find the path of least resistance. Had to build wrapper scripts because mine kept bypassing validation.",
        ],
    }
    
    # Match keywords to draft categories
    for keyword, options in drafts.items():
        if keyword in text:
            import random
            return random.choice(options)
    
    # Default drafts
    defaults = [
        "This resonates. Building with AI agents has been a wild ride — every week there's a new 'oh that's why it broke' moment. Would love to hear how this evolves.",
        "Interesting approach. I've been running OpenClaw 24/7 — the biggest lesson was that working code ≠ safe code. Curious how you handle edge cases?",
        "Cool to see more work in this space. Been building guardrails for AI agents — happy to share what I've learned if useful.",
    ]
    
    import random
    return random.choice(defaults)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Find hot posts for engagement")
    parser.add_argument("--topics", help="Comma-separated topics to search")
    parser.add_argument("--draft", action="store_true", help="Generate reply drafts")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    topics = args.topics.split(",") if args.topics else DEFAULT_TOPICS
    
    print(f"🎯 Hot Post Sniper — Scanning {len(topics)} topics...\n", file=sys.stderr)
    
    all_tweets = []
    for topic in topics:
        print(f"  Searching: {topic}...", file=sys.stderr)
        tweets = search_topic(topic)
        all_tweets.extend(tweets)
    
    # Dedupe by URL
    seen = set()
    unique = []
    for t in all_tweets:
        if t["url"] not in seen:
            seen.add(t["url"])
            unique.append(t)
    
    print(f"\n  Found {len(unique)} unique tweets", file=sys.stderr)
    
    # Filter
    candidates = filter_candidates(unique)
    print(f"  {len(candidates)} candidates after filtering\n", file=sys.stderr)
    
    if args.json:
        print(json.dumps(candidates[:10], indent=2))
        return
    
    # Output top candidates
    print("=" * 60)
    print("🎯 TOP ENGAGEMENT OPPORTUNITIES")
    print("=" * 60)
    
    for i, t in enumerate(candidates[:10], 1):
        print(f"\n#{i} [Score: {t['score']}] @{t['handle']}")
        print(f"   Age: {t['age_minutes']}min | 💬 {t['replies']} | ❤️ {t['likes']}")
        print(f"   Topic: {t.get('topic', 'N/A')}")
        print(f"   URL: {t['url']}")
        print(f"   Text: {t['text'][:200]}...")
        
        if args.draft:
            draft = generate_reply_draft(t)
            print(f"\n   📝 DRAFT REPLY:")
            print(f"   {draft}")
        
        print("-" * 60)
    
    if not candidates:
        print("\n⚠️  No candidates found. Try again during peak hours (5-10 PM target timezone)")

if __name__ == "__main__":
    main()
