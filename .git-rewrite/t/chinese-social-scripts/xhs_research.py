#!/usr/bin/env python3
"""
XHS Research Tool - Scrape covers and notes from Xiaohongshu without login.
Uses SSR data from explore page (no cookie/login needed).

Usage:
    python3 xhs_research.py --category skincare --count 50 --download
"""
import requests, json, re, os, time, sys

def get_ssr_feeds(session, category='homefeed.skincare_v3'):
    """Get feeds from XHS explore page SSR data."""
    url = f"https://www.xiaohongshu.com/explore?channel_id={category}"
    r = session.get(url, timeout=15)
    if r.status_code != 200:
        return []
    
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)\s*</script>', r.text, re.DOTALL)
    if not match:
        return []
    
    raw = match.group(1).replace('undefined', 'null')
    data = json.loads(raw)
    feeds = data.get('feed', {}).get('feeds', [])
    
    results = []
    for item in feeds:
        nc = item.get('noteCard', {})
        cover = nc.get('cover', {})
        url = cover.get('urlDefault', '')
        if url:
            results.append({
                'title': nc.get('displayTitle', ''),
                'user': nc.get('user', {}).get('nickname', ''),
                'cover_url': url,
                'note_id': item.get('id', ''),
                'likes': nc.get('interactInfo', {}).get('likedCount', ''),
                'width': cover.get('width', 0),
                'height': cover.get('height', 0),
                'category': category,
            })
    return results


def download_covers(covers, output_dir):
    """Download cover images."""
    os.makedirs(output_dir, exist_ok=True)
    downloaded = 0
    for c in covers:
        try:
            r = requests.get(c['cover_url'], timeout=10)
            if r.status_code == 200 and len(r.content) > 5000:
                fname = f"{output_dir}/{c['note_id']}.jpg"
                with open(fname, 'wb') as f:
                    f.write(r.content)
                downloaded += 1
        except:
            pass
    return downloaded


CATEGORIES = {
    'skincare': 'homefeed.skincare_v3',
    'cosmetics': 'homefeed.cosmetics_v3',
    'fashion': 'homefeed.fashion_v3',
    'food': 'homefeed.food_v3',
    'travel': 'homefeed.travel_v3',
    'fitness': 'homefeed.fitness_v3',
    'home': 'homefeed.household_product_v3',
}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='XHS Cover Research Tool')
    parser.add_argument('--category', '-c', default='skincare', choices=list(CATEGORIES.keys()))
    parser.add_argument('--all', action='store_true', help='Scrape all categories')
    parser.add_argument('--download', '-d', action='store_true', help='Download cover images')
    parser.add_argument('--output', '-o', default='/tmp/xhs_covers', help='Output directory')
    args = parser.parse_args()
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    })
    
    cats = CATEGORIES if args.all else {args.category: CATEGORIES[args.category]}
    all_covers = []
    
    for name, cat_id in cats.items():
        feeds = get_ssr_feeds(session, cat_id)
        all_covers.extend(feeds)
        print(f"📌 {name}: {len(feeds)} covers")
        time.sleep(0.5)
    
    print(f"\n📊 Total: {len(all_covers)} covers")
    
    if args.download:
        n = download_covers(all_covers, args.output)
        print(f"📥 Downloaded {n} images to {args.output}")
    
    # Save metadata
    meta_path = f"{args.output}/metadata.json"
    os.makedirs(args.output, exist_ok=True)
    with open(meta_path, 'w') as f:
        json.dump(all_covers, f, ensure_ascii=False, indent=2)
    print(f"💾 Metadata saved to {meta_path}")


if __name__ == '__main__':
    main()
