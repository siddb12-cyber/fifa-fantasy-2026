#!/usr/bin/env python3
"""
dashboard_builder.py — FIFA Fantasy 2026
Reads leaderboard + poll data from Google Sheets and updates HTML dashboard.

Works in two modes:
  GitHub Actions: credentials from GOOGLE_CREDENTIALS_JSON env var (base64)
  Local:          credentials from C:/Users/siddh/Downloads/HK/FIFA/google_credentials.json

Usage:
  python dashboard_builder.py           # build only
  python dashboard_builder.py --deploy  # build + git push (local use)
"""

import os, sys, json, re, base64, tempfile, subprocess
import datetime
from pathlib import Path

import gspread, pytz
from google.oauth2.service_account import Credentials

# ── CONFIG ────────────────────────────────────────────────────────────────────
IST         = pytz.timezone('Asia/Kolkata')
DASH_DIR    = Path(__file__).resolve().parent.parent   # repo root
SHEET_ID    = os.environ.get('GOOGLE_SHEET_ID', '')
GCP_CREDS   = os.environ.get('GOOGLE_CREDENTIALS_JSON', '')  # base64-encoded JSON
LOCAL_CREDS = Path(r'C:\Users\siddh\Downloads\HK\FIFA\google_credentials.json')
SCOPES      = ['https://www.googleapis.com/auth/spreadsheets']

# Player display names (no country/footballer — removed in Session 4)
PLAYERS_META = {
    'Budhya': 'Sidhant Budhkar',
    'Ambu':   'Kushal Ambulkar',
    'Vini':   'Vineet Nayak',
    'Baby':   'Susmit Gulavani',
    'Abs':    'Abhishek Desai',
    'Anna':   'Nishant Salian',
    'Umaga':  'Umang Budhkar',
    'PR':     'Pranav Raut',
}

AVATAR_MAP = {
    p.lower(): f'assets/avatars/{p.lower()}_avatar.png'
    for p in PLAYERS_META
}


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
def connect_sheets():
    """Connect using env var credentials (GitHub Actions) or local file."""
    if GCP_CREDS:
        creds_dict = json.loads(base64.b64decode(GCP_CREDS.encode()).decode())
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_dict, f)
            creds_path = f.name
        print('  ✅ Credentials loaded from env var')
    elif LOCAL_CREDS.exists():
        creds_path = str(LOCAL_CREDS)
        print('  ✅ Credentials loaded from local file')
    else:
        raise FileNotFoundError(
            'No credentials found. Set GOOGLE_CREDENTIALS_JSON env var or place '
            'google_credentials.json at C:/Users/siddh/Downloads/HK/FIFA/'
        )

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    gc    = gspread.authorize(creds)

    if SHEET_ID:
        sh = gc.open_by_key(SHEET_ID)
    else:
        sh = gc.open('FIFA World Cup 2026')

    print(f'  ✅ Sheet connected: {sh.title}')
    return sh


def fetch_leaderboard(sh):
    ws   = sh.worksheet('Leaderboard')
    rows = ws.get_all_records()
    data = []
    for row in rows:
        player = str(row.get('Player', '')).strip()
        if not player:
            continue
        pts     = int(row.get('Total Points', 0) or 0)
        correct = int(row.get('Correct',      0) or 0)
        wrong   = int(row.get('Wrong',        0) or 0)
        missed  = int(row.get('Missed',       0) or 0)
        streak  = str(row.get('Streak',      '—'))
        data.append({
            'rank':    0,           # will be recalculated below
            'player':  player,
            'full':    PLAYERS_META.get(player, player),
            'avatar':  AVATAR_MAP.get(player.lower(), ''),
            'pts':     pts,
            'correct': correct,
            'wrong':   wrong,
            'missed':  missed,
            'streak':  streak,
            'delta':   '0',
        })
    data.sort(key=lambda x: -x['pts'])
    for i, r in enumerate(data):
        r['rank'] = i + 1
    return data


def fetch_poll_responses(sh, match_id):
    """Returns (vote_counts, player_pts) for a given match."""
    ws          = sh.worksheet('Poll Responses')
    rows        = ws.get_all_records()
    vote_counts = {'a': 0, 'draw': 0, 'b': 0}
    player_pts  = []

    for r in rows:
        if str(r.get('Match ID', '')) != match_id:
            continue
        ans = str(r.get('Their Answer', '')).lower()
        if 'draw' in ans:
            vote_counts['draw'] += 1
        elif r.get('Team A', '').lower() in ans or ans.endswith('wins') and 'b' not in ans:
            vote_counts['a'] += 1
        else:
            vote_counts['b'] += 1
        player_pts.append({
            'player': r.get('Player Name', ''),
            'ans':    r.get('Their Answer', ''),
            'pts':    int(r.get('Points Awarded', 0) or 0),
            'avatar': AVATAR_MAP.get(str(r.get('Player Name', '')).lower(), ''),
        })
    return vote_counts, player_pts


def fetch_schedule(sh):
    ws   = sh.worksheet('Full Schedule')
    rows = ws.get_all_records()
    data = []
    for r in rows:
        data.append({
            'id':     r.get('Match ID', ''),
            'stage':  r.get('Group/Stage', ''),
            'date':   r.get('Date (IST)', ''),
            'teamA':  r.get('Team A', ''),
            'teamB':  r.get('Team B', ''),
            'venue':  r.get('Venue', ''),
            'city':   r.get('City', ''),
            'status': r.get('Status', 'Upcoming'),
            'scoreA': r.get('Score A') or None,
            'scoreB': r.get('Score B') or None,
        })
    return data


# ── HTML INJECTION ────────────────────────────────────────────────────────────
def inject_data(html, window_var, data):
    """
    Replace `window.VAR_NAME || [...]` with live data.
    Works regardless of what const variable name the HTML uses.
    e.g. handles both:
      const LB = window.LEADERBOARD || [...]
      const LEADERBOARD = window.LEADERBOARD || [...]
    """
    data_str = json.dumps(data, ensure_ascii=False)
    pattern  = rf'window\.{re.escape(window_var)}\s*\|\|\s*\[.*?\]'
    replace  = f'window.{window_var} || {data_str}'
    new_html, n = re.subn(pattern, replace, html, flags=re.DOTALL)
    if n == 0:
        print(f'  ⚠ Pattern window.{window_var} not found — skipping')
    else:
        print(f'  ✅ Injected window.{window_var} ({len(data)} items)')
    return new_html


def build_index(leaderboard):
    path = DASH_DIR / 'index.html'
    html = path.read_text(encoding='utf-8')
    html = inject_data(html, 'LEADERBOARD', leaderboard)
    path.write_text(html, encoding='utf-8')


def build_stats(leaderboard):
    path = DASH_DIR / 'stats.html'
    if not path.exists():
        return
    html = path.read_text(encoding='utf-8')
    html = inject_data(html, 'LEADERBOARD', leaderboard)
    path.write_text(html, encoding='utf-8')


def build_match_pages(sh, schedule):
    """Generate per-match HTML from template for completed/live matches."""
    template = DASH_DIR / 'match' / 'template.html'
    if not template.exists():
        print('  ⚠ match/template.html not found — skipping match pages')
        return

    tmpl = template.read_text(encoding='utf-8')
    for m in schedule:
        if m['status'] == 'Upcoming':
            continue
        vc, pp = fetch_poll_responses(sh, m['id'])
        match_data = {**m, 'voteCounts': vc, 'playerPoints': pp}
        data_str   = json.dumps(match_data, ensure_ascii=False)
        # Replace window.MATCH_DATA || {...}
        pattern  = r'window\.MATCH_DATA\s*\|\|\s*\{.*?\}'
        replace  = f'window.MATCH_DATA || {data_str}'
        html, n  = re.subn(pattern, replace, tmpl, flags=re.DOTALL)
        if n == 0:
            # Fallback: replace the const MATCH = window.MATCH_DATA || { line
            html = re.sub(
                r'const MATCH = window\.MATCH_DATA \|\| \{',
                f'const MATCH = {data_str};\nconst _unused = {{',
                tmpl
            )
        out = DASH_DIR / 'match' / f'{m["id"]}.html'
        out.write_text(html, encoding='utf-8')
        print(f'  ✅ match/{m["id"]}.html built')


# ── GIT DEPLOY ────────────────────────────────────────────────────────────────
def git_push():
    try:
        os.chdir(DASH_DIR)
        ts = datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')
        subprocess.run(['git', 'config', 'user.name',  'FIFA Fantasy Bot'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'bot@fifa-fantasy-2026.com'], check=True, capture_output=True)
        subprocess.run(['git', 'add', '-A'], check=True, capture_output=True)
        diff = subprocess.run(['git', 'diff', '--cached', '--quiet'])
        if diff.returncode != 0:
            subprocess.run(['git', 'commit', '-m', f'Dashboard update: {ts}'], check=True, capture_output=True)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True, capture_output=True)
            print(f'✅ Pushed to GitHub Pages: {ts}')
        else:
            print('ℹ No changes to push')
    except subprocess.CalledProcessError as e:
        print(f'⚠ Git push failed: {e}')


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print('🔗 Connecting to Google Sheets...')
    sh = connect_sheets()

    print('📊 Fetching data...')
    leaderboard = fetch_leaderboard(sh)
    schedule    = fetch_schedule(sh)

    print('🏗 Building dashboard...')
    build_index(leaderboard)
    build_stats(leaderboard)
    build_match_pages(sh, schedule)

    ts = datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')
    print(f'\n✅ Dashboard rebuilt at {ts}')

    if '--deploy' in sys.argv:
        print('\n📤 Deploying to GitHub Pages...')
        git_push()


if __name__ == '__main__':
    main()
