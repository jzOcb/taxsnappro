exec(open('/tmp/sandbox_bootstrap.py').read())

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os

# --- Config ---
W, H = 1242, 1660
output_dir = "chinese-social-scripts/covers"

# Colors
DARK_BROWN = (61, 43, 31)
ROSE_GOLD = (183, 110, 121)
GOLD = (212, 175, 55)
LIGHT_GOLD = (212, 175, 55, 80)
WHITE = (255, 255, 255)
SHADOW = (61, 43, 31, 40)

# Fonts
font_bold = lambda s: ImageFont.truetype("/tmp/fonts/NotoSansSC-Bold.otf", s)
font_reg = lambda s: ImageFont.truetype("/tmp/fonts/NotoSansSC-Regular.otf", s)

# --- Create gradient background ---
img = Image.new("RGBA", (W, H))
draw = ImageDraw.Draw(img)

# Three-stop gradient: soft pink -> cream -> light gold
colors = [
    (253, 240, 240),  # #FDF0F0 soft pink
    (255, 248, 240),  # #FFF8F0 cream
    (255, 245, 230),  # #FFF5E6 light gold
]

for y in range(H):
    t = y / H
    if t < 0.5:
        t2 = t / 0.5
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * t2)
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * t2)
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * t2)
    else:
        t2 = (t - 0.5) / 0.5
        r = int(colors[1][0] + (colors[2][0] - colors[1][0]) * t2)
        g = int(colors[1][1] + (colors[2][1] - colors[1][1]) * t2)
        b = int(colors[1][2] + (colors[2][2] - colors[1][2]) * t2)
    draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

# --- Helper functions ---
def draw_text_shadow(draw, pos, text, font, fill, shadow_offset=3):
    """Draw text with subtle drop shadow"""
    sx, sy = pos[0] + shadow_offset, pos[1] + shadow_offset
    draw.text((sx, sy), text, font=font, fill=(61, 43, 31, 35))
    draw.text(pos, text, font=font, fill=fill)

def draw_centered_text_shadow(draw, y, text, font, fill, shadow_offset=3):
    """Draw centered text with shadow"""
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    draw_text_shadow(draw, (x, y), text, font, fill, shadow_offset)
    return tw

def draw_sparkle(draw, cx, cy, size, color=(212, 175, 55, 180)):
    """Draw a 4-pointed sparkle/star"""
    draw.line([(cx, cy - size), (cx, cy + size)], fill=color, width=2)
    draw.line([(cx - size, cy), (cx + size, cy)], fill=color, width=2)
    s2 = int(size * 0.6)
    draw.line([(cx - s2, cy - s2), (cx + s2, cy + s2)], fill=color, width=1)
    draw.line([(cx + s2, cy - s2), (cx - s2, cy + s2)], fill=color, width=1)

def draw_pill_badge(draw, cx, cy, text, font, bg_color, text_color, padding_x=30, padding_y=12):
    """Draw a rounded pill badge with centered text"""
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x1 = cx - tw // 2 - padding_x
    y1 = cy - th // 2 - padding_y
    x2 = cx + tw // 2 + padding_x
    y2 = cy + th // 2 + padding_y
    radius = (y2 - y1) // 2
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=bg_color)
    draw.text((cx - tw // 2, cy - th // 2 - 2), text, font=font, fill=text_color)
    return (x2 - x1, y2 - y1)

def draw_diamond(draw, cx, cy, size, color):
    """Draw a small diamond shape"""
    draw.polygon([(cx, cy-size), (cx+size, cy), (cx, cy+size), (cx-size, cy)], fill=color)

# --- Decorative sparkles at top ---
sparkle_positions = [
    (120, 80, 18), (320, 50, 12), (550, 90, 22), (780, 45, 15),
    (950, 75, 20), (1100, 55, 14), (200, 140, 10), (1050, 130, 11),
    (680, 60, 16), (420, 130, 9),
]
for sx, sy, ss in sparkle_positions:
    alpha = 120 + (ss * 3)
    draw_sparkle(draw, sx, sy, ss, (212, 175, 55, min(alpha, 200)))

# Small dots scattered
import random
random.seed(42)
for _ in range(30):
    dx = random.randint(50, W-50)
    dy = random.randint(30, 200)
    ds = random.randint(2, 5)
    draw.ellipse([dx-ds, dy-ds, dx+ds, dy+ds], fill=(212, 175, 55, random.randint(40, 100)))

# --- Decorative top arcs ---
for i in range(3):
    offset = i * 2
    draw.arc([100+offset, -200+offset, W-100-offset, 250-offset], 0, 180,
             fill=(212, 175, 55, 50 - i*15), width=2)

# --- Side decorative diamonds ---
for i in range(5):
    y_pos = 300 + i * 80
    draw_diamond(draw, 65, y_pos, 6, (183, 110, 121, 100 - i*15))
for i in range(5):
    y_pos = 320 + i * 80
    draw_diamond(draw, W - 65, y_pos, 6, (183, 110, 121, 100 - i*15))

# --- Main Title Area ---
title_font = font_bold(105)
draw_centered_text_shadow(draw, 260, "年底囤货开箱", title_font, DARK_BROWN, shadow_offset=4)

subtitle_font = font_bold(58)
draw_centered_text_shadow(draw, 395, "精致女孩的年终犒劳", subtitle_font, ROSE_GOLD, shadow_offset=2)

# --- Decorative divider line ---
divider_y = 490
line_color = (212, 175, 55, 120)
draw.line([(200, divider_y), (520, divider_y)], fill=line_color, width=2)
draw.line([(722, divider_y), (W-200, divider_y)], fill=line_color, width=2)
draw_diamond(draw, W//2, divider_y, 10, (212, 175, 55, 180))
draw_diamond(draw, 190, divider_y, 5, (212, 175, 55, 120))
draw_diamond(draw, W-190, divider_y, 5, (212, 175, 55, 120))

# --- Gift Box Illustration ---
box_cx, box_cy = W // 2, 650
box_w, box_h = 200, 160
lid_h = 45

# Box shadow
draw.rounded_rectangle(
    [box_cx - box_w//2 + 6, box_cy - box_h//2 + lid_h + 6,
     box_cx + box_w//2 + 6, box_cy + box_h//2 + 6],
    radius=12, fill=(61, 43, 31, 25)
)
# Box body
draw.rounded_rectangle(
    [box_cx - box_w//2, box_cy - box_h//2 + lid_h,
     box_cx + box_w//2, box_cy + box_h//2],
    radius=12, fill=(255, 235, 230, 220)
)
draw.rounded_rectangle(
    [box_cx - box_w//2, box_cy - box_h//2 + lid_h,
     box_cx + box_w//2, box_cy + box_h//2],
    radius=12, outline=ROSE_GOLD, width=3
)
# Lid
draw.rounded_rectangle(
    [box_cx - box_w//2 - 10, box_cy - box_h//2,
     box_cx + box_w//2 + 10, box_cy - box_h//2 + lid_h],
    radius=10, fill=(255, 225, 220, 240)
)
draw.rounded_rectangle(
    [box_cx - box_w//2 - 10, box_cy - box_h//2,
     box_cx + box_w//2 + 10, box_cy - box_h//2 + lid_h],
    radius=10, outline=ROSE_GOLD, width=3
)
# Ribbon cross
draw.line([(box_cx, box_cy - box_h//2), (box_cx, box_cy + box_h//2)], fill=GOLD, width=4)
draw.line([(box_cx - box_w//2, box_cy - box_h//2 + lid_h + (box_h - lid_h)//2),
           (box_cx + box_w//2, box_cy - box_h//2 + lid_h + (box_h - lid_h)//2)],
          fill=GOLD, width=4)
# Bow
bow_y = box_cy - box_h//2 - 5
draw.ellipse([box_cx - 40, bow_y - 25, box_cx - 5, bow_y + 10], outline=GOLD, width=3)
draw.ellipse([box_cx + 5, bow_y - 25, box_cx + 40, bow_y + 10], outline=GOLD, width=3)
draw.ellipse([box_cx - 8, bow_y - 8, box_cx + 8, bow_y + 8], fill=GOLD)

# Sparkles around gift box
draw_sparkle(draw, box_cx - 140, box_cy - 50, 14, (212, 175, 55, 150))
draw_sparkle(draw, box_cx + 145, box_cy - 40, 12, (212, 175, 55, 130))
draw_sparkle(draw, box_cx - 120, box_cy + 50, 10, (212, 175, 55, 100))
draw_sparkle(draw, box_cx + 130, box_cy + 60, 11, (212, 175, 55, 110))

# --- Product Count Badge ---
badge_y = 810
badge_font = font_bold(48)
draw_pill_badge(draw, W//2, badge_y, "9件海外小众好物", badge_font,
                (255, 255, 255, 200), ROSE_GOLD, padding_x=40, padding_y=18)

draw.line([(120, badge_y), (300, badge_y)], fill=(212, 175, 55, 80), width=1)
draw.line([(W-300, badge_y), (W-120, badge_y)], fill=(212, 175, 55, 80), width=1)

# --- Brand Names ---
brand_font = font_reg(36)
brand_text = "法尔曼  ·  Elemis  ·  Baume 27  ·  Perfumer H"
bbox = brand_font.getbbox(brand_text)
tw = bbox[2] - bbox[0]
brand_x = (W - tw) // 2
brand_y = 880
draw.text((brand_x + 2, brand_y + 2), brand_text, font=brand_font, fill=(61, 43, 31, 20))
draw.text((brand_x, brand_y), brand_text, font=brand_font, fill=(140, 100, 80, 200))

# --- Content Description Area ---
desc_y = 970
draw.rounded_rectangle(
    [100, desc_y - 20, W - 100, desc_y + 230],
    radius=20, fill=(255, 255, 255, 60)
)

content_lines = [
    ("🎄 Lane Crawford 圣诞日历", font_reg(34)),
    ("🇫🇷 法式贵妇护肤 · 瑞士抗老精华", font_reg(34)),
    ("🇬🇧 伦敦小众香水 · 手工蜡烛", font_reg(34)),
    ("💝 北美打工人的年终犒劳清单", font_reg(34)),
]

for i, (text, font) in enumerate(content_lines):
    y = desc_y + 10 + i * 55
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    draw.text((x, y), text, font=font, fill=(80, 60, 45, 220))

# --- Bottom Tags ---
tag_y = 1300
tag_font = font_bold(32)
tags = ["欧洲小众", "贵妇护肤", "开箱测评", "年终好物"]

tag_widths = []
tag_padding_x = 24
tag_gap = 20
for tag in tags:
    bbox = tag_font.getbbox(tag)
    tw = bbox[2] - bbox[0]
    tag_widths.append(tw)

total_w = sum(tw + tag_padding_x * 2 for tw in tag_widths) + tag_gap * (len(tags) - 1)
start_x = (W - total_w) // 2

for i, (tag, tw) in enumerate(zip(tags, tag_widths)):
    pill_w = tw + tag_padding_x * 2
    pill_h = 50
    x1 = start_x
    y1 = tag_y
    x2 = x1 + pill_w
    y2 = y1 + pill_h
    
    if i % 2 == 0:
        bg = (255, 235, 230, 180)
        tc = ROSE_GOLD
    else:
        bg = (255, 245, 230, 180)
        tc = (160, 120, 50)
    
    draw.rounded_rectangle([x1, y1, x2, y2], radius=pill_h//2, fill=bg)
    draw.rounded_rectangle([x1, y1, x2, y2], radius=pill_h//2, outline=(*tc, 80), width=1)
    
    bbox = tag_font.getbbox(tag)
    th = bbox[3] - bbox[1]
    draw.text((x1 + tag_padding_x, y1 + (pill_h - th) // 2 - 2), tag, font=tag_font, fill=tc)
    
    start_x = x2 + tag_gap

# --- Bottom decorative area ---
div2_y = 1400
draw.line([(200, div2_y), (W-200, div2_y)], fill=(212, 175, 55, 60), width=1)

persona_font = font_reg(30)
persona_text = "🌸 北美打工人の年终犒劳 · 给自己最好的年货 🌸"
bbox = persona_font.getbbox(persona_text)
tw = bbox[2] - bbox[0]
draw.text(((W - tw) // 2, 1430), persona_text, font=persona_font, fill=(140, 100, 80, 160))

# --- Watermark ---
wm_font = font_reg(26)
wm_text = "2026年终好物"
bbox = wm_font.getbbox(wm_text)
tw = bbox[2] - bbox[0]
draw.text(((W - tw) // 2, 1560), wm_text, font=wm_font, fill=(180, 150, 130, 80))

# --- Bottom sparkles ---
bottom_sparkles = [
    (150, 1520, 10), (400, 1550, 8), (621, 1530, 12),
    (850, 1545, 9), (1080, 1515, 11),
]
for sx, sy, ss in bottom_sparkles:
    draw_sparkle(draw, sx, sy, ss, (212, 175, 55, 80))

# --- Subtle border frame ---
border_margin = 40
draw.rounded_rectangle(
    [border_margin, border_margin, W - border_margin, H - border_margin],
    radius=30, outline=(212, 175, 55, 50), width=2
)

corners = [
    (border_margin + 10, border_margin + 10),
    (W - border_margin - 10, border_margin + 10),
    (border_margin + 10, H - border_margin - 10),
    (W - border_margin - 10, H - border_margin - 10),
]
for cx, cy in corners:
    draw_diamond(draw, cx, cy, 8, (212, 175, 55, 100))

# --- Save ---
final = Image.new("RGB", (W, H), (255, 255, 255))
final.paste(img, mask=img.split()[3])

tmp_out = "/tmp/年底囤货-cover.png"
final.save(tmp_out, "PNG", quality=95)

# Also write base64 version for sandbox transfer
import base64
with open(tmp_out, 'rb') as f:
    b64data = base64.b64encode(f.read()).decode()
with open("/tmp/cover_b64.txt", 'w') as f:
    f.write(b64data)

print(f"✅ Cover saved to {tmp_out}")
print(f"   Base64 at /tmp/cover_b64.txt ({len(b64data)} chars)")
print(f"   Size: {final.size}")
