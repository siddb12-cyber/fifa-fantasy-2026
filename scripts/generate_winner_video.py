#!/usr/bin/env python3
"""
generate_winner_video.py — FIFA Fantasy 2026: Winner Announcement Video

Renders a vertical (1080x1920) motion-graphics "reveal" video: countdown from
9th place up to the Champion, matching the dashboard's dark aurora theme.
No browser needed — pure PIL frame rendering + ffmpeg encode (Playwright/
Chromium can't be installed in the build sandbox — network allowlist blocks
the download — so this is the approach that actually works end-to-end).

Data source (in priority order):
  1. --html PATH   : pulls window.LEADERBOARD straight out of a built
                      index.html (same JSON dashboard_builder.py injects) —
                      once the Final is scored + bonus points land, this is
                      the real, live, zero-manual-entry path.
  2. --demo        : built-in placeholder numbers (illustrative only, NOT
                      real standings) so the pipeline can be test-rendered
                      before the tournament is decided.

Requires: pip install pillow   (ffmpeg must be on PATH — https://ffmpeg.org)

Usage:
  python generate_winner_video.py --demo
  python generate_winner_video.py --html "../index.html" --out final_video.mp4

For the fastest possible preview while iterating on the look:
  python generate_winner_video.py --demo --fast
"""
import argparse, json, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── CONFIG ──────────────────────────────────────────────────────────────────
W, H   = 1080, 1920   # override with --scale for fast low-res previews
FPS    = 20            # override with --fps for fast previews
REPO_ROOT   = Path(__file__).resolve().parent.parent          # scripts/ -> repo root
AVATAR_DIR  = REPO_ROOT / 'assets' / 'avatars'                  # same avatars the dashboard uses
OUT_DEFAULT = REPO_ROOT / 'winner_reveal.mp4'

BG        = (6, 6, 15)
PURPLE    = (124, 58, 237)
PURPLE_LT = (167, 139, 250)
GOLD      = (251, 191, 36)
WHITE     = (237, 237, 245)
MUTED     = (140, 140, 160)

# ── FONTS (cross-platform fallback chain) ──────────────────────────────────
# Poppins (Google Font, matches the dashboard's typography) is what this was
# designed and previewed with, but it's NOT bundled with Windows — only
# available where it's been installed (the build sandbox has it via the
# google-fonts package; your Windows machine almost certainly doesn't).
# For the closest match to the preview: install "Poppins" from fonts.google.com
# first. Without it, this automatically falls back to Segoe UI / Arial, which
# still looks clean, just not pixel-identical to the sample video.
FONT_CANDIDATES = {
    'bold':     ['Poppins-Bold.ttf', 'seguibl.ttf', 'segoeuib.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf'],
    'semibold': ['Poppins-SemiBold.ttf', 'Poppins-Bold.ttf', 'segoeuisb.ttf', 'segoeuib.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf'],
    'medium':   ['Poppins-Medium.ttf', 'Poppins-Regular.ttf', 'segoeui.ttf', 'arial.ttf', 'DejaVuSans.ttf'],
    'regular':  ['Poppins-Regular.ttf', 'segoeui.ttf', 'arial.ttf', 'DejaVuSans.ttf'],
}
FONT_SEARCH_DIRS = [
    Path('/usr/share/fonts/truetype/google-fonts'),
    Path('/usr/share/fonts/truetype/dejavu'),
    Path(r'C:\Windows\Fonts'),
    Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'Windows' / 'Fonts',
    Path('/System/Library/Fonts'),
    Path('/Library/Fonts'),
]
_font_warned = set()


@lru_cache(maxsize=None)
def font(weight, size):
    """Cached (dict lookup after first hit) — reloading a TTF from disk per
    glyph draw call was the #1 performance bottleneck in the first draft
    (~5 fps -> ~55 fps after caching fonts + avatars)."""
    for name in FONT_CANDIDATES[weight]:
        for d in FONT_SEARCH_DIRS:
            p = d / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
    for name in FONT_CANDIDATES[weight]:
        try:
            return ImageFont.truetype(name, size)   # let the OS/fontconfig resolve it
        except Exception:
            continue
    if weight not in _font_warned:
        print(f"  ⚠ No font found for weight '{weight}' (tried {FONT_CANDIDATES[weight]}) "
              f"— falling back to PIL's bitmap default, install Poppins for the intended look")
        _font_warned.add(weight)
    return ImageFont.load_default()


F_TITLE   = lambda s=88: font('bold', s)
F_SUB     = lambda s=40: font('medium', s)
F_NAME    = lambda s=54: font('semibold', s)
F_PTS     = lambda s=64: font('bold', s)
F_RANK    = lambda s=46: font('bold', s)
F_SMALL   = lambda s=30: font('regular', s)

PLAYERS_META = {
    'Budhya': 'Sidhant', 'Ambu': 'Kushal', 'Vini': 'Vineet', 'Baby': 'Susmit',
    'Abs': 'Abhishek', 'Anna': 'Nishant', 'Umaga': 'Umang', 'PR': 'Pranav', 'Ash': 'Ashish',
}

DEMO_LEADERBOARD = [
    # Illustrative ONLY — not real standings. Ordered high -> low for demo purposes.
    {'player': 'Budhya', 'pts': 187},
    {'player': 'Anna',   'pts': 171},
    {'player': 'Ash',    'pts': 164},
    {'player': 'Abs',    'pts': 158},
    {'player': 'Baby',   'pts': 149},
    {'player': 'Vini',   'pts': 142},
    {'player': 'Umaga',  'pts': 133},
    {'player': 'Ambu',   'pts': 121},
    {'player': 'PR',     'pts': 108},
]


def load_leaderboard(html_path):
    html = Path(html_path).read_text(encoding='utf-8')
    m = re.search(r'window\.LEADERBOARD\s*\|\|\s*(\[.*?\])', html, re.DOTALL)
    if not m:
        raise RuntimeError(f'window.LEADERBOARD not found in {html_path}')
    data = json.loads(m.group(1))
    data.sort(key=lambda r: -int(r.get('pts', 0)))
    return data


def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def make_bg():
    """Dark radial glow background, matching the dashboard's aurora theme."""
    img = Image.new('RGB', (W, H), BG)
    glow = Image.new('L', (W, H), 0)
    gd = ImageDraw.Draw(glow)
    cx, cy = W // 2, int(H * 0.32)
    for r, alpha in [(900, 10), (650, 18), (420, 28), (240, 40)]:
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=alpha)
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    purple_layer = Image.new('RGB', (W, H), PURPLE)
    img = Image.composite(purple_layer, img, glow)
    return img


def make_circle_crop(path, base_size=420):
    """Expensive part (open the ~1792x2400 source, crop, mask) done ONCE per
    player and cached on the Renderer. Ring is drawn separately per-frame
    (cheap ellipse outline) so the same cached circle works for both the
    purple reveal ring and the gold champion ring without recomputing."""
    im = Image.open(path).convert('RGBA')
    w, h = im.size
    side = min(w, h)
    im = im.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
    im = im.resize((base_size, base_size), Image.LANCZOS)
    mask = Image.new('L', (base_size, base_size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, base_size, base_size], fill=255)
    out = Image.new('RGBA', (base_size, base_size), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def sized_avatar_with_ring(base_circle, size, ring_color, ring_w=8):
    """Cheap per-frame step: resize the small cached circle (not the huge
    source image) and stamp a ring outline on top."""
    av = base_circle.resize((size, size), Image.LANCZOS)
    canvas = Image.new('RGBA', (size + ring_w * 2, size + ring_w * 2), (0, 0, 0, 0))
    canvas.paste(av, (ring_w, ring_w), av)
    rd = ImageDraw.Draw(canvas)
    rd.ellipse([0, 0, size + ring_w * 2 - 1, size + ring_w * 2 - 1], outline=ring_color, width=ring_w)
    return canvas


def text_center(draw, xy, text, fnt, fill, anchor='mm'):
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor)


def rounded_rect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


class Renderer:
    def __init__(self, leaderboard, out_path, demo=False, frames_dir=None):
        self.lb = leaderboard
        self.out_path = Path(out_path)
        self.demo = demo
        self.bg = make_bg()
        # Fresh, unique directory per run — avoids any stale-file cleanup issues.
        self.frames_dir = Path(frames_dir) if frames_dir else Path(tempfile.mkdtemp(prefix='fifa_frames_'))
        self.frames_dir.mkdir(parents=True, exist_ok=True)

        self.avatar_circles = {}   # player -> cached base circle (see make_circle_crop)
        for row in self.lb:
            p = row['player']
            path = AVATAR_DIR / f'{p.lower()}_avatar.png'
            if path.exists():
                self.avatar_circles[p] = make_circle_crop(path)

    def frame(self):
        img = self.bg.copy()
        if self.demo:
            d = ImageDraw.Draw(img)
            d.text((W - 24, 24), 'SAMPLE — placeholder data', font=F_SMALL(26),
                   fill=(255, 140, 140), anchor='ra')
        return img

    def save(self, img, idx):
        img.convert('RGB').save(self.frames_dir / f'frame_{idx:05d}.png')

    # ── Scenes ──────────────────────────────────────────────────────────────
    def scene_intro(self, start_idx, seconds=3.0):
        n = int(FPS * seconds)
        for i in range(n):
            t = i / max(1, n - 1)
            img = self.frame()
            fade = ease_out_cubic(min(1.0, t * 2))
            scale_t = ease_out_cubic(t)
            y = H // 2 - 60 + int((1 - scale_t) * 40)
            alpha = int(255 * fade)
            layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            text_center(ld, (W // 2, y - 70), 'FIFA FANTASY 2026', F_TITLE(64), WHITE + (alpha,))
            text_center(ld, (W // 2, y + 30), 'FINAL RESULTS', F_SUB(46), PURPLE_LT + (alpha,))
            text_center(ld, (W // 2, y + 110), 'who takes the crown?', F_SMALL(30), MUTED + (alpha,))
            img = Image.alpha_composite(img.convert('RGBA'), layer)
            self.save(img, start_idx + i)
        return start_idx + n

    def scene_reveal(self, start_idx, rows, seconds_each=1.6):
        idx = start_idx
        n_each = int(FPS * seconds_each)
        total = len(rows)
        for k, row in enumerate(rows):
            player = row['player']
            pts = int(row.get('pts', 0))
            rank = total - k + 1  # countdown rows exclude champion (#1)
            full = PLAYERS_META.get(player, player)
            base_circle = self.avatar_circles.get(player)
            av_fixed = sized_avatar_with_ring(base_circle, 150, PURPLE_LT) if base_circle else None
            for i in range(n_each):
                t = i / max(1, n_each - 1)
                slide = ease_out_cubic(min(1.0, t * 1.6))
                count_t = ease_in_out(min(1.0, t * 1.3))
                img = self.frame()
                layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                ld = ImageDraw.Draw(layer)

                card_y = H // 2
                offset_x = int((1 - slide) * -500)
                alpha = int(255 * min(1.0, t * 2.2))

                cx = W // 2 + offset_x

                card_w, card_h = 860, 260
                box = [cx - card_w // 2, card_y - card_h // 2, cx + card_w // 2, card_y + card_h // 2]
                rounded_rect(ld, box, 32, fill=(20, 18, 34, min(220, alpha)))
                rounded_rect(ld, box, 32, outline=PURPLE + (alpha,), width=3)

                badge_c = (cx - card_w // 2 + 70, card_y)
                ld.ellipse([badge_c[0] - 46, badge_c[1] - 46, badge_c[0] + 46, badge_c[1] + 46],
                           fill=PURPLE + (alpha,))
                text_center(ld, badge_c, f'#{rank}', F_RANK(40), WHITE + (alpha,))

                if av_fixed:
                    av_pos = (cx - card_w // 2 + 160, card_y - av_fixed.height // 2)
                    a = av_fixed.copy()
                    a.putalpha(a.split()[3].point(lambda p: int(p * alpha / 255)))
                    layer.alpha_composite(a, av_pos)

                name_x = cx - card_w // 2 + 350
                text_center(ld, (name_x, card_y - 40), full, F_NAME(46), WHITE + (alpha,), anchor='lm')
                pts_shown = int(pts * count_t)
                text_center(ld, (name_x, card_y + 35), f'{pts_shown} pts', F_PTS(56), GOLD + (alpha,), anchor='lm')

                img = Image.alpha_composite(img.convert('RGBA'), layer)
                self.save(img, idx)
                idx += 1
        return idx

    def scene_champion(self, start_idx, row, seconds=5.0):
        n = int(FPS * seconds)
        player = row['player']
        pts = int(row.get('pts', 0))
        full = PLAYERS_META.get(player, player)
        base_circle = self.avatar_circles.get(player)
        for i in range(n):
            t = i / max(1, n - 1)
            pop = ease_out_cubic(min(1.0, t * 3))
            img = self.frame()
            layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            alpha = int(255 * min(1.0, t * 3))

            cy = H // 2 - 60
            scale = 0.7 + 0.3 * pop
            av_size = int(320 * scale)
            if base_circle:
                av = sized_avatar_with_ring(base_circle, av_size, GOLD, ring_w=12)
                pos = (W // 2 - av.width // 2, cy - av.height // 2 - 60)
                a = av.copy()
                a.putalpha(a.split()[3].point(lambda p: int(p * alpha / 255)))
                layer.alpha_composite(a, pos)

            text_center(ld, (W // 2, cy + 210), '\U0001F451 CHAMPION \U0001F451', F_SUB(44), GOLD + (alpha,))
            text_center(ld, (W // 2, cy + 280), full, F_TITLE(66), WHITE + (alpha,))
            text_center(ld, (W // 2, cy + 360), f'{pts} pts', F_PTS(58), PURPLE_LT + (alpha,))

            import random
            random.seed(i // 2)
            for _ in range(40):
                x = random.randint(0, W)
                y = random.randint(0, H)
                sz = random.randint(3, 7)
                col = random.choice([GOLD, PURPLE_LT, WHITE])
                ld.ellipse([x, y, x + sz, y + sz], fill=col + (int(alpha * 0.5),))

            img = Image.alpha_composite(img.convert('RGBA'), layer)
            self.save(img, start_idx + i)
        return start_idx + n

    def scene_outro(self, start_idx, seconds=2.5):
        n = int(FPS * seconds)
        for i in range(n):
            t = i / max(1, n - 1)
            alpha = int(255 * ease_out_cubic(t))
            img = self.frame()
            layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            text_center(ld, (W // 2, H // 2 - 20), 'THANKS FOR PLAYING', F_TITLE(56), WHITE + (alpha,))
            text_center(ld, (W // 2, H // 2 + 60), 'FIFA Fantasy 2026', F_SUB(36), PURPLE_LT + (alpha,))
            img = Image.alpha_composite(img.convert('RGBA'), layer)
            self.save(img, start_idx + i)
        return start_idx + n

    def render(self, intro_s=3.0, reveal_s=1.6, champion_s=5.0, outro_s=2.5, keep_frames=False):
        t0 = time.time()
        idx = 0
        idx = self.scene_intro(idx, seconds=intro_s)
        ranked = list(reversed(self.lb))  # lowest rank first for the countdown
        countdown_rows = ranked[:-1]      # everyone except the champion
        champion_row = self.lb[0]
        idx = self.scene_reveal(idx, countdown_rows, seconds_each=reveal_s)
        idx = self.scene_champion(idx, champion_row, seconds=champion_s)
        idx = self.scene_outro(idx, seconds=outro_s)

        print(f'Rendered {idx} frames in {time.time()-t0:.1f}s -> encoding with ffmpeg...')
        subprocess.run([
            'ffmpeg', '-y', '-framerate', str(FPS),
            '-i', str(self.frames_dir / 'frame_%05d.png'),
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18',
            str(self.out_path)
        ], check=True, capture_output=True)
        print(f'✅ Wrote {self.out_path}  ({time.time()-t0:.1f}s total)')
        if not keep_frames:
            shutil.rmtree(self.frames_dir, ignore_errors=True)


def main():
    global W, H, FPS
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', help='Path to a built index.html to pull window.LEADERBOARD from')
    ap.add_argument('--demo', action='store_true', help='Use built-in placeholder data')
    ap.add_argument('--out', default=str(OUT_DEFAULT))
    ap.add_argument('--fps', type=int, default=FPS)
    ap.add_argument('--scale', type=float, default=1.0, help='Resolution multiplier, e.g. 0.4 for a fast low-res preview')
    ap.add_argument('--fast', action='store_true', help='Shorthand for a quick low-res preview: --fps 10 --scale 0.35 and shorter scenes')
    args = ap.parse_args()

    if args.html:
        lb = load_leaderboard(args.html)
        demo = False
    elif args.demo:
        lb = DEMO_LEADERBOARD
        demo = True
    else:
        print('Specify --html PATH (real data) or --demo (placeholder). Defaulting to --demo.')
        lb = DEMO_LEADERBOARD
        demo = True

    FPS = args.fps
    scale = args.scale
    intro_s, reveal_s, champion_s, outro_s = 3.0, 1.6, 5.0, 2.5
    if args.fast:
        FPS = 10
        scale = 0.35
        intro_s, reveal_s, champion_s, outro_s = 1.5, 0.8, 2.0, 1.0

    W = int(1080 * scale)
    H = int(1920 * scale)

    Renderer(lb, args.out, demo=demo).render(
        intro_s=intro_s, reveal_s=reveal_s, champion_s=champion_s, outro_s=outro_s
    )


if __name__ == '__main__':
    main()
