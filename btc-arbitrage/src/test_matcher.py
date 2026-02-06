#!/usr/bin/env python3
"""
Test script for the new Market Matcher v3.
Runs a single scan cycle and prints all discovered pairs by category.
"""

import sys
import os
import time
import logging
import json

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from market_matcher import MatcherEngine, convert_v3_to_legacy_pair

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger("test-matcher")


def main():
    print("=" * 70)
    print("🧪 MARKET MATCHER v3 — TEST RUN")
    print("=" * 70)
    print()

    start = time.time()
    engine = MatcherEngine()
    pairs = engine.find_all_pairs()
    elapsed = time.time() - start

    print()
    print("=" * 70)
    print(f"📊 RESULTS: {len(pairs)} pairs found in {elapsed:.1f}s")
    print("=" * 70)

    # Group by category
    by_cat = engine.get_pairs_by_category()
    categories_found = set()

    for cat, cat_pairs in sorted(by_cat.items()):
        categories_found.add(cat)
        print()
        print(f"┌{'─' * 68}┐")
        print(f"│ 📂 {cat.upper():63s}│")
        print(f"│ {len(cat_pairs)} pairs{' ' * 59}│")
        print(f"├{'─' * 68}┤")

        for i, p in enumerate(cat_pairs):
            print(f"│                                                                    │")
            print(f"│  [{i+1}] {p.pair_id:62s}│")
            print(f"│  PM:  {p.pm_event_title[:62]:62s}│")
            print(f"│  K:   {p.kalshi_event_ticker:62s}│")
            print(f"│  Match Quality: {p.match_quality}/100{' ' * 47}│")
            print(f"│  Notes: {p.notes[:60]:60s}│")

            # Show PM tokens summary
            if p.pm_tokens:
                prices = [t.get("yes_price", 0) for t in p.pm_tokens if t.get("yes_price", 0) > 0.001]
                if prices:
                    print(f"│  PM tokens: {len(p.pm_tokens)} | prices: {min(prices):.3f}–{max(prices):.3f}{' ' * 30}│"[:71] + "│")
                else:
                    print(f"│  PM tokens: {len(p.pm_tokens)} (settled/zero prices){' ' * 35}│"[:71] + "│")

            # Show Kalshi markets summary
            if p.kalshi_markets:
                prices = [m.get("yes_price", 0) for m in p.kalshi_markets if m.get("yes_price", 0) > 0.001]
                if prices:
                    print(f"│  K markets: {len(p.kalshi_markets)} | prices: {min(prices):.3f}–{max(prices):.3f}{' ' * 30}│"[:71] + "│")
                else:
                    print(f"│  K markets: {len(p.kalshi_markets)} (no active prices){' ' * 35}│"[:71] + "│")

            # Show legacy conversion
            legacy = convert_v3_to_legacy_pair(p)
            print(f"│  Spread: {legacy['spread']:+.3f} (PM {legacy['pm_yes_price']:.3f} - K {legacy['kalshi_yes_price']:.3f}){' ' * 20}│"[:71] + "│")

        print(f"└{'─' * 68}┘")

    # Quality checks
    print()
    print("=" * 70)
    print("🔬 QUALITY CHECKS")
    print("=" * 70)

    # Check 1: Categories found
    print(f"\n  Categories found: {len(categories_found)}")
    for cat in sorted(categories_found):
        count = len(by_cat.get(cat, []))
        print(f"    ✅ {cat}: {count} pairs")

    target_cats = {"weather", "crypto", "nba", "trump_mentions", "fed_rate"}
    missing = target_cats - categories_found
    if missing:
        print(f"    ⚠️  Missing categories: {missing}")
    if len(categories_found) >= 5:
        print(f"  ✅ PASS: {len(categories_found)} categories ≥ 5 required")
    else:
        print(f"  ❌ FAIL: only {len(categories_found)} categories (need ≥5)")

    # Check 2: Weather cities
    weather_cities = set()
    for p in by_cat.get("weather", []):
        weather_cities.add(p.asset)
    print(f"\n  Weather cities: {weather_cities or 'none'}")
    expected_cities = {"NYC", "Miami", "Chicago", "Seattle", "Atlanta"}
    found_cities = weather_cities & expected_cities
    if len(found_cities) >= 3:
        print(f"  ✅ PASS: {len(found_cities)}/5 weather cities matched")
    else:
        print(f"  ⚠️  Only {len(found_cities)}/5 weather cities ({found_cities})")

    # Check 3: NBA games
    nba_count = len(by_cat.get("nba", []))
    print(f"\n  NBA games matched: {nba_count}")
    if nba_count > 0:
        print(f"  ✅ PASS: NBA games found")
    else:
        print(f"  ⚠️  No NBA games matched (may be no overlapping games today)")

    # Check 4: Duplicate check
    pair_ids = [p.pair_id for p in pairs]
    unique_ids = set(pair_ids)
    if len(pair_ids) == len(unique_ids):
        print(f"\n  ✅ PASS: 0 duplicate pairs")
    else:
        dupes = len(pair_ids) - len(unique_ids)
        print(f"\n  ❌ FAIL: {dupes} duplicate pairs found")

    # Check 5: Performance
    print(f"\n  Scan time: {elapsed:.1f}s")
    if elapsed < 60:
        print(f"  ✅ PASS: {elapsed:.1f}s < 60s target")
    else:
        print(f"  ❌ FAIL: {elapsed:.1f}s > 60s target")

    # Check 6: Cache efficiency
    cache_stats = engine.cache.stats
    total_requests = cache_stats["hits"] + cache_stats["misses"]
    hit_rate = cache_stats["hits"] / max(total_requests, 1) * 100
    print(f"\n  API cache: {total_requests} requests, {hit_rate:.0f}% hit rate")
    print(f"    Hits: {cache_stats['hits']}, Misses: {cache_stats['misses']}, Errors: {cache_stats['errors']}")

    print()
    print("=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)

    return len(pairs)


if __name__ == "__main__":
    count = main()
    sys.exit(0 if count > 0 else 1)
