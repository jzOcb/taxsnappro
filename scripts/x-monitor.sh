#!/usr/bin/env bash
# X/Twitter Monitor — scans for engagement opportunities, drafts replies
# Runs via cron every 4h, sends opportunities to Telegram for approval
# SAFE: read-only bird CLI usage, no posting

set -euo pipefail

export AUTH_TOKEN="6cf34d4b14fa23b3f6d2112996c56708b6accbcb"
export CT0="aefda05c68918fa5d59c32453a6a154758da3764f45ddaf5894990a890f2929dee7f2fafefd7b55eb6400f74b03d32eded1ecdabace67c3af8b248662ef9878a0b2d83bad3eccb2d6ba25e59d72102a7"

STATE_DIR="/home/clawdbot/clawd/memory/x-monitor"
mkdir -p "$STATE_DIR"

SEEN_FILE="$STATE_DIR/seen-tweets.txt"
touch "$SEEN_FILE"

OUTPUT_FILE="$STATE_DIR/opportunities-$(date +%Y%m%d-%H%M).md"

# Track what we find
OPPORTUNITIES=""
COUNT=0

add_opportunity() {
    local category="$1"
    local handle="$2"
    local text="$3"
    local url="$4"
    local date="$5"
    
    # Check if we've seen this URL before
    if grep -qF "$url" "$SEEN_FILE" 2>/dev/null; then
        return
    fi
    
    echo "$url" >> "$SEEN_FILE"
    COUNT=$((COUNT + 1))
    
    OPPORTUNITIES="${OPPORTUNITIES}
### ${COUNT}. [${category}] @${handle}
> ${text:0:280}
🔗 ${url}
📅 ${date}
---
"
}

echo "🔍 X Monitor scan started at $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# --- SCAN 1: @openclaw latest tweets (reply opportunities) ---
echo "Scanning @openclaw..."
while IFS= read -r line; do
    if [[ "$line" =~ ^@openclaw ]]; then
        current_text=""
        current_url=""
        current_date=""
    fi
    if [[ "$line" =~ ^date: ]]; then
        current_date="${line#date: }"
    fi
    if [[ "$line" =~ ^url:\ (https://x.com/.+) ]]; then
        current_url="${BASH_REMATCH[1]}"
    fi
    if [[ -z "${current_text:-}" && ! "$line" =~ ^@ && ! "$line" =~ ^date: && ! "$line" =~ ^url: && ! "$line" =~ ^─ && -n "$line" ]]; then
        current_text="$line"
    fi
    if [[ "$line" =~ ^─── && -n "${current_url:-}" ]]; then
        add_opportunity "OPENCLAW" "openclaw" "${current_text:-}" "${current_url}" "${current_date:-}"
        current_text=""
        current_url=""
        current_date=""
    fi
done < <(bird user-tweets @openclaw -n 5 --plain 2>/dev/null || true)

# --- SCAN 2: Search "openclaw security" ---
echo "Scanning 'openclaw security'..."
while IFS= read -r line; do
    if [[ "$line" =~ ^@([A-Za-z0-9_]+)\ \( ]]; then
        current_handle="${BASH_REMATCH[1]}"
        current_text=""
        current_url=""
        current_date=""
    fi
    if [[ "$line" =~ ^date: ]]; then
        current_date="${line#date: }"
    fi
    if [[ "$line" =~ ^url:\ (https://x.com/.+) ]]; then
        current_url="${BASH_REMATCH[1]}"
    fi
    if [[ -z "${current_text:-}" && ! "$line" =~ ^@ && ! "$line" =~ ^date: && ! "$line" =~ ^url: && ! "$line" =~ ^─ && ! "$line" =~ ^PHOTO && -n "$line" ]]; then
        current_text="$line"
    fi
    if [[ "$line" =~ ^─── && -n "${current_url:-}" ]]; then
        add_opportunity "SECURITY" "${current_handle:-unknown}" "${current_text:-}" "${current_url}" "${current_date:-}"
        current_text=""
        current_url=""
        current_date=""
    fi
done < <(bird search "openclaw security OR hardening OR guardrails" -n 10 --plain 2>/dev/null || true)

# --- SCAN 3: Search "openclaw" in Chinese ---
echo "Scanning 'openclaw' Chinese community..."
while IFS= read -r line; do
    if [[ "$line" =~ ^@([A-Za-z0-9_]+)\ \( ]]; then
        current_handle="${BASH_REMATCH[1]}"
        current_text=""
        current_url=""
        current_date=""
    fi
    if [[ "$line" =~ ^date: ]]; then
        current_date="${line#date: }"
    fi
    if [[ "$line" =~ ^url:\ (https://x.com/.+) ]]; then
        current_url="${BASH_REMATCH[1]}"
    fi
    if [[ -z "${current_text:-}" && ! "$line" =~ ^@ && ! "$line" =~ ^date: && ! "$line" =~ ^url: && ! "$line" =~ ^─ && ! "$line" =~ ^PHOTO && -n "$line" ]]; then
        current_text="$line"
    fi
    if [[ "$line" =~ ^─── && -n "${current_url:-}" ]]; then
        add_opportunity "CHINESE" "${current_handle:-unknown}" "${current_text:-}" "${current_url}" "${current_date:-}"
        current_text=""
        current_url=""
        current_date=""
    fi
done < <(bird search "openclaw 安全 OR 设置 OR agent OR 龙虾" -n 10 --plain 2>/dev/null || true)

# --- SCAN 4: Search for agent guardrails / security discussions ---
echo "Scanning 'AI agent guardrails'..."
while IFS= read -r line; do
    if [[ "$line" =~ ^@([A-Za-z0-9_]+)\ \( ]]; then
        current_handle="${BASH_REMATCH[1]}"
        current_text=""
        current_url=""
        current_date=""
    fi
    if [[ "$line" =~ ^date: ]]; then
        current_date="${line#date: }"
    fi
    if [[ "$line" =~ ^url:\ (https://x.com/.+) ]]; then
        current_url="${BASH_REMATCH[1]}"
    fi
    if [[ -z "${current_text:-}" && ! "$line" =~ ^@ && ! "$line" =~ ^date: && ! "$line" =~ ^url: && ! "$line" =~ ^─ && ! "$line" =~ ^PHOTO && -n "$line" ]]; then
        current_text="$line"
    fi
    if [[ "$line" =~ ^─── && -n "${current_url:-}" ]]; then
        add_opportunity "GUARDRAILS" "${current_handle:-unknown}" "${current_text:-}" "${current_url}" "${current_date:-}"
        current_text=""
        current_url=""
        current_date=""
    fi
done < <(bird search "AI agent guardrails OR \"agent security\" open source" -n 10 --plain 2>/dev/null || true)

# --- SCAN 5: Check mentions ---
echo "Scanning mentions..."
while IFS= read -r line; do
    if [[ "$line" =~ ^@([A-Za-z0-9_]+)\ \( ]]; then
        current_handle="${BASH_REMATCH[1]}"
        current_text=""
        current_url=""
        current_date=""
    fi
    if [[ "$line" =~ ^date: ]]; then
        current_date="${line#date: }"
    fi
    if [[ "$line" =~ ^url:\ (https://x.com/.+) ]]; then
        current_url="${BASH_REMATCH[1]}"
    fi
    if [[ -z "${current_text:-}" && ! "$line" =~ ^@ && ! "$line" =~ ^date: && ! "$line" =~ ^url: && ! "$line" =~ ^─ && ! "$line" =~ ^PHOTO && -n "$line" ]]; then
        current_text="$line"
    fi
    if [[ "$line" =~ ^─── && -n "${current_url:-}" ]]; then
        add_opportunity "MENTION" "${current_handle:-unknown}" "${current_text:-}" "${current_url}" "${current_date:-}"
        current_text=""
        current_url=""
        current_date=""
    fi
done < <(bird mentions -n 10 --plain 2>/dev/null || true)

# --- SCAN 6: Key accounts latest posts ---
for account in steipete galnagli asterai_io ryancarson predict_anon; do
    echo "Scanning @${account}..."
    while IFS= read -r line; do
        if [[ "$line" =~ ^@([A-Za-z0-9_]+)\ \( ]]; then
            current_handle="${BASH_REMATCH[1]}"
            current_text=""
            current_url=""
            current_date=""
        fi
        if [[ "$line" =~ ^date: ]]; then
            current_date="${line#date: }"
        fi
        if [[ "$line" =~ ^url:\ (https://x.com/.+) ]]; then
            current_url="${BASH_REMATCH[1]}"
        fi
        if [[ -z "${current_text:-}" && ! "$line" =~ ^@ && ! "$line" =~ ^date: && ! "$line" =~ ^url: && ! "$line" =~ ^─ && ! "$line" =~ ^PHOTO && ! "$line" =~ ^VIDEO && -n "$line" ]]; then
            current_text="$line"
        fi
        if [[ "$line" =~ ^─── && -n "${current_url:-}" ]]; then
            add_opportunity "KEY_ACCOUNT" "${current_handle:-$account}" "${current_text:-}" "${current_url}" "${current_date:-}"
            current_text=""
            current_url=""
            current_date=""
        fi
    done < <(bird user-tweets "@${account}" -n 3 --plain 2>/dev/null || true)
done

# --- Output results ---
echo "## Found ${COUNT} new opportunities" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

if [ "$COUNT" -gt 0 ]; then
    echo "$OPPORTUNITIES" >> "$OUTPUT_FILE"
fi

# Trim seen file to last 500 entries
if [ "$(wc -l < "$SEEN_FILE")" -gt 500 ]; then
    tail -500 "$SEEN_FILE" > "$SEEN_FILE.tmp"
    mv "$SEEN_FILE.tmp" "$SEEN_FILE"
fi

echo "✅ Scan complete: ${COUNT} new opportunities found"
echo "📄 Results: ${OUTPUT_FILE}"

# Output the count for the cron job to pick up
echo "OPPORTUNITY_COUNT=${COUNT}"
echo "OPPORTUNITY_FILE=${OUTPUT_FILE}"
