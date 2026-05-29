"""
setup_test_sheet.py
Creates a minimal Google Sheet for the 2-player dummy test.
Run once before the test starts.
"""
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime

CREDS_PATH  = r"C:\Users\siddh\Downloads\HK\FIFA\google_credentials.json"
SHEET_NAME  = "FIFA Fantasy Test — 2 Players"
USER_EMAIL  = "siddb12@gmail.com"

# ── PASTE YOUR MANUALLY CREATED SHEET ID HERE ─────────────────────────────────
# 1. Go to sheets.google.com → create a blank sheet
# 2. Copy the ID from the URL: .../spreadsheets/d/THIS_PART/edit
# 3. Share the sheet with your service account email (client_email in google_credentials.json)
EXISTING_SHEET_ID = "19OIAI-7Uih4KEOw4zY7-IuA2HH4jzjKZFOQ0VwhHJuw"   # ← paste your Sheet ID between the quotes

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

TEST_PLAYERS = [
    {"pet": "Sidhant", "full": "Sidhant Budhkar"},
    {"pet": "Jio",     "full": "Sidhant (Jio)"},
]

TEST_MATCHES = [
    ["T001", "Test Match 1", "30 May 2026 21:00", "Sidhant FC",    "Jio United",     "The Living Room",     "Mumbai"],
    ["T002", "Test Match 2", "31 May 2026 20:30", "Mumbai Bhai FC","Delhi Dhamaka",   "WhatsApp Stadium",    "Anywhere"],
    ["T003", "Test Match 3", "01 Jun 2026 21:00", "Chai United",   "Coffee Athletic", "The Office Pantry",   "Everywhere"],
    ["T004", "Test Final",   "02 Jun 2026 19:00", "Test FC Alpha", "Test FC Bravo",   "Grand Test Arena",    "Nowhere Real"],
]

GREEN      = {"red": 0.13, "green": 0.55, "blue": 0.13}
GOLD       = {"red": 1.0,  "green": 0.84, "blue": 0.0}
WHITE      = {"red": 1.0,  "green": 1.0,  "blue": 1.0}
DARK_GREEN = {"red": 0.0,  "green": 0.27, "blue": 0.0}


def connect():
    try:
        creds  = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
        client = gspread.authorize(creds)
        client.list_spreadsheet_files()
        return client, creds
    except Exception as e:
        print(f"⚠ Drive scope failed, trying Sheets only: {e}")
        creds  = Credentials.from_service_account_file(CREDS_PATH, scopes=SHEETS_SCOPES)
        return gspread.authorize(creds), Credentials.from_service_account_file(CREDS_PATH, scopes=SHEETS_SCOPES)


def create_sheet(client, creds):
    try:
        service = build("sheets", "v4", credentials=creds)
        body    = {"properties": {"title": SHEET_NAME}}
        resp    = service.spreadsheets().create(body=body, fields="spreadsheetId").execute()
        sheet_id = resp["spreadsheetId"]
        print(f"✅ Created sheet: {sheet_id}")
        # Share with user
        try:
            drive = build("drive", "v3", credentials=creds)
            drive.permissions().create(
                fileId=sheet_id,
                body={"type": "user", "role": "writer", "emailAddress": USER_EMAIL},
                sendNotificationEmail=False,
            ).execute()
            print(f"✅ Shared with {USER_EMAIL}")
        except Exception as e:
            print(f"⚠ Share failed (manual share needed): {e}")
            print(f"   URL: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
        return client.open_by_key(sheet_id)
    except Exception as e:
        raise RuntimeError(f"Sheet creation failed: {e}")


def setup_tabs(sh):
    existing = [ws.title for ws in sh.worksheets()]

    tabs = ["Leaderboard", "Poll Responses", "Sent Log", "Test Schedule"]
    for tab in tabs:
        if tab not in existing:
            sh.add_worksheet(tab, rows=200, cols=20)
            print(f"  + Created tab: {tab}")

    # Remove default Sheet1
    if "Sheet1" in existing:
        sh.del_worksheet(sh.worksheet("Sheet1"))

    # ── LEADERBOARD ──────────────────────────────────────────────────────────
    ws = sh.worksheet("Leaderboard")
    ws.clear()
    headers = ["Rank", "Player", "Full Name", "Total Points", "Correct", "Wrong", "Missed", "Streak", "Last Updated"]
    ws.append_row(headers)
    ws.format("A1:I1", {"backgroundColor": DARK_GREEN,
                         "textFormat": {"bold": True, "foregroundColor": WHITE},
                         "horizontalAlignment": "CENTER"})
    rows = []
    for i, p in enumerate(TEST_PLAYERS):
        rows.append([i+1, p["pet"], p["full"], 0, 0, 0, 0, "—",
                     datetime.now().strftime("%d %b %Y %H:%M IST")])
    ws.append_rows(rows)
    ws.freeze(rows=1)
    print("  ✅ Leaderboard seeded with 2 players")

    # ── POLL RESPONSES ───────────────────────────────────────────────────────
    ws = sh.worksheet("Poll Responses")
    ws.clear()
    headers = ["Match ID", "Match Name", "Player Name", "Their Answer", "Correct Answer", "Points Awarded", "Timestamp"]
    ws.append_row(headers)
    ws.format("A1:G1", {"backgroundColor": DARK_GREEN,
                         "textFormat": {"bold": True, "foregroundColor": WHITE},
                         "horizontalAlignment": "CENTER"})
    ws.freeze(rows=1)
    print("  ✅ Poll Responses tab ready")

    # ── SENT LOG ─────────────────────────────────────────────────────────────
    ws = sh.worksheet("Sent Log")
    ws.clear()
    headers = ["Match ID", "Notif Type", "Telegram Poll ID", "Sent At", "Match Time IST", "Mode"]
    ws.append_row(headers)
    ws.format("A1:F1", {"backgroundColor": DARK_GREEN,
                         "textFormat": {"bold": True, "foregroundColor": WHITE},
                         "horizontalAlignment": "CENTER"})
    ws.freeze(rows=1)
    print("  ✅ Sent Log tab ready")

    # ── TEST SCHEDULE ────────────────────────────────────────────────────────
    ws = sh.worksheet("Test Schedule")
    ws.clear()
    headers = ["Match ID", "Stage", "Date (IST)", "Team A", "Team B", "Venue", "City", "Status", "Score A", "Score B"]
    ws.append_row(headers)
    ws.format("A1:J1", {"backgroundColor": DARK_GREEN,
                         "textFormat": {"bold": True, "foregroundColor": WHITE},
                         "horizontalAlignment": "CENTER"})
    rows = [[m[0], m[1], m[2], m[3], m[4], m[5], m[6], "Upcoming", "", ""] for m in TEST_MATCHES]
    ws.append_rows(rows)
    ws.freeze(rows=1)
    print(f"  ✅ Test Schedule populated with {len(TEST_MATCHES)} matches")


def main():
    print("Setting up FIFA Fantasy TEST Google Sheet (2 players)...")
    if not EXISTING_SHEET_ID:
        print("\n❌  STOP: Paste your Sheet ID into EXISTING_SHEET_ID in this script first.")
        print("   Steps:")
        print("   1. Go to sheets.google.com → create a blank sheet")
        print("   2. Copy the ID from the URL: .../spreadsheets/d/YOUR_ID/edit")
        print("   3. Share it (Editor) with the client_email in google_credentials.json")
        print("   4. Paste the ID into EXISTING_SHEET_ID = \"\" at the top of this script")
        return
    client, creds = connect()
    try:
        sh = client.open_by_key(EXISTING_SHEET_ID)
        print(f"✅ Opened existing sheet: {EXISTING_SHEET_ID}")
    except Exception as e:
        print(f"❌ Could not open sheet: {e}")
        print("   Make sure you shared the sheet with your service account (client_email).")
        return
    setup_tabs(sh)
    print(f"\n✅ Done! Sheet ID: {sh.id}")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{sh.id}/edit")
    print(f"\n📌 Copy this Sheet ID into GitHub Secrets as: GOOGLE_SHEET_ID")
    print(f"   Value: {sh.id}")


if __name__ == "__main__":
    main()
