"""
FIFA 2026 Fantasy — Gemini AI Avatar Generator
Generates cartoon-style FIFA player cards using Google Gemini Imagen.
Run this on your Windows machine: python scripts/generate_avatars_gemini.py

Requires: pip install google-genai pillow
API key must be set as GEMINI_API_KEY environment variable.
"""

import os, sys, json, base64, io, time, socket
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Force IPv4 — fixes HuggingFace SSL/connection failures on Windows (IPv6 DNS issue)
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
AV_DIR   = BASE_DIR / "assets" / "avatars"
AV_DIR.mkdir(parents=True, exist_ok=True)

CARD_W, CARD_H = 500, 700

# ── Player prompts ──────────────────────────────────────────────────────────
BASE_STYLE = (
    "anime style football player, cel-shaded, vibrant saturated colors, "
    "clean smooth shading, expressive face, dynamic pose, waist-up portrait, "
    "FIFA World Cup stadium bokeh background with colorful lights, "
    "high quality anime illustration, sharp detailed artwork"
)

NEGATIVE = (
    "numbers, digits, text, letters, jersey number, shirt number, "
    "words, typography, 3 arms, extra limbs, deformed hands, ugly, "
    "realistic photo, blurry, low quality, watermark, signature"
)

PLAYERS = [
    {
        "pet":    "Budhya",
        "team":   "Portugal",
        "jersey": 7,
        "pri":    "#C8102E",
        "sec":    "#006600",
        "prompt": f"{BASE_STYLE}. Wearing plain crimson red jersey with dark green collar (no text on chest). Heroic celebration, arms raised, glowing red and green stadium lights behind.",
    },
    {
        "pet":    "Ambu",
        "team":   "Argentina",
        "jersey": 10,
        "pri":    "#74ACDF",
        "sec":    "#FFFFFF",
        "prompt": f"{BASE_STYLE}. Wearing plain sky blue and white striped jersey (no text on chest). Pointing to the sky, euphoric grin, blue and white confetti swirling around.",
    },
    {
        "pet":    "Vini",
        "team":   "England",
        "jersey": 9,
        "pri":    "#CF111A",
        "sec":    "#FFFFFF",
        "prompt": f"{BASE_STYLE}. Wearing plain white jersey with red trim (no text on chest). Fierce determined look, jaw clenched, white and red stadium flares glowing behind.",
    },
    {
        "pet":    "Baby",
        "team":   "Spain",
        "jersey": 6,
        "pri":    "#AA151B",
        "sec":    "#F1BF00",
        "prompt": f"{BASE_STYLE}. Wearing plain deep red jersey with yellow collar (no text on chest). Wide joyful laugh, eyes sparkling, red and gold fireworks exploding behind.",
    },
    {
        "pet":    "Abs",
        "team":   "Germany",
        "jersey": 8,
        "pri":    "#1C1C1C",
        "sec":    "#E8C84A",
        "prompt": f"{BASE_STYLE}. Wearing plain black jersey with gold trim (no text on chest). Cool collected smirk, one eyebrow raised, dramatic gold stadium spotlights behind.",
    },
    {
        "pet":    "Anna",
        "team":   "France",
        "jersey": 11,
        "pri":    "#002395",
        "sec":    "#ED2939",
        "prompt": f"{BASE_STYLE}. Wearing plain navy blue jersey with red collar (no text on chest). Explosive celebration roar, blue white red tricolor lights behind.",
    },
    {
        "pet":    "Umaga",
        "team":   "Brazil",
        "jersey": 1,
        "pri":    "#009C3B",
        "sec":    "#FFDF00",
        "prompt": f"{BASE_STYLE}. Wearing plain bright yellow jersey with green collar (no text on chest). Huge beaming smile, samba energy, yellow and green carnival lights behind.",
    },
    {
        "pet":    "PR",
        "team":   "Netherlands",
        "jersey": 4,
        "pri":    "#E8641A",
        "sec":    "#FFFFFF",
        "prompt": f"{BASE_STYLE}. Wearing plain vivid orange jersey with white collar (no text on chest). Passionate battle cry, fist pumped up high, sea of orange stadium lights behind.",
    },
]

# ── Font ────────────────────────────────────────────────────────────────────
def get_font(size, bold=True):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

# ── Card frame overlay ───────────────────────────────────────────────────────
def add_card_frame(ai_image: Image.Image, player: dict) -> Image.Image:
    """Wrap the AI-generated image in a minimal FIFA card frame."""
    def hex_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    pri = hex_rgb(player["pri"])
    sec = hex_rgb(player["sec"])

    # Resize AI image to fill upper 70% of card
    ai_h = int(CARD_H * 0.72)
    ai_img = ai_image.resize((CARD_W, ai_h), Image.LANCZOS)

    # Card canvas
    card = Image.new("RGB", (CARD_W, CARD_H), (12, 14, 22))
    card.paste(ai_img, (0, 0))

    draw = ImageDraw.Draw(card)

    # Bottom info panel gradient
    panel_y = ai_h
    for y in range(panel_y, CARD_H):
        t = (y - panel_y) / max(CARD_H - panel_y - 1, 1)
        r = int(pri[0] * (1 - t) + 12 * t)
        g = int(pri[1] * (1 - t) + 14 * t)
        b = int(pri[2] * (1 - t) + 22 * t)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))

    # Divider line
    draw.line([(0, panel_y), (CARD_W, panel_y)], fill=sec, width=4)

    # Jersey number badge (left)
    badge_x, badge_y = 52, panel_y + 55
    draw.ellipse([badge_x - 42, badge_y - 42, badge_x + 42, badge_y + 42],
                 fill=sec, outline=(255, 255, 255), width=3)
    num_str  = str(player["jersey"])
    num_font = get_font(42, bold=True)
    num_bbox = num_font.getbbox(num_str)
    nw = num_bbox[2] - num_bbox[0]
    nh = num_bbox[3] - num_bbox[1]
    # Determine text color for contrast
    lum = 0.299 * sec[0] + 0.587 * sec[1] + 0.114 * sec[2]
    num_col = (20, 20, 20) if lum > 160 else (255, 255, 255)
    draw.text((badge_x - nw // 2 - num_bbox[0], badge_y - nh // 2 - num_bbox[1]),
              num_str, font=num_font, fill=num_col)

    # Player pet name
    name_x = 112
    name_font = get_font(52, bold=True)
    # Shadow
    draw.text((name_x + 2, panel_y + 18 + 2), player["pet"].upper(), font=name_font, fill=(0, 0, 0))
    draw.text((name_x, panel_y + 18), player["pet"].upper(), font=name_font, fill=(255, 255, 255))

    # Team name
    team_font = get_font(20, bold=False)
    lum2 = 0.299 * sec[0] + 0.587 * sec[1] + 0.114 * sec[2]
    team_col = sec if lum2 > 50 else (220, 220, 220)
    draw.text((name_x, panel_y + 82), player["team"].upper(), font=team_font, fill=team_col)

    # Accent line
    draw.line([(name_x, panel_y + 108), (CARD_W - 20, panel_y + 108)], fill=sec, width=2)

    # FIFA 2026 watermark
    wm_font  = get_font(13, bold=False)
    wm_str   = "FIFA WORLD CUP 2026™"
    wm_bbox  = wm_font.getbbox(wm_str)
    wm_w     = wm_bbox[2] - wm_bbox[0]
    draw.text((CARD_W - wm_w - 14, CARD_H - 26), wm_str, font=wm_font, fill=(180, 180, 180))

    # Outer border
    border = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(border)
    bd.rounded_rectangle([2, 2, CARD_W - 3, CARD_H - 3], radius=18,
                          fill=None, outline=sec + (210,), width=5)
    bd.rounded_rectangle([9, 9, CARD_W - 10, CARD_H - 10], radius=13,
                          fill=None, outline=pri + (90,), width=2)
    card.paste(border, (0, 0), border)

    return card


# ── Image generation via Stability AI ─────────────────────────────────────────
STABILITY_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"

def generate_image(prompt: str, api_key: str = None) -> Image.Image:
    """Generate via Stability AI Core — 3 credits/image, real negative prompts."""
    import requests as req_lib

    key = os.environ.get("STABILITY_KEY", api_key or "").strip()
    r = req_lib.post(
        STABILITY_URL,
        headers={"Authorization": f"Bearer {key}", "Accept": "image/*"},
        files={"none": ""},
        data={
            "prompt":          prompt,
            "negative_prompt": NEGATIVE,
            "aspect_ratio":    "2:3",
            "output_format":   "png",
            "style_preset":    "anime",
            "seed":            abs(hash(prompt)) % 2147483647,
        },
        timeout=60,
    )
    if r.status_code == 200:
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    raise RuntimeError(f"Stability AI {r.status_code}: {r.text[:200]}")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    api_key = os.environ.get("STABILITY_KEY", "").strip()
    if not api_key:
        for ep in [BASE_DIR.parent / ".env", BASE_DIR / ".env"]:
            if ep.exists():
                for line in ep.read_text().splitlines():
                    if line.startswith("STABILITY_KEY"):
                        api_key = line.split("=", 1)[-1].strip().strip('"').strip("'")
                        break
            if api_key:
                break
    if not api_key:
        print("ERROR: STABILITY_KEY not set.")
        sys.exit(1)
    print("Using Stability AI Core (comic-book style preset)")

    print("FIFA 2026 Fantasy — Gemini Avatar Generator")
    print("=" * 45)
    print(f"Saving cards to: {AV_DIR}\n")

    for i, player in enumerate(PLAYERS):
        pet = player["pet"]
        print(f"[{i+1}/8] Generating {pet} ({player['team']} #{player['jersey']})...", end=" ", flush=True)
        try:
            ai_img = generate_image(player["prompt"], api_key)
            out    = AV_DIR / f"{pet.lower()}_avatar.png"
            ai_img.save(out, "PNG")
            print(f"DONE -> {out.name}")
        except Exception as e:
            print(f"FAILED: {e}")

        # Pause between requests (HF rate limit)
        if i < len(PLAYERS) - 1:
            time.sleep(3)

    print("\nAll done!")


if __name__ == "__main__":
    main()
