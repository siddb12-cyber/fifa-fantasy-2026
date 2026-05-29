#!/usr/bin/env python3
"""
poll_bot.py — FIFA Fantasy 2026: Telegram Poll Automation
Runs every 30 min via GitHub Actions. No machine, no scheduler, fully automated.

Sends:
  - Native Telegram poll 24h before each match
  - Text reminder 6h before
  - Text reminder 3h before
  - Final warning 90min before

Deduplication via Google Sheets "Sent Log" tab.
"""
import os, json, datetime, base64, tempfile, random
import pytz, requests, gspread
from google.oauth2.service_account import Credentials

# ── CONFIG (all from GitHub Secrets / env vars) ────────────────────────────────
TOKEN     = os.environ.get('TELEGRAM_TOKEN', '')
CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID', '')
SHEET_ID  = os.environ.get('GOOGLE_SHEET_ID', '')
GCP_CREDS = os.environ.get('GOOGLE_CREDENTIALS_JSON', '')   # base64-encoded JSON
TEST_MODE = os.environ.get('TEST_MODE', 'true').lower() == 'true'

IST  = pytz.timezone('Asia/Kolkata')
BASE = f'https://api.telegram.org/bot{TOKEN}'

# Notification windows: (type, minutes_before_match)
NOTIFS = [
    ('poll',  24 * 60),
    ('r6h',   6  * 60),
    ('r3h',   3  * 60),
    ('r90m',  90),
]
WINDOW = 29  # tolerance window in minutes (matches GitHub Actions cron interval)

# ── FUNNY ROASTS (rotated randomly) ───────────────────────────────────────────
ROASTS = [
    "Even your horoscope picked a side. Why haven't you? 🔮",
    "Pro tip: wrong answer = 0 pts. No answer = −2 pts. Do the math. 🤦",
    "The algorithm predicts you'll overthink this and still get it wrong.",
    "Fun fact: every second you wait, someone else is getting it right. 📉",
    "Your gut has an opinion. Listen to it. Or don't. We'll see.",
    "Hot take: silence is NOT a strategy. Vote. Now.",
    "Bro it's literally one tap. One. Single. Tap. ⬆️",
    "Even a coin flip is better than -2 pts. Think about it. 🪙",
    "The poll has been sitting there, waiting. Judging. 👀",
    "Champions decide early. Procrastinators pay -2 pts.",
]

OPENERS = [
    "The oracle demands your wisdom (or lack thereof).",
    "The cosmos have aligned. Your prediction, please.",
    "Destiny is calling. Pick up. 📞",
    "This is not a drill. Real points. Real consequences.",
    "Your prophecy is required. The group is watching.",
    "Intelligence optional. Participation mandatory.",
    "Place your bets, geniuses and otherwise.",
    "The fantasy gods are hungry. Feed them your prediction.",
]


# ── TELEGRAM HELPERS ──────────────────────────────────────────────────────────
def tg(method, payload):
    """Send a Telegram API request."""
    try:
        r = requests.post(f'{BASE}/{method}', json=payload, timeout=15)
        data = r.json()
        if not data.get('ok'):
            print(f'  ⚠ Telegram error ({method}): {data.get("description")}')
        return data
    except Exception as e:
        print(f'  ⚠ Request failed ({method}): {e}')
        return {}


# ── GOOGLE SHEETS HELPERS ─────────────────────────────────────────────────────
def connect_sheets():
    """Connect to Google Sheets using base64-encoded credentials from env."""
    if not GCP_CREDS or not SHEET_ID:
        print('  ⚠ No Google credentials or Sheet ID — skipping Sheets logging')
        return None
    try:
        creds_dict = json.loads(base64.b64decode(GCP_CREDS.encode()).decode())
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_dict, f)
            creds_path = f.name
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        print('  ✅ Google Sheets connected')
        return gc
    except Exception as e:
        print(f'  ⚠ Sheets connection failed: {e}')
        return None


def get_sent_log(gc):
    """Return set of 'match_id::notif_type' already sent."""
    if not gc:
        return set()
    try:
        sh = gc.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet('Sent Log')
        except:
            ws = sh.add_worksheet('Sent Log', rows=1000, cols=6)
            ws.append_row(['Match ID', 'Notif Type', 'Telegram Poll ID', 'Sent At', 'Match Time IST', 'Mode'])
        rows = ws.get_all_values()
        return {f"{r[0]}::{r[1]}" for r in rows[1:] if len(r) >= 2}
    except Exception as e:
        print(f'  ⚠ Sheets get_sent_log failed: {e}')
        return set()


def log_sent(gc, match_id, notif_type, poll_id='', match_datetime=''):
    """Log a sent notification to Google Sheets."""
    if not gc:
        return
    try:
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet('Sent Log')
        now_str = datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')
        ws.append_row([match_id, notif_type, poll_id, now_str, match_datetime, 'TEST' if TEST_MODE else 'PROD'])
        print(f'  ✅ Logged to Sheets: {match_id}::{notif_type}')
    except Exception as e:
        print(f'  ⚠ Sheets log_sent failed: {e}')


# ── TIME HELPERS ──────────────────────────────────────────────────────────────
def parse_ist(s):
    """Parse 'DD Mon YYYY HH:MM' in IST."""
    for fmt in ('%d %b %Y %H:%M', '%d %B %Y %H:%M'):
        try:
            return IST.localize(datetime.datetime.strptime(s.strip(), fmt))
        except ValueError:
            continue
    raise ValueError(f'Cannot parse datetime: {s}')


def tz_times(dt_ist):
    """Return kickoff times in multiple time zones."""
    zones = {
        '🇮🇳 IST':     'Asia/Kolkata',
        '🇺🇸 Texas':   'America/Chicago',
        '🇺🇸 LA':      'America/Los_Angeles',
        '🇩🇪 Germany': 'Europe/Berlin',
    }
    lines = []
    for label, tz in zones.items():
        local = dt_ist.astimezone(pytz.timezone(tz))
        lines.append(f"  {label}: {local.strftime('%I:%M %p %Z')}")
    return '\n'.join(lines)


# ── MESSAGE BUILDERS ──────────────────────────────────────────────────────────
def build_poll_caption(match):
    """24h poll caption — creative, funny, multi-timezone."""
    ta, tb = match['team_a'], match['team_b']
    dt     = parse_ist(match['datetime_ist'])
    stage  = match.get('stage', 'Match')
    opener = random.choice(OPENERS)
    times  = tz_times(dt)

    return (
        f"⚽ *FIFA FANTASY 2026 — {stage.upper()}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏟  *{ta}*  ⚔️  *{tb}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🕐 *Kickoff times:*\n{times}\n\n"
        f"🎯 _{opener}_\n\n"
        f"Vote in the poll below 👇\n"
        f"⚠️ *No vote = −2 pts.* Don't ghost the poll."
    )


def build_reminder(match, notif_type):
    """Reminder messages — increasingly urgent and roast-y."""
    ta, tb = match['team_a'], match['team_b']
    dt     = parse_ist(match['datetime_ist'])
    time   = dt.strftime('%I:%M %p IST')
    roast  = random.choice(ROASTS)

    if notif_type == 'r6h':
        return (
            f"⏰ *6 HOURS LEFT | {ta} vs {tb}*\n\n"
            f"Poll closes at kickoff ({time}).\n\n"
            f"_{roast}_\n\n"
            f"Scroll up ↑ tap your pick. Done."
        )
    elif notif_type == 'r3h':
        return (
            f"🔔 *3 HOURS | {ta} vs {tb}*\n\n"
            f"THREE HOURS. That's 180 minutes of regret if you miss this.\n\n"
            f"_{roast}_\n\n"
            f"⬆️ Poll is waiting. Your -2 pts are loading..."
        )
    elif notif_type == 'r90m':
        return (
            f"🚨 *LAST CALL — 90 MIN TO KICKOFF*\n\n"
            f"*{ta}* ⚔️ *{tb}* is happening. Right now. Almost.\n\n"
            f"If you haven't voted yet → 👻 you are *that person.*\n\n"
            f"Final warning. Scroll up. One tap. Save yourself. ⬆️"
        )
    return ''


# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
def main():
    if not TOKEN or not CHAT_ID:
        print('❌ TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set. Exiting.')
        return

    # Load match schedule
    schedule_file = 'scripts/test_matches.json' if TEST_MODE else 'scripts/matches.json'
    with open(schedule_file) as f:
        matches = json.load(f)

    gc       = connect_sheets()
    sent_log = get_sent_log(gc)
    now_ist  = datetime.datetime.now(IST)

    print(f'\n⏰ Poll Bot running at {now_ist.strftime("%d %b %Y %H:%M IST")}')
    print(f'   Mode: {"🧪 TEST" if TEST_MODE else "🏆 PRODUCTION"}  |  Schedule: {len(matches)} matches\n')

    sent_count = 0

    for match in matches:
        try:
            match_time = parse_ist(match['datetime_ist'])
        except ValueError as e:
            print(f'  ⚠ Skipping {match["id"]}: {e}')
            continue

        diff_min = (match_time - now_ist).total_seconds() / 60

        # Skip past matches entirely
        if diff_min < -120:
            continue

        for notif_type, threshold in NOTIFS:
            key = f"{match['id']}::{notif_type}"

            if key in sent_log:
                continue  # already sent

            # Are we inside the 30-min window for this notification?
            if threshold - WINDOW < diff_min <= threshold:
                ta, tb = match['team_a'], match['team_b']
                print(f'  📨 [{notif_type}] {match["id"]} — {ta} vs {tb}  (in {diff_min:.0f} min)')

                poll_id = ''

                if notif_type == 'poll':
                    # Step 1: Send the caption/context message
                    tg('sendMessage', {
                        'chat_id':    CHAT_ID,
                        'text':       build_poll_caption(match),
                        'parse_mode': 'Markdown',
                    })
                    # Step 2: Send native Telegram poll
                    resp = tg('sendPoll', {
                        'chat_id':               CHAT_ID,
                        'question':              f'⚽ {ta}  vs  {tb} — Who wins?',
                        'options':               [
                            f'🔵 {ta} wins',
                            f'🤝 Draw (the diplomat choice)',
                            f'🔴 {tb} wins',
                        ],
                        'is_anonymous':          False,
                        'allows_multiple_answers': False,
                        'protect_content':       False,
                    })
                    result = resp.get('result', {})
                    poll_id = result.get('poll', {}).get('id', '')

                else:
                    msg = build_reminder(match, notif_type)
                    if msg:
                        tg('sendMessage', {
                            'chat_id':    CHAT_ID,
                            'text':       msg,
                            'parse_mode': 'Markdown',
                        })

                log_sent(gc, match['id'], notif_type, poll_id, match['datetime_ist'])
                sent_count += 1

    if sent_count == 0:
        print('  ✅ Nothing to send right now.')
    else:
        print(f'\n  ✅ Sent {sent_count} notification(s).')


if __name__ == '__main__':
    main()
