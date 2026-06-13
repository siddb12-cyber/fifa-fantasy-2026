#!/usr/bin/env python3
"""
update_schedule.py — FIFA Fantasy 2026
Updates Full Schedule (scores + status) and Match Log in Google Sheets
with real match results sourced from live web data.

Run locally: python scripts/update_schedule.py
"""
import os, sys, json, base64, tempfile, datetime
import gspread
from pathlib import Path
from google.oauth2.service_account import Credentials
import pytz

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# -- CONFIG -------------------------------------------------------------------
BASE_DIR   = Path(r"C:\Users\siddh\Downloads\HK\FIFA")
CREDS_PATH = BASE_DIR / "google_credentials.json"

# Also support base64-encoded env var (GitHub Actions style)
GCP_CREDS_B64 = os.environ.get('GOOGLE_CREDENTIALS_JSON', '')
SHEET_ID       = os.environ.get('GOOGLE_SHEET_ID', '18SfYYXYaGxvh-2bZIq_h4dOXfS7YtD5c49nW454MY2o')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
IST    = pytz.timezone('Asia/Kolkata')

# -- CONFIRMED RESULTS (sourced June 13 2026) ---------------------------------
# Format: match_id -> {score_a, score_b, team_a, team_b, stage, date, venue, city, notes}
RESULTS = {
    'M001': {
        'score_a': 2, 'score_b': 0,
        'team_a': 'Mexico', 'team_b': 'S. Africa',
        'stage': 'Group A', 'date': '11 Jun 2026',
        'venue': 'Estadio Azteca', 'city': 'Mexico City',
        'notes': "Quinones 9', Jimenez 2H. Mexico dominant opener.",
    },
    'M002': {
        'score_a': 2, 'score_b': 1,
        'team_a': 'South Korea', 'team_b': 'Czechia',
        'stage': 'Group A', 'date': '11 Jun 2026',
        'venue': 'Estadio Akron', 'city': 'Zapopan',
        'notes': "Krejci 1-0 (header). Hwang In-beom equalised. Son winner late.",
    },
    'M007': {
        'score_a': 1, 'score_b': 1,
        'team_a': 'Canada', 'team_b': 'Bosnia-Herz.',
        'stage': 'Group B', 'date': '12 Jun 2026',
        'venue': 'BMO Field', 'city': 'Toronto',
        'notes': "Lukic 21' (Bosnia). Larin 78' (Canada). Canada's first WC point.",
    },
    'M019': {
        'score_a': 4, 'score_b': 1,
        'team_a': 'USA', 'team_b': 'Paraguay',
        'stage': 'Group D', 'date': '12 Jun 2026',
        'venue': 'SoFi Stadium', 'city': 'Los Angeles',
        'notes': "Bobadilla OG 6', Pulisic 30', Balogun 45', Mauricio 72' (Par), Reyna 90+5'. USMNT dominant.",
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


def update_full_schedule(sh):
    """Update Status, Score A, Score B for completed matches."""
    ws = sh.worksheet('Full Schedule')
    rows = ws.get_all_values()
    header = rows[0]

    try:
        col_id     = header.index('Match ID') + 1
        col_status = header.index('Status') + 1
        col_sa     = header.index('Score A') + 1
        col_sb     = header.index('Score B') + 1
    except ValueError as e:
        print(f"  [WARN] Missing column in Full Schedule: {e}")
        print(f"  Headers found: {header}")
        return

    updated = 0
    for i, row in enumerate(rows[1:], start=2):
        if not row or not row[0]:
            continue
        mid = row[col_id - 1].strip()
        if mid in RESULTS:
            r = RESULTS[mid]
            ws.update_cell(i, col_status, 'Completed')
            ws.update_cell(i, col_sa,     str(r['score_a']))
            ws.update_cell(i, col_sb,     str(r['score_b']))
            print(f"  [OK] {mid}: {r['team_a']} {r['score_a']}-{r['score_b']} {r['team_b']}")
            updated += 1

    print(f"\n  Full Schedule: {updated} match(es) updated.")


def update_match_log(sh):
    """Upsert entries in the Match Log tab — update existing rows, add missing ones."""
    try:
        ws = sh.worksheet('Match Log')
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet('Match Log', rows=500, cols=10)
        ws.append_row(['Match ID', 'Stage', 'Date', 'Team A', 'Score A',
                       'Score B', 'Team B', 'Venue', 'Result', 'Notes'])
        print("  [INFO] Created Match Log tab")

    all_values = ws.get_all_values()
    header = all_values[0] if all_values else []

    try:
        mid_col = header.index('Match ID')
    except ValueError:
        mid_col = 0

    # Map match_id -> sheet row number (1-based)
    row_map = {}
    for i, row in enumerate(all_values[1:], start=2):
        if row and len(row) > mid_col:
            row_map[row[mid_col].strip()] = i

    # Ensure correct header
    expected_cols = ['Match ID', 'Stage', 'Date', 'Team A', 'Score A',
                     'Score B', 'Team B', 'Venue', 'Result', 'Notes']
    if header != expected_cols:
        ws.update('A1', [expected_cols])

    added = updated = 0
    for mid, r in RESULTS.items():
        sa, sb = r['score_a'], r['score_b']
        ta, tb = r['team_a'], r['team_b']
        result = f"{ta} Win" if sa > sb else (f"{tb} Win" if sb > sa else "Draw")

        new_row = [
            mid, r['stage'], r['date'],
            ta, str(sa), str(sb), tb,
            f"{r['venue']}, {r['city']}",
            result, r['notes']
        ]

        if mid in row_map:
            row_num = row_map[mid]
            ws.update(f'A{row_num}', [new_row])
            print(f"  [UPDATE] row {row_num}: {mid} {ta} {sa}-{sb} {tb}")
            updated += 1
        else:
            ws.append_row(new_row)
            print(f"  [ADD]    {mid}: {ta} {sa}-{sb} {tb} ({result})")
            added += 1

    print(f"\n  Match Log: {updated} updated, {added} added.")


def main():
    gc = connect()
    sh = gc.open_by_key(SHEET_ID)

    print("\n--- Updating Full Schedule ---")
    update_full_schedule(sh)

    print("\n--- Updating Match Log ---")
    update_match_log(sh)

    print("\n[DONE] All updates complete.")


if __name__ == '__main__':
    main()
