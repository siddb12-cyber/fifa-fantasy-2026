"""
dashboard_builder.py
FIFA World Cup 2026 Fantasy — GitHub Pages Dashboard Builder

Fetches latest data from Google Sheets and rebuilds the static HTML pages.
Run after every match result. Optionally commits & pushes to GitHub Pages.

Usage:
  python dashboard_builder.py              # build only
  python dashboard_builder.py --deploy     # build + git push
  python dashboard_builder.py --demo       # inject demo data
"""

import os
import sys
import json
import shutil
import logging
import subprocess
from pathlib import Path
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
import pytz

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(r"C:\Users\siddh\Downloads\HK\FIFA")
DASH_DIR    = BASE_DIR / "FIFA World Cup Fantasy Game"
SCRIPTS_DIR = DASH_DIR / "scripts"
CREDS_PATH  = BASE_DIR / "google_credentials.json"
SHEET_NAME  = "FIFA World Cup 2026"
IST         = pytz.timezone("Asia/Kolkata")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

PLAYERS_META = {
    "Budhya": {"team":"Portugal",    "flag":"🇵🇹","jersey":7,  "star":"C. Ronaldo", "full":"Sidhant Budhkar"},
    "Ambu":   {"team":"Argentina",   "flag":"🇦🇷","jersey":10, "star":"L. Messi",   "full":"Kushal Ambulkar"},
    "Vini":   {"team":"England",     "flag":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","jersey":9,  "star":"H. Kane",   "full":"Vineet Nayak"},
    "Baby":   {"team":"Spain",       "flag":"🇪🇸","jersey":8,  "star":"Pedri",      "full":"Susmit Gulavani"},
    "Abs":    {"team":"Germany",     "flag":"🇩🇪","jersey":8,  "star":"J. Musiala", "full":"Abhishek Desai"},
    "Anna":   {"team":"France",      "flag":"🇫🇷","jersey":10, "star":"K. Mbappé",  "full":"Nishant Salian"},
    "Umaga":  {"team":"Brazil",      "flag":"🇧🇷","jersey":10, "star":"Vinicius Jr","full":"Umang Budhkar"},
    "PR":     {"team":"Netherlands", "flag":"🇳🇱","jersey":11, "star":"X. Simons",  "full":"Pranav Raut"},
}

log_path = BASE_DIR / "logs" / "dashboard_builder.log"
log_path.parent.mkdir(parents=True, exist_ok=True)   # create logs dir if missing
logging.basicConfig(
    filename=str(log_path), level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
def get_sheet():
    creds  = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME)


def fetch_leaderboard(sh):
    ws   = sh.worksheet("Leaderboard")
    rows = ws.get_all_records()
    result = []
    for row in rows:
        player = row.get("Player", "")
        meta   = PLAYERS_META.get(player, {})
        pts    = int(row.get("Total Points", 0))
        result.append({
            "rank":    int(row.get("Rank", 0)),
            "player":  player,
            "team":    meta.get("team", row.get("Team", "")),
            "flag":    meta.get("flag", "🏳️"),
            "jersey":  meta.get("jersey", 0),
            "star":    meta.get("star", ""),
            "pts":     pts,
            "correct": int(row.get("Correct", 0)),
            "wrong":   int(row.get("Wrong", 0)),
            "missed":  int(row.get("Missed", 0)),
            "streak":  row.get("Streak", "—"),
            "delta":   "0",
        })
    # Re-sort by pts descending
    result.sort(key=lambda x: -x["pts"])
    for i, r in enumerate(result):
        r["rank"] = i + 1
    return result


def fetch_schedule(sh):
    ws   = sh.worksheet("Full Schedule")
    rows = ws.get_all_records()
    FLAG_MAP = {
        "Portugal":"🇵🇹","Argentina":"🇦🇷","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Spain":"🇪🇸",
        "Germany":"🇩🇪","France":"🇫🇷","Brazil":"🇧🇷","Netherlands":"🇳🇱",
        "Mexico":"🇲🇽","USA":"🇺🇸","Canada":"🇨🇦","Morocco":"🇲🇦",
        "Japan":"🇯🇵","South Korea":"🇰🇷","Saudi Arabia":"🇸🇦","Australia":"🇦🇺",
        "TBD":"🏳️","??":"🏳️",
    }
    schedule = []
    for r in rows:
        schedule.append({
            "id":     r["Match ID"],
            "stage":  r["Group/Stage"],
            "date":   r["Date (IST)"],
            "teamA":  r["Team A"],
            "teamB":  r["Team B"],
            "flagA":  FLAG_MAP.get(r["Team A"],"🏳️"),
            "flagB":  FLAG_MAP.get(r["Team B"],"🏳️"),
            "venue":  r["Venue"],
            "city":   r["City"],
            "status": r.get("Status","Upcoming"),
            "scoreA": r.get("Score A") or None,
            "scoreB": r.get("Score B") or None,
        })
    return schedule


def fetch_poll_responses(sh, match_id):
    ws   = sh.worksheet("Poll Responses")
    rows = ws.get_all_records()
    vote_counts = {"a": 0, "draw": 0, "b": 0}
    player_pts  = []

    for r in rows:
        if r["Match ID"] != match_id:
            continue
        ans = str(r.get("Their Answer","")).lower()
        if "draw" in ans:
            vote_counts["draw"] += 1
        elif r.get("Team A","").lower() in ans:
            vote_counts["a"] += 1
        else:
            vote_counts["b"] += 1
        player_pts.append({
            "player": r["Player Name"],
            "ans":    r["Their Answer"],
            "pts":    int(r.get("Points Awarded", 0)),
        })
    return vote_counts, player_pts


# ── INJECT DATA INTO HTML ─────────────────────────────────────────────────────
def inject_js_var(html: str, var_name: str, data) -> str:
    """Replace `window.VAR_NAME || [...]` with live data."""
    import re
    pattern = rf"(const\s+{var_name}\s*=\s*)window\.{var_name}\s*\|\|\s*\[.*?\];"
    replacement = f"\\1{json.dumps(data, ensure_ascii=False)};"
    new_html, count = re.subn(pattern, replacement, html, flags=re.DOTALL)
    if count == 0:
        log.warning(f"Could not inject {var_name} — pattern not found")
    return new_html


def build_index(leaderboard):
    src_path = DASH_DIR / "index.html"
    html     = src_path.read_text(encoding="utf-8")
    html     = inject_js_var(html, "LEADERBOARD", leaderboard)
    src_path.write_text(html, encoding="utf-8")
    log.info("index.html updated")


def build_schedule(schedule):
    src_path = DASH_DIR / "schedule.html"
    html     = src_path.read_text(encoding="utf-8")
    html     = inject_js_var(html, "SCHEDULE", schedule)
    src_path.write_text(html, encoding="utf-8")
    log.info("schedule.html updated")


def build_match_page(match, vote_counts, player_pts):
    """Generate a match-specific HTML page from the template."""
    template_path = DASH_DIR / "match" / "template.html"
    out_path      = DASH_DIR / "match" / f"{match['id']}.html"
    html          = template_path.read_text(encoding="utf-8")

    match_data = {
        **match,
        "voteCounts":   vote_counts,
        "playerPoints": player_pts,
    }
    html = html.replace(
        "const MATCH = window.MATCH_DATA || {",
        f"const MATCH = {json.dumps(match_data, ensure_ascii=False)};\nconst _unused = {{"
    )
    out_path.write_text(html, encoding="utf-8")
    log.info(f"match/{match['id']}.html generated")


def build_all_match_pages(sh, schedule):
    for match in schedule:
        vc, pp = fetch_poll_responses(sh, match["id"])
        build_match_page(match, vc, pp)


# ── DEMO MODE ─────────────────────────────────────────────────────────────────
DEMO_LEADERBOARD = [
    {"rank":1,"player":"Budhya","team":"Portugal",    "flag":"🇵🇹","jersey":7, "star":"C. Ronaldo","pts":9, "correct":3,"wrong":0,"missed":0,"streak":"🔥🔥🔥","delta":"+1"},
    {"rank":2,"player":"Anna",  "team":"France",      "flag":"🇫🇷","jersey":10,"star":"K. Mbappé", "pts":6, "correct":2,"wrong":1,"missed":0,"streak":"🔥🔥","delta":"+2"},
    {"rank":3,"player":"Ambu",  "team":"Argentina",   "flag":"🇦🇷","jersey":10,"star":"L. Messi",  "pts":6, "correct":2,"wrong":1,"missed":0,"streak":"🔥","delta":"-1"},
    {"rank":4,"player":"Vini",  "team":"England",     "flag":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","jersey":9, "star":"H. Kane",  "pts":3, "correct":1,"wrong":2,"missed":0,"streak":"—","delta":"0"},
    {"rank":5,"player":"Baby",  "team":"Spain",       "flag":"🇪🇸","jersey":8, "star":"Pedri",     "pts":3, "correct":1,"wrong":1,"missed":1,"streak":"—","delta":"0"},
    {"rank":6,"player":"Abs",   "team":"Germany",     "flag":"🇩🇪","jersey":8, "star":"J. Musiala","pts":0, "correct":0,"wrong":1,"missed":2,"streak":"🧊","delta":"-1"},
    {"rank":7,"player":"Umaga", "team":"Brazil",      "flag":"🇧🇷","jersey":10,"star":"Vinicius Jr","pts":-2,"correct":0,"wrong":1,"missed":1,"streak":"🧊🧊","delta":"0"},
    {"rank":8,"player":"PR",    "team":"Netherlands", "flag":"🇳🇱","jersey":11,"star":"X. Simons", "pts":-4,"correct":0,"wrong":0,"missed":2,"streak":"🧊🧊🧊","delta":"-1"},
]

DEMO_MATCH = {
    "id":"DEMO","stage":"Demo Match","date":"15 Jun 2026 04:00",
    "teamA":"Portugal","teamB":"Argentina","flagA":"🇵🇹","flagB":"🇦🇷",
    "venue":"MetLife Stadium","city":"East Rutherford, NJ",
    "status":"Completed","scoreA":2,"scoreB":1,
    "voteCounts":{"a":5,"draw":1,"b":2},
    "playerPoints":[
        {"player":"Budhya","ans":"Portugal","pts":3},
        {"player":"Anna",  "ans":"Portugal","pts":3},
        {"player":"Vini",  "ans":"Portugal","pts":3},
        {"player":"Ambu",  "ans":"Argentina","pts":0},
        {"player":"Baby",  "ans":"Draw","pts":0},
        {"player":"Abs",   "ans":"Argentina","pts":0},
        {"player":"Umaga", "ans":"MISSED","pts":-2},
        {"player":"PR",    "ans":"MISSED","pts":-2},
    ],
}


def run_demo():
    """Inject demo data into pages and generate demo match page."""
    log.info("Running in DEMO mode")
    build_index(DEMO_LEADERBOARD)

    # Build demo match page
    build_match_page(DEMO_MATCH, DEMO_MATCH["voteCounts"], DEMO_MATCH["playerPoints"])

    ts = datetime.now(IST).strftime("%d %b %Y %H:%M IST")
    print(f"✅ Demo dashboard built at {ts}")
    print(f"   index.html    → Updated with demo leaderboard")
    print(f"   match/DEMO.html → Demo match: Portugal 2-1 Argentina")


# ── GIT DEPLOY ────────────────────────────────────────────────────────────────
def git_push():
    """Commit and push dashboard to GitHub Pages."""
    try:
        os.chdir(DASH_DIR)
        ts = datetime.now(IST).strftime("%d %b %Y %H:%M IST")
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Dashboard update: {ts}"], check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
        log.info(f"Git push successful: {ts}")
        print(f"✅ Pushed to GitHub Pages: {ts}")
    except subprocess.CalledProcessError as e:
        log.error(f"Git push failed: {e.stderr.decode()}")
        print(f"⚠️  Git push failed: {e.stderr.decode()}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    deploy = "--deploy" in sys.argv
    demo   = "--demo"   in sys.argv

    if demo:
        run_demo()
        if deploy:
            git_push()
        return

    log.info("=== Dashboard Builder Started ===")
    try:
        sh = get_sheet()
    except Exception as e:
        log.error(f"Could not connect to Google Sheets: {e}")
        print(f"❌ Google Sheets connection failed: {e}")
        sys.exit(1)

    leaderboard = fetch_leaderboard(sh)
    schedule    = fetch_schedule(sh)

    build_index(leaderboard)
    build_schedule(schedule)
    build_all_match_pages(sh, schedule)

    ts = datetime.now(IST).strftime("%d %b %Y %H:%M IST")
    log.info(f"Dashboard rebuilt: {ts}")
    print(f"✅ Dashboard rebuilt: {ts}")

    if deploy:
        git_push()


if __name__ == "__main__":
    main()
