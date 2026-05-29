"""
poll_scheduler.py
FIFA World Cup 2026 Fantasy — WhatsApp Poll Automation

Schedule: Run every hour via Windows Task Scheduler
  - Reads Full Schedule from Google Sheets
  - Posts WhatsApp polls 24 hours before kickoff (IST)
  - Closes polls 5 minutes before kickoff
  - Records responses to Poll Responses tab
  - Calculates points after match result
  - Triggers dashboard rebuild
  - Sends WhatsApp match report after game

Dependencies:
  pip install gspread google-auth selenium webdriver-manager requests pytz schedule
"""

import os
import sys
import time
import json
import logging
import requests
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytz
import gspread
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# ── CONFIG ─────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(r"C:\Users\siddh\Downloads\HK\FIFA")
CREDS_PATH     = BASE_DIR / "google_credentials.json"
SHEET_NAME     = "FIFA World Cup 2026"
CHROME_PROFILE = r"C:\Users\siddh\AppData\Local\Google\Chrome\User Data\Profile 6"
WA_GROUP       = "FIFA 26 Test Group"              # test group — update to final group name when ready
FOOTBALL_API   = "https://api.football-data.org/v4"
FOOTBALL_KEY   = ""                               # ← paste your free-tier key from football-data.org
FIFA_COMP_ID   = 2000                             # FIFA World Cup competition ID

IST  = pytz.timezone("Asia/Kolkata")
UTC  = pytz.utc

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

PLAYERS = [
    "Budhya", "Ambu", "Vini", "Baby",
    "Abs", "Anna", "Umaga", "PR",
]

# ── LOGGING ───────────────────────────────────────────────────────────────────
log_path = BASE_DIR / "logs" / "poll_scheduler.log"
logging.basicConfig(
    filename=str(log_path),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
def get_sheet():
    creds  = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME)


def get_schedule(sh):
    ws   = sh.worksheet("Full Schedule")
    rows = ws.get_all_records()
    return rows


def get_leaderboard(sh):
    ws   = sh.worksheet("Leaderboard")
    rows = ws.get_all_records()
    return rows


# ── TIME HELPERS ──────────────────────────────────────────────────────────────
def parse_ist(date_str):
    """Parse 'DD Mon YYYY HH:MM' → aware IST datetime."""
    dt = datetime.strptime(date_str.strip(), "%d %b %Y %H:%M")
    return IST.localize(dt)


def now_ist():
    return datetime.now(IST)


# ── WHATSAPP AUTOMATION ───────────────────────────────────────────────────────
def get_driver():
    opts = Options()
    opts.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    # opts.add_argument("--headless=new")  # uncomment for headless mode
    driver = webdriver.Chrome(options=opts)
    return driver


def open_wa_group(driver):
    driver.get("https://web.whatsapp.com")
    wait = WebDriverWait(driver, 30)
    # Wait for WhatsApp to load
    wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]')))
    time.sleep(3)

    # Search for group
    search = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
    search.click()
    time.sleep(1)
    search.send_keys(WA_GROUP)
    time.sleep(2)
    # Click first result
    result = wait.until(EC.element_to_be_clickable(
        (By.XPATH, f'//span[@title="{WA_GROUP}"]')
    ))
    result.click()
    time.sleep(2)
    log.info(f"Opened WhatsApp group: {WA_GROUP}")


def send_wa_message(driver, msg):
    wait = WebDriverWait(driver, 10)
    box  = wait.until(EC.element_to_be_clickable(
        (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
    ))
    box.click()
    # Handle newlines
    for line in msg.split("\n"):
        box.send_keys(line)
        box.send_keys(Keys.SHIFT + Keys.ENTER)
    box.send_keys(Keys.ENTER)
    time.sleep(2)
    log.info(f"Sent WA message: {msg[:60]}...")


def post_poll(match):
    """Post a WhatsApp poll for the given match."""
    team_a = match["Team A"]
    team_b = match["Team B"]
    msg = (
        f"🏆 *FIFA WORLD CUP 2026 — FANTASY POLL*\n\n"
        f"⚽ *{team_a}* vs *{team_b}*\n"
        f"📅 Kickoff: {match['Date (IST)']} IST\n"
        f"🏟️ {match['Venue']}, {match['City']}\n\n"
        f"*Who wins? Vote now!*\n"
        f"1️⃣  {team_a} 🏆\n"
        f"2️⃣  Draw 🤝\n"
        f"3️⃣  {team_b} 🏆\n\n"
        f"⏰ Poll closes 5 mins before kickoff!\n"
        f"🔥 +3 for correct | 0 for wrong | -2 for no vote"
    )
    try:
        driver = get_driver()
        open_wa_group(driver)
        send_wa_message(driver, msg)
        driver.quit()
        log.info(f"Poll posted for {team_a} vs {team_b}")
        return True
    except Exception as e:
        log.error(f"Failed to post poll: {e}")
        return False


def send_match_report(match, result, points_summary):
    """Send post-match report to WhatsApp group."""
    team_a   = match["Team A"]
    team_b   = match["Team B"]
    score_a  = result.get("score_a", "?")
    score_b  = result.get("score_b", "?")
    winner   = team_a if score_a > score_b else (team_b if score_b > score_a else "Draw")

    lines = [
        f"🏁 *FULL TIME — FIFA 2026*",
        f"",
        f"⚽ *{team_a} {score_a} — {score_b} {team_b}*",
        f"",
        f"📊 *Fantasy Points This Match:*",
    ]
    for player, pts in sorted(points_summary.items(), key=lambda x: -x[1]):
        emoji = "✅" if pts > 0 else ("⬜" if pts == 0 else "❌")
        lines.append(f"{emoji} {player}: {'+' if pts >= 0 else ''}{pts} pts")

    lines += [
        f"",
        f"🏆 *Updated Leaderboard:* [coming shortly]",
        f"📱 Full report: https://siddb12-cyber.github.io/fifa-fantasy-2026/match/{match['Match ID']}.html",
    ]
    msg = "\n".join(lines)

    try:
        driver = get_driver()
        open_wa_group(driver)
        send_wa_message(driver, msg)
        driver.quit()
        log.info(f"Match report sent for {team_a} vs {team_b}")
    except Exception as e:
        log.error(f"Failed to send match report: {e}")


# ── FOOTBALL-DATA.ORG API ─────────────────────────────────────────────────────
def fetch_match_result(match_id_api):
    """Fetch match result from football-data.org."""
    headers = {"X-Auth-Token": FOOTBALL_KEY}
    url     = f"{FOOTBALL_API}/matches/{match_id_api}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        score = data.get("score", {})
        ft    = score.get("fullTime", {})
        return {
            "score_a": ft.get("home"),
            "score_b": ft.get("away"),
            "status":  data.get("status"),
        }
    except Exception as e:
        log.error(f"API fetch failed for match {match_id_api}: {e}")
        return None


# ── POINTS ENGINE ─────────────────────────────────────────────────────────────
def determine_result_label(score_a, score_b):
    if score_a > score_b:
        return "home"   # Team A wins
    elif score_b > score_a:
        return "away"   # Team B wins
    else:
        return "draw"


def calc_points(player_answer, correct_result):
    """
    player_answer: 'home' | 'draw' | 'away' | None (missed)
    correct_result: 'home' | 'draw' | 'away'
    Returns: +3, 0, or -2
    """
    if player_answer is None:
        return -2   # missed
    return 3 if player_answer == correct_result else 0


def update_points(sh, match, result):
    """
    Read poll responses for this match, calculate points, update Leaderboard.
    Returns dict {player: points}
    """
    resp_ws = sh.worksheet("Poll Responses")
    all_rows = resp_ws.get_all_records()

    match_id      = match["Match ID"]
    correct_label = determine_result_label(result["score_a"], result["score_b"])

    # Map player → their answer for this match
    poll_answers = {}
    for row in all_rows:
        if row["Match ID"] == match_id:
            poll_answers[row["Player Name"]] = row["Their Answer"].lower()

    # Canonical answer mapping
    team_a = match["Team A"].lower()
    team_b = match["Team B"].lower()

    def normalise(ans):
        if team_a in ans:
            return "home"
        if team_b in ans:
            return "away"
        if "draw" in ans:
            return "draw"
        return None

    points_summary = {}
    updates        = []

    for player in PLAYERS:
        raw_ans  = poll_answers.get(player)
        norm_ans = normalise(raw_ans) if raw_ans else None
        pts      = calc_points(norm_ans, correct_label)
        points_summary[player] = pts

        # Write correct answer + points back to Poll Responses
        for i, row in enumerate(all_rows):
            if row["Match ID"] == match_id and row["Player Name"] == player:
                row_num = i + 2
                resp_ws.update_cell(row_num, 5, correct_label)   # Correct Answer
                resp_ws.update_cell(row_num, 6, pts)             # Points Awarded

        # If player missed (no row), add a missed-entry row
        if player not in poll_answers:
            resp_ws.append_row([
                match_id,
                f"{match['Team A']} vs {match['Team B']}",
                player, "MISSED", correct_label, pts,
                datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            ])

    # Update Leaderboard
    lb_ws   = sh.worksheet("Leaderboard")
    lb_rows = lb_ws.get_all_records()

    for i, row in enumerate(lb_rows):
        player = row["Player"]
        delta  = points_summary.get(player, -2)
        new_total   = int(row["Total Points"]) + delta
        new_correct = int(row["Correct"]) + (1 if delta == 3 else 0)
        new_wrong   = int(row["Wrong"])   + (1 if delta == 0 and poll_answers.get(player) else 0)
        new_missed  = int(row["Missed"])  + (1 if delta == -2 else 0)
        ts = datetime.now(IST).strftime("%d %b %Y %H:%M IST")

        row_num = i + 2
        lb_ws.update(f"F{row_num}:K{row_num}", [[new_total, new_correct, new_wrong, new_missed, "—", ts]])

    log.info(f"Points updated for match {match_id}: {points_summary}")
    return points_summary


# ── MATCH LOG UPDATE ──────────────────────────────────────────────────────────
def update_match_log(sh, match, poll_posted_at, poll_closed_at, result=None, points_done=False):
    ws = sh.worksheet("Match Log")
    # Check if entry exists
    rows = ws.get_all_records()
    existing = [r for r in rows if r["Match ID"] == match["Match ID"]]

    score_a = result["score_a"] if result else ""
    score_b = result["score_b"] if result else ""
    outcome = ""
    if result:
        if score_a > score_b:
            outcome = match["Team A"]
        elif score_b > score_a:
            outcome = match["Team B"]
        else:
            outcome = "Draw"

    row = [
        match["Match ID"],
        match["Date (IST)"],
        match["Team A"],
        match["Team B"],
        score_a, score_b, outcome,
        poll_posted_at, poll_closed_at,
        "Yes" if points_done else "No",
    ]

    if existing:
        # Find and update row
        for i, r in enumerate(rows):
            if r["Match ID"] == match["Match ID"]:
                ws.update(f"A{i+2}:J{i+2}", [row])
                break
    else:
        ws.append_row(row)


def update_schedule_status(sh, match_id, status, score_a="", score_b=""):
    ws   = sh.worksheet("Full Schedule")
    rows = ws.get_all_records()
    for i, row in enumerate(rows):
        if row["Match ID"] == match_id:
            row_num = i + 2
            ws.update_cell(row_num, 8, status)
            if score_a != "":
                ws.update_cell(row_num, 9, score_a)
            if score_b != "":
                ws.update_cell(row_num, 10, score_b)
            break


# ── MAIN SCHEDULER LOOP ───────────────────────────────────────────────────────
def run():
    log.info("=== Poll Scheduler Started ===")
    now = now_ist()
    log.info(f"Current IST: {now.strftime('%d %b %Y %H:%M')}")

    try:
        sh       = get_sheet()
        schedule = get_schedule(sh)
    except Exception as e:
        log.error(f"Could not connect to Google Sheets: {e}")
        sys.exit(1)

    for match in schedule:
        match_id = match["Match ID"]
        status   = match.get("Status", "Upcoming")
        date_str = match.get("Date (IST)", "")

        if not date_str or match["Team A"] in ("??", "TBD") or match["Team B"] in ("??", "TBD"):
            continue   # skip TBD knockouts

        try:
            kickoff = parse_ist(date_str)
        except Exception:
            log.warning(f"Cannot parse date '{date_str}' for {match_id}")
            continue

        poll_open_time  = kickoff - timedelta(hours=24)
        poll_close_time = kickoff - timedelta(minutes=5)

        # ── POST POLL ──────────────────────────────────────────────────────
        if status == "Upcoming":
            if poll_open_time <= now < poll_close_time:
                poll_posted = match.get("Poll Posted", "")
                if not poll_posted:
                    log.info(f"Posting poll for {match_id}: {match['Team A']} vs {match['Team B']}")
                    posted = post_poll(match)
                    if posted:
                        ts = now.strftime("%Y-%m-%d %H:%M IST")
                        update_match_log(sh, match, ts, "", None, False)
                        update_schedule_status(sh, match_id, "Poll Open")
                        # Record poll-posted timestamp in Full Schedule col K
                        ws = sh.worksheet("Full Schedule")
                        rows = ws.get_all_records()
                        for i, r in enumerate(rows):
                            if r["Match ID"] == match_id:
                                ws.update_cell(i + 2, 11, ts)
                                break

        # ── CLOSE POLL & RECORD RESULT ─────────────────────────────────────
        if status == "Poll Open":
            if now >= poll_close_time and now < kickoff + timedelta(hours=3):
                log.info(f"Poll time closed for {match_id}, waiting for result...")
                update_schedule_status(sh, match_id, "In Progress")

        # ── FETCH RESULT & CALCULATE POINTS ───────────────────────────────
        if status in ("In Progress", "Poll Open"):
            if now >= kickoff + timedelta(hours=2):
                log.info(f"Fetching result for {match_id}")
                # Try API first (needs FOOTBALL_KEY set)
                result = None
                if FOOTBALL_KEY:
                    # Match IDs from API would need mapping — placeholder
                    pass

                # Manual fallback: check if score is in sheet
                if match.get("Score A") and match.get("Score B"):
                    result = {
                        "score_a": int(match["Score A"]),
                        "score_b": int(match["Score B"]),
                    }

                if result and result["score_a"] is not None:
                    points = update_points(sh, match, result)
                    update_schedule_status(sh, match_id, "Completed",
                                           result["score_a"], result["score_b"])
                    send_match_report(match, result, points)
                    # Trigger dashboard rebuild
                    subprocess.Popen(
                        ["python", str(BASE_DIR / "FIFA World Cup Fantasy Game" / "scripts" / "dashboard_builder.py")],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    log.info(f"✅ Match {match_id} fully processed")

    log.info("=== Scheduler run complete ===")


if __name__ == "__main__":
    run()
