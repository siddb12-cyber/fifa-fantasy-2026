#!/usr/bin/env python3
"""
setup_bonus_tab.py — FIFA Fantasy 2026: One-time Bonus Questions setup

Creates a "Bonus Answers" tab and populates it with each player's picks for
the 5 end-of-tournament bonus questions (each worth +10 pts, added once after
the Final). Layout is two blocks in the same tab so the scoring logic in
poll_bot.py (fetch_bonus_points) can find both by header text:

  Block 1 (row 1 header): Player | WC Winner | Golden Ball | Golden Boot | Golden Glove | Golden Playmaker
    -> one row per player, their picks

  Block 2 (a few rows down, header "Question" | "Correct Answer"):
    -> 5 rows, one per question, Correct Answer left BLANK until the
       tournament is over. Bonus scoring stays inert (adds 0 pts) until
       ALL 5 are filled in — see fetch_bonus_points() in poll_bot.py.

Run ONCE, locally (this machine can reach Google's API; the sandbox can't):
  python scripts/setup_bonus_tab.py            # creates + populates
  python scripts/setup_bonus_tab.py --force    # overwrite if tab already exists

Filling in the 5 correct answers later: just edit the "Correct Answer"
column in the sheet directly (Google Sheets, by hand) once the tournament
is decided — no script needed for that part. The next poll_bot.py run will
pick them up automatically.
"""
import os
import sys
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

# ── CONFIG ──────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent.parent
CREDS_PATH  = REPO_ROOT / 'google_credentials.json'
SHEET_ID_FILE = REPO_ROOT / 'logs' / 'sheet_id.txt'
SHEET_ID    = os.environ.get('GOOGLE_SHEET_ID', '').strip()
if not SHEET_ID and SHEET_ID_FILE.exists():
    SHEET_ID = SHEET_ID_FILE.read_text(encoding='utf-8').strip()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

TAB_NAME = 'Bonus Answers'

QUESTIONS = [
    'WC Winner',
    'Golden Ball',
    'Golden Boot',
    'Golden Glove',
    'Golden Playmaker',
]

# Picks transcribed from the screenshot shared 2026-07-03, mapped to the
# same nicknames used everywhere else in the sheet (PLAYERS_ALL / PLAYERS_META).
# NOTE: Vini's Golden Boot pick is written "Mbpape" in the source screenshot —
# left as-is here (not silently corrected). If that's a typo for Mbappé,
# fix it directly in the sheet before results are filled in, otherwise it
# will score as a literal (non-matching) answer.
PLAYER_ANSWERS = [
    # Player,  WC Winner,  Golden Ball,        Golden Boot,   Golden Glove,     Golden Playmaker
    ['Budhya', 'Portugal', 'Bruno Fernandes',  'Harry Kane',  'Mike Maignan',   'Bruno Fernandes'],
    ['Ambu',   'France',   'Olise',            'Mbappe',      'Alisson',        'Olise'],
    ['PR',     'Spain',    'Olise',            'Mbappe',      'David Raya',     'Olise'],
    ['Abs',    'France',   'Mbappe',           'Mbappe',      'Maignan',        'Messi'],
    ['Vini',   'France',   'Mbappe',           'Mbpape',      'Pickford',       'Lamine Yamal'],
    ['Baby',   'Portugal', 'Cristiano Ronaldo','Mbappe',      'Diogo Costa',    'Bruno Fernandes'],
    ['Umaga',  'Portugal', 'Rodri',            'Olise',       'Pickford',       'Bruno Fernandes'],
    ['Anna',   'Spain',    'Lamine Yamal',     'Mbappe',      'Unai Simon',     'Bruno Fernandes'],
    ['Ash',    'Spain',    'Lamine Yamal',     'Kylian Mbappe','Unai Simon',    'Lamine Yamal'],
]


def connect_sheets():
    if not SHEET_ID:
        sys.exit('❌ No GOOGLE_SHEET_ID env var and logs/sheet_id.txt not found.')
    if not CREDS_PATH.exists():
        sys.exit(f'❌ Credentials file not found at {CREDS_PATH}')
    creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    print(f'✅ Connected: {sh.title}')
    return sh


def build_rows():
    rows = [['Player'] + QUESTIONS]
    rows.extend(PLAYER_ANSWERS)
    rows.append([''] * (len(QUESTIONS) + 1))          # blank separator row
    rows.append(['Question', 'Correct Answer'])
    for q in QUESTIONS:
        rows.append([q, ''])                            # blank — fill in after the Final
    return rows


def main():
    force = '--force' in sys.argv
    sh = connect_sheets()

    try:
        ws = sh.worksheet(TAB_NAME)
        if not force:
            sys.exit(
                f"⚠ '{TAB_NAME}' tab already exists — refusing to overwrite "
                f"(you may have already filled in Correct Answers).\n"
                f"   Re-run with --force only if you're sure you want to wipe and recreate it."
            )
        print(f"⚠ --force set: clearing existing '{TAB_NAME}' tab")
        ws.clear()
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(TAB_NAME, rows=30, cols=6)
        print(f"✅ Created '{TAB_NAME}' tab")

    rows = build_rows()
    ws.update(values=rows, range_name='A1')
    print(f'✅ Wrote {len(PLAYER_ANSWERS)} player rows + 5-question Correct Answer block')
    print('\nNext step: once the tournament is decided, fill in the "Correct Answer" '
          'column (rows below the "Question" header) directly in Google Sheets. '
          'poll_bot.py will automatically add +10 pts per correct pick to each '
          "player's leaderboard total on its next run — nothing else to run.")


if __name__ == '__main__':
    main()
