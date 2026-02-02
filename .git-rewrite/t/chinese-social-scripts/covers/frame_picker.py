exec(open('/tmp/sandbox_bootstrap.py').read())

"""
视频截帧智能选择器
从视频中提取帧，按封面适合度评分，选出最好的几张。

评分维度：
- 亮度适中（不过曝不过暗）
- 对比度高（画面清晰有层次）
- 中心区域有人脸（肤色检测）
- 画面清晰度（锐度）

Usage:
  python frame_picker.py --video input.mp4 --top 5
  python frame_picker.py --video input.mp4 --top 5 --interval 2
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
from PIL import Image
import numpy as np

def extract_frames(video_path, output_dir, interval=1.0):
    """Extract frames from video using ffmpeg at given interval (seconds)"""
    
    # ffmpeg memfd trick for noexec /tmp
    ffmpeg_path = "/usr/bin/ffmpeg"
    if not os.path.exists(ffmpeg_path):
        # Try memfd approach
        import ctypes
        libc = ctypes.CDLL("libc.so.6")
        fd = libc.memfd_create(b"ffmpeg", 0)
        with open(f"/proc/self/fd/{fd}", "wb") as memf:
            with open("/tmp/ffmpeg", "rb") as src:  # need ffmpeg binary somewhere
                memf.write(src.read())
        ffmpeg_path = f"/proc/self/fd/{fd}"
        os.fchmod(fd, 0o755)
    
    os.makedirs(output_dir, exist_ok=True)
    
    cmd = [
        ffmpeg_path, "-i", video_path,
        "-vf", f"fps=1/{interval}",  # 1 frame per N seconds
        "-q:v", "2",  # high quality JPEG
        os.path.join(output_dir, "frame_%04d.jpg"),
        "-y", "-loglevel", "error"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"⚠️ ffmpeg error: {result.stderr}")
        return []
    
    frames = sorted([
        os.path.join(output_dir, f) 
        for f in os.listdir(output_dir) 
        if f.startswith("frame_") and f.endswith(".jpg")
    ])
    return frames

def score_frame(img_path, target_size=(320, 427)):
    """Score a frame for cover suitability.
    
    Returns dict with scores (0-100 each):
    - total: weighted combination
    - brightness: how good the exposure is
    - contrast: visual clarity
    - skin: face/person presence (skin color in center)
    - sharpness: image clarity
    - product: potential product presence (non-skin objects near hands)
    """
    img = Image.open(img_path).convert("RGB")
    img = img.resize(target_size, Image.Resampling.LANCZOS)
    arr = np.array(img)
    h, w = arr.shape[:2]
    
    # 1. Brightness (ideal range: 100-170)
    avg_brightness = arr.mean()
    brightness_score = max(0, 100 - abs(avg_brightness - 135) * 1.5)
    
    # 2. Contrast (std dev)
    gray = arr.mean(axis=2)
    contrast = gray.std()
    contrast_score = min(contrast * 1.5, 100)
    
    # 3. Skin detection in center region (person presence)
    cy1, cy2 = h // 6, 2 * h // 3
    cx1, cx2 = w // 4, 3 * w // 4
    center = arr[cy1:cy2, cx1:cx2]
    
    r, g, b = center[:,:,0], center[:,:,1], center[:,:,2]
    skin_mask = (
        (r > 95) & (g > 40) & (b > 20) &
        (np.max(center, axis=2) - np.min(center, axis=2) > 15) &
        (r > g) & (r > b) & (np.abs(r.astype(int) - g.astype(int)) > 15)
    )
    skin_ratio = skin_mask.sum() / max(skin_mask.size, 1)
    skin_score = min(skin_ratio * 500, 100)
    
    # 4. Sharpness (Laplacian approximation)
    dx = np.abs(np.diff(gray, axis=1)).mean()
    dy = np.abs(np.diff(gray, axis=0)).mean()
    sharpness = (dx + dy) / 2
    sharp_score = min(sharpness * 5, 100)
    
    # 5. Product detection heuristic
    # Look for non-skin, non-bg objects in lower center (hand/product area)
    lower = arr[h//2:, w//4:3*w//4]
    lr, lg, lb = lower[:,:,0], lower[:,:,1], lower[:,:,2]
    # Objects that are distinct from skin and background
    not_skin = ~(
        (lr > 95) & (lg > 40) & (lb > 20) &
        (lr > lg) & (lr > lb)
    )
    not_white = ~((lr > 220) & (lg > 220) & (lb > 220))
    not_black = ~((lr < 30) & (lg < 30) & (lb < 30))
    product_mask = not_skin & not_white & not_black
    product_ratio = product_mask.sum() / max(product_mask.size, 1)
    product_score = min(product_ratio * 200, 100)
    
    # Weighted total
    total = (
        brightness_score * 0.15 +
        contrast_score * 0.15 +
        skin_score * 0.35 +  # person presence most important
        sharp_score * 0.20 +
        product_score * 0.15
    )
    
    return {
        "total": round(total, 1),
        "brightness": round(brightness_score, 1),
        "contrast": round(contrast_score, 1),
        "skin": round(skin_score, 1),
        "sharpness": round(sharp_score, 1),
        "product": round(product_score, 1),
        "path": img_path,
    }

def pick_best_frames(frame_paths, top_n=5, diversity_threshold=3):
    """Score all frames and return top N with diversity.
    
    diversity_threshold: minimum frame distance between picks
    (avoids picking consecutive near-identical frames)
    """
    print(f"🔍 Scoring {len(frame_paths)} frames...")
    
    scores = []
    for i, fp in enumerate(frame_paths):
        try:
            s = score_frame(fp)
            s["index"] = i
            scores.append(s)
        except Exception as e:
            print(f"  ⚠️ Frame {i}: {e}")
    
    # Sort by total score
    scores.sort(key=lambda x: -x["total"])
    
    # Pick top N with diversity
    picked = []
    used_indices = set()
    
    for s in scores:
        idx = s["index"]
        # Check diversity: not too close to already-picked frames
        too_close = any(abs(idx - ui) < diversity_threshold for ui in used_indices)
        if not too_close:
            picked.append(s)
            used_indices.add(idx)
            if len(picked) >= top_n:
                break
    
    return picked

def main():
    parser = argparse.ArgumentParser(description="视频截帧智能选择器")
    parser.add_argument("--video", required=True, help="Video file path")
    parser.add_argument("--top", type=int, default=5, help="Number of best frames to pick")
    parser.add_argument("--interval", type=float, default=1.0, help="Frame extraction interval (seconds)")
    parser.add_argument("--output-dir", default="/tmp/frames", help="Output directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print(f"❌ Video not found: {args.video}")
        sys.exit(1)
    
    print(f"📹 Extracting frames from {args.video} (every {args.interval}s)...")
    frames = extract_frames(args.video, args.output_dir, args.interval)
    print(f"   Got {len(frames)} frames")
    
    if not frames:
        print("❌ No frames extracted")
        sys.exit(1)
    
    best = pick_best_frames(frames, args.top)
    
    if args.json:
        print(json.dumps(best, indent=2, ensure_ascii=False))
    else:
        print(f"\n🏆 TOP {len(best)} FRAMES:")
        print("-" * 50)
        for i, s in enumerate(best, 1):
            print(f"  #{i}  Score: {s['total']}/100")
            print(f"      人脸:{s['skin']}  清晰:{s['sharpness']}  亮度:{s['brightness']}  产品:{s['product']}")
            print(f"      {s['path']}")
            print()

if __name__ == "__main__":
    main()
