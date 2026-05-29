"""
avatar_generator.py
FIFA World Cup 2026 Fantasy — Player Avatar Generator

Creates premium cartoon-style FIFA cards from WhatsApp DPs.
Uses OpenCV bilateral filter + adaptive edge detection for real cartoon effect.

Usage: python avatar_generator.py
Outputs to: FIFA World Cup Fantasy Game/assets/avatars/
"""

import os
import sys
import math
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

try:
    import cv2
    OPENCV_OK = True
except ImportError:
    OPENCV_OK = False
    print("⚠ opencv-python not found — install with: pip install opencv-python")
    print("  Falling back to PIL-only cartoon mode (less effective)")

# ── PATHS ─────────────────────────────────────────────────────────────────────
SRC_DIR  = Path(r"C:\Users\siddh\Downloads\HK\FIFA\FIFA World Cup Fantasy Game\assets\avatars")
OUT_DIR  = Path(r"C:\Users\siddh\Downloads\HK\FIFA\FIFA World Cup Fantasy Game\assets\avatars")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── PLAYER DATA ───────────────────────────────────────────────────────────────
# (team, jersey, primary_color, secondary_color, text_color, gradient_end)
PLAYERS = {
    "Budhya": ("Portugal",    7,  "#FF0000", "#006600", "#FFFFFF", "#8B0000"),
    "Ambu":   ("Argentina",   10, "#75AADB", "#FFFFFF", "#FFFFFF", "#2C6FA6"),
    "Vini":   ("England",     9,  "#CF111A", "#FFFFFF", "#FFFFFF", "#8B0000"),
    "Baby":   ("Spain",       6,  "#AA151B", "#F1BF00", "#FFFFFF", "#6B0000"),
    "Abs":    ("Germany",     8,  "#1C1C1C", "#E8C84A", "#FFFFFF", "#3D3D3D"),
    "Anna":   ("France",      11, "#002395", "#ED2939", "#FFFFFF", "#001266"),
    "Umaga":  ("Brazil",      1,  "#009C3B", "#FFDF00", "#FFFFFF", "#006B2B"),
    "PR":     ("Netherlands", 4,  "#FF4500", "#FFFFFF", "#FFFFFF", "#CC3700"),
}

TEAM_FLAGS = {
    "Portugal": "PT", "Argentina": "AR", "England": "EN",
    "Spain": "ES", "Germany": "DE", "France": "FR",
    "Brazil": "BR", "Netherlands": "NL",
}

CARD_W, CARD_H = 440, 600


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def find_dp(pet_name: str):
    """Find photo by (PetName) pattern. Supports: Name (PetName).jpeg/jpg/png"""
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"):
        for f in SRC_DIR.glob(ext):
            if f"({pet_name})" in f.name:
                return f
            if f"({pet_name.lower()})" in f.name.lower():
                return f
    return None


# ── FACE DETECTION + SMART CROP ───────────────────────────────────────────────
def detect_and_crop_face(img_pil: Image.Image) -> Image.Image:
    """
    Detect the largest face in the image and return a square crop centered on it.
    Falls back to top-center square crop if no face detected (handles group photos
    where haarcascade fails). Works on full-body, upper-body, and close-up shots.
    """
    if not OPENCV_OK:
        # Fallback: crop top-center square (works for most portrait shots)
        w, h = img_pil.size
        sq = min(w, h)
        left = (w - sq) // 2
        return img_pil.crop((left, 0, left + sq, sq))

    img_bgr = cv2.cvtColor(np.array(img_pil.convert("RGB")), cv2.COLOR_RGB2BGR)
    gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h_img, w_img = img_bgr.shape[:2]

    # Load Haar cascade (bundled with every opencv-python install)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    # Try detection at multiple scales (handles small faces in full-body shots)
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.05, minNeighbors=4, minSize=(40, 40)
    )

    if len(faces) == 0:
        # Try with lower sensitivity for difficult lighting / side angles
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30)
        )

    if len(faces) > 0:
        # Pick the largest face (avoids background faces)
        fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])

        # Expand crop: add padding around face (forehead, chin, sides)
        pad_x = int(fw * 0.55)
        pad_y_top = int(fh * 0.70)   # more headroom above for hair
        pad_y_bot = int(fh * 0.40)   # chin to neck

        x1 = max(0, fx - pad_x)
        y1 = max(0, fy - pad_y_top)
        x2 = min(w_img, fx + fw + pad_x)
        y2 = min(h_img, fy + fh + pad_y_bot)

        # Make it square (expand shorter dimension)
        cw, ch = x2 - x1, y2 - y1
        if cw > ch:
            diff = cw - ch
            y1 = max(0, y1 - diff // 2)
            y2 = min(h_img, y2 + diff - diff // 2)
        elif ch > cw:
            diff = ch - cw
            x1 = max(0, x1 - diff // 2)
            x2 = min(w_img, x2 + diff - diff // 2)

        cropped = img_pil.crop((x1, y1, x2, y2))
        print(f"    ✓ Face detected at ({fx},{fy}) {fw}×{fh}px → crop ({x1},{y1})→({x2},{y2})")
        return cropped

    # No face found — try profile face detector
    profile_path = cv2.data.haarcascades + "haarcascade_profileface.xml"
    profile_cascade = cv2.CascadeClassifier(profile_path)
    faces = profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))
    if len(faces) > 0:
        fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])
        pad = int(fw * 0.6)
        x1 = max(0, fx - pad)
        y1 = max(0, fy - int(fh * 0.7))
        x2 = min(w_img, fx + fw + pad)
        y2 = min(h_img, fy + fh + int(fh * 0.4))
        sq = max(x2 - x1, y2 - y1)
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        x1 = max(0, cx - sq // 2)
        y1 = max(0, cy - sq // 2)
        x2 = min(w_img, x1 + sq)
        y2 = min(h_img, y1 + sq)
        print(f"    ✓ Profile face detected → crop ({x1},{y1})→({x2},{y2})")
        return img_pil.crop((x1, y1, x2, y2))

    # Last resort — center crop (face is usually center of photo)
    print(f"    ⚠ No face detected — using center square crop")
    sq   = min(w_img, h_img)
    left = (w_img - sq) // 2
    top  = (h_img - sq) // 2
    return img_pil.crop((left, top, left + sq, top + sq))


# ── CLEAN CARTOON EFFECT ─────────────────────────────────────────────────────
def ghibli_style(img_pil: Image.Image, size=(320, 320)) -> Image.Image:
    """
    Clean cartoon effect using bilateral filter stack.
    No cv2.stylization (too aggressive/blotchy).
    Produces smooth natural skin tones with a soft painted look.
    1. 6× bilateral filter  — smooth painting without color distortion
    2. Subtle contrast/brightness boost
    3. Very light warm grade — just a hint, not heavy
    4. Subtle edge lines via adaptive threshold (light, not harsh ink)
    """
    img_pil = img_pil.resize(size, Image.LANCZOS)
    img_bgr = cv2.cvtColor(np.array(img_pil.convert("RGB")), cv2.COLOR_RGB2BGR)

    # Step 1: Bilateral filter stack — smooth painting, preserves edges
    smooth = img_bgr.copy()
    for _ in range(6):
        smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=75, sigmaSpace=75)

    # Step 2: Subtle contrast boost
    smooth = cv2.convertScaleAbs(smooth, alpha=1.08, beta=5)

    # Step 3: Very light warm grade (subtle, only +4% R, -5% B)
    b, g, r = cv2.split(smooth.astype(np.float32))
    r = np.clip(r * 1.04, 0, 255)
    b = np.clip(b * 0.95, 0, 255)
    smooth = cv2.merge([b.astype(np.uint8), g.astype(np.uint8), r.astype(np.uint8)])

    # Step 4: Soft edge overlay — very subtle, no harsh black lines
    gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray  = cv2.medianBlur(gray, 5)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 9, 9)
    # Blend edges at only 30% weight — just a hint of cartoon lines
    edges_f = edges.astype(np.float32) / 255.0
    result  = smooth.astype(np.float32)
    for c in range(3):
        result[:, :, c] = np.clip(result[:, :, c] * (0.70 + 0.30 * edges_f), 0, 255)

    return Image.fromarray(cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2RGB))


def cartoon_pil(img_pil: Image.Image, size=(320, 320)) -> Image.Image:
    """Fallback (no OpenCV): soft watercolor approximation with PIL."""
    img = img_pil.resize(size, Image.LANCZOS)
    for _ in range(6):
        img = img.filter(ImageFilter.SMOOTH_MORE)
    img = ImageEnhance.Color(img).enhance(1.5)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Brightness(img).enhance(1.05)
    # Warm tint
    r, g, b = img.split()
    r = ImageEnhance.Brightness(r).enhance(1.08)
    b = ImageEnhance.Brightness(b).enhance(0.90)
    return Image.merge("RGB", (r, g, b))


def apply_cartoon(img_pil: Image.Image, size=(320, 320)) -> Image.Image:
    if OPENCV_OK:
        return ghibli_style(img_pil, size)
    return cartoon_pil(img_pil, size)


# ── CIRCLE CROP ───────────────────────────────────────────────────────────────
def circle_crop(img: Image.Image, size: int) -> Image.Image:
    img = img.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(img, mask=mask)
    return result


# ── GRADIENT ──────────────────────────────────────────────────────────────────
def vertical_gradient(draw, x0, y0, x1, y1, color_top, color_bottom):
    r1, g1, b1 = color_top
    r2, g2, b2 = color_bottom
    h = max(y1 - y0, 1)
    for y in range(h):
        t = y / (h - 1) if h > 1 else 0
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        draw.line([(x0, y0 + y), (x1, y0 + y)], fill=(r, g, b))


# ── PREMIUM CARD ──────────────────────────────────────────────────────────────
def make_avatar_card(pet, face_cartoon, team, jersey,
                     primary, secondary, text_col, grad_end):
    W, H       = CARD_W, CARD_H
    GOLD       = (212, 175, 55)
    GOLD_LIGHT = (255, 215, 0)
    BLACK      = (8, 8, 16)
    WHITE      = (255, 255, 255)

    p_rgb = hex_to_rgb(primary)
    s_rgb = hex_to_rgb(secondary)
    g_rgb = hex_to_rgb(grad_end)

    # ── BASE CANVAS ──
    card = Image.new("RGB", (W, H), BLACK)
    draw = ImageDraw.Draw(card)

    # Background gradient (team color top → near-black bottom)
    vertical_gradient(draw, 0, 0, W, int(H * 0.5), g_rgb, BLACK)
    vertical_gradient(draw, 0, int(H * 0.5), W, H, BLACK, (12, 12, 22))

    # ── GOLD BORDER ──
    for i in range(4):
        draw.rounded_rectangle([i, i, W - i, H - i], radius=22 - i,
                                outline=(*GOLD, 255 - i * 40), width=1)

    # ── TOP BAND ──
    draw.rounded_rectangle([5, 5, W - 5, 68], radius=17, fill=p_rgb)

    # ── FONTS ──
    def load_font(name, size):
        for fname in [name, "arial.ttf", "Arial.ttf"]:
            try:
                return ImageFont.truetype(fname, size)
            except Exception:
                pass
        return ImageFont.load_default()

    num_font  = load_font("arialbd.ttf", 32)
    name_font = load_font("arialbd.ttf", 44)
    sub_font  = load_font("arial.ttf",   19)
    sm_font   = load_font("arial.ttf",   15)

    # ── JERSEY NUMBER BADGE ──
    bx, by, bs = 14, 10, 52
    draw.rounded_rectangle([bx, by, bx + bs, by + bs], radius=10, fill=GOLD)
    draw.rounded_rectangle([bx + 3, by + 3, bx + bs - 3, by + bs - 3], radius=7, fill=p_rgb)
    ns  = str(jersey)
    nb  = draw.textbbox((0, 0), ns, font=num_font)
    nw  = nb[2] - nb[0]
    nh  = nb[3] - nb[1]
    draw.text((bx + (bs - nw) // 2, by + (bs - nh) // 2 - 2), ns, font=num_font, fill=GOLD_LIGHT)

    # ── TEAM NAME (top right) ──
    tu = team.upper()
    tb = draw.textbbox((0, 0), tu, font=sub_font)
    draw.text((W - (tb[2] - tb[0]) - 18, 24), tu, font=sub_font, fill=WHITE)

    # ── FACE PHOTO WITH RINGS ──
    face_size  = 240
    face_x_ctr = W // 2
    face_y_top = 82

    # Outer gold glow (soft)
    glow = face_size + 36
    glow_img  = Image.new("RGBA", (glow, glow), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_img)
    for i in range(14):
        a = max(0, 90 - i * 6)
        gd.ellipse([i, i, glow - i, glow - i], outline=(*GOLD_LIGHT, a), width=2)
    card.paste(glow_img, (face_x_ctr - glow // 2, face_y_top - 18), glow_img)

    # Gold ring
    ring = face_size + 14
    ri   = Image.new("RGBA", (ring, ring), (0, 0, 0, 0))
    rd   = ImageDraw.Draw(ri)
    rd.ellipse([0, 0, ring, ring], fill=(*GOLD, 255))
    rd.ellipse([5, 5, ring - 5, ring - 5], fill=(0, 0, 0, 0))
    card.paste(ri, (face_x_ctr - ring // 2, face_y_top - 7), ri)

    # Team-color inner ring
    ir   = face_size + 4
    ii   = Image.new("RGBA", (ir, ir), (0, 0, 0, 0))
    Id   = ImageDraw.Draw(ii)
    Id.ellipse([0, 0, ir, ir], fill=(*p_rgb, 255))
    Id.ellipse([3, 3, ir - 3, ir - 3], fill=(0, 0, 0, 0))
    card.paste(ii, (face_x_ctr - ir // 2, face_y_top - 2), ii)

    # Circular cartoon face
    face_circle = circle_crop(face_cartoon, face_size)
    card.paste(face_circle.convert("RGB"),
               (face_x_ctr - face_size // 2, face_y_top),
               face_circle.split()[3])

    # ── SEPARATOR ──
    sep_y = face_y_top + face_size + 24
    draw.line([(60, sep_y), (W - 60, sep_y)], fill=GOLD, width=2)
    draw.line([(80, sep_y + 4), (W - 80, sep_y + 4)], fill=(*GOLD, 80), width=1)

    # ── PLAYER NAME ──
    pet_u = pet.upper()
    pb    = draw.textbbox((0, 0), pet_u, font=name_font)
    pw    = pb[2] - pb[0]
    name_y = sep_y + 12
    draw.text(((W - pw) // 2 + 2, name_y + 2), pet_u, font=name_font, fill=(0, 0, 0))
    draw.text(((W - pw) // 2, name_y), pet_u, font=name_font, fill=GOLD_LIGHT)

    # ── TEAM SUBTITLE ──
    star_col = s_rgb if max(s_rgb) > 50 else GOLD
    sub_str  = f"★  {team.upper()}  ★"
    sb       = draw.textbbox((0, 0), sub_str, font=sm_font)
    sw       = sb[2] - sb[0]
    draw.text(((W - sw) // 2, name_y + 52), sub_str, font=sm_font, fill=star_col)

    # ── FOOTER BAR ──
    fy = H - 54
    draw.rounded_rectangle([5, fy, W - 5, H - 5], radius=16, fill=p_rgb)
    draw.rounded_rectangle([5, fy, W - 5, fy + 20], radius=16, fill=(*WHITE, 20))

    ftxt = "⚽  FIFA WORLD CUP 2026  ⚽"
    try:
        ft = draw.textbbox((0, 0), ftxt, font=sm_font)
        fw = ft[2] - ft[0]
        draw.text(((W - fw) // 2, fy + 18), ftxt, font=sm_font, fill=(*GOLD_LIGHT, 230))
    except Exception:
        pass

    return card


# ── JERSEY BACK ───────────────────────────────────────────────────────────────
def make_jersey_back(pet, jersey, primary, secondary):
    W, H  = 300, 380
    GOLD  = (212, 175, 55)
    p_rgb = hex_to_rgb(primary)
    s_rgb = hex_to_rgb(secondary)

    img  = Image.new("RGB", (W, H), p_rgb)
    draw = ImageDraw.Draw(img)

    # Jersey stripe texture
    for y in range(0, H, 14):
        lighter = tuple(min(255, c + 18) for c in p_rgb)
        draw.line([(0, y), (W, y)], fill=lighter, width=7)

    # Gold border
    draw.rounded_rectangle([3, 3, W - 3, H - 3], radius=16, outline=GOLD, width=3)

    def load_font(name, size):
        for fn in [name, "arial.ttf"]:
            try:
                return ImageFont.truetype(fn, size)
            except Exception:
                pass
        return ImageFont.load_default()

    big_font  = load_font("arialbd.ttf", 110)
    name_font = load_font("arialbd.ttf", 36)
    tiny_font = load_font("arial.ttf", 16)

    # Number
    ns = str(jersey)
    nb = draw.textbbox((0, 0), ns, font=big_font)
    nw = nb[2] - nb[0]
    draw.text(((W - nw) // 2 + 3, 75 + 3), ns, font=big_font, fill=(0, 0, 0, 80))
    draw.text(((W - nw) // 2, 75), ns, font=big_font,
              fill=s_rgb if max(s_rgb) > 50 else GOLD)

    # Name
    pu = pet.upper()
    pb = draw.textbbox((0, 0), pu, font=name_font)
    pw = pb[2] - pb[0]
    draw.text(((W - pw) // 2, 208), pu, font=name_font, fill=GOLD)

    draw.line([(40, 258), (W - 40, 258)], fill=(*GOLD, 180), width=2)

    ft  = "FIFA WORLD CUP 2026"
    fb  = draw.textbbox((0, 0), ft, font=tiny_font)
    fw  = fb[2] - fb[0]
    draw.text(((W - fw) // 2, 270), ft, font=tiny_font, fill=(*s_rgb[:3], 200))

    return img


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 62)
    print("  FIFA Fantasy 2026 — Cartoon Avatar Generator")
    print(f"  Style: {'Ghibli (stylization + warm grade)' if OPENCV_OK else 'PIL watercolor fallback'}")
    print("=" * 62 + "\n")

    success = 0
    for pet, (team, jersey, primary, secondary, text_col, grad_end) in PLAYERS.items():
        dp_path = find_dp(pet)
        if not dp_path:
            print(f"  ⚠  {pet}: DP not found in {SRC_DIR}")
            print(f"       Expected: *({pet})*.jpg")
            continue

        print(f"  🎨  {pet}  ({team} #{jersey})  ←  {dp_path.name}")
        try:
            face_raw = Image.open(dp_path).convert("RGB")
            # Smart face detection + crop (handles full-body / upper-body shots)
            face_raw = detect_and_crop_face(face_raw)

            face_cartoon = apply_cartoon(face_raw, size=(320, 320))

            card = make_avatar_card(pet, face_cartoon, team, jersey,
                                    primary, secondary, text_col, grad_end)
            p = OUT_DIR / f"{pet.lower()}_avatar.png"
            card.save(p, "PNG", optimize=True)
            print(f"       ✅  {p.name}")

            jersey_card = make_jersey_back(pet, jersey, primary, secondary)
            jp = OUT_DIR / f"{pet.lower()}_jersey_back.png"
            jersey_card.save(jp, "PNG", optimize=True)
            print(f"       ✅  {jp.name}")

            success += 1
        except Exception as e:
            import traceback
            print(f"       ❌  Error: {e}")
            traceback.print_exc()

    print(f"\n{'=' * 62}")
    print(f"  Done: {success}/{len(PLAYERS)} avatars generated → {OUT_DIR}")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
