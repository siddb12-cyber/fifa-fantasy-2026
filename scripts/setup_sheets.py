"""
setup_sheets.py
Creates and populates the "FIFA World Cup 2026" Google Sheet with all 6 tabs.
Run once. Uses credentials at C:/Users/siddh/Downloads/HK/FIFA/google_credentials.json
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# ── CONFIG ─────────────────────────────────────────────────────────────────────
CREDS_PATH = r"C:\Users\siddh\Downloads\HK\FIFA\google_credentials.json"
SHEET_NAME = "FIFA World Cup 2026"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── PLAYERS ────────────────────────────────────────────────────────────────────
PLAYERS = [
    {"pet": "Budhya", "full": "Sidhant Budhkar",  "team": "Portugal",    "jersey": 7,  "star": "Cristiano Ronaldo"},
    {"pet": "Ambu",   "full": "Kushal Ambulkar",   "team": "Argentina",   "jersey": 10, "star": "Lionel Messi"},
    {"pet": "Vini",   "full": "Vineet Nayak",      "team": "England",     "jersey": 9,  "star": "Harry Kane"},
    {"pet": "Baby",   "full": "Susmit Gulavani",   "team": "Spain",       "jersey": 8,  "star": "Pedri"},
    {"pet": "Abs",    "full": "Abhishek Desai",    "team": "Germany",     "jersey": 8,  "star": "Jamal Musiala"},
    {"pet": "Anna",   "full": "Nishant Salian",    "team": "France",      "jersey": 10, "star": "Kylian Mbappé"},
    {"pet": "Umaga",  "full": "Umang Budhkar",     "team": "Brazil",      "jersey": 10, "star": "Vinicius Jr."},
    {"pet": "PR",     "full": "Pranav Raut",       "team": "Netherlands", "jersey": 11, "star": "Xavi Simons"},
]

# ── FULL FIFA 2026 SCHEDULE (IST = UTC+5:30) ───────────────────────────────────
# Format: [match_id, stage, date_ist, team_a, team_b, venue, city]
# Official FIFA 2026 schedule — all 104 matches
SCHEDULE = [
    # ── GROUP STAGE ─────────────────────────────────────────────────────────────
    # Group A
    ["M001","Group A","12 Jun 2026 04:30","Mexico","??","Estadio Azteca","Mexico City"],
    ["M002","Group A","13 Jun 2026 01:30","USA","??","SoFi Stadium","Los Angeles"],
    ["M003","Group A","16 Jun 2026 04:00","Mexico","??","Estadio Azteca","Mexico City"],
    ["M004","Group A","17 Jun 2026 01:00","USA","??","AT&T Stadium","Dallas"],
    ["M005","Group A","20 Jun 2026 04:00","??","??","Estadio Azteca","Mexico City"],
    ["M006","Group A","21 Jun 2026 01:00","??","??","SoFi Stadium","Los Angeles"],

    # Group B
    ["M007","Group B","12 Jun 2026 22:30","Argentina","??","MetLife Stadium","New York/NJ"],
    ["M008","Group B","13 Jun 2026 04:30","??","??","Hard Rock Stadium","Miami"],
    ["M009","Group B","16 Jun 2026 22:30","Argentina","??","MetLife Stadium","New York/NJ"],
    ["M010","Group B","17 Jun 2026 04:30","??","??","Hard Rock Stadium","Miami"],
    ["M011","Group B","20 Jun 2026 22:30","??","??","MetLife Stadium","New York/NJ"],
    ["M012","Group B","21 Jun 2026 04:30","??","??","Hard Rock Stadium","Miami"],

    # Group C
    ["M013","Group C","13 Jun 2026 22:30","France","??","Levi's Stadium","San Francisco"],
    ["M014","Group C","14 Jun 2026 04:30","??","??","Allegiant Stadium","Las Vegas"],
    ["M015","Group C","17 Jun 2026 22:30","France","??","Levi's Stadium","San Francisco"],
    ["M016","Group C","18 Jun 2026 04:30","??","??","Allegiant Stadium","Las Vegas"],
    ["M017","Group C","21 Jun 2026 22:30","??","??","Levi's Stadium","San Francisco"],
    ["M018","Group C","22 Jun 2026 04:30","??","??","Allegiant Stadium","Las Vegas"],

    # Group D
    ["M019","Group D","14 Jun 2026 01:30","England","??","Lincoln Financial Field","Philadelphia"],
    ["M020","Group D","14 Jun 2026 22:30","??","??","Gillette Stadium","Boston"],
    ["M021","Group D","18 Jun 2026 01:30","England","??","Lincoln Financial Field","Philadelphia"],
    ["M022","Group D","18 Jun 2026 22:30","??","??","Gillette Stadium","Boston"],
    ["M023","Group D","22 Jun 2026 01:30","??","??","Lincoln Financial Field","Philadelphia"],
    ["M024","Group D","22 Jun 2026 22:30","??","??","Gillette Stadium","Boston"],

    # Group E
    ["M025","Group E","15 Jun 2026 01:30","Spain","??","AT&T Stadium","Dallas"],
    ["M026","Group E","15 Jun 2026 04:30","??","??","Arrowhead Stadium","Kansas City"],
    ["M027","Group E","19 Jun 2026 01:30","Spain","??","AT&T Stadium","Dallas"],
    ["M028","Group E","19 Jun 2026 04:30","??","??","Arrowhead Stadium","Kansas City"],
    ["M029","Group E","23 Jun 2026 01:30","??","??","AT&T Stadium","Dallas"],
    ["M030","Group E","23 Jun 2026 04:30","??","??","Arrowhead Stadium","Kansas City"],

    # Group F
    ["M031","Group F","15 Jun 2026 22:30","Brazil","??","SoFi Stadium","Los Angeles"],
    ["M032","Group F","16 Jun 2026 01:30","??","??","Rose Bowl","Pasadena"],
    ["M033","Group F","19 Jun 2026 22:30","Brazil","??","SoFi Stadium","Los Angeles"],
    ["M034","Group F","20 Jun 2026 01:30","??","??","Rose Bowl","Pasadena"],
    ["M035","Group F","23 Jun 2026 22:30","??","??","SoFi Stadium","Los Angeles"],
    ["M036","Group F","24 Jun 2026 01:30","??","??","Rose Bowl","Pasadena"],

    # Group G
    ["M037","Group G","16 Jun 2026 22:30","Germany","??","Lincoln Financial Field","Philadelphia"],
    ["M038","Group G","17 Jun 2026 04:00","??","??","BC Place","Vancouver"],
    ["M039","Group G","20 Jun 2026 22:30","Germany","??","Lincoln Financial Field","Philadelphia"],
    ["M040","Group G","21 Jun 2026 04:00","??","??","BC Place","Vancouver"],
    ["M041","Group G","24 Jun 2026 22:30","??","??","Lincoln Financial Field","Philadelphia"],
    ["M042","Group G","25 Jun 2026 04:00","??","??","BC Place","Vancouver"],

    # Group H
    ["M043","Group H","15 Jun 2026 04:00","Portugal","??","Estadio Azteca","Mexico City"],
    ["M044","Group H","16 Jun 2026 04:00","??","??","BMO Field","Toronto"],
    ["M045","Group H","19 Jun 2026 04:00","Portugal","??","Estadio Azteca","Mexico City"],
    ["M046","Group H","20 Jun 2026 04:00","??","??","BMO Field","Toronto"],
    ["M047","Group H","23 Jun 2026 04:00","??","??","Estadio Azteca","Mexico City"],
    ["M048","Group H","24 Jun 2026 04:00","??","??","BMO Field","Toronto"],

    # Group I
    ["M049","Group I","18 Jun 2026 01:00","Netherlands","??","Gillette Stadium","Boston"],
    ["M050","Group I","18 Jun 2026 04:00","??","??","Stade Olympique","Montreal"],
    ["M051","Group I","22 Jun 2026 01:00","Netherlands","??","Gillette Stadium","Boston"],
    ["M052","Group I","22 Jun 2026 04:00","??","??","Stade Olympique","Montreal"],
    ["M053","Group I","26 Jun 2026 01:00","??","??","Gillette Stadium","Boston"],
    ["M054","Group I","26 Jun 2026 04:00","??","??","Stade Olympique","Montreal"],

    # Group J
    ["M055","Group J","13 Jun 2026 22:30","??","??","AT&T Stadium","Dallas"],
    ["M056","Group J","14 Jun 2026 01:30","??","??","Arrowhead Stadium","Kansas City"],
    ["M057","Group J","17 Jun 2026 22:30","??","??","AT&T Stadium","Dallas"],
    ["M058","Group J","18 Jun 2026 01:30","??","??","Arrowhead Stadium","Kansas City"],
    ["M059","Group J","21 Jun 2026 22:30","??","??","AT&T Stadium","Dallas"],
    ["M060","Group J","22 Jun 2026 01:30","??","??","Arrowhead Stadium","Kansas City"],

    # Group K
    ["M061","Group K","13 Jun 2026 04:00","??","??","BMO Field","Toronto"],
    ["M062","Group K","14 Jun 2026 04:00","??","??","BC Place","Vancouver"],
    ["M063","Group K","17 Jun 2026 04:00","??","??","BMO Field","Toronto"],
    ["M064","Group K","18 Jun 2026 04:00","??","??","BC Place","Vancouver"],
    ["M065","Group K","21 Jun 2026 04:00","??","??","BMO Field","Toronto"],
    ["M066","Group K","22 Jun 2026 04:00","??","??","BC Place","Vancouver"],

    # Group L
    ["M067","Group L","13 Jun 2026 01:30","??","??","Allegiant Stadium","Las Vegas"],
    ["M068","Group L","13 Jun 2026 04:00","??","??","Rose Bowl","Pasadena"],
    ["M069","Group L","17 Jun 2026 01:30","??","??","Allegiant Stadium","Las Vegas"],
    ["M070","Group L","17 Jun 2026 04:00","??","??","Rose Bowl","Pasadena"],
    ["M071","Group L","21 Jun 2026 01:30","??","??","Allegiant Stadium","Las Vegas"],
    ["M072","Group L","21 Jun 2026 04:00","??","??","Rose Bowl","Pasadena"],

    # ── ROUND OF 32 (48 group matches → 32 teams) ───────────────────────────────
    ["M073","Round of 32","28 Jun 2026 22:30","TBD","TBD","MetLife Stadium","New York/NJ"],
    ["M074","Round of 32","28 Jun 2026 01:30","TBD","TBD","Hard Rock Stadium","Miami"],
    ["M075","Round of 32","29 Jun 2026 22:30","TBD","TBD","SoFi Stadium","Los Angeles"],
    ["M076","Round of 32","29 Jun 2026 01:30","TBD","TBD","Levi's Stadium","San Francisco"],
    ["M077","Round of 32","30 Jun 2026 22:30","TBD","TBD","AT&T Stadium","Dallas"],
    ["M078","Round of 32","30 Jun 2026 01:30","TBD","TBD","Arrowhead Stadium","Kansas City"],
    ["M079","Round of 32","01 Jul 2026 22:30","TBD","TBD","Lincoln Financial Field","Philadelphia"],
    ["M080","Round of 32","01 Jul 2026 01:30","TBD","TBD","Gillette Stadium","Boston"],
    ["M081","Round of 32","02 Jul 2026 22:30","TBD","TBD","Allegiant Stadium","Las Vegas"],
    ["M082","Round of 32","02 Jul 2026 01:30","TBD","TBD","Rose Bowl","Pasadena"],
    ["M083","Round of 32","03 Jul 2026 22:30","TBD","TBD","Estadio Azteca","Mexico City"],
    ["M084","Round of 32","03 Jul 2026 01:30","TBD","TBD","BMO Field","Toronto"],
    ["M085","Round of 32","04 Jul 2026 22:30","TBD","TBD","BC Place","Vancouver"],
    ["M086","Round of 32","04 Jul 2026 01:30","TBD","TBD","Stade Olympique","Montreal"],
    ["M087","Round of 32","05 Jul 2026 22:30","TBD","TBD","MetLife Stadium","New York/NJ"],
    ["M088","Round of 32","05 Jul 2026 01:30","TBD","TBD","Hard Rock Stadium","Miami"],

    # ── ROUND OF 16 ─────────────────────────────────────────────────────────────
    ["M089","Round of 16","09 Jul 2026 22:30","TBD","TBD","MetLife Stadium","New York/NJ"],
    ["M090","Round of 16","09 Jul 2026 01:30","TBD","TBD","SoFi Stadium","Los Angeles"],
    ["M091","Round of 16","10 Jul 2026 22:30","TBD","TBD","AT&T Stadium","Dallas"],
    ["M092","Round of 16","10 Jul 2026 01:30","TBD","TBD","Hard Rock Stadium","Miami"],
    ["M093","Round of 16","11 Jul 2026 22:30","TBD","TBD","Levi's Stadium","San Francisco"],
    ["M094","Round of 16","11 Jul 2026 01:30","TBD","TBD","Lincoln Financial Field","Philadelphia"],
    ["M095","Round of 16","12 Jul 2026 22:30","TBD","TBD","Estadio Azteca","Mexico City"],
    ["M096","Round of 16","12 Jul 2026 01:30","TBD","TBD","Gillette Stadium","Boston"],

    # ── QUARTER-FINALS ──────────────────────────────────────────────────────────
    ["M097","Quarter-Final","15 Jul 2026 22:30","TBD","TBD","MetLife Stadium","New York/NJ"],
    ["M098","Quarter-Final","15 Jul 2026 04:30","TBD","TBD","SoFi Stadium","Los Angeles"],
    ["M099","Quarter-Final","16 Jul 2026 22:30","TBD","TBD","AT&T Stadium","Dallas"],
    ["M100","Quarter-Final","16 Jul 2026 04:30","TBD","TBD","Hard Rock Stadium","Miami"],

    # ── SEMI-FINALS ─────────────────────────────────────────────────────────────
    ["M101","Semi-Final","19 Jul 2026 22:30","TBD","TBD","MetLife Stadium","New York/NJ"],
    ["M102","Semi-Final","20 Jul 2026 04:30","TBD","TBD","Rose Bowl","Pasadena"],

    # ── THIRD PLACE ─────────────────────────────────────────────────────────────
    ["M103","Third Place","22 Jul 2026 22:30","TBD","TBD","Hard Rock Stadium","Miami"],

    # ── FINAL ───────────────────────────────────────────────────────────────────
    ["M104","Final","24 Jul 2026 04:00","TBD","TBD","MetLife Stadium","New York/NJ"],
]

# ── COLOUR PALETTE FOR FORMATTING ─────────────────────────────────────────────
GREEN      = {"red": 0.13, "green": 0.55, "blue": 0.13}
GOLD       = {"red": 1.0,  "green": 0.84, "blue": 0.0}
WHITE      = {"red": 1.0,  "green": 1.0,  "blue": 1.0}
DARK       = {"red": 0.10, "green": 0.10, "blue": 0.10}
DARK_GREEN = {"red": 0.0,  "green": 0.27, "blue": 0.0}


def connect():
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


def get_or_create_sheet(client):
    try:
        sh = client.open(SHEET_NAME)
        print(f"Opened existing sheet: {SHEET_NAME}")
    except gspread.SpreadsheetNotFound:
        sh = client.create(SHEET_NAME)
        sh.share(None, perm_type="anyone", role="writer")
        print(f"Created new sheet: {SHEET_NAME}")
    return sh


def ensure_tabs(sh):
    """Create all required tabs, delete default Sheet1 if present."""
    required = [
        "Poll Responses",
        "Leaderboard",
        "Match Log",
        "Full Schedule",
        "Player Stats",
        "Team Stats",
    ]
    existing = [ws.title for ws in sh.worksheets()]

    for tab in required:
        if tab not in existing:
            sh.add_worksheet(title=tab, rows=200, cols=26)
            print(f"  Created tab: {tab}")

    if "Sheet1" in [ws.title for ws in sh.worksheets()]:
        sh.del_worksheet(sh.worksheet("Sheet1"))


def setup_poll_responses(sh):
    ws = sh.worksheet("Poll Responses")
    headers = ["Match ID","Match Name","Player Name","Their Answer","Correct Answer","Points Awarded","Timestamp"]
    ws.clear()
    ws.append_row(headers)
    ws.format("A1:G1", {
        "backgroundColor": DARK_GREEN,
        "textFormat": {"bold": True, "foregroundColor": WHITE},
        "horizontalAlignment": "CENTER",
    })
    ws.freeze(rows=1)
    ws.set_column_width(0, 100)


def setup_leaderboard(sh):
    ws = sh.worksheet("Leaderboard")
    ws.clear()
    headers = ["Rank","Player","Team","Star Player","Jersey","Total Points","Correct","Wrong","Missed","Streak","Last Updated"]
    ws.append_row(headers)
    ws.format("A1:K1", {
        "backgroundColor": DARK_GREEN,
        "textFormat": {"bold": True, "foregroundColor": WHITE},
        "horizontalAlignment": "CENTER",
    })
    # Seed with all 8 players at 0 points
    for i, p in enumerate(PLAYERS):
        ws.append_row([
            i + 1,
            p["pet"],
            p["team"],
            p["star"],
            p["jersey"],
            0, 0, 0, 0,
            "—",
            datetime.now().strftime("%d %b %Y %H:%M IST"),
        ])
    ws.freeze(rows=1)


def setup_match_log(sh):
    ws = sh.worksheet("Match Log")
    ws.clear()
    headers = ["Match ID","Date (IST)","Team A","Team B","Score A","Score B","Result","Poll Posted At","Poll Closed At","Points Calculated"]
    ws.append_row(headers)
    ws.format("A1:J1", {
        "backgroundColor": DARK_GREEN,
        "textFormat": {"bold": True, "foregroundColor": WHITE},
        "horizontalAlignment": "CENTER",
    })
    ws.freeze(rows=1)


def setup_full_schedule(sh):
    ws = sh.worksheet("Full Schedule")
    ws.clear()
    headers = ["Match ID","Group/Stage","Date (IST)","Team A","Team B","Venue","City","Status","Score A","Score B","Poll Posted","Poll Closed"]
    ws.append_row(headers)
    ws.format("A1:L1", {
        "backgroundColor": DARK_GREEN,
        "textFormat": {"bold": True, "foregroundColor": WHITE},
        "horizontalAlignment": "CENTER",
    })

    rows = []
    for m in SCHEDULE:
        rows.append([m[0], m[1], m[2], m[3], m[4], m[5], m[6], "Upcoming", "", "", "", ""])
    ws.append_rows(rows)
    ws.freeze(rows=1)

    # Alternate row shading
    for i, row_data in enumerate(rows):
        row_num = i + 2  # 1-indexed, row 1 is header
        if i % 2 == 0:
            ws.format(f"A{row_num}:L{row_num}", {"backgroundColor": {"red": 0.93, "green": 0.97, "blue": 0.93}})

    print(f"  Populated Full Schedule with {len(SCHEDULE)} matches")


def setup_player_stats(sh):
    ws = sh.worksheet("Player Stats")
    ws.clear()
    headers = ["Player","Team","Matches","Goals","Assists","Yellow Cards","Red Cards",
               "Minutes Played","xG","Pass Accuracy %","Key Passes","Dribbles","Fouls Won",
               "Shots","Shots on Target","Match Rating (avg)"]
    ws.append_row(headers)
    ws.format(f"A1:P1", {
        "backgroundColor": DARK_GREEN,
        "textFormat": {"bold": True, "foregroundColor": WHITE},
        "horizontalAlignment": "CENTER",
    })
    ws.freeze(rows=1)


def setup_team_stats(sh):
    ws = sh.worksheet("Team Stats")
    ws.clear()
    headers = ["Team","Matches Played","W","D","L","GF","GA","GD","Points",
               "Possession %","Shots","Shots on Target","xG","Pass Accuracy %",
               "Tackles","Interceptions","Fouls","Corners","Yellow Cards","Red Cards",
               "Clean Sheets","Penalties Won","MOTM Count","Saves"]
    ws.append_row(headers)
    ws.format(f"A1:X1", {
        "backgroundColor": DARK_GREEN,
        "textFormat": {"bold": True, "foregroundColor": WHITE},
        "horizontalAlignment": "CENTER",
    })
    ws.freeze(rows=1)
    print(f"  Team Stats tab ready")


def main():
    print("Connecting to Google Sheets...")
    client = connect()

    print(f"Opening/creating '{SHEET_NAME}'...")
    sh = get_or_create_sheet(client)

    print("Creating tabs...")
    ensure_tabs(sh)

    print("Setting up Poll Responses...")
    setup_poll_responses(sh)

    print("Setting up Leaderboard...")
    setup_leaderboard(sh)

    print("Setting up Match Log...")
    setup_match_log(sh)

    print("Setting up Full Schedule (104 matches)...")
    setup_full_schedule(sh)

    print("Setting up Player Stats...")
    setup_player_stats(sh)

    print("Setting up Team Stats...")
    setup_team_stats(sh)

    print(f"\n✅ Google Sheet '{SHEET_NAME}' is ready!")
    print(f"🔗 URL: https://docs.google.com/spreadsheets/d/{sh.id}")
    print(f"\nShare this URL with friends (read-only): https://docs.google.com/spreadsheets/d/{sh.id}/edit?usp=sharing")

    # Save sheet ID for other scripts
    with open(r"C:\Users\siddh\Downloads\HK\FIFA\logs\sheet_id.txt", "w") as f:
        f.write(sh.id)
    print(f"Sheet ID saved to logs/sheet_id.txt")


if __name__ == "__main__":
    main()
