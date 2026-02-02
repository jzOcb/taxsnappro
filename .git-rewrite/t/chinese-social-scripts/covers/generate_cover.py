exec(open('/tmp/sandbox_bootstrap.py').read())

"""
RedNote Cover Image Generator — Parameterized CLI Tool
Usage:
  python3 generate_cover.py --title "标题" --subtitle "副标题" --style elegant
  python3 generate_cover.py --title "好物推荐" --tags "护肤,美妆" --style fresh
"""

import argparse
import math
import os
import random
import base64
from PIL import Image, ImageDraw, ImageFont

# --- Constants ---
W, H = 1242, 1660  # RedNote 3:4

# --- Font helpers ---
def font_bold(size):
    return ImageFont.truetype("/tmp/fonts/NotoSansSC-Bold.otf", size)

def font_reg(size):
    return ImageFont.truetype("/tmp/fonts/NotoSansSC-Regular.otf", size)

# --- Style presets ---
STYLES = {
    "elegant": {
        "name": "elegant",
        "gradient": [(253, 240, 240), (255, 248, 240), (255, 245, 230)],
        "title_color": (61, 43, 31),
        "subtitle_color": (183, 110, 121),
        "accent": (212, 175, 55),
        "accent_alpha": 150,
        "tag_bg1": (255, 235, 230, 180),
        "tag_color1": (183, 110, 121),
        "tag_bg2": (255, 245, 230, 180),
        "tag_color2": (160, 120, 50),
        "text_secondary": (140, 100, 80),
        "border_color": (212, 175, 55, 50),
    },
    "fresh": {
        "name": "fresh",
        "gradient": [(235, 250, 240), (240, 252, 245), (245, 255, 248)],
        "title_color": (30, 80, 50),
        "subtitle_color": (60, 140, 90),
        "accent": (60, 180, 100),
        "accent_alpha": 130,
        "tag_bg1": (220, 245, 230, 180),
        "tag_color1": (40, 120, 70),
        "tag_bg2": (230, 250, 240, 180),
        "tag_color2": (50, 100, 60),
        "text_secondary": (60, 100, 70),
        "border_color": (60, 180, 100, 50),
    },
    "bold": {
        "name": "bold",
        "gradient": [(40, 40, 45), (30, 30, 35), (25, 25, 30)],
        "title_color": (255, 255, 255),
        "subtitle_color": (255, 80, 80),
        "accent": (255, 60, 60),
        "accent_alpha": 160,
        "tag_bg1": (255, 60, 60, 200),
        "tag_color1": (255, 255, 255),
        "tag_bg2": (80, 80, 90, 200),
        "tag_color2": (255, 255, 255),
        "text_secondary": (200, 200, 210),
        "border_color": (255, 60, 60, 60),
    },
    "minimal": {
        "name": "minimal",
        "gradient": [(250, 250, 250), (245, 245, 245), (240, 240, 240)],
        "title_color": (40, 40, 40),
        "subtitle_color": (120, 120, 120),
        "accent": (100, 100, 100),
        "accent_alpha": 100,
        "tag_bg1": (230, 230, 230, 180),
        "tag_color1": (60, 60, 60),
        "tag_bg2": (220, 220, 220, 180),
        "tag_color2": (80, 80, 80),
        "text_secondary": (120, 120, 120),
        "border_color": (180, 180, 180, 50),
    },
    "luxury": {
        "name": "luxury",
        "gradient": [(30, 25, 20), (25, 20, 18), (20, 18, 15)],
        "title_color": (212, 175, 55),
        "subtitle_color": (180, 150, 80),
        "accent": (212, 175, 55),
        "accent_alpha": 180,
        "tag_bg1": (212, 175, 55, 200),
        "tag_color1": (30, 25, 20),
        "tag_bg2": (60, 50, 35, 200),
        "tag_color2": (212, 175, 55),
        "text_secondary": (160, 140, 100),
        "border_color": (212, 175, 55, 60),
    },
}

# --- Drawing helpers ---
def draw_gradient(img, colors):
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        if t < 0.5:
            t2 = t / 0.5
            idx = 0
        else:
            t2 = (t - 0.5) / 0.5
            idx = 1
        r = int(colors[idx][0] + (colors[idx+1][0] - colors[idx][0]) * t2)
        g = int(colors[idx][1] + (colors[idx+1][1] - colors[idx][1]) * t2)
        b = int(colors[idx][2] + (colors[idx+1][2] - colors[idx][2]) * t2)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

def draw_sparkle(draw, cx, cy, size, color):
    draw.line([(cx, cy - size), (cx, cy + size)], fill=color, width=2)
    draw.line([(cx - size, cy), (cx + size, cy)], fill=color, width=2)
    s2 = int(size * 0.6)
    draw.line([(cx - s2, cy - s2), (cx + s2, cy + s2)], fill=color, width=1)
    draw.line([(cx + s2, cy - s2), (cx - s2, cy + s2)], fill=color, width=1)

def draw_diamond(draw, cx, cy, size, color):
    draw.polygon([(cx, cy-size), (cx+size, cy), (cx, cy+size), (cx-size, cy)], fill=color)

def draw_text_centered(draw, y, text, font, fill):
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    return x, tw

def wrap_text(text, font, max_width):
    """Wrap Chinese text to fit within max_width"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines

def generate_cover(title, subtitle=None, style_name="elegant", tags=None,
                   persona=None, watermark=None, product_images=None, output=None):
    """Generate a RedNote cover image"""
    
    style = STYLES.get(style_name, STYLES["elegant"])
    accent = style["accent"]
    accent_a = (*accent, style["accent_alpha"])
    
    # Create canvas
    img = Image.new("RGBA", (W, H))
    draw_gradient(img, style["gradient"])
    draw = ImageDraw.Draw(img)
    
    # --- Top sparkles ---
    random.seed(hash(title) % 10000)
    for _ in range(10):
        sx = random.randint(80, W - 80)
        sy = random.randint(30, 180)
        ss = random.randint(8, 22)
        draw_sparkle(draw, sx, sy, ss, (*accent, random.randint(80, 180)))
    
    # Scattered dots
    for _ in range(25):
        dx = random.randint(50, W - 50)
        dy = random.randint(20, 220)
        ds = random.randint(2, 5)
        draw.ellipse([dx-ds, dy-ds, dx+ds, dy+ds], fill=(*accent, random.randint(30, 80)))
    
    # --- Decorative arcs ---
    for i in range(3):
        draw.arc([100+i*2, -200+i*2, W-100-i*2, 250-i*2], 0, 180,
                 fill=(*accent, 40 - i*12), width=2)
    
    # --- Side diamonds ---
    for i in range(5):
        alpha = 90 - i * 15
        draw_diamond(draw, 65, 300 + i * 80, 6, (*style["subtitle_color"], max(alpha, 20)))
        draw_diamond(draw, W - 65, 320 + i * 80, 6, (*style["subtitle_color"], max(alpha, 20)))
    
    # --- Title ---
    # Auto-wrap title if too long
    title_size = 105 if len(title) <= 8 else 85 if len(title) <= 12 else 70
    title_font = font_bold(title_size)
    max_title_w = W - 200
    title_lines = wrap_text(title, title_font, max_title_w)
    
    title_y_start = 260 if len(title_lines) == 1 else 230
    for i, line in enumerate(title_lines[:3]):
        bbox = title_font.getbbox(line)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        # Shadow
        draw.text((x + 4, title_y_start + i * (title_size + 15) + 4), line,
                  font=title_font, fill=(*style["title_color"][:3], 30))
        draw.text((x, title_y_start + i * (title_size + 15)), line,
                  font=title_font, fill=style["title_color"])
    
    title_bottom = title_y_start + len(title_lines) * (title_size + 15) + 20
    
    # --- Subtitle ---
    if subtitle:
        sub_size = 58 if len(subtitle) <= 12 else 46
        sub_font = font_bold(sub_size)
        sub_lines = wrap_text(subtitle, sub_font, W - 200)
        for i, line in enumerate(sub_lines[:2]):
            bbox = sub_font.getbbox(line)
            tw = bbox[2] - bbox[0]
            x = (W - tw) // 2
            draw.text((x + 2, title_bottom + i * (sub_size + 10) + 2), line,
                      font=sub_font, fill=(*style["subtitle_color"][:3], 30))
            draw.text((x, title_bottom + i * (sub_size + 10)), line,
                      font=sub_font, fill=style["subtitle_color"])
        title_bottom += len(sub_lines) * (sub_size + 10) + 30
    else:
        title_bottom += 20
    
    # --- Divider ---
    div_y = title_bottom + 20
    line_color = (*accent, 100)
    draw.line([(200, div_y), (520, div_y)], fill=line_color, width=2)
    draw.line([(722, div_y), (W - 200, div_y)], fill=line_color, width=2)
    draw_diamond(draw, W // 2, div_y, 10, (*accent, 160))
    draw_diamond(draw, 190, div_y, 5, (*accent, 100))
    draw_diamond(draw, W - 190, div_y, 5, (*accent, 100))
    
    # --- Product images area ---
    content_y = div_y + 60
    
    if product_images:
        # Composite product images in a row
        img_area_h = 350
        n = len(product_images)
        img_w = min(300, (W - 200) // n - 20)
        
        for i, img_path in enumerate(product_images[:4]):
            try:
                prod = Image.open(img_path).convert("RGBA")
                prod.thumbnail((img_w, img_area_h - 40))
                pw, ph = prod.size
                x = (W - (n * (img_w + 20) - 20)) // 2 + i * (img_w + 20)
                y = content_y + (img_area_h - ph) // 2
                
                # Drop shadow
                shadow = Image.new("RGBA", (pw + 10, ph + 10), (0, 0, 0, 0))
                sd = ImageDraw.Draw(shadow)
                sd.rounded_rectangle([5, 5, pw + 5, ph + 5], radius=10,
                                    fill=(*style["title_color"][:3], 30))
                img.paste(shadow, (x - 3, y + 3), shadow)
                img.paste(prod, (x, y), prod)
            except Exception as e:
                pass
        
        content_y += img_area_h + 20
    else:
        # Decorative element instead of product images
        box_cx, box_cy = W // 2, content_y + 120
        box_w, box_h = 180, 140
        lid_h = 40
        
        # Gift box
        draw.rounded_rectangle(
            [box_cx - box_w//2 + 5, box_cy - box_h//2 + lid_h + 5,
             box_cx + box_w//2 + 5, box_cy + box_h//2 + 5],
            radius=10, fill=(*style["title_color"][:3], 20))
        draw.rounded_rectangle(
            [box_cx - box_w//2, box_cy - box_h//2 + lid_h,
             box_cx + box_w//2, box_cy + box_h//2],
            radius=10, fill=(*style["gradient"][0], 220),
            outline=style["subtitle_color"], width=3)
        draw.rounded_rectangle(
            [box_cx - box_w//2 - 8, box_cy - box_h//2,
             box_cx + box_w//2 + 8, box_cy - box_h//2 + lid_h],
            radius=8, fill=(*style["gradient"][0], 240),
            outline=style["subtitle_color"], width=3)
        # Ribbon
        draw.line([(box_cx, box_cy - box_h//2), (box_cx, box_cy + box_h//2)],
                  fill=accent, width=4)
        draw.line([(box_cx - box_w//2, box_cy + 10), (box_cx + box_w//2, box_cy + 10)],
                  fill=accent, width=4)
        # Bow
        bow_y = box_cy - box_h//2 - 5
        draw.ellipse([box_cx - 35, bow_y - 22, box_cx - 5, bow_y + 8], outline=accent, width=3)
        draw.ellipse([box_cx + 5, bow_y - 22, box_cx + 35, bow_y + 8], outline=accent, width=3)
        draw.ellipse([box_cx - 7, bow_y - 7, box_cx + 7, bow_y + 7], fill=accent)
        
        # Sparkles around box
        for dx, dy, ds in [(-130, -40, 14), (135, -30, 12), (-110, 50, 10), (120, 55, 11)]:
            draw_sparkle(draw, box_cx + dx, box_cy + dy, ds, (*accent, 120))
        
        content_y += 300
    
    # --- Tags ---
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            tag_y = content_y + 20
            tag_font = font_bold(32)
            tag_px = 24
            tag_gap = 16
            
            # Calculate total width
            tag_widths = []
            for t in tag_list:
                bbox = tag_font.getbbox(t)
                tag_widths.append(bbox[2] - bbox[0])
            total = sum(tw + tag_px * 2 for tw in tag_widths) + tag_gap * (len(tag_list) - 1)
            sx = (W - total) // 2
            
            for i, (tag, tw) in enumerate(zip(tag_list, tag_widths)):
                pw = tw + tag_px * 2
                ph = 50
                bg = style["tag_bg1"] if i % 2 == 0 else style["tag_bg2"]
                tc = style["tag_color1"] if i % 2 == 0 else style["tag_color2"]
                
                draw.rounded_rectangle([sx, tag_y, sx + pw, tag_y + ph],
                                      radius=ph // 2, fill=bg)
                draw.rounded_rectangle([sx, tag_y, sx + pw, tag_y + ph],
                                      radius=ph // 2, outline=(*tc, 60), width=1)
                
                bbox = tag_font.getbbox(tag)
                th = bbox[3] - bbox[1]
                draw.text((sx + tag_px, tag_y + (ph - th) // 2 - 2), tag,
                         font=tag_font, fill=tc)
                sx += pw + tag_gap
            
            content_y = tag_y + 80
    
    # --- Persona line ---
    if persona:
        p_font = font_reg(30)
        bbox = p_font.getbbox(persona)
        tw = bbox[2] - bbox[0]
        py = max(content_y + 40, 1380)
        draw.text(((W - tw) // 2, py), persona, font=p_font,
                  fill=(*style["text_secondary"], 160))
    
    # --- Watermark ---
    if watermark:
        wm_font = font_reg(26)
        bbox = wm_font.getbbox(watermark)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, 1560), watermark, font=wm_font,
                  fill=(*style["text_secondary"], 80))
    
    # --- Bottom sparkles ---
    for sx, sy, ss in [(150, 1520, 10), (400, 1550, 8), (621, 1530, 12),
                        (850, 1545, 9), (1080, 1515, 11)]:
        draw_sparkle(draw, sx, sy, ss, (*accent, 70))
    
    # --- Border frame ---
    m = 40
    draw.rounded_rectangle([m, m, W - m, H - m], radius=30,
                          outline=style["border_color"], width=2)
    for cx, cy in [(m+10, m+10), (W-m-10, m+10), (m+10, H-m-10), (W-m-10, H-m-10)]:
        draw_diamond(draw, cx, cy, 8, (*accent, 80))
    
    # --- Flatten and save ---
    final = Image.new("RGB", (W, H), style["gradient"][0])
    final.paste(img, mask=img.split()[3])
    
    if not output:
        safe_title = title.replace(" ", "_")[:20]
        output = f"/tmp/{safe_title}-cover.png"
    
    final.save(output, "PNG", quality=95)
    
    # Base64 for transfer
    with open(output, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    with open("/tmp/cover_b64.txt", 'w') as f:
        f.write(b64)
    
    return output, final.size, len(b64)

def main():
    parser = argparse.ArgumentParser(description="RedNote Cover Image Generator")
    parser.add_argument("--title", required=True, help="Main title (Chinese)")
    parser.add_argument("--subtitle", help="Subtitle/tagline")
    parser.add_argument("--style", default="elegant",
                       choices=list(STYLES.keys()),
                       help="Color scheme preset")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--persona", default="北美全职码农小经理",
                       help="Persona text line")
    parser.add_argument("--watermark", help="Small watermark text")
    parser.add_argument("--product-images", help="Comma-separated image paths")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    prod_imgs = None
    if args.product_images:
        prod_imgs = [p.strip() for p in args.product_images.split(",")]
    
    path, size, b64len = generate_cover(
        title=args.title,
        subtitle=args.subtitle,
        style_name=args.style,
        tags=args.tags,
        persona=args.persona,
        watermark=args.watermark,
        product_images=prod_imgs,
        output=args.output,
    )
    
    print(f"✅ Cover saved: {path}")
    print(f"   Size: {size[0]}x{size[1]}")
    print(f"   Base64: {b64len} chars → /tmp/cover_b64.txt")

if __name__ == "__main__":
    main()
