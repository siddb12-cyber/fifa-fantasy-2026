"""
FIFA 2026 Fantasy — Premium Card Avatar Generator
Creates FIFA Ultimate Team-style trading cards for all 8 players.
Output: assets/avatars/{petname}_card.png  (500x700 px)
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
from pathlib import Path
import math

# ── Paths ──────────────────────────────────────────────────────────────────
import os, sys

def _resolve_base():
    """Return the correct base directory regardless of OS."""
    win_path = Path(r"C:\Users\siddh\Downloads\HK\FIFA\FIFA World Cup Fantasy Game")
    lin_path = Path("/sessions/blissful-beautiful-brahmagupta/mnt/FIFA World Cup Fantasy Game")
    # Use script's own directory as anchor when possible
    script_dir = Path(__file__).resolve().parent  # scripts/
    candidate  = script_dir.parent               # FIFA World Cup Fantasy Game/
    if candidate.exists():
        return candidate
    if win_path.exists():
        return win_path
    if lin_path.exists():
        return lin_path
    return win_path  # fallback default

BASE_DIR = _resolve_base()
AV_DIR   = BASE_DIR / "assets" / "avatars"

FONT_BOLD    = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REGULAR = r"C:\Windows\Fonts\arial.ttf"

FALLBACK_FONTS = [
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

# ── Player Config ──────────────────────────────────────────────────────────
#  pet_name : (team, jersey, primary_hex, secondary_hex, accent_hex, bg_dark_hex)
PLAYERS = {
    "Budhya": ("Portugal",    7,  "#C8102E", "#006600", "#FFFFFF", "#6B0000"),
    "Ambu":   ("Argentina",   10, "#74ACDF", "#FFFFFF", "#FFFFFF", "#2C6FA6"),
    "Vini":   ("England",     9,  "#CF111A", "#FFFFFF", "#FFFFFF", "#8B0000"),
    "Baby":   ("Spain",       6,  "#AA151B", "#F1BF00", "#F1BF00", "#6B0000"),
    "Abs":    ("Germany",     8,  "#1C1C1C", "#E8C84A", "#E8C84A", "#3D3D3D"),
    "Anna":   ("France",      11, "#002395", "#ED2939", "#FFFFFF", "#001266"),
    "Umaga":  ("Brazil",      1,  "#009C3B", "#FFDF00", "#FFDF00", "#005C22"),
    "PR":     ("Netherlands", 4,  "#E8641A", "#FFFFFF", "#FFFFFF", "#9B3C00"),
}

# Photo file map
PHOTO_FILES = {
    "Budhya": "Sidhant (Budhya).jpeg",
    "Ambu":   "Kushal (Ambu).jpeg",
    "Vini":   "Vineet (Vini).jpeg",
    "Baby":   "Susmit (Baby).jpeg",
    "Abs":    "Abhishek (Abs).jpeg",
    "Anna":   "Nishant (Anna).jpeg",
    "Umaga":  "Umang (Umaga).jpeg",
    "PR":     "Pranav (PR).jpeg",
}

CARD_W, CARD_H = 500, 700


def get_font(size, bold=True):
    paths = [FONT_BOLD if bold else FONT_REGULAR] + FALLBACK_FONTS
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def cartoon_effect(img_pil: Image.Image, size=(460, 390)) -> Image.Image:
    """Fast cartoon effect: resize small, bilateral filter, edge overlay."""
    # Resize small first (huge speedup on bilateral)
    small = img_pil.resize((320, int(320 * size[1] / size[0])), Image.LANCZOS)
    img_bgr = cv2.cvtColor(np.array(small.convert("RGB")), cv2.COLOR_RGB2BGR)

    # 4-pass bilateral at smaller size = much faster
    smooth = img_bgr.copy()
    for _ in range(4):
        smooth = cv2.bilateralFilter(smooth, d=7, sigmaColor=80, sigmaSpace=80)

    # Contrast + warm grade
    smooth = cv2.convertScaleAbs(smooth, alpha=1.1, beta=8)
    b, g, r = cv2.split(smooth.astype(np.float32))
    r = np.clip(r * 1.05, 0, 255)
    b = np.clip(b * 0.94, 0, 255)
    smooth = cv2.merge([b.astype(np.uint8), g.astype(np.uint8), r.astype(np.uint8)])

    # Edge overlay
    gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray  = cv2.medianBlur(gray, 5)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 9, 9)
    edges_f = edges.astype(np.float32) / 255.0
    result   = smooth.astype(np.float32)
    for c in range(3):
        result[:, :, c] = np.clip(result[:, :, c] * (0.72 + 0.28 * edges_f), 0, 255)

    # Upscale to target size
    out = Image.fromarray(cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2RGB))
    return out.resize(size, Image.LANCZOS)


def detect_and_crop(img_pil: Image.Image, size=(460, 390)) -> Image.Image:
    """Detect face, crop upper-body; fall back to center-top crop."""
    img_rgb = np.array(img_pil.convert("RGB"))
    gray    = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    w_img, h_img = img_pil.size

    # Try frontal face
    fc  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    fcs = fc.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))

    if len(fcs) == 0:
        # Try profile face
        pc  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
        fcs = pc.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))

    if len(fcs) > 0:
        x, y, fw, fh = fcs[0]
        # Upper-body crop: face + some headroom + lower body
        pad_top    = int(fh * 0.6)
        pad_sides  = int(fw * 0.8)
        pad_bottom = int(fh * 2.5)
        x1 = max(0, x - pad_sides)
        y1 = max(0, y - pad_top)
        x2 = min(w_img, x + fw + pad_sides)
        y2 = min(h_img, y + fh + pad_bottom)
        cropped = img_pil.crop((x1, y1, x2, y2))
    else:
        # Center crop (top portion)
        sq  = min(w_img, h_img)
        cx  = (w_img - sq) // 2
        cropped = img_pil.crop((cx, 0, cx + sq, sq))

    return cropped


def draw_rounded_rect(draw, xy, radius, fill, outline=None, outline_width=3):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    r = radius
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill,
                            outline=outline, width=outline_width)


def gradient_rect(img: Image.Image, xy, color1, color2, vertical=True):
    """Fill a rectangle with a two-color gradient."""
    x0, y0, x1, y1 = xy
    region = Image.new("RGB", (x1 - x0, y1 - y0))
    draw   = ImageDraw.Draw(region)
    if vertical:
        steps = y1 - y0
        for i in range(steps):
            t = i / max(steps - 1, 1)
            r = int(color1[0] + (color2[0] - color1[0]) * t)
            g = int(color1[1] + (color2[1] - color1[1]) * t)
            b = int(color1[2] + (color2[2] - color1[2]) * t)
            draw.line([(0, i), (x1 - x0, i)], fill=(r, g, b))
    img.paste(region, (x0, y0))


def add_shimmer(img: Image.Image):
    """Add a subtle diagonal shimmer overlay to make the card feel premium."""
    shimmer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(shimmer)
    w, h    = img.size
    # Diagonal highlight band
    for i in range(-h, w, 60):
        alpha = 18
        pts   = [(i, 0), (i + 40, 0), (i + 40 + h, h), (i + h, h)]
        draw.polygon(pts, fill=(255, 255, 255, alpha))
    return Image.alpha_composite(img.convert("RGBA"), shimmer).convert("RGB")


def make_card(pet_name: str) -> Image.Image:
    team, jersey, pri_hex, sec_hex, acc_hex, dark_hex = PLAYERS[pet_name]
    pri  = hex_to_rgb(pri_hex)
    sec  = hex_to_rgb(sec_hex)
    dark = hex_to_rgb(dark_hex)

    # ── Base card ─────────────────────────────────────────────────────────
    card = Image.new("RGB", (CARD_W, CARD_H), (10, 12, 18))
    draw = ImageDraw.Draw(card)

    # Background: dark-to-primary gradient
    gradient_rect(card, (0, 0, CARD_W, CARD_H), (10, 12, 18), dark)

    # Subtle diagonal lines texture
    for x in range(-CARD_H, CARD_W, 18):
        draw.line([(x, 0), (x + CARD_H, CARD_H)], fill=(255, 255, 255, 8), width=1)

    # ── Photo area (upper 58%) ────────────────────────────────────────────
    PHOTO_H = int(CARD_H * 0.58)
    photo_path = AV_DIR / PHOTO_FILES[pet_name]

    try:
        raw = Image.open(photo_path)
        cropped = detect_and_crop(raw)
        # Apply cartoon effect
        photo = cartoon_effect(cropped, size=(CARD_W - 20, PHOTO_H - 10))
        # Paste centered
        px = (CARD_W - photo.width) // 2
        py = 15
        card.paste(photo, (px, py))
    except Exception as e:
        print(f"  [!] Photo error for {pet_name}: {e}")
        # Grey placeholder
        ph = Image.new("RGB", (CARD_W - 20, PHOTO_H - 10), (80, 80, 90))
        card.paste(ph, (10, 15))

    # ── Gradient divider strip ────────────────────────────────────────────
    divider_y = PHOTO_H + 10
    gradient_rect(card, (0, divider_y, CARD_W, divider_y + 8), pri, sec, vertical=False)

    # ── Bottom info section ───────────────────────────────────────────────
    info_y = divider_y + 18
    gradient_rect(card, (0, divider_y, CARD_W, CARD_H), dark, (10, 12, 18))

    # Jersey number — large badge (left side)
    badge_cx, badge_cy = 80, info_y + 70
    badge_r            = 55
    # Badge circle
    badge_img  = Image.new("RGBA", (badge_r * 2 + 10, badge_r * 2 + 10), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge_img)
    badge_draw.ellipse([5, 5, badge_r * 2 + 5, badge_r * 2 + 5], fill=pri + (230,), outline=sec + (255,), width=4)
    card.paste(badge_img, (badge_cx - badge_r - 5, badge_cy - badge_r - 5), badge_img)

    num_font   = get_font(52, bold=True)
    num_str    = str(jersey)
    num_bbox   = num_font.getbbox(num_str)
    num_w      = num_bbox[2] - num_bbox[0]
    num_h      = num_bbox[3] - num_bbox[1]
    # Choose text color: white unless primary is very light
    luminance = 0.299 * pri[0] + 0.587 * pri[1] + 0.114 * pri[2]
    num_color = (255, 255, 255) if luminance < 180 else (10, 12, 18)
    draw.text((badge_cx - num_w // 2 - num_bbox[0], badge_cy - num_h // 2 - num_bbox[1]),
              num_str, font=num_font, fill=num_color)

    # Pet name — large, right of badge
    name_x   = badge_cx + badge_r + 18
    name_font = get_font(54, bold=True)
    # Shadow
    draw.text((name_x + 2, info_y + 30 + 2), pet_name.upper(), font=name_font, fill=(0, 0, 0))
    draw.text((name_x, info_y + 30), pet_name.upper(), font=name_font, fill=(255, 255, 255))

    # Team name
    team_font = get_font(22, bold=False)
    draw.text((name_x + 2, info_y + 102 + 2), team.upper(), font=team_font, fill=(0, 0, 0))
    draw.text((name_x, info_y + 102), team.upper(), font=team_font, fill=sec)

    # Decorative accent line under name
    accent_y = info_y + 135
    draw.line([(name_x, accent_y), (CARD_W - 20, accent_y)], fill=sec, width=2)

    # FIFA 2026 label bottom-right
    fifa_font  = get_font(14, bold=False)
    label_str  = "FIFA WORLD CUP 2026™"
    label_bbox = fifa_font.getbbox(label_str)
    label_w    = label_bbox[2] - label_bbox[0]
    draw.text((CARD_W - label_w - 16, CARD_H - 28), label_str,
              font=fifa_font, fill=(180, 180, 180))

    # ── Card border (rounded rect) ────────────────────────────────────────
    border_img  = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border_img)
    border_draw.rounded_rectangle([2, 2, CARD_W - 3, CARD_H - 3],
                                   radius=18, fill=None,
                                   outline=sec + (220,), width=5)
    # Inner border
    border_draw.rounded_rectangle([9, 9, CARD_W - 10, CARD_H - 10],
                                   radius=14, fill=None,
                                   outline=pri + (100,), width=2)
    card.paste(border_img, (0, 0), border_img)

    # ── Shimmer overlay ───────────────────────────────────────────────────
    card = add_shimmer(card)

    return card


def main():
    AV_DIR.mkdir(parents=True, exist_ok=True)
    print("FIFA 2026 Fantasy — Card Avatar Generator")
    print("=" * 42)
    for pet_name in PLAYERS:
        print(f"  Generating {pet_name}...", end=" ", flush=True)
        try:
            card = make_card(pet_name)
            out  = AV_DIR / f"{pet_name.lower()}_card.png"
            card.save(out, "PNG")
            print(f"OK  -> {out.name}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"ERROR: {e}")

    print("\nAll done! Cards saved to:", AV_DIR)


if __name__ == "__main__":
    main()

