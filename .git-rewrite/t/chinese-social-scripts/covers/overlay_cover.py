exec(open('/tmp/sandbox_bootstrap.py').read())

"""
小红书封面文字叠加工具
输入照片/截帧 → 加大字标题+描边 → 输出封面

基于实际分析：焦言蛋白 Johanne + 柯基吃烤鱼 + 洪成成_橙橙子
"""

import argparse
import os
import base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1242, 1660

def font_bold(size):
    return ImageFont.truetype("/tmp/fonts/NotoSansSC-Bold.otf", size)

def font_reg(size):
    return ImageFont.truetype("/tmp/fonts/NotoSansSC-Regular.otf", size)

# --- Color presets (高级感配色) ---
COLOR_PRESETS = {
    "white":   {"fill": (255, 255, 255), "stroke": (20, 20, 20)},
    "cream":   {"fill": (255, 245, 230), "stroke": (40, 30, 20)},
    "red":     {"fill": (230, 55, 55),   "stroke": (30, 0, 0)},
    "coral":   {"fill": (235, 100, 80),  "stroke": (50, 15, 10)},
    "orange":  {"fill": (245, 160, 50),  "stroke": (60, 30, 0)},
    "gold":    {"fill": (220, 185, 75),  "stroke": (50, 35, 0)},
    "green":   {"fill": (80, 160, 100),  "stroke": (10, 40, 15)},
    "sage":    {"fill": (140, 170, 130), "stroke": (25, 40, 20)},
    "blue":    {"fill": (80, 140, 210),  "stroke": (10, 25, 55)},
    "purple":  {"fill": (160, 100, 180), "stroke": (35, 15, 45)},
    "pink":    {"fill": (235, 130, 155), "stroke": (55, 20, 30)},
    "brown":   {"fill": (140, 95, 65),   "stroke": (30, 15, 5)},
    "black":   {"fill": (30, 30, 30),    "stroke": (200, 200, 200)},
}

def draw_text_stroke(draw, x, y, text, font, fill, stroke_color, stroke_width):
    """Draw text with thick stroke outline for readability"""
    # Draw stroke by offsetting in all directions
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx * dx + dy * dy <= stroke_width * stroke_width:
                draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
    # Draw main text on top
    draw.text((x, y), text, font=font, fill=fill)

def draw_text_shadow(draw, x, y, text, font, fill, shadow_offset=4, shadow_color=(0,0,0,120)):
    """Draw text with drop shadow"""
    # Shadow layer (need RGBA image for alpha)
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color[:3])
    draw.text((x, y), text, font=font, fill=fill)

def auto_font_size(text, max_width, max_size=140, min_size=60):
    """Find the largest font size that fits within max_width"""
    for size in range(max_size, min_size - 1, -4):
        f = font_bold(size)
        bbox = f.getbbox(text)
        tw = bbox[2] - bbox[0]
        if tw <= max_width:
            return size, tw
    return min_size, max_width

def generate_overlay(photo_path, title, subtitle=None, tags=None,
                     title_color="white", subtitle_color=None,
                     position="bottom-left", output=None):
    """
    Generate cover by overlaying text on a photo.
    
    Args:
        photo_path: path to background photo/video frame
        title: main title text (≤8 chars ideal)
        subtitle: optional subtitle
        tags: comma-separated hashtag labels
        title_color: color preset name or hex
        subtitle_color: color preset (defaults to title_color)
        position: text position (bottom-left, bottom-center, center, top-left)
        output: output file path
    """
    
    # Load and resize photo to cover dimensions
    photo = Image.open(photo_path).convert("RGB")
    
    # Smart crop to 3:4 ratio
    pw, ph = photo.size
    target_ratio = W / H
    current_ratio = pw / ph
    
    if current_ratio > target_ratio:
        # Too wide, crop sides
        new_w = int(ph * target_ratio)
        left = (pw - new_w) // 2
        photo = photo.crop((left, 0, left + new_w, ph))
    else:
        # Too tall, crop top/bottom (keep upper portion for faces)
        new_h = int(pw / target_ratio)
        photo = photo.crop((0, 0, pw, new_h))
    
    photo = photo.resize((W, H), Image.Resampling.LANCZOS)
    
    # Create overlay layer
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Optional: slight gradient at bottom for text readability
    if position.startswith("bottom"):
        for y in range(H - 600, H):
            alpha = int(((y - (H - 600)) / 600) * 100)
            draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    
    # Get colors
    tc = COLOR_PRESETS.get(title_color, COLOR_PRESETS["white"])
    sc = COLOR_PRESETS.get(subtitle_color or title_color, tc)
    
    # --- Position calculations ---
    margin = 60
    max_text_w = W - margin * 2
    
    if position == "bottom-left":
        base_x = margin
        base_y = H - 350
        align = "left"
    elif position == "bottom-center":
        base_x = W // 2
        base_y = H - 350
        align = "center"
    elif position == "center":
        base_x = W // 2
        base_y = H // 2 - 100
        align = "center"
    elif position == "top-left":
        base_x = margin
        base_y = 120
        align = "left"
    else:
        base_x = margin
        base_y = H - 350
        align = "left"
    
    # --- Draw title ---
    # Split into lines if needed (manual line break with \n)
    title_lines = title.split("\\n") if "\\n" in title else [title]
    
    y_cursor = base_y
    for line in title_lines:
        size, tw = auto_font_size(line, max_text_w, max_size=150, min_size=65)
        title_font = font_bold(size)
        stroke_w = max(4, size // 22)
        
        if align == "center":
            tx = (W - tw) // 2
        elif align == "left":
            tx = base_x
        else:
            tx = base_x
        
        draw_text_stroke(draw, tx, y_cursor, line, title_font,
                        tc["fill"], tc["stroke"], stroke_w)
        
        bbox = title_font.getbbox(line)
        line_h = bbox[3] - bbox[1]
        y_cursor += line_h + 15
    
    # --- Draw subtitle ---
    if subtitle:
        sub_lines = subtitle.split("\\n") if "\\n" in subtitle else [subtitle]
        y_cursor += 10
        for line in sub_lines:
            sub_size, sub_tw = auto_font_size(line, max_text_w, max_size=70, min_size=36)
            sub_font = font_bold(sub_size)
            sub_stroke = max(3, sub_size // 25)
            
            if align == "center":
                sx = (W - sub_tw) // 2
            else:
                sx = base_x
            
            draw_text_stroke(draw, sx, y_cursor, line, sub_font,
                            sc["fill"], sc["stroke"], sub_stroke)
            
            bbox = sub_font.getbbox(line)
            y_cursor += (bbox[3] - bbox[1]) + 10
    
    # --- Draw tags ---
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        tag_font = font_bold(32)
        tag_h = 44
        tag_px = 18
        tag_gap = 12
        
        # Position tags at top-right or below title
        tag_y = min(y_cursor + 25, H - 100)
        tag_x = base_x if align == "left" else margin
        
        for tag in tag_list:
            text = f"#{tag}" if not tag.startswith("#") else tag
            bbox = tag_font.getbbox(text)
            tw = bbox[2] - bbox[0]
            
            if tag_x + tw + tag_px * 2 > W - margin:
                tag_x = base_x if align == "left" else margin
                tag_y += tag_h + tag_gap
            
            # Tag background (semi-transparent)
            draw.rounded_rectangle(
                [tag_x, tag_y, tag_x + tw + tag_px * 2, tag_y + tag_h],
                radius=tag_h // 2,
                fill=(0, 0, 0, 100))
            draw.text((tag_x + tag_px, tag_y + 4), text,
                     font=tag_font, fill=(255, 255, 255, 230))
            
            tag_x += tw + tag_px * 2 + tag_gap
    
    # --- Composite ---
    photo_rgba = photo.convert("RGBA")
    result = Image.alpha_composite(photo_rgba, overlay)
    final = result.convert("RGB")
    
    # Save
    if not output:
        safe = title.replace("\\n", "").replace(" ", "")[:15]
        output = f"/tmp/{safe}-cover.png"
    
    final.save(output, "PNG", quality=95)
    
    # Base64
    with open(output, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    with open("/tmp/cover_b64.txt", 'w') as f:
        f.write(b64)
    
    return output, final.size, len(b64)


def main():
    parser = argparse.ArgumentParser(description="小红书封面文字叠加工具")
    parser.add_argument("--photo", required=True, help="Background photo path")
    parser.add_argument("--title", required=True, help="Main title (use \\n for line break)")
    parser.add_argument("--subtitle", help="Subtitle text")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--title-color", default="white", 
                       choices=list(COLOR_PRESETS.keys()),
                       help="Title color preset")
    parser.add_argument("--subtitle-color", help="Subtitle color (default: same as title)")
    parser.add_argument("--position", default="bottom-left",
                       choices=["bottom-left", "bottom-center", "center", "top-left"],
                       help="Text position")
    parser.add_argument("--output", help="Output path")
    
    args = parser.parse_args()
    
    path, size, b64len = generate_overlay(
        photo_path=args.photo,
        title=args.title,
        subtitle=args.subtitle,
        tags=args.tags,
        title_color=args.title_color,
        subtitle_color=args.subtitle_color,
        position=args.position,
        output=args.output,
    )
    
    print(f"✅ Cover: {path}")
    print(f"   Size: {size[0]}x{size[1]}")
    print(f"   Base64: {b64len} chars")

if __name__ == "__main__":
    main()
