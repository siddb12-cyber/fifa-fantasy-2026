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
FORCE       = os.environ.get('FORCE_SEND', 'false').lower() == 'true'   # bypass timing check
FORCE_MATCH = os.environ.get('FORCE_MATCH', '').strip()               # specific match ID to force (e.g. T002)

# ── PLAYER TELEGRAM ID MAPPING ─────────────────────────────────────────────────
# Map each player's Telegram user_id → pet name. Add as they join the group.
PLAYER_IDS = {
    8331670846: 'Budhya',   # Sidhant
    # Add others once they send /start in the group and you get their IDs:
    # 123456789: 'Ambu',
    # 987654321: 'Vini',
    # 111111111: 'Baby',
    # 222222222: 'Abs',
    # 333333333: 'Anna',
    # 444444444: 'Umaga',
    # 555555555: 'PR',
}
PLAYERS_ALL = ['Budhya', 'Ambu', 'Vini', 'Baby', 'Abs', 'Anna', 'Umaga', 'PR']

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


# ── POLL ANSWER COLLECTION ────────────────────────────────────────────────────
def get_update_offset(gc):
    """Get last processed Telegram update offset from Sheets (Bot Config tab)."""
    if not gc:
        return 0
    try:
        sh = gc.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet('Bot Config')
        except:
            ws = sh.add_worksheet('Bot Config', rows=20, cols=2)
            ws.append_row(['Key', 'Value'])
            ws.append_row(['update_offset', '0'])
            return 0
        for row in ws.get_all_values()[1:]:
            if row and row[0] == 'update_offset':
                return int(row[1] or 0)
        return 0
    except Exception as e:
        print(f'  ⚠ get_update_offset failed: {e}')
        return 0


def save_update_offset(gc, offset):
    """Save last processed update offset to Bot Config sheet."""
    if not gc or not offset:
        return
    try:
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet('Bot Config')
        rows = ws.get_all_values()
        for i, row in enumerate(rows):
            if row and row[0] == 'update_offset':
                ws.update_cell(i + 1, 2, str(offset))
                return
        ws.append_row(['update_offset', str(offset)])
    except Exception as e:
        print(f'  ⚠ save_update_offset failed: {e}')


def collect_poll_answers(gc, match_lookup):
    """
    Fetch Telegram poll_answer updates and write votes to Poll Responses sheet.
    match_lookup: {match_id: {team_a, team_b}} built from schedule file.
    """
    if not gc or not TOKEN:
        return

    offset   = get_update_offset(gc)
    print(f'\n📥 Collecting poll answers (offset: {offset})...')

    # Build poll_id → match_id map from Sent Log
    poll_map = {}
    try:
        sh      = gc.open_by_key(SHEET_ID)
        log_ws  = sh.worksheet('Sent Log')
        for row in log_ws.get_all_records():
            pid = str(row.get('Telegram Poll ID', '')).strip()
            mid = str(row.get('Match ID', '')).strip()
            if pid and mid:
                poll_map[pid] = mid
    except Exception as e:
        print(f'  ⚠ Could not load Sent Log: {e}')
        return

    if not poll_map:
        print('  ℹ No polls in Sent Log yet — skipping.')
        return

    # Fetch updates
    try:
        r = requests.get(
            f'{BASE}/getUpdates',
            params={'offset': offset + 1, 'allowed_updates': '["poll_answer"]', 'timeout': 5},
            timeout=15
        )
        updates = r.json().get('result', [])
    except Exception as e:
        print(f'  ⚠ getUpdates failed: {e}')
        return

    if not updates:
        print('  ✅ No new poll answers.')
        return

    # Open / create Poll Responses sheet
    try:
        resp_ws = sh.worksheet('Poll Responses')
    except:
        resp_ws = sh.add_worksheet('Poll Responses', rows=1000, cols=7)
        resp_ws.append_row(['Match ID', 'Match Name', 'Player Name',
                             'Their Answer', 'Correct Answer', 'Points Awarded', 'Timestamp'])

    existing  = {f"{r['Match ID']}::{r['Player Name']}"
                 for r in resp_ws.get_all_records() if r.get('Match ID')}
    new_count = 0
    max_uid   = offset

    for update in updates:
        uid = update.get('update_id', 0)
        if uid > max_uid:
            max_uid = uid

        pa = update.get('poll_answer')
        if not pa:
            continue

        poll_id     = str(pa.get('poll_id', ''))
        user_id     = pa.get('user', {}).get('id')
        option_ids  = pa.get('option_ids', [])
        option      = option_ids[0] if option_ids else None

        player = PLAYER_IDS.get(user_id)
        if not player:
            print(f'  ⚠ Unknown user_id {user_id} — add to PLAYER_IDS dict')
            continue

        match_id = poll_map.get(poll_id)
        if not match_id:
            print(f'  ⚠ Unknown poll_id {poll_id}')
            continue

        key = f'{match_id}::{player}'
        if key in existing:
            continue  # already recorded

        # Resolve option index → answer text using match teams
        info    = match_lookup.get(match_id, {})
        ta      = info.get('team_a', 'Team A')
        tb      = info.get('team_b', 'Team B')
        options = [f'{ta} wins', 'Draw', f'{tb} wins']
        answer  = options[option] if option is not None and option < 3 else 'Unknown'

        match_name = f'{ta} vs {tb}'
        ts         = datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')
        resp_ws.append_row([match_id, match_name, player, answer, '', '', ts])
        existing.add(key)
        new_count += 1
        print(f'  ✅ {player} → {answer} ({match_id})')

    save_update_offset(gc, max_uid)
    print(f'  ✅ {new_count} new answer(s) recorded. Offset saved: {max_uid}')


# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
def main():
    if not TOKEN or not CHAT_ID:
        print('❌ TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set. Exiting.')
        return

    # Load match schedule
    schedule_file = 'scripts/test_matches.json' if TEST_MODE else 'scripts/matches.json'
    with open(schedule_file) as f:
        matches = json.load(f)

    # Build match_id → {team_a, team_b} lookup for answer resolution
    match_lookup = {m['id']: {'team_a': m['team_a'], 'team_b': m['team_b']} for m in matches}

    gc = connect_sheets()

    # ── Step 1: Collect any pending poll answers from Telegram ─────────────────
    collect_poll_answers(gc, match_lookup)

    # ── Step 2: Send scheduled polls / reminders ───────────────────────────────
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

            if key in sent_log and not FORCE:
                continue  # already sent

            # Are we inside the 30-min window? OR force-sending the first match's poll
            in_window = threshold - WINDOW < diff_min <= threshold
            # Force: if FORCE_MATCH specified, target that match; else default to first match
            target_id  = FORCE_MATCH if FORCE_MATCH else matches[0]['id']
            force_this = FORCE and match['id'] == target_id and notif_type == 'poll'

            if not in_window and not force_this:
                continue

            ta, tb = match['team_a'], match['team_b']
            print(f'  📨 [{notif_type}] {match["id"]} — {ta} vs {tb}  (in {diff_min:.0f} min)')

            poll_id = ''

            if notif_type == 'poll':
                # Step 1: Send caption/context message
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
