#!/usr/bin/env python3
"""
stats_fetcher.py — FIFA Fantasy 2026: Live Stats Fetcher
Runs every 2 hours via GitHub Actions.
Fetches match/player/team stats from football-data.org free tier.
Updates Google Sheets: Player Stats, Team Stats, Full Schedule (scores).

Works in GitHub Actions (env var credentials) and locally (file credentials).
"""

import os, json, time, base64, tempfile, logging
from pathlib import Path
from datetime import datetime

import requests, gspread, pytz
from google.oauth2.service_account import Credentials

# ── CONFIG — all from GitHub Secrets / env vars ───────────────────────────────
FOOTBALL_KEY = os.environ.get('FOOTBALL_API_KEY', '')
SHEET_ID     = os.environ.get('GOOGLE_SHEET_ID', '')
GCP_CREDS    = os.environ.get('GOOGLE_CREDENTIALS_JSON', '')   # base64-encoded JSON
LOCAL_CREDS  = Path(r'C:\Users\siddh\Downloads\HK\FIFA\google_credentials.json')

API_BASE  = 'https://api.football-data.org/v4'
FIFA_COMP = 2000   # FIFA World Cup competition ID on football-data.org
IST       = pytz.timezone('Asia/Kolkata')
SCOPES    = ['https://www.googleapis.com/auth/spreadsheets']

# Log to stdout (works everywhere — GitHub Actions shows it in run logs)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
log = logging.getLogger(__name__)


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
def connect_sheets():
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
        raise FileNotFoundError('No credentials found. Set GOOGLE_CREDENTIALS_JSON env var.')

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    gc    = gspread.authorize(creds)
    sh    = gc.open_by_key(SHEET_ID) if SHEET_ID else gc.open('FIFA World Cup 2026')
    print(f'  ✅ Sheet connected: {sh.title}')
    return sh


# ── API HELPERS ───────────────────────────────────────────────────────────────
def api_headers():
    return {'X-Auth-Token': FOOTBALL_KEY}


def fetch_json(url):
    resp = requests.get(url, headers=api_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


# ── TEAM STATS ────────────────────────────────────────────────────────────────
def update_team_stats(sh):
    print('📊 Updating team stats...')
    try:
        data = fetch_json(f'{API_BASE}/competitions/{FIFA_COMP}/standings')
    except Exception as e:
        print(f'  ⚠ Could not fetch standings: {e}')
        return

    ws = sh.worksheet('Team Stats')
    ws.clear()
    ws.append_row([
        'Team','Matches Played','W','D','L','GF','GA','GD','Points',
        'Possession %','Shots','Shots on Target','xG','Pass Accuracy %',
        'Tackles','Interceptions','Fouls','Corners','Yellow Cards','Red Cards',
        'Clean Sheets','Penalties Won','MOTM Count','Saves'
    ])

    rows = []
    for group in data.get('standings', []):
        for entry in group.get('table', []):
            team = entry.get('team', {}).get('name', '')
            rows.append([
                team,
                entry.get('playedGames', 0),
                entry.get('won', 0),
                entry.get('draw', 0),
                entry.get('lost', 0),
                entry.get('goalsFor', 0),
                entry.get('goalsAgainst', 0),
                entry.get('goalDifference', 0),
                entry.get('points', 0),
                '—','—','—','—','—','—','—','—','—','—','—','—','—','—','—',
            ])

    if rows:
        ws.append_rows(rows)
        print(f'  ✅ Team stats: {len(rows)} teams updated')
    else:
        print('  ℹ No standings data yet (tournament may not have started)')


# ── PLAYER STATS ──────────────────────────────────────────────────────────────
def update_player_stats(sh):
    print('⚽ Updating player stats...')
    try:
        data = fetch_json(f'{API_BASE}/competitions/{FIFA_COMP}/scorers?limit=20')
    except Exception as e:
        print(f'  ⚠ Could not fetch scorers: {e}')
        return

    ws = sh.worksheet('Player Stats')
    ws.clear()
    ws.append_row([
        'Player','Team','Matches','Goals','Assists','Yellow Cards','Red Cards',
        'Minutes Played','xG','Pass Accuracy %','Key Passes','Dribbles','Fouls Won',
        'Shots','Shots on Target','Match Rating (avg)'
    ])

    rows = []
    for scorer in data.get('scorers', []):
        player = scorer.get('player', {})
        team   = scorer.get('team', {})
        rows.append([
            player.get('name', ''),
            team.get('name', ''),
            scorer.get('playedMatches', 0),
            scorer.get('goals', 0),
            scorer.get('assists', 0) or 0,
            0, 0,
            '—','—','—','—','—','—','—','—','—',
        ])

    if rows:
        ws.append_rows(rows)
        print(f'  ✅ Player stats: {len(rows)} players updated')
    else:
        print('  ℹ No scorer data yet (tournament may not have started)')


# ── MATCH RESULTS SYNC ────────────────────────────────────────────────────────
def sync_match_results(sh):
    """Sync actual scores into Full Schedule for live/completed matches."""
    print('🔄 Syncing match results...')
    try:
        data    = fetch_json(f'{API_BASE}/competitions/{FIFA_COMP}/matches')
        matches = data.get('matches', [])
    except Exception as e:
        print(f'  ⚠ Could not fetch matches: {e}')
        return

    ws       = sh.worksheet('Full Schedule')
    schedule = ws.get_all_records()

    LIVE_STATUSES     = {'IN_PLAY', 'PAUSED', 'EXTRA_TIME', 'PENALTY_SHOOTOUT'}
    FINISHED_STATUSES = {'FINISHED', 'AWARDED'}
    updated = 0

    for api_match in matches:
        status = api_match.get('status', '')
        if status not in LIVE_STATUSES and status not in FINISHED_STATUSES:
            continue

        home = api_match.get('homeTeam', {}).get('name', '')
        away = api_match.get('awayTeam', {}).get('name', '')

        score_obj = api_match.get('score', {})
        sc        = score_obj.get('fullTime', {}) if status in FINISHED_STATUSES \
                    else (score_obj.get('halfTime', {}) or score_obj.get('fullTime', {}))
        score_home = sc.get('home')
        score_away = sc.get('away')
        dash_status = 'Completed' if status in FINISHED_STATUSES else 'Live'

        for i, row in enumerate(schedule):
            ta = row.get('Team A', '')
            tb = row.get('Team B', '')
            if (home in ta or ta in home) and (away in tb or tb in away):
                row_num = i + 2
                ws.update_cell(row_num, 8, dash_status)
                if score_home is not None:
                    ws.update_cell(row_num, 9, score_home)
                    ws.update_cell(row_num, 10, score_away)
                print(f'  ✅ {dash_status}: {ta} {score_home}-{score_away} {tb}')
                updated += 1
                break

    print(f'  ✅ {updated} match result(s) synced')


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print(f'\n⏰ Stats Fetcher running at {datetime.now(IST).strftime("%d %b %Y %H:%M IST")}')

    if not FOOTBALL_KEY:
        print('⚠ FOOTBALL_API_KEY not set — skipping API calls. Add it to GitHub Secrets.')
        return

    print('🔗 Connecting to Google Sheets...')
    sh = connect_sheets()

    update_team_stats(sh)
    time.sleep(2)
    update_player_stats(sh)
    time.sleep(2)
    sync_match_results(sh)

    print('\n✅ Stats Fetcher complete')


if __name__ == '__main__':
    main()
