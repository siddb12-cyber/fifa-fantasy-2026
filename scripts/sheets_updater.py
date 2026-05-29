"""
sheets_updater.py
FIFA World Cup 2026 Fantasy — Poll Response Recorder

Runs every 15 minutes during match windows.
Reads WhatsApp poll responses (manually entered or via web scraping)
and updates the Google Sheet.

In the manual workflow:
  - You call record_response(match_id, player, answer) after reading WA responses
  - Or run this script with args: python sheets_updater.py M001 Sidd "Portugal"

Dependencies: pip install gspread google-auth pytz
"""

import sys
import logging
import gspread
from pathlib import Path
from datetime import datetime
from google.oauth2.service_account import Credentials
import pytz

BASE_DIR   = Path(r"C:\Users\siddh\Downloads\HK\FIFA")
CREDS_PATH = BASE_DIR / "google_credentials.json"
SHEET_NAME = "FIFA World Cup 2026"
IST        = pytz.timezone("Asia/Kolkata")
SCOPES     = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

log_path = BASE_DIR / "logs" / "sheets_updater.log"
logging.basicConfig(
    filename=str(log_path), level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def get_sheet():
    creds  = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME)


def get_match_name(sh, match_id):
    ws   = sh.worksheet("Full Schedule")
    rows = ws.get_all_records()
    for r in rows:
        if r["Match ID"] == match_id:
            return f"{r['Team A']} vs {r['Team B']}"
    return match_id


def record_response(sh, match_id, player_name, answer):
    """
    Record a single poll response.
    answer: e.g. "Portugal", "Draw", "Argentina"
    """
    ws         = sh.worksheet("Poll Responses")
    match_name = get_match_name(sh, match_id)
    timestamp  = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

    # Check for duplicate
    rows = ws.get_all_records()
    for row in rows:
        if row["Match ID"] == match_id and row["Player Name"] == player_name:
            log.warning(f"Duplicate response skipped: {match_id} / {player_name}")
            return False

    ws.append_row([
        match_id, match_name, player_name,
        answer, "", 0, timestamp,
    ])
    log.info(f"Recorded: {match_id} | {player_name} → {answer}")
    return True


def bulk_record(sh, match_id, responses: dict):
    """
    responses: {player_name: answer}
    e.g. {"Sidd": "Portugal", "Kushal": "Argentina", "Vineet": "Draw", ...}
    """
    for player, answer in responses.items():
        record_response(sh, match_id, player, answer)
    log.info(f"Bulk recorded {len(responses)} responses for {match_id}")


def show_responses(sh, match_id):
    """Print current poll responses for a match."""
    ws   = sh.worksheet("Poll Responses")
    rows = ws.get_all_records()
    print(f"\n📋 Responses for {match_id}:")
    for row in rows:
        if row["Match ID"] == match_id:
            pts = row["Points Awarded"]
            pts_str = f"+{pts}" if int(pts or 0) > 0 else str(pts or "—")
            print(f"  {row['Player Name']:<12} → {row['Their Answer']:<15} [{pts_str} pts]")


def recalculate_leaderboard(sh):
    """Re-derive full leaderboard from Poll Responses (useful for corrections)."""
    resp_ws = sh.worksheet("Poll Responses")
    lb_ws   = sh.worksheet("Leaderboard")
    rows    = resp_ws.get_all_records()

    # Aggregate
    totals = {}
    for row in rows:
        player = row["Player Name"]
        pts    = int(row.get("Points Awarded") or 0)
        if player not in totals:
            totals[player] = {"total": 0, "correct": 0, "wrong": 0, "missed": 0}
        totals[player]["total"] += pts
        if pts == 3:
            totals[player]["correct"] += 1
        elif pts == 0 and row["Their Answer"] != "MISSED":
            totals[player]["wrong"] += 1
        elif row["Their Answer"] == "MISSED":
            totals[player]["missed"] += 1

    # Update leaderboard
    lb_rows = lb_ws.get_all_records()
    ts      = datetime.now(IST).strftime("%d %b %Y %H:%M IST")

    for i, row in enumerate(lb_rows):
        player = row["Player"]
        data   = totals.get(player, {"total": 0, "correct": 0, "wrong": 0, "missed": 0})
        row_num = i + 2
        lb_ws.update(f"F{row_num}:K{row_num}", [[
            data["total"], data["correct"], data["wrong"], data["missed"], "—", ts
        ]])

    # Sort by total points and re-rank
    lb_rows = lb_ws.get_all_records()
    sorted_rows = sorted(lb_rows, key=lambda x: int(x.get("Total Points", 0)), reverse=True)
    for rank, row in enumerate(sorted_rows, 1):
        for i, original in enumerate(lb_rows):
            if original["Player"] == row["Player"]:
                lb_ws.update_cell(i + 2, 1, rank)
                break

    log.info("Leaderboard recalculated")
    print("✅ Leaderboard recalculated")


# ── CLI USAGE ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sh = get_sheet()

    if len(sys.argv) == 4:
        # python sheets_updater.py M001 Sidd "Portugal"
        _, match_id, player, answer = sys.argv
        record_response(sh, match_id, player, answer)
        print(f"✅ Recorded: {match_id} | {player} → {answer}")

    elif len(sys.argv) == 2 and sys.argv[1].startswith("M"):
        show_responses(sh, sys.argv[1])

    elif len(sys.argv) == 2 and sys.argv[1] == "recalc":
        recalculate_leaderboard(sh)

    else:
        print("""
FIFA Fantasy 2026 — Sheets Updater

Usage:
  Record single response:   python sheets_updater.py M001 Sidd "Portugal"
  Show match responses:     python sheets_updater.py M001
  Recalculate leaderboard:  python sheets_updater.py recalc
""")
