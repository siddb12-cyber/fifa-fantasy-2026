"""
avatar_generator.py
FIFA Fantasy 2026 — Cartoon Avatar Generator

Reads WhatsApp DP images from:
  C:/Users/siddh/Downloads/HK/FIFA/assets/avatars/
  (filenames like: Sidhant (Sidd).jpg, Kushal (Kushal).jpg, etc.)

Outputs cartoon PNG avatars to:
  C:/Users/siddh/Downloads/HK/FIFA/FIFA World Cup Fantasy Game/assets/avatars/

Also generates animated GIF stubs for celebration / cry / shrug.

Requirements:
  pip install Pillow numpy opencv-python
"""

import os
import re
import glob
import shutil
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── PATHS ─────────────────────────────────────────────────────────────────────
SRC_DIR  = Path(r"C:\Users\siddh\Downloads\HK\FIFA\assets\avatars")
OUT_DIR  = Path(r"C:\Users\siddh\Downloads\HK\FIFA\FIFA World Cup Fantasy Game\assets\avatars")
ANIM_DIR = Path(r"C:\Users\siddh\Downloads\HK\FIFA\FIFA World Cup Fantasy Game\assets\animations")

OUT_DIR.mkdir(parents=True, exist_ok=True)
ANIM_DIR.mkdir(parents=True, exist_ok=True)

# ── PLAYER CONFIG ─────────────────────────────────────────────────────────────
# pet_name → (team, jersey_number, primary_color_hex, secondary_color_hex, celebration_emoji)
PLAYERS = {
    "Budhya": ("Portugal",    7,  "#FF0000", "#FFFFFF", "SIUUU! ✈️"),
    "Ambu":   ("Argentina",   10, "#75AADB", "#FFFFFF", "🙏 Gracias"),
    "Vini":   ("England",     9,  "#FFFFFF", "#CF111A", "⚽ Come On!"),
    "Baby":   ("Spain",       8,  "#AA151B", "#F1BF00", "¡Campeones!"),
    "Abs":    ("Germany",     8,  "#000000", "#FFFFFF", "Danke! 🇩🇪"),
    "Anna":   ("France",      10, "#002395", "#ED2939", "Allez! 🇫🇷"),
    "Umaga":  ("Brazil",      10, "#009C3B", "#FFDF00", "Joga Bonito! 🇧🇷"),
    "PR":     ("Netherlands", 11, "#FF6600", "#FFFFFF", "Oranje! 🇳🇱"),
}

# Filename pattern: "Full Name (PetName).ext"
# or just "PetName.ext"
PET_NAME_RE = re.compile(r'\((\w+)\)', re.IGNORECASE)


def find_dp(pet_name: str) -> Path | None:
    """Find the source WhatsApp DP for a given pet name."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        # Try exact pattern "Full Name (PetName).ext"
        for f in SRC_DIR.glob(f"*({pet_name}).{ext}"):
            return f
        for f in SRC_DIR.glob(f"*({pet_name.lower()}).{ext}"):
            return f
        # Try just "PetName.ext"
        candidate = SRC_DIR / f"{pet_name}.{ext}"
        if candidate.exists():
            return candidate
        candidate = SRC_DIR / f"{pet_name.lower()}.{ext}"
        if candidate.exists():
            return candidate
    # Fuzzy: any file containing the pet name
    for f in SRC_DIR.iterdir():
        if pet_name.lower() in f.stem.lower():
            return f
    return None


def cartoon_filter(img: Image.Image, size=(300, 300)) -> Image.Image:
    """
    Apply a FIFA Ultimate Team cartoon look:
    1. Resize & crop to square
    2. Bilateral-style smooth (multiple box blurs)
    3. Boost saturation & contrast
    4. Subtle edge darken via multiply
    """
    # Crop to square from center
    w, h = img.size
    s    = min(w, h)
    img  = img.crop(((w-s)//2, (h-s)//2, (w+s)//2, (h+s)//2))
    img  = img.resize(size, Image.LANCZOS).convert("RGB")

    # Smooth (simulate bilateral)
    smooth = img
    for _ in range(4):
        smooth = smooth.filter(ImageFilter.SMOOTH_MORE)

    # Boost saturation
    sat = ImageEnhance.Color(smooth)
    smooth = sat.enhance(1.8)

    # Boost contrast
    con = ImageEnhance.Contrast(smooth)
    smooth = con.enhance(1.3)

    # Boost brightness slightly
    bri = ImageEnhance.Brightness(smooth)
    smooth = bri.enhance(1.05)

    return smooth


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_avatar_card(
    face_img: Image.Image,
    pet_name: str,
    team: str,
    jersey_num: int,
    primary: str,
    secondary: str,
    size=(400, 520),
) -> Image.Image:
    """
    Compose a FIFA Ultimate Team card:
    ┌──────────────────────────┐
    │  TEAM    [JerseyNum]     │  ← primary color header
    │  ┌────────────────────┐  │
    │  │   [FACE PHOTO]     │  │  ← cartoon face
    │  └────────────────────┘  │
    │         PET NAME         │  ← secondary color footer
    │         [TEAM]           │
    └──────────────────────────┘
    """
    W, H   = size
    card   = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(card)
    pr     = hex_to_rgb(primary)
    sc     = hex_to_rgb(secondary)

    # ── CARD BACKGROUND ── rounded rectangle
    bg_color = (15, 20, 15, 255)
    draw.rounded_rectangle([(0, 0), (W-1, H-1)], radius=28, fill=bg_color, outline=(*pr, 255), width=4)

    # ── GOLD SHIMMER TOP STRIPE ──
    draw.rounded_rectangle([(4, 4), (W-5, 90)], radius=24, fill=(*pr, 220))

    # ── JERSEY NUMBER (top left) ──
    try:
        font_big  = ImageFont.truetype("arial.ttf", 52)
        font_med  = ImageFont.truetype("arial.ttf", 28)
        font_sm   = ImageFont.truetype("arial.ttf", 22)
        font_name = ImageFont.truetype("arialbd.ttf", 34)
    except OSError:
        font_big  = ImageFont.load_default()
        font_med  = font_big
        font_sm   = font_big
        font_name = font_big

    # Jersey number on header
    num_color = sc if sc != (255, 255, 255) else (255, 215, 0)
    draw.text((20, 10), f"#{jersey_num}", font=font_big, fill=(*num_color, 255))

    # Team name on header (right)
    draw.text((W - 10, 18), team.upper(), font=font_sm, fill=(*sc, 220), anchor="ra")

    # ── FACE CIRCLE ──
    face_size = 240
    face_y    = 95
    face_x    = (W - face_size) // 2

    # Circle background (glow)
    glow_r = face_size // 2 + 8
    glow_x = face_x + face_size // 2
    glow_y = face_y + face_size // 2
    for r_off in range(8, 0, -1):
        alpha = int(80 * (1 - r_off / 8))
        draw.ellipse(
            [glow_x - glow_r - r_off//2, glow_y - glow_r - r_off//2,
             glow_x + glow_r + r_off//2, glow_y + glow_r + r_off//2],
            fill=(*pr, alpha)
        )

    # Mask face to circle
    face_resized = face_img.resize((face_size, face_size), Image.LANCZOS).convert("RGBA")
    mask         = Image.new("L", (face_size, face_size), 0)
    ImageDraw.Draw(mask).ellipse([(0, 0), (face_size, face_size)], fill=255)
    face_circle  = Image.new("RGBA", (face_size, face_size), (0, 0, 0, 0))
    face_circle.paste(face_resized, mask=mask)

    card.paste(face_circle, (face_x, face_y), face_circle)

    # Circle border
    draw.ellipse(
        [face_x - 4, face_y - 4, face_x + face_size + 4, face_y + face_size + 4],
        outline=(*pr, 255), width=4
    )

    # ── FOOTER SECTION ──
    footer_y = face_y + face_size + 18

    # Divider line
    draw.line([(20, footer_y), (W-20, footer_y)], fill=(*pr, 120), width=1)

    # Pet name (large, centered)
    draw.text((W//2, footer_y + 16), pet_name.upper(), font=font_name,
              fill=(255, 215, 0, 255), anchor="mt")

    # Team (smaller, centered)
    draw.text((W//2, footer_y + 58), team, font=font_med,
              fill=(*sc, 200), anchor="mt")

    # FIFA 2026 branding
    draw.text((W//2, H - 22), "FIFA WORLD CUP 2026", font=font_sm,
              fill=(*pr, 160), anchor="ms")

    return card


def make_back_of_jersey(
    pet_name: str,
    jersey_num: int,
    primary: str,
    secondary: str,
    size=(400, 520),
) -> Image.Image:
    """Back of jersey showing pet name + number (for sharing)."""
    W, H = size
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pr   = hex_to_rgb(primary)
    sc   = hex_to_rgb(secondary)

    # Jersey background
    draw.rounded_rectangle([(0, 0), (W-1, H-1)], radius=28, fill=(*pr, 255), outline=(255, 215, 0, 255), width=3)

    # Horizontal collar
    draw.rounded_rectangle([(W//2-60, 10), (W//2+60, 80)], radius=20, fill=(*sc, 200))

    try:
        f_big  = ImageFont.truetype("arialbd.ttf", 80)
        f_name = ImageFont.truetype("arialbd.ttf", 48)
    except OSError:
        f_big  = ImageFont.load_default()
        f_name = f_big

    # Name on back
    draw.text((W//2, 160), pet_name.upper(), font=f_name, fill=(*sc, 255), anchor="mm",
              stroke_width=2, stroke_fill=(*pr, 200))

    # Number on back
    draw.text((W//2, 320), str(jersey_num), font=f_big, fill=(*sc, 255), anchor="mm",
              stroke_width=3, stroke_fill=(*pr, 200))

    return img


def make_celebration_gif(pet_name: str, primary: str, secondary: str) -> list[Image.Image]:
    """Simple 6-frame celebration GIF — avatar bouncing with trophy."""
    frames = []
    pr = hex_to_rgb(primary)
    sc = hex_to_rgb(secondary)
    W, H = 200, 200

    for i in range(6):
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw  = ImageDraw.Draw(frame)

        # Pulsing circle
        r = 80 + (i % 3) * 6
        draw.ellipse([(W//2-r, H//2-r), (W//2+r, H//2+r)], fill=(*pr, 200))

        # Trophy emoji area
        try:
            fnt = ImageFont.truetype("seguiemj.ttf", 60)
        except OSError:
            fnt = ImageFont.load_default()

        # Bounce offset
        y_off = -8 if i % 2 == 0 else 8
        draw.text((W//2, H//2 + y_off), "🏆", font=fnt, anchor="mm")

        # Name
        try:
            fnt_sm = ImageFont.truetype("arial.ttf", 18)
        except OSError:
            fnt_sm = ImageFont.load_default()
        draw.text((W//2, H - 20), pet_name, font=fnt_sm, fill=(*sc, 255), anchor="mm")

        frames.append(frame)
    return frames


def make_cry_gif() -> list[Image.Image]:
    """Simple 4-frame crying animation."""
    frames = []
    W, H = 200, 200
    for i in range(4):
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw  = ImageDraw.Draw(frame)
        draw.ellipse([(60, 40), (140, 120)], fill=(150, 180, 255, 200))
        # Tear drops (animated position)
        ty = 100 + i * 15
        draw.ellipse([(85, ty), (95, ty+20)], fill=(100, 150, 255, 180))
        draw.ellipse([(105, ty-5), (115, ty+15)], fill=(100, 150, 255, 180))
        try:
            fnt = ImageFont.truetype("seguiemj.ttf", 40)
        except OSError:
            fnt = ImageFont.load_default()
        draw.text((W//2, 75), "😢", font=fnt, anchor="mm")
        frames.append(frame)
    return frames


def make_shrug_gif() -> list[Image.Image]:
    """Simple 4-frame shrug animation."""
    frames = []
    W, H = 200, 200
    for i in range(4):
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw  = ImageDraw.Draw(frame)
        draw.ellipse([(60, 30), (140, 110)], fill=(180, 160, 140, 200))
        try:
            fnt = ImageFont.truetype("seguiemj.ttf", 50)
        except OSError:
            fnt = ImageFont.load_default()
        # Shrug alternates
        emoji = "🤷" if i % 2 == 0 else "🤷‍♂️"
        draw.text((W//2, 140), emoji, font=fnt, anchor="mm")
        frames.append(frame)
    return frames


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("=== FIFA Fantasy 2026 — Avatar Generator ===\n")

    # List source images
    print(f"Looking for DPs in: {SRC_DIR}")
    src_files = list(SRC_DIR.iterdir()) if SRC_DIR.exists() else []
    print(f"Found {len(src_files)} files: {[f.name for f in src_files]}\n")

    generated = []
    skipped   = []

    for pet_name, (team, jersey_num, primary, secondary, cel) in PLAYERS.items():
        print(f"Processing {pet_name} ({team} #{jersey_num})...")

        dp_path = find_dp(pet_name)
        if dp_path is None:
            print(f"  ⚠️  No DP found for {pet_name} — generating placeholder")
            # Create a colored placeholder face
            face = Image.new("RGB", (300, 300), hex_to_rgb(primary))
            draw = ImageDraw.Draw(face)
            try:
                fnt = ImageFont.truetype("arial.ttf", 60)
            except OSError:
                fnt = ImageFont.load_default()
            draw.text((150, 150), pet_name[0].upper(), font=fnt,
                      fill=hex_to_rgb(secondary), anchor="mm")
        else:
            print(f"  ✅ Found DP: {dp_path.name}")
            face = Image.open(dp_path).convert("RGB")
            face = cartoon_filter(face, size=(300, 300))

        # Front card avatar
        card = make_avatar_card(face, pet_name, team, jersey_num, primary, secondary)
        out_front = OUT_DIR / f"{pet_name.lower()}_avatar.png"
        card.save(out_front, "PNG")
        print(f"  💾 Saved: {out_front.name}")

        # Back of jersey
        back = make_back_of_jersey(pet_name, jersey_num, primary, secondary)
        out_back = OUT_DIR / f"{pet_name.lower()}_jersey_back.png"
        back.save(out_back, "PNG")

        generated.append(pet_name)

        # ── ANIMATED GIFs ──
        # Celebration
        cel_frames = make_celebration_gif(pet_name, primary, secondary)
        cel_path   = ANIM_DIR / f"{pet_name.lower()}_celebrate.gif"
        cel_frames[0].save(
            cel_path, save_all=True, append_images=cel_frames[1:],
            duration=200, loop=0, format="GIF"
        )

        print(f"  🎉 Celebration GIF: {cel_path.name}")

    # Shared cry GIF
    cry_frames = make_cry_gif()
    cry_path   = ANIM_DIR / "cry.gif"
    cry_frames[0].save(cry_path, save_all=True, append_images=cry_frames[1:], duration=250, loop=0)
    print(f"\n😢 Cry GIF saved: {cry_path.name}")

    # Shared shrug GIF
    shrug_frames = make_shrug_gif()
    shrug_path   = ANIM_DIR / "shrug.gif"
    shrug_frames[0].save(shrug_path, save_all=True, append_images=shrug_frames[1:], duration=300, loop=0)
    print(f"🤷 Shrug GIF saved: {shrug_path.name}")

    print(f"\n=== Done! ===")
    print(f"✅ Generated: {generated}")
    if skipped:
        print(f"⚠️  Skipped:   {skipped}")
    print(f"\nAvatars saved to: {OUT_DIR}")
    print(f"Animations saved to: {ANIM_DIR}")


if __name__ == "__main__":
    main()
