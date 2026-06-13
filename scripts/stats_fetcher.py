#!/usr/bin/env python3
"""
stats_fetcher.py — FIFA Fantasy 2026: Live Stats Fetcher
Runs every 2 hours via GitHub Actions (stats_updater.yml).

Steps:
  1. update_team_stats    — Group standings → Team Stats tab
  2. update_player_stats  — Top scorers    → Player Stats tab
  3. sync_match_results   — Finished/live matches → Full Schedule (Status, Score A/B)
                            + Match Log (one row per completed match)

poll_bot.py then reads Full Schedule Status=Completed to auto-score players.
"""

import os, sys, json, time, base64, tempfile, logging
from pathlib import Path
from datetime import datetime, timezone

import requests, gspread, pytz
from google.oauth2.service_account import Credentials

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── CONFIG ────────────────────────────────────────────────────────────────────
FOOTBALL_KEY = os.environ.get('FOOTBALL_API_KEY', '')
SHEET_ID     = os.environ.get('GOOGLE_SHEET_ID', '')
GCP_CREDS    = os.environ.get('GOOGLE_CREDENTIALS_JSON', '')
LOCAL_CREDS  = Path(r'C:\Users\siddh\Downloads\HK\FIFA\google_credentials.json')

API_BASE  = 'https://api.football-data.org/v4'
FIFA_COMP = 2000
IST       = pytz.timezone('Asia/Kolkata')
SCOPES    = ['https://www.googleapis.com/auth/spreadsheets']

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# ── TEAM NAME ALIASES (API name → sheet name) ─────────────────────────────────
# football-data.org returns full names; our sheet uses short/variant names.
TEAM_ALIASES = {
    'South Africa':               'S. Africa',
    'United States':              'USA',
    'Korea Republic':             'South Korea',
    'Bosnia and Herzegovina':     'Bosnia-Herz.',
    'Bosnia & Herzegovina':       'Bosnia-Herz.',
    'Turkey':                     'Turkiye',
    'Türkiye':                    'Turkiye',
    'Curacao':                    'Curacao',
    'Côte d\'Ivoire':             'Ivory Coast',
    'Ivory Coast':                'Ivory Coast',
    'Netherlands':                'Netherlands',
    'Czech Republic':             'Czechia',
    'IR Iran':                    'Iran',
    'Korea DPR':                  'North Korea',
    'Trinidad and Tobago':        'Trinidad & Tobago',
    'Central African Republic':   'CAR',
    'DR Congo':                   'DR Congo',
    'Equatorial Guinea':          'Eq. Guinea',
    'New Zealand':                'New Zealand',
    'Saudi Arabia':               'Saudi Arabia',
    'United Arab Emirates':       'UAE',
}

LIVE_STATUSES     = {'IN_PLAY', 'PAUSED', 'EXTRA_TIME', 'PENALTY_SHOOTOUT'}
FINISHED_STATUSES = {'FINISHED', 'AWARDED'}


def normalise(name: str) -> str:
    """Resolve an API team name to the sheet's short name."""
    return TEAM_ALIASES.get(name, name)


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
def connect_sheets():
    if GCP_CREDS:
        creds_dict = json.loads(base64.b64decode(GCP_CREDS.encode()).decode())
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_dict, f)
            creds_path = f.name
        print('  [OK] Credentials loaded from env var')
    elif LOCAL_CREDS.exists():
        creds_path = str(LOCAL_CREDS)
        print('  [OK] Credentials loaded from local file')
    else:
        raise FileNotFoundError('No credentials. Set GOOGLE_CREDENTIALS_JSON env var.')

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    gc    = gspread.authorize(creds)
    sh    = gc.open_by_key(SHEET_ID) if SHEET_ID else gc.open('FIFA World Cup 2026')
    print(f'  [OK] Sheet connected: {sh.title}')
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
    print('Updating team stats...')
    try:
        data = fetch_json(f'{API_BASE}/competitions/{FIFA_COMP}/standings')
    except Exception as e:
        print(f'  [WARN] Could not fetch standings: {e}')
        return

    ws = sh.worksheet('Team Stats')
    ws.clear()
    header = [
        'Team', 'Matches Played', 'W', 'D', 'L', 'GF', 'GA', 'GD', 'Points',
        'Possession %', 'Shots', 'Shots on Target', 'xG', 'Pass Accuracy %',
        'Tackles', 'Interceptions', 'Fouls', 'Corners',
        'Yellow Cards', 'Red Cards', 'Clean Sheets',
        'Penalties Won', 'MOTM Count', 'Saves',
    ]
    rows = [header]
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

    ws.update(values=rows, range_name='A1')
    print(f'  [OK] Team stats: {len(rows)-1} teams')


# ── PLAYER STATS ──────────────────────────────────────────────────────────────
def update_player_stats(sh):
    print('Updating player stats...')
    try:
        data = fetch_json(f'{API_BASE}/competitions/{FIFA_COMP}/scorers?limit=20')
    except Exception as e:
        print(f'  [WARN] Could not fetch scorers: {e}')
        return

    ws = sh.worksheet('Player Stats')
    ws.clear()
    header = [
        'Player', 'Team', 'Matches', 'Goals', 'Assists',
        'Yellow Cards', 'Red Cards', 'Minutes Played',
        'xG', 'Pass Accuracy %', 'Key Passes', 'Dribbles',
        'Fouls Won', 'Shots', 'Shots on Target', 'Match Rating (avg)',
    ]
    rows = [header]
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

    ws.update(values=rows, range_name='A1')
    print(f'  [OK] Player stats: {len(rows)-1} players')


# ── FULL SCHEDULE + MATCH LOG ─────────────────────────────────────────────────
def sync_match_results(sh):
    """
    For every finished or live API match:
      - Update Full Schedule: Status, Score A, Score B
      - Update Match Log: upsert one row per completed match
    Uses header-based column detection so rebuilds don't break column numbers.
    """
    print('Syncing match results...')
    try:
        data        = fetch_json(f'{API_BASE}/competitions/{FIFA_COMP}/matches')
        api_matches = data.get('matches', [])
    except Exception as e:
        print(f'  [WARN] Could not fetch matches: {e}')
        return

    # ── Full Schedule setup ───────────────────────────────────────────────────
    sched_ws  = sh.worksheet('Full Schedule')
    sched_raw = sched_ws.get_all_values()
    if not sched_raw:
        print('  [WARN] Full Schedule is empty')
        return

    sched_header = sched_raw[0]
    try:
        c_match_id = sched_header.index('Match ID')
        c_team_a   = sched_header.index('Team A')
        c_team_b   = sched_header.index('Team B')
        c_status   = sched_header.index('Status')
        c_score_a  = sched_header.index('Score A')
        c_score_b  = sched_header.index('Score B')
    except ValueError as e:
        print(f'  [WARN] Full Schedule missing column: {e}')
        return

    # Build lookup: (normalised_team_a, normalised_team_b) -> (row_index_0based, row_data)
    sched_by_teams = {}
    sched_by_mid   = {}
    for i, row in enumerate(sched_raw[1:], start=1):
        if len(row) <= max(c_team_a, c_team_b, c_match_id):
            continue
        ta  = row[c_team_a].strip()
        tb  = row[c_team_b].strip()
        mid = row[c_match_id].strip()
        sched_by_teams[(ta, tb)] = i
        sched_by_mid[mid]        = i

    # ── Match Log setup ───────────────────────────────────────────────────────
    try:
        log_ws = sh.worksheet('Match Log')
    except gspread.exceptions.WorksheetNotFound:
        log_ws = sh.add_worksheet('Match Log', rows=500, cols=10)

    log_raw    = log_ws.get_all_values()
    log_header = log_raw[0] if log_raw else []
    expected_log_header = [
        'Match ID', 'Group/Stage', 'Date', 'Team A', 'Score A',
        'Score B', 'Team B', 'Venue', 'Result', 'Notes',
    ]
    if log_header != expected_log_header:
        log_ws.update(values=[expected_log_header], range_name='A1')
        log_raw    = log_ws.get_all_values()
        log_header = log_raw[0]

    # Map mid -> row index (1-based, 1=header)
    try:
        lc_mid = log_header.index('Match ID')
    except ValueError:
        lc_mid = 0
    log_row_map = {}
    for i, row in enumerate(log_raw[1:], start=2):
        if row and len(row) > lc_mid:
            log_row_map[row[lc_mid].strip()] = i

    # ── Process each API match ────────────────────────────────────────────────
    sched_updated = 0
    log_added     = 0
    log_updated   = 0
    now_ist       = datetime.now(IST).strftime('%d %b %Y')

    for api_m in api_matches:
        status = api_m.get('status', '')
        if status not in LIVE_STATUSES and status not in FINISHED_STATUSES:
            continue

        api_home = api_m.get('homeTeam', {}).get('name', '')
        api_away = api_m.get('awayTeam', {}).get('name', '')
        home     = normalise(api_home)
        away     = normalise(api_away)

        score_obj  = api_m.get('score', {})
        ft         = score_obj.get('fullTime', {})
        ht         = score_obj.get('halfTime', {})
        if status in FINISHED_STATUSES:
            score_home = ft.get('home')
            score_away = ft.get('away')
        else:
            # Live: show current score (fullTime updates in-play on v4)
            score_home = ft.get('home') if ft.get('home') is not None else ht.get('home')
            score_away = ft.get('away') if ft.get('away') is not None else ht.get('away')

        if score_home is None or score_away is None:
            continue

        sheet_status = 'Completed' if status in FINISHED_STATUSES else 'Live'

        # ── Find matching row in Full Schedule ────────────────────────────────
        sched_row_idx = sched_by_teams.get((home, away))
        if sched_row_idx is None:
            # Try reverse (home/away might be swapped vs sheet order — unlikely but safe)
            sched_row_idx = sched_by_teams.get((away, home))
        if sched_row_idx is None:
            # Fuzzy fallback: partial name match
            for (ta, tb), idx in sched_by_teams.items():
                if (home.lower() in ta.lower() or ta.lower() in home.lower()) and \
                   (away.lower() in tb.lower() or tb.lower() in away.lower()):
                    sched_row_idx = idx
                    break

        if sched_row_idx is None:
            print(f'  [SKIP] No sheet row for: {home} vs {away}')
            continue

        # Sheet rows are 1-based; index 0 = header row (index 1 in raw list)
        sheet_row_num = sched_row_idx + 1  # +1 for header

        # Read the actual Match ID from the sheet row
        sched_data_row = sched_raw[sched_row_idx]
        mid            = sched_data_row[c_match_id].strip() if len(sched_data_row) > c_match_id else ''
        stage          = sched_data_row[sched_header.index('Group/Stage')].strip() \
                         if 'Group/Stage' in sched_header else ''
        venue_col      = sched_header.index('Venue') if 'Venue' in sched_header else -1
        city_col       = sched_header.index('City')  if 'City'  in sched_header else -1
        venue          = sched_data_row[venue_col].strip() if venue_col >= 0 and len(sched_data_row) > venue_col else ''
        city           = sched_data_row[city_col].strip()  if city_col  >= 0 and len(sched_data_row) > city_col  else ''
        venue_full     = f'{venue}, {city}' if city else venue

        # ── Update Full Schedule row ──────────────────────────────────────────
        sched_ws.update_cell(sheet_row_num, c_status  + 1, sheet_status)
        sched_ws.update_cell(sheet_row_num, c_score_a + 1, str(score_home))
        sched_ws.update_cell(sheet_row_num, c_score_b + 1, str(score_away))
        print(f'  [SCHED] {sheet_status}: {home} {score_home}-{score_away} {away}  ({mid})')
        sched_updated += 1

        # ── Update Match Log (completed matches only) ─────────────────────────
        if status not in FINISHED_STATUSES:
            continue

        result_str = f'{home} Win' if score_home > score_away \
                     else (f'{away} Win' if score_away > score_home else 'Draw')

        # Match date from API (UTC → IST)
        utc_date = api_m.get('utcDate', '')
        try:
            dt_utc    = datetime.fromisoformat(utc_date.replace('Z', '+00:00'))
            dt_ist    = dt_utc.astimezone(IST)
            match_date = dt_ist.strftime('%d %b %Y')
        except Exception:
            match_date = now_ist

        log_row = [mid, stage, match_date, home, str(score_home),
                   str(score_away), away, venue_full, result_str, '']

        if mid in log_row_map:
            # Update scores + result; preserve Notes (col 10) if user filled it in
            existing_row_num = log_row_map[mid]
            existing_notes   = ''
            existing_raw     = log_raw[existing_row_num - 1]  # -1 because log_raw is 0-based
            if len(existing_raw) >= 10:
                existing_notes = existing_raw[9]
            log_row[9] = existing_notes  # keep user's notes
            log_ws.update(values=[log_row], range_name=f'A{existing_row_num}')
            print(f'  [LOG-U] Updated: {mid} {home} {score_home}-{score_away} {away}')
            log_updated += 1
        else:
            log_ws.append_row(log_row)
            print(f'  [LOG-A] Added:   {mid} {home} {score_home}-{score_away} {away}')
            log_added += 1

        time.sleep(0.5)  # stay within Sheets API rate limit

    print(f'  [OK] Full Schedule: {sched_updated} row(s) updated')
    print(f'  [OK] Match Log: {log_updated} updated, {log_added} added')


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print(f'\nStats Fetcher running at {datetime.now(IST).strftime("%d %b %Y %H:%M IST")}')

    if not FOOTBALL_KEY:
        print('[WARN] FOOTBALL_API_KEY not set — skipping. Add it to GitHub Secrets.')
        return

    print('Connecting to Google Sheets...')
    sh = connect_sheets()

    update_team_stats(sh)
    time.sleep(2)
    update_player_stats(sh)
    time.sleep(2)
    sync_match_results(sh)

    print('\n[DONE] Stats Fetcher complete')


if __name__ == '__main__':
    main()
