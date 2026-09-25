# UI textures for the phone screen and the glass notification tiles (PIL).
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = '/tmp/claude-0/-home-user-htmlpreview/841d5631-4c5a-5292-a263-54034b87c66d/scratchpad/anim/node_modules/@fontsource'

def font(size, weight=600):
    for p in (f'{FONTS}/inter/files/inter-latin-{weight}-normal.woff', f'{FONTS}/inter/files/inter-latin-{weight}-normal.woff2'):
        try: return ImageFont.truetype(p, size)
        except Exception: pass
    return ImageFont.load_default()

APPS = [  # (name, message, colour)
    ('MESSAGES', 'Are you free tonight?', (52, 199, 89)),
    ('SOCIAL', '12 people liked your post', (255, 45, 85)),
    ('VIDEO', 'New: 10 study hacks', (255, 59, 48)),
    ('GROUP CHAT', '47 new messages', (10, 132, 255)),
    ('SHOP', 'Flash deal: 10 min left', (255, 149, 0)),
    ('REMINDER', 'Just one more scroll…', (175, 82, 222)),
]

def tile_texture(i, W=1024, H=264):
    name, msg, col = APPS[i % len(APPS)]
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    r = H // 2 - 8
    d.rounded_rectangle([6, 6, W - 6, H - 6], radius=r, fill=(248, 248, 250, 225))
    s = int(H * 0.73); m = (H - s) // 2
    d.rounded_rectangle([m + 4, m, m + 4 + s, m + s], radius=s // 4, fill=col + (255,))
    d.ellipse([m + 4 + s * 0.3, m + s * 0.3, m + 4 + s * 0.7, m + s * 0.7], fill=(255, 255, 255, 255))
    k = H / 264
    d.text((m + s + 40, 48 * k), name, font=font(int(40 * k), 600), fill=(20, 20, 24, 150))
    d.text((m + s + 40, 104 * k), msg, font=font(int(54 * k), 500), fill=(12, 12, 14, 255))
    d.text((W - 150 * k, 48 * k), 'now', font=font(int(40 * k), 400), fill=(20, 20, 24, 120))
    return img

def phone_screen(W=720, H=1480):
    """Dark lock screen with a stack of banners (portrait, top = +y of the phone)."""
    img = Image.new('RGB', (W, H), (0, 0, 0)); d = ImageDraw.Draw(img)
    for y in range(H):  # deep gradient wallpaper
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(40 + 60 * k), int(18 + 10 * k), int(90 + 60 * (1 - k))))
    d.text((W / 2, 150), 'Tuesday, March 10', font=font(40, 500), fill=(255, 255, 255), anchor='mm')
    d.text((W / 2, 290), '9:41', font=font(210, 600), fill=(255, 255, 255), anchor='mm')
    y = 520
    for i in range(6):
        t = tile_texture(i, W - 60, 150).convert('RGBA')
        img.paste(t, (30, y), t); y += 165
    return img.filter(ImageFilter.GaussianBlur(0.6))

if __name__ == '__main__':
    out = os.path.join(HERE, 'tex'); os.makedirs(out, exist_ok=True)
    for i in range(len(APPS)): tile_texture(i).save(f'{out}/tile_{i}.png')
    phone_screen().save(f'{out}/phone_screen.png')
    print('ok')
