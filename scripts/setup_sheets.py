"""
setup_sheets.py
Creates and populates the "FIFA World Cup 2026" Google Sheet with all 6 tabs.
Run once. Uses credentials at C:/Users/siddh/Downloads/HK/FIFA/google_credentials.json
"""

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import json

# ── CONFIG ─────────────────────────────────────────────────────────────────────
CREDS_PATH       = r"C:\Users\siddh\Downloads\HK\FIFA\google_credentials.json"
SHEET_NAME       = "FIFA World Cup 2026"
USER_EMAIL       = "siddb12@gmail.com"
# Sheet already exists — paste its ID here so we skip Drive create entirely
EXISTING_SHEET_ID = "18SfYYXYaGxvh-2bZIq_h4dOXfS7YtD5c49nW454MY2o"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
# Sheets-only scopes (fallback if Drive API not enabled)
SHEETS_ONLY_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

# ── PLAYERS ────────────────────────────────────────────────────────────────────
PLAYERS = [
    {"pet": "Budhya", "full": "Sidhant Budhkar"},
    {"pet": "Ambu",   "full": "Kushal Ambulkar"},
    {"pet": "Vini",   "full": "Vineet Nayak"},
    {"pet": "Baby",   "full": "Susmit Gulavani"},
    {"pet": "Abs",    "full": "Abhishek Desai"},
    {"pet": "Anna",   "full": "Nishant Salian"},
    {"pet": "Umaga",  "full": "Umang Budhkar"},
    {"pet": "PR",     "full": "Pranav Raut"},
]

# ── FULL FIFA 2026 SCHEDULE (IST = UTC+5:30) ───────────────────────────────────
# Format: [match_id, stage, date_ist, team_a, team_b, venue, city]
# Official FIFA 2026 schedule — all 104 matches
SCHEDULE = [
    # ── GROUP STAGE ─────────────────────────────────────────────────────────────
    # Group A: Mexico, S. Africa, South Korea, Czechia
    ["M001","Group A","11 Jun 2026 01:30","Mexico","S. Africa","SoFi Stadium","Los Angeles"],
    ["M002","Group A","11 Jun 2026 04:00","South Korea","Czechia","AT&T Stadium","Dallas"],
    ["M003","Group A","15 Jun 2026 01:30","Mexico","Czechia","Rose Bowl","Los Angeles"],
    ["M004","Group A","15 Jun 2026 04:00","S. Africa","South Korea","NRG Stadium","Houston"],
    ["M005","Group A","19 Jun 2026 00:00","Czechia","S. Africa","Estadio Azteca","Mexico City"],
    ["M006","Group A","19 Jun 2026 00:00","South Korea","Mexico","Gillette Stadium","Boston"],

    # Group B: Canada, Bosnia-Herz., Qatar, Switzerland
    ["M007","Group B","12 Jun 2026 01:30","Canada","Bosnia-Herz.","BMO Field","Toronto"],
    ["M008","Group B","12 Jun 2026 04:00","Qatar","Switzerland","BC Place","Vancouver"],
    ["M009","Group B","16 Jun 2026 01:30","Canada","Qatar","BMO Field","Toronto"],
    ["M010","Group B","16 Jun 2026 04:00","Bosnia-Herz.","Switzerland","Levi's Stadium","San Jose"],
    ["M011","Group B","20 Jun 2026 00:00","Switzerland","Canada","Estadio BBVA","Monterrey"],
    ["M012","Group B","20 Jun 2026 00:00","Bosnia-Herz.","Qatar","Hard Rock Stadium","Miami"],

    # Group C: Brazil ⭐, Morocco, Haiti, Scotland
    ["M013","Group C","12 Jun 2026 04:30","Brazil","Morocco","MetLife Stadium","New York"],
    ["M014","Group C","13 Jun 2026 01:30","Haiti","Scotland","Arrowhead Stadium","Kansas City"],
    ["M015","Group C","17 Jun 2026 01:30","Brazil","Haiti","Lincoln Financial Field","Philadelphia"],
    ["M016","Group C","17 Jun 2026 04:00","Scotland","Morocco","Rose Bowl","Los Angeles"],
    ["M017","Group C","21 Jun 2026 00:00","Morocco","Haiti","Hard Rock Stadium","Miami"],
    ["M018","Group C","21 Jun 2026 00:00","Scotland","Brazil","AT&T Stadium","Dallas"],

    # Group D: USA, Paraguay, Australia, Türkiye
    ["M019","Group D","12 Jun 2026 22:30","USA","Paraguay","SoFi Stadium","Los Angeles"],
    ["M020","Group D","13 Jun 2026 04:00","Australia","Türkiye","Levi's Stadium","San Jose"],
    ["M021","Group D","17 Jun 2026 22:30","USA","Australia","Rose Bowl","Los Angeles"],
    ["M022","Group D","17 Jun 2026 04:30","Türkiye","Paraguay","Gillette Stadium","Boston"],
    ["M023","Group D","22 Jun 2026 00:00","Paraguay","Australia","NRG Stadium","Houston"],
    ["M024","Group D","22 Jun 2026 00:00","Türkiye","USA","AT&T Stadium","Dallas"],

    # Group E: Germany ⭐, Curaçao, Ivory Coast, Ecuador
    ["M025","Group E","13 Jun 2026 01:30","Germany","Curaçao","MetLife Stadium","New York"],
    ["M026","Group E","13 Jun 2026 22:30","Ivory Coast","Ecuador","Estadio BBVA","Monterrey"],
    ["M027","Group E","17 Jun 2026 22:30","Germany","Ivory Coast","SoFi Stadium","Los Angeles"],
    ["M028","Group E","18 Jun 2026 01:30","Ecuador","Curaçao","Lincoln Financial Field","Philadelphia"],
    ["M029","Group E","22 Jun 2026 04:00","Curaçao","Ivory Coast","Levi's Stadium","San Jose"],
    ["M030","Group E","22 Jun 2026 04:00","Ecuador","Germany","BC Place","Vancouver"],

    # Group F: Netherlands ⭐, Japan, Sweden, Tunisia
    ["M031","Group F","13 Jun 2026 04:00","Netherlands","Japan","Arrowhead Stadium","Kansas City"],
    ["M032","Group F","13 Jun 2026 22:30","Sweden","Tunisia","BMO Field","Toronto"],
    ["M033","Group F","18 Jun 2026 01:30","Netherlands","Sweden","Gillette Stadium","Boston"],
    ["M034","Group F","18 Jun 2026 22:30","Tunisia","Japan","AT&T Stadium","Dallas"],
    ["M035","Group F","23 Jun 2026 00:00","Japan","Sweden","NRG Stadium","Houston"],
    ["M036","Group F","23 Jun 2026 00:00","Tunisia","Netherlands","Hard Rock Stadium","Miami"],

    # Group G: Belgium, Egypt, Iran, New Zealand
    ["M037","Group G","14 Jun 2026 01:30","Belgium","Egypt","SoFi Stadium","Los Angeles"],
    ["M038","Group G","14 Jun 2026 04:00","Iran","New Zealand","MetLife Stadium","New York"],
    ["M039","Group G","18 Jun 2026 04:00","Belgium","Iran","Rose Bowl","Los Angeles"],
    ["M040","Group G","18 Jun 2026 22:30","New Zealand","Egypt","Estadio BBVA","Monterrey"],
    ["M041","Group G","23 Jun 2026 04:00","Egypt","Iran","BC Place","Vancouver"],
    ["M042","Group G","23 Jun 2026 04:00","New Zealand","Belgium","BMO Field","Toronto"],

    # Group H: Spain ⭐, Cape Verde, Saudi Arabia, Uruguay
    ["M043","Group H","14 Jun 2026 22:30","Spain","Cape Verde","Estadio Azteca","Mexico City"],
    ["M044","Group H","15 Jun 2026 01:30","Saudi Arabia","Uruguay","Arrowhead Stadium","Kansas City"],
    ["M045","Group H","19 Jun 2026 01:30","Spain","Saudi Arabia","Levi's Stadium","San Jose"],
    ["M046","Group H","19 Jun 2026 04:00","Uruguay","Cape Verde","Lincoln Financial Field","Philadelphia"],
    ["M047","Group H","23 Jun 2026 00:00","Cape Verde","Saudi Arabia","MetLife Stadium","New York"],
    ["M048","Group H","23 Jun 2026 00:00","Uruguay","Spain","Hard Rock Stadium","Miami"],

    # Group I: France ⭐, Senegal, Iraq, Norway
    ["M049","Group I","15 Jun 2026 04:00","France","Senegal","AT&T Stadium","Dallas"],
    ["M050","Group I","15 Jun 2026 22:30","Iraq","Norway","Gillette Stadium","Boston"],
    ["M051","Group I","19 Jun 2026 22:30","France","Iraq","BC Place","Vancouver"],
    ["M052","Group I","20 Jun 2026 01:30","Norway","Senegal","NRG Stadium","Houston"],
    ["M053","Group I","24 Jun 2026 00:00","Senegal","Iraq","Estadio Azteca","Mexico City"],
    ["M054","Group I","24 Jun 2026 00:00","Norway","France","SoFi Stadium","Los Angeles"],

    # Group J: Argentina ⭐, Algeria, Austria, Jordan
    ["M055","Group J","15 Jun 2026 22:30","Argentina","Algeria","Rose Bowl","Los Angeles"],
    ["M056","Group J","16 Jun 2026 01:30","Austria","Jordan","MetLife Stadium","New York"],
    ["M057","Group J","20 Jun 2026 01:30","Argentina","Austria","Hard Rock Stadium","Miami"],
    ["M058","Group J","20 Jun 2026 04:00","Jordan","Algeria","Arrowhead Stadium","Kansas City"],
    ["M059","Group J","24 Jun 2026 04:00","Algeria","Austria","Estadio BBVA","Monterrey"],
    ["M060","Group J","24 Jun 2026 04:00","Jordan","Argentina","Lincoln Financial Field","Philadelphia"],

    # Group K: Portugal ⭐, Congo DR, Uzbekistan, Colombia
    ["M061","Group K","16 Jun 2026 22:30","Portugal","Congo DR","BMO Field","Toronto"],
    ["M062","Group K","17 Jun 2026 01:30","Uzbekistan","Colombia","AT&T Stadium","Dallas"],
    ["M063","Group K","21 Jun 2026 01:30","Portugal","Uzbekistan","SoFi Stadium","Los Angeles"],
    ["M064","Group K","21 Jun 2026 04:00","Colombia","Congo DR","NRG Stadium","Houston"],
    ["M065","Group K","25 Jun 2026 00:00","Congo DR","Uzbekistan","Gillette Stadium","Boston"],
    ["M066","Group K","25 Jun 2026 00:00","Colombia","Portugal","BC Place","Vancouver"],

    # Group L: England ⭐, Croatia, Ghana, Panama
    ["M067","Group L","17 Jun 2026 04:00","England","Croatia","MetLife Stadium","New York"],
    ["M068","Group L","18 Jun 2026 01:30","Ghana","Panama","Estadio Azteca","Mexico City"],
    ["M069","Group L","22 Jun 2026 01:30","England","Ghana","Rose Bowl","Los Angeles"],
    ["M070","Group L","22 Jun 2026 04:00","Panama","Croatia","Arrowhead Stadium","Kansas City"],
    ["M071","Group L","26 Jun 2026 00:00","Croatia","Ghana","Lincoln Financial Field","Philadelphia"],
    ["M072","Group L","26 Jun 2026 00:00","Panama","England","Levi's Stadium","San Jose"],

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
    """Connect with full scopes (Drive + Sheets). Falls back to Sheets-only."""
    try:
        creds  = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
        client = gspread.authorize(creds)
        # Quick connectivity test
        client.list_spreadsheet_files()
        return client, creds
    except Exception as e:
        if "403" in str(e) or "quota" in str(e).lower() or "drive" in str(e).lower():
            print(f"⚠  Drive API issue detected: {e}")
            print("   Retrying with Sheets-only scope...")
            creds  = Credentials.from_service_account_file(CREDS_PATH, scopes=SHEETS_ONLY_SCOPES)
            client = gspread.authorize(creds)
            return client, creds
        raise


def _create_via_sheets_api(creds):
    """Create a spreadsheet using Sheets API v4 (no Drive API required)."""
    service = build("sheets", "v4", credentials=creds)
    body = {"properties": {"title": SHEET_NAME}}
    resp = service.spreadsheets().create(body=body, fields="spreadsheetId").execute()
    sheet_id = resp["spreadsheetId"]
    print(f"  Created sheet via Sheets API: {sheet_id}")
    return sheet_id


def _share_with_user(sheet_id, creds):
    """Share the sheet with the user's email via Drive API."""
    try:
        drive = build("drive", "v3", credentials=creds)
        drive.permissions().create(
            fileId=sheet_id,
            body={"type": "user", "role": "writer", "emailAddress": USER_EMAIL},
            sendNotificationEmail=False,
        ).execute()
        print(f"  Shared with {USER_EMAIL} (writer)")
    except Exception as e:
        print(f"  ⚠ Could not auto-share (Drive API may not be enabled): {e}")
        print(f"  👉 Manually share this URL with yourself:")
        print(f"     https://docs.google.com/spreadsheets/d/{sheet_id}/edit")


def get_or_create_sheet(client, creds):
    # Step 1: If we know the sheet ID already, open directly (fastest, no Drive API needed)
    if EXISTING_SHEET_ID:
        try:
            sh = client.open_by_key(EXISTING_SHEET_ID)
            print(f"✅ Opened existing sheet by ID: {EXISTING_SHEET_ID}")
            return sh
        except Exception as e:
            print(f"⚠  Could not open sheet by ID: {e}")
            print(f"   → Go to the sheet → Share → add your service account email as Editor")
            print(f"   → Find service account email in google_credentials.json (client_email field)")
            raise SystemExit(1)

    # Step 2: Try opening by name
    try:
        sh = client.open(SHEET_NAME)
        print(f"Opened existing sheet by name: {SHEET_NAME}")
        return sh
    except gspread.SpreadsheetNotFound:
        pass

    # Step 3: Try Drive-backed create
    try:
        sh = client.create(SHEET_NAME)
        sh.share(USER_EMAIL, perm_type="user", role="writer", notify=False)
        print(f"Created sheet + shared with {USER_EMAIL}")
        return sh
    except Exception as e:
        print(f"⚠  Drive create failed ({e})")
        print("   Falling back to Sheets API v4 direct create...")

    # Step 4: Sheets API create (no Drive API needed)
    sheet_id = _create_via_sheets_api(creds)
    _share_with_user(sheet_id, creds)
    sh = client.open_by_key(sheet_id)
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


def setup_leaderboard(sh):
    ws = sh.worksheet("Leaderboard")
    ws.clear()
    headers = ["Rank","Player","Full Name","Total Points","Correct","Wrong","Missed","Streak","Last Updated"]
    ws.append_row(headers)
    ws.format("A1:I1", {
        "backgroundColor": DARK_GREEN,
        "textFormat": {"bold": True, "foregroundColor": WHITE},
        "horizontalAlignment": "CENTER",
    })
    # Seed with all 8 players at 0 points
    rows = []
    for i, p in enumerate(PLAYERS):
        rows.append([
            i + 1,
            p["pet"],
            p["full"],
            0, 0, 0, 0,
            "—",
            datetime.now().strftime("%d %b %Y %H:%M IST"),
        ])
    ws.append_rows(rows)
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
    # Row shading skipped — would hit Sheets API rate limits (60 writes/min)
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
    print("Connecting to Google API...")
    client, creds = connect()

    print(f"Opening/creating '{SHEET_NAME}'...")
    sh = get_or_create_sheet(client, creds)

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
