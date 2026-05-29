"""
stats_fetcher.py
FIFA World Cup 2026 Fantasy — Live Stats Fetcher

Runs every 30 minutes via Windows Task Scheduler.
Fetches match and player stats from football-data.org free tier,
updates Google Sheets Player Stats and Team Stats tabs.

Dependencies: pip install gspread google-auth requests pytz
"""

import time
import logging
import requests
import gspread
from pathlib import Path
from datetime import datetime
from google.oauth2.service_account import Credentials
import pytz

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(r"C:\Users\siddh\Downloads\HK\FIFA")
CREDS_PATH   = BASE_DIR / "google_credentials.json"
SHEET_NAME   = "FIFA World Cup 2026"
API_BASE     = "https://api.football-data.org/v4"
FOOTBALL_KEY = "0c802b9b126b4e7b987bf005bea418a6"# ← paste your free key from football-data.org
FIFA_COMP    = 2000   # FIFA World Cup 2026 competition ID

IST    = pytz.timezone("Asia/Kolkata")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

log_path = BASE_DIR / "logs" / "stats_fetcher.log"
logging.basicConfig(
    filename=str(log_path), level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def headers():
    return {"X-Auth-Token": FOOTBALL_KEY}


def get_sheet():
    creds  = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME)


# ── API FETCHERS ──────────────────────────────────────────────────────────────
def fetch_standings():
    url  = f"{API_BASE}/competitions/{FIFA_COMP}/standings"
    resp = requests.get(url, headers=headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_scorers():
    url  = f"{API_BASE}/competitions/{FIFA_COMP}/scorers?limit=20"
    resp = requests.get(url, headers=headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_matches():
    url  = f"{API_BASE}/competitions/{FIFA_COMP}/matches"
    resp = requests.get(url, headers=headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


# ── TEAM STATS UPDATE ─────────────────────────────────────────────────────────
def update_team_stats(sh):
    try:
        data = fetch_standings()
    except Exception as e:
        log.error(f"Failed to fetch standings: {e}")
        return

    ws = sh.worksheet("Team Stats")
    ws.clear()
    headers_row = ["Team","Matches Played","W","D","L","GF","GA","GD","Points",
                   "Possession %","Shots","Shots on Target","xG","Pass Accuracy %",
                   "Tackles","Interceptions","Fouls","Corners","Yellow Cards","Red Cards",
                   "Clean Sheets","Penalties Won","MOTM Count","Saves"]
    ws.append_row(headers_row)

    rows = []
    for group in data.get("standings", []):
        for entry in group.get("table", []):
            team = entry.get("team", {}).get("name", "")
            rows.append([
                team,
                entry.get("playedGames", 0),
                entry.get("won", 0),
                entry.get("draw", 0),
                entry.get("lost", 0),
                entry.get("goalsFor", 0),
                entry.get("goalsAgainst", 0),
                entry.get("goalDifference", 0),
                entry.get("points", 0),
                "—","—","—","—","—","—","—","—","—","—","—","—","—","—","—",
            ])

    if rows:
        ws.append_rows(rows)
        log.info(f"Team stats updated: {len(rows)} teams")


# ── PLAYER / SCORER STATS UPDATE ─────────────────────────────────────────────
def update_player_stats(sh):
    try:
        data = fetch_scorers()
    except Exception as e:
        log.error(f"Failed to fetch scorers: {e}")
        return

    ws = sh.worksheet("Player Stats")
    ws.clear()
    headers_row = ["Player","Team","Matches","Goals","Assists","Yellow Cards","Red Cards",
                   "Minutes Played","xG","Pass Accuracy %","Key Passes","Dribbles","Fouls Won",
                   "Shots","Shots on Target","Match Rating (avg)"]
    ws.append_row(headers_row)

    rows = []
    for scorer in data.get("scorers", []):
        player = scorer.get("player", {})
        team   = scorer.get("team", {})
        rows.append([
            player.get("name", ""),
            team.get("name", ""),
            scorer.get("playedMatches", 0),
            scorer.get("goals", 0),
            scorer.get("assists", 0) or 0,
            scorer.get("penalties", 0),  # reused as yellow placeholder
            0,  # red cards
            "—","—","—","—","—","—","—","—","—",
        ])

    if rows:
        ws.append_rows(rows)
        log.info(f"Player stats updated: {len(rows)} players")


# ── MATCH SCHEDULE SYNC ───────────────────────────────────────────────────────
def sync_match_results(sh):
    """Sync actual scores back into Full Schedule for matches marked In Progress."""
    try:
        data    = fetch_matches()
        matches = data.get("matches", [])
    except Exception as e:
        log.error(f"Failed to fetch matches: {e}")
        return

    ws       = sh.worksheet("Full Schedule")
    schedule = ws.get_all_records()

    # API status → dashboard status mapping (exact enum values from football-data.org)
    LIVE_STATUSES     = {"IN_PLAY", "PAUSED", "EXTRA_TIME", "PENALTY_SHOOTOUT"}
    FINISHED_STATUSES = {"FINISHED", "AWARDED"}

    for api_match in matches:
        status = api_match.get("status", "")
        if status not in LIVE_STATUSES and status not in FINISHED_STATUSES:
            continue

        home = api_match.get("homeTeam", {}).get("name", "")
        away = api_match.get("awayTeam", {}).get("name", "")

        # Get score — fullTime for FINISHED, currentScore / halfTime for live
        score_obj  = api_match.get("score", {})
        if status in FINISHED_STATUSES:
            sc = score_obj.get("fullTime", {})
        else:
            sc = score_obj.get("halfTime", {}) or score_obj.get("fullTime", {})
        score_home = sc.get("home")
        score_away = sc.get("away")

        dash_status = "Completed" if status in FINISHED_STATUSES else "Live"

        # Match against our schedule by team names
        for i, row in enumerate(schedule):
            if (home in row.get("Team A", "") or row.get("Team A", "") in home) and \
               (away in row.get("Team B", "") or row.get("Team B", "") in away):
                row_num = i + 2
                ws.update_cell(row_num, 8, dash_status)
                if score_home is not None:
                    ws.update_cell(row_num, 9, score_home)
                    ws.update_cell(row_num, 10, score_away)
                log.info(f"Updated [{dash_status}]: {home} {score_home}-{score_away} {away}")
                break

    log.info("Match results sync complete")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    log.info("=== Stats Fetcher Started ===")
    if not FOOTBALL_KEY:
        log.warning("FOOTBALL_KEY not set — API calls will return 403. Set your free key from football-data.org")

    sh = get_sheet()
    update_team_stats(sh)
    time.sleep(2)
    update_player_stats(sh)
    time.sleep(2)
    sync_match_results(sh)
    log.info("=== Stats Fetcher Complete ===")


if __name__ == "__main__":
    main()
