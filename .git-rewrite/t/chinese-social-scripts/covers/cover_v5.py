#!/usr/bin/env python3
"""
XHS Cover Generator V5 — Data-driven, based on analysis of 70+ real XHS covers.

Key findings applied:
- 3:4 portrait (1080x1440) — 72% of top covers use this
- Warm color palette (74% warm tones)
- Bold text with thick stroke for readability
- Text placement: top or bottom 20% (not center)
- High contrast between text and background

Modes:
1. text_overlay — Bold text on photo (most common)
2. split_layout — Top text + bottom photo (popular for tutorials)
3. collage — Magazine-style multi-image (Jason's preference)
"""

import sys, os
sys.path.insert(0, '/tmp/pip_packages')

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import json, math, random

# Standard XHS dimensions
XHS_WIDTH = 1080
XHS_HEIGHT = 1440

# Font paths
FONTS = {
    'bold': '/tmp/pip_packages/PIL/fonts/NotoSansSC-Bold.otf',
    'smiley': None,  # Will check
}

# Check available fonts
for name, path in list(FONTS.items()):
    if path and not os.path.exists(path):
        FONTS[name] = None

# Find any available Chinese font
FONT_SEARCH_PATHS = [
    '/tmp/pip_packages/PIL/fonts/',
    '/usr/share/fonts/',
    '/tmp/fonts/',
]

def find_font(size=72, bold=True):
    """Find best available Chinese font."""
    candidates = [
        'NotoSansSC-Bold.otf',
        'NotoSansSC-Regular.otf', 
        'SmileySans-Oblique.otf',
        'SmileySans-Oblique.ttf',
    ]
    for search_dir in FONT_SEARCH_PATHS:
        if not os.path.isdir(search_dir):
            continue
        for root, dirs, files in os.walk(search_dir):
            for c in candidates:
                if c in files:
                    return ImageFont.truetype(os.path.join(root, c), size)
    # Fallback
    return ImageFont.load_default()


def draw_text_with_stroke(draw, xy, text, font, fill=(255,255,255), stroke_fill=(0,0,0), stroke_width=4):
    """Draw text with thick outline for readability."""
    x, y = xy
    # Draw stroke
    for dx in range(-stroke_width, stroke_width+1):
        for dy in range(-stroke_width, stroke_width+1):
            if dx*dx + dy*dy <= stroke_width*stroke_width:
                draw.text((x+dx, y+dy), text, font=font, fill=stroke_fill)
    # Draw fill
    draw.text((x, y), text, font=font, fill=fill)


def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width."""
    lines = []
    current_line = ""
    for char in text:
        test = current_line + char
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current_line:
                lines.append(current_line)
            current_line = char
        else:
            current_line = test
    if current_line:
        lines.append(current_line)
    return lines


def text_overlay_cover(photo_path, title, subtitle="", tags=None, 
                       text_position="bottom", color_scheme="warm",
                       output_path=None):
    """
    Mode 1: Bold text overlay on photo.
    Most common XHS cover style.
    """
    # Load and resize photo to 3:4
    img = Image.open(photo_path).convert('RGB')
    img = resize_and_crop(img, XHS_WIDTH, XHS_HEIGHT)
    
    # Enhance photo slightly
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = ImageEnhance.Color(img).enhance(1.15)
    
    draw = ImageDraw.Draw(img)
    
    # Color schemes
    schemes = {
        'warm': {'text': (255, 255, 255), 'stroke': (180, 60, 30), 'accent': (255, 200, 50)},
        'cool': {'text': (255, 255, 255), 'stroke': (30, 60, 120), 'accent': (100, 200, 255)},
        'dark': {'text': (255, 255, 255), 'stroke': (0, 0, 0), 'accent': (255, 215, 0)},
        'pink': {'text': (255, 255, 255), 'stroke': (180, 50, 100), 'accent': (255, 150, 180)},
        'green': {'text': (255, 255, 255), 'stroke': (30, 100, 60), 'accent': (150, 230, 150)},
    }
    colors = schemes.get(color_scheme, schemes['warm'])
    
    # Title font
    title_size = 82 if len(title) < 10 else 68 if len(title) < 15 else 56
    title_font = find_font(title_size)
    
    # Wrap title
    max_text_width = XHS_WIDTH - 120
    lines = wrap_text(title, title_font, max_text_width, draw)
    
    # Calculate text block height
    line_height = title_size + 12
    total_text_height = len(lines) * line_height
    
    # Position
    if text_position == "bottom":
        # Dark gradient at bottom
        gradient = Image.new('RGBA', (XHS_WIDTH, 400), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(gradient)
        for y in range(400):
            alpha = int(200 * (y / 400) ** 1.5)
            gdraw.rectangle([(0, y), (XHS_WIDTH, y+1)], fill=(0, 0, 0, alpha))
        img.paste(Image.alpha_composite(Image.new('RGBA', gradient.size, (0,0,0,0)), gradient).convert('RGB'),
                  (0, XHS_HEIGHT - 400), gradient)
        
        text_y = XHS_HEIGHT - total_text_height - 100
    else:
        # Dark gradient at top
        gradient = Image.new('RGBA', (XHS_WIDTH, 350), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(gradient)
        for y in range(350):
            alpha = int(180 * (1 - y / 350) ** 1.5)
            gdraw.rectangle([(0, y), (XHS_WIDTH, y+1)], fill=(0, 0, 0, alpha))
        img.paste(Image.alpha_composite(Image.new('RGBA', gradient.size, (0,0,0,0)), gradient).convert('RGB'),
                  (0, 0), gradient)
        
        text_y = 60
    
    # Draw title
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        text_w = bbox[2] - bbox[0]
        x = 60  # Left-aligned (XHS style)
        y = text_y + i * line_height
        draw_text_with_stroke(draw, (x, y), line, title_font,
                            fill=colors['text'], stroke_fill=colors['stroke'], stroke_width=5)
    
    # Tags
    if tags:
        tag_font = find_font(32)
        tag_y = text_y + total_text_height + 20
        tag_x = 60
        for tag in tags[:3]:
            tag_text = f"#{tag}"
            bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
            tw = bbox[2] - bbox[0]
            # Tag background
            draw.rounded_rectangle(
                [(tag_x-8, tag_y-4), (tag_x+tw+8, tag_y+36)],
                radius=6, fill=(*colors['accent'], 180)
            )
            draw.text((tag_x, tag_y), tag_text, font=tag_font, fill=colors['stroke'])
            tag_x += tw + 24
    
    if output_path:
        img.save(output_path, quality=95)
    return img


def split_cover(photo_path, title, subtitle="", tags=None,
                bg_color=(255, 240, 230), output_path=None):
    """
    Mode 2: Top text section + bottom photo.
    Popular for tutorials, reviews, comparisons.
    """
    img = Image.new('RGB', (XHS_WIDTH, XHS_HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Text section (top 35%)
    text_height = int(XHS_HEIGHT * 0.35)
    
    # Title
    title_size = 76 if len(title) < 12 else 60
    title_font = find_font(title_size)
    lines = wrap_text(title, title_font, XHS_WIDTH - 120, draw)
    
    line_h = title_size + 16
    total_h = len(lines) * line_h
    start_y = (text_height - total_h) // 2
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        tw = bbox[2] - bbox[0]
        x = (XHS_WIDTH - tw) // 2  # Centered
        y = start_y + i * line_h
        draw_text_with_stroke(draw, (x, y), line, title_font,
                            fill=(60, 30, 10), stroke_fill=bg_color, stroke_width=0)
    
    # Decorative line
    draw.line([(60, text_height - 20), (XHS_WIDTH - 60, text_height - 20)], 
              fill=(200, 180, 160), width=2)
    
    # Photo section (bottom 65%)
    photo = Image.open(photo_path).convert('RGB')
    photo_area_h = XHS_HEIGHT - text_height
    photo = resize_and_crop(photo, XHS_WIDTH, photo_area_h)
    img.paste(photo, (0, text_height))
    
    # Tags at bottom
    if tags:
        draw = ImageDraw.Draw(img)
        tag_font = find_font(28)
        tag_y = XHS_HEIGHT - 50
        tag_x = 60
        for tag in tags[:4]:
            draw.text((tag_x, tag_y), f"#{tag}", font=tag_font, fill=(255, 255, 255, 200))
            bbox = draw.textbbox((0, 0), f"#{tag}", font=tag_font)
            tag_x += bbox[2] - bbox[0] + 20
    
    if output_path:
        img.save(output_path, quality=95)
    return img


def collage_cover(photos, title, subtitle="", tags=None,
                  layout="2x1", bg_color=(255, 245, 235), output_path=None):
    """
    Mode 3: Magazine-style collage (Jason's preferred style).
    Multiple photos + floating text + decorative elements.
    """
    img = Image.new('RGB', (XHS_WIDTH, XHS_HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)
    
    if layout == "2x1":
        # Two photos stacked with gap
        gap = 20
        photo_h = (XHS_HEIGHT - 300 - gap) // 2  # Leave 300px for text
        
        for i, photo_path in enumerate(photos[:2]):
            photo = Image.open(photo_path).convert('RGB')
            photo = resize_and_crop(photo, XHS_WIDTH - 80, photo_h)
            # Round corners effect (simple crop)
            y_offset = 40 + i * (photo_h + gap)
            img.paste(photo, (40, y_offset))
    
    elif layout == "side_by_side":
        # Two photos side by side
        photo_w = (XHS_WIDTH - 100) // 2
        photo_h = XHS_HEIGHT - 350
        
        for i, photo_path in enumerate(photos[:2]):
            photo = Image.open(photo_path).convert('RGB')
            photo = resize_and_crop(photo, photo_w, photo_h)
            x_offset = 40 + i * (photo_w + 20)
            img.paste(photo, (x_offset, 40))
    
    # Title at bottom
    title_font = find_font(64)
    draw = ImageDraw.Draw(img)
    lines = wrap_text(title, title_font, XHS_WIDTH - 120, draw)
    
    text_y = XHS_HEIGHT - 250
    for i, line in enumerate(lines):
        x = 60
        y = text_y + i * 76
        draw_text_with_stroke(draw, (x, y), line, title_font,
                            fill=(60, 30, 10), stroke_fill=(255, 200, 100), stroke_width=3)
    
    # Decorative elements
    _add_decorations(draw, XHS_WIDTH, XHS_HEIGHT)
    
    # Tags
    if tags:
        tag_font = find_font(28)
        tag_y = XHS_HEIGHT - 60
        tag_x = 60
        for tag in tags[:3]:
            tag_text = f"✨{tag}"
            draw.text((tag_x, tag_y), tag_text, font=tag_font, fill=(150, 100, 60))
            bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
            tag_x += bbox[2] - bbox[0] + 20
    
    if output_path:
        img.save(output_path, quality=95)
    return img


def _add_decorations(draw, w, h):
    """Add subtle decorative elements (hearts, sparkles, dots)."""
    decorations = ['✦', '♡', '⋆', '◦', '∗']
    for _ in range(8):
        x = random.randint(20, w - 40)
        y = random.randint(20, h - 40)
        size = random.randint(16, 32)
        font = find_font(size)
        dec = random.choice(decorations)
        alpha = random.randint(80, 180)
        draw.text((x, y), dec, font=font, fill=(200, 150, 100, alpha))


def resize_and_crop(img, target_w, target_h):
    """Resize and center-crop to exact dimensions."""
    w, h = img.size
    ratio_w = target_w / w
    ratio_h = target_h / h
    ratio = max(ratio_w, ratio_h)
    
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    
    # Center crop
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def demo(photo_path, output_dir='/tmp/xhs_demo_covers'):
    """Generate demo covers with all modes."""
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    
    # Mode 1: Text overlay variants
    for pos in ['bottom', 'top']:
        for scheme in ['warm', 'dark', 'pink']:
            out = f"{output_dir}/overlay_{pos}_{scheme}.jpg"
            text_overlay_cover(
                photo_path,
                title="油皮亲妈！这瓶精华真的绝了",
                tags=["护肤好物", "油皮精华", "平价护肤"],
                text_position=pos,
                color_scheme=scheme,
                output_path=out
            )
            results.append(out)
    
    # Mode 2: Split layout
    out = f"{output_dir}/split.jpg"
    split_cover(
        photo_path,
        title="换季护肤必看！敏感肌自救指南",
        tags=["敏感肌", "换季护肤", "护肤干货"],
        output_path=out
    )
    results.append(out)
    
    # Mode 3: Collage (needs 2 photos, use same photo twice for demo)
    out = f"{output_dir}/collage.jpg"
    collage_cover(
        [photo_path, photo_path],
        title="一周护肤记录｜皮肤真的变好了",
        tags=["护肤日记", "皮肤管理"],
        output_path=out
    )
    results.append(out)
    
    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('photo', help='Photo path')
    parser.add_argument('--title', '-t', default='测试封面标题')
    parser.add_argument('--mode', '-m', choices=['overlay', 'split', 'collage'], default='overlay')
    parser.add_argument('--output', '-o', default='/tmp/cover_output.jpg')
    parser.add_argument('--demo', action='store_true', help='Generate all demo variants')
    args = parser.parse_args()
    
    if args.demo:
        results = demo(args.photo)
        print(f"Generated {len(results)} demo covers")
        for r in results:
            print(f"  {r}")
    else:
        if args.mode == 'overlay':
            text_overlay_cover(args.photo, args.title, output_path=args.output)
        elif args.mode == 'split':
            split_cover(args.photo, args.title, output_path=args.output)
        elif args.mode == 'collage':
            collage_cover([args.photo], args.title, output_path=args.output)
        print(f"Saved: {args.output}")
