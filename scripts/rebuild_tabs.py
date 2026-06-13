#!/usr/bin/env python3
"""
rebuild_tabs.py — FIFA Fantasy 2026
Wipes and rebuilds Full Schedule and Match Log tabs from scratch.

Full Schedule: rebuilt from matches.json (all 104 matches), completed matches get scores.
Match Log:     rebuilt with only confirmed completed matches + their results.

Run locally: python scripts/rebuild_tabs.py
"""
import os, sys, json, base64, tempfile
from pathlib import Path
from google.oauth2.service_account import Credentials
import gspread

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# -- CONFIG -------------------------------------------------------------------
BASE_DIR   = Path(r"C:\Users\siddh\Downloads\HK\FIFA")
CREDS_PATH = BASE_DIR / "google_credentials.json"
GCP_CREDS_B64 = os.environ.get('GOOGLE_CREDENTIALS_JSON', '')
SHEET_ID       = os.environ.get('GOOGLE_SHEET_ID', '18SfYYXYaGxvh-2bZIq_h4dOXfS7YtD5c49nW454MY2o')
MATCHES_JSON   = Path(__file__).parent / 'matches.json'

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# -- CONFIRMED RESULTS --------------------------------------------------------
RESULTS = {
    'M001': {
        'score_a': 2, 'score_b': 0,
        'date': '11 Jun 2026',
        'venue_full': 'Estadio Azteca, Mexico City',
        'notes': "Quinones 9', Jimenez 2H. Mexico dominant opener.",
    },
    'M002': {
        'score_a': 2, 'score_b': 1,
        'date': '11 Jun 2026',
        'venue_full': 'Estadio Akron, Zapopan',
        'notes': "Krejci 1-0 (header). Hwang equalised. Son winner late.",
    },
    'M007': {
        'score_a': 1, 'score_b': 1,
        'date': '12 Jun 2026',
        'venue_full': 'BMO Field, Toronto',
        'notes': "Lukic 21' (Bosnia). Larin 78' (Canada). Canada's first WC point.",
    },
    'M019': {
        'score_a': 4, 'score_b': 1,
        'date': '12 Jun 2026',
        'venue_full': 'SoFi Stadium, Los Angeles',
        'notes': "Bobadilla OG 6', Pulisic 30', Balogun 45', Mauricio 72' (Par), Reyna 90+5'.",
    },
}


def connect():
    if GCP_CREDS_B64:
        creds_dict = json.loads(base64.b64decode(GCP_CREDS_B64.encode()).decode())
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_dict, f)
            creds_path = f.name
    elif CREDS_PATH.exists():
        creds_path = str(CREDS_PATH)
    else:
        raise FileNotFoundError(f"No credentials found at {CREDS_PATH}")

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    gc = gspread.authorize(creds)
    print("[OK] Connected to Google Sheets")
    return gc


def rebuild_full_schedule(sh, matches):
    print("\n--- Rebuilding Full Schedule ---")
    ws = sh.worksheet('Full Schedule')

    # Wipe everything
    ws.clear()
    print("  [CLEARED] Full Schedule wiped")

    # Header
    header = [
        'Match ID', 'Group/Stage', 'Date (IST)', 'Kickoff (IST)',
        'Team A', 'Team B', 'Venue', 'City',
        'Status', 'Score A', 'Score B',
        'Poll Posted', 'Poll Closed'
    ]

    rows = [header]

    for m in matches:
        mid = m['id']
        r   = RESULTS.get(mid, {})

        # Parse datetime_ist into date + time parts
        dt_str = m.get('datetime_ist', '')
        parts  = dt_str.rsplit(' ', 1)          # e.g. "12 Jun 2026 22:30" -> ["12 Jun 2026", "22:30"]
        date_part = parts[0] if len(parts) == 2 else dt_str
        time_part = parts[1] if len(parts) == 2 else ''

        if r:
            status  = 'Completed'
            score_a = str(r['score_a'])
            score_b = str(r['score_b'])
        else:
            status  = 'Upcoming'
            score_a = ''
            score_b = ''

        rows.append([
            mid,
            m.get('stage', ''),
            date_part,
            time_part,
            m.get('team_a', ''),
            m.get('team_b', ''),
            m.get('venue', ''),
            m.get('city', ''),
            status,
            score_a,
            score_b,
            '',   # Poll Posted
            '',   # Poll Closed
        ])

    ws.update(values=rows, range_name='A1')
    print(f"  [OK] Written {len(rows)-1} match rows + header")

    # Bold the header row
    try:
        ws.format('A1:M1', {'textFormat': {'bold': True}})
    except Exception:
        pass

    completed = sum(1 for m in matches if m['id'] in RESULTS)
    upcoming  = len(matches) - completed
    print(f"  [OK] {completed} Completed, {upcoming} Upcoming")


def rebuild_match_log(sh, matches):
    print("\n--- Rebuilding Match Log ---")
    ws = sh.worksheet('Match Log')

    # Wipe everything
    ws.clear()
    print("  [CLEARED] Match Log wiped")

    header = [
        'Match ID', 'Group/Stage', 'Date', 'Team A', 'Score A',
        'Score B', 'Team B', 'Venue', 'Result', 'Notes'
    ]

    # Build match lookup: id -> match info from matches.json
    match_map = {m['id']: m for m in matches}

    rows = [header]
    for mid, r in RESULTS.items():
        m  = match_map.get(mid, {})
        sa = r['score_a']
        sb = r['score_b']
        ta = m.get('team_a', '')
        tb = m.get('team_b', '')
        result = f"{ta} Win" if sa > sb else (f"{tb} Win" if sb > sa else "Draw")

        rows.append([
            mid,
            m.get('stage', ''),
            r['date'],
            ta, str(sa), str(sb), tb,
            r['venue_full'],
            result,
            r['notes'],
        ])

    ws.update(values=rows, range_name='A1')
    print(f"  [OK] Written {len(rows)-1} completed match row(s) + header")

    try:
        ws.format('A1:J1', {'textFormat': {'bold': True}})
    except Exception:
        pass


def main():
    with open(MATCHES_JSON) as f:
        matches = json.load(f)
    print(f"[INFO] Loaded {len(matches)} matches from matches.json")

    gc = connect()
    sh = gc.open_by_key(SHEET_ID)

    rebuild_full_schedule(sh, matches)
    rebuild_match_log(sh, matches)

    print("\n[DONE] Both tabs rebuilt successfully.")


if __name__ == '__main__':
    main()
