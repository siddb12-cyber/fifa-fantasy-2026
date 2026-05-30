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
TRIAL_MODE  = os.environ.get('TRIAL_MODE',  'false').lower() == 'true' # use trial_matches.json

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
            ws = sh.add_worksheet('Sent Log', rows=1000, cols=7)
            ws.append_row(['Match ID', 'Notif Type', 'Telegram Poll ID', 'Message ID', 'Sent At', 'Match Time IST', 'Mode'])
        rows = ws.get_all_values()
        return {f"{r[0]}::{r[1]}" for r in rows[1:] if len(r) >= 2}
    except Exception as e:
        print(f'  ⚠ Sheets get_sent_log failed: {e}')
        return set()


def get_poll_message_ids(gc):
    """Return {match_id: telegram_message_id} for all sent polls — used for reply-to on reminders."""
    if not gc:
        return {}
    try:
        sh   = gc.open_by_key(SHEET_ID)
        ws   = sh.worksheet('Sent Log')
        rows = ws.get_all_records()
        result = {}
        for row in rows:
            if row.get('Notif Type') == 'poll':
                mid = str(row.get('Message ID', '')).strip()
                if mid and mid.isdigit():
                    result[str(row.get('Match ID', ''))] = int(mid)
        return result
    except Exception as e:
        print(f'  ⚠ get_poll_message_ids failed: {e}')
        return {}


def log_sent(gc, match_id, notif_type, poll_id='', message_id='', match_datetime=''):
    """Log a sent notification to Google Sheets."""
    if not gc:
        return
    try:
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet('Sent Log')
        now_str = datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')
        ws.append_row([match_id, notif_type, poll_id, str(message_id), now_str, match_datetime, 'TEST' if TEST_MODE else 'PROD'])
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


# ── PLAYER ID SHEET HELPERS ───────────────────────────────────────────────────
def get_or_create_player_ids_sheet(gc):
    """Return the 'Player IDs' worksheet, creating it if needed."""
    sh = gc.open_by_key(SHEET_ID)
    try:
        return sh.worksheet('Player IDs')
    except:
        ws = sh.add_worksheet('Player IDs', rows=50, cols=4)
        ws.append_row(['Telegram Name', 'User ID', 'Pet Name', 'Joined At'])
        # Pre-seed Sidhant so existing votes still work
        ws.append_row(['Sidhant', '8331670846', 'Budhya',
                       datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')])
        return ws


def load_player_ids(gc):
    """Load {user_id (int): pet_name} from 'Player IDs' sheet."""
    if not gc:
        return {}
    try:
        ws   = get_or_create_player_ids_sheet(gc)
        rows = ws.get_all_records()
        result = {}
        for row in rows:
            uid  = str(row.get('User ID', '')).strip()
            name = str(row.get('Pet Name', '')).strip()
            if uid.isdigit() and name:
                result[int(uid)] = name
        return result
    except Exception as e:
        print(f'  ⚠ load_player_ids failed: {e}')
        return {}


def log_new_member(gc, user_id, telegram_name):
    """Log a new group member to 'Player IDs' sheet (Pet Name left blank for Sidhant to fill)."""
    if not gc:
        return
    try:
        ws   = get_or_create_player_ids_sheet(gc)
        rows = ws.get_all_records()
        # Don't duplicate
        for row in rows:
            if str(row.get('User ID', '')) == str(user_id):
                return
        ts = datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')
        ws.append_row([telegram_name, str(user_id), '', ts])
        print(f'  📋 New member logged: {telegram_name} (ID: {user_id}) — fill Pet Name in sheet')
    except Exception as e:
        print(f'  ⚠ log_new_member failed: {e}')


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


def collect_updates(gc, match_lookup, player_ids):
    """
    Process Telegram updates:
      - new_chat_members → log to Player IDs sheet for Sidhant to map
      - poll_answer      → record vote to Poll Responses sheet
    player_ids: {user_id (int): pet_name} loaded from sheet.
    """
    if not gc or not TOKEN:
        return

    offset = get_update_offset(gc)
    print(f'\n📥 Processing updates (offset: {offset})...')

    # Build poll_id → match_id map from Sent Log
    poll_map = {}
    try:
        sh     = gc.open_by_key(SHEET_ID)
        log_ws = sh.worksheet('Sent Log')
        for row in log_ws.get_all_records():
            pid = str(row.get('Telegram Poll ID', '')).strip()
            mid = str(row.get('Match ID', '')).strip()
            if pid and mid:
                poll_map[pid] = mid
    except Exception as e:
        print(f'  ⚠ Could not load Sent Log: {e}')
        return

    # Fetch both message (for joins) and poll_answer updates
    try:
        r = requests.get(
            f'{BASE}/getUpdates',
            params={
                'offset':          offset + 1,
                'allowed_updates': '["message","poll_answer"]',
                'timeout':         5
            },
            timeout=15
        )
        updates = r.json().get('result', [])
    except Exception as e:
        print(f'  ⚠ getUpdates failed: {e}')
        return

    if not updates:
        print('  ✅ No new updates.')
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
    new_votes = 0
    max_uid   = offset

    for update in updates:
        uid = update.get('update_id', 0)
        if uid > max_uid:
            max_uid = uid

        # ── Handle new members joining ────────────────────────────────────────
        msg = update.get('message', {})
        new_members = msg.get('new_chat_members', [])
        for member in new_members:
            if member.get('is_bot'):
                continue  # skip bots joining
            user_id  = member.get('id')
            tg_name  = (member.get('first_name', '') + ' ' +
                        member.get('last_name', '')).strip()
            username = member.get('username', '')
            display  = f"{tg_name} (@{username})" if username else tg_name
            log_new_member(gc, user_id, display)

        # ── Handle poll answers ───────────────────────────────────────────────
        pa = update.get('poll_answer')
        if not pa:
            continue

        poll_id    = str(pa.get('poll_id', ''))
        user_id    = pa.get('user', {}).get('id')
        option_ids = pa.get('option_ids', [])
        option     = option_ids[0] if option_ids else None

        player = player_ids.get(user_id)
        if not player:
            tg_name = pa.get('user', {}).get('first_name', str(user_id))
            print(f'  ⚠ {tg_name} (ID: {user_id}) voted but has no Pet Name yet — fill in Player IDs sheet')
            continue

        match_id = poll_map.get(poll_id)
        if not match_id:
            continue

        key = f'{match_id}::{player}'
        if key in existing:
            continue

        info    = match_lookup.get(match_id, {})
        ta      = info.get('team_a', 'Team A')
        tb      = info.get('team_b', 'Team B')
        options = [f'{ta} wins', 'Draw', f'{tb} wins']
        answer  = options[option] if option is not None and option < 3 else 'Unknown'

        ts = datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')
        resp_ws.append_row([match_id, f'{ta} vs {tb}', player, answer, '', '', ts])
        existing.add(key)
        new_votes += 1
        print(f'  ✅ {player} → {answer} ({match_id})')

    save_update_offset(gc, max_uid)
    print(f'  ✅ {new_votes} vote(s) recorded. Offset saved: {max_uid}')


# ── AUTO-SCORING ──────────────────────────────────────────────────────────────
def get_correct_answer(score_a, score_b, team_a, team_b):
    """Derive the correct poll answer from match scores."""
    try:
        sa, sb = int(score_a), int(score_b)
    except (ValueError, TypeError):
        return None
    if sa > sb:
        return f'{team_a} wins'
    elif sb > sa:
        return f'{team_b} wins'
    else:
        return 'Draw'


def score_completed_matches(gc, match_lookup):
    """
    Auto-scores all completed matches in Full Schedule.
    For each completed match:
      - Reads Score A / Score B → derives correct answer
      - Fills 'Correct Answer' + 'Points Awarded' for all existing Poll Response rows
      - Adds MISSED rows (−2 pts) for players who never voted
      - Updates Leaderboard totals
    Only processes rows where 'Correct Answer' is still blank (idempotent).
    """
    if not gc:
        return
    try:
        sh       = gc.open_by_key(SHEET_ID)
        sched_ws = sh.worksheet('Full Schedule')
        resp_ws  = sh.worksheet('Poll Responses')
    except Exception as e:
        print(f'  ⚠ score_completed_matches: sheet open failed: {e}')
        return

    schedule = sched_ws.get_all_records()
    resp_rows = resp_ws.get_all_values()   # raw, including header
    if not resp_rows:
        return
    header    = resp_rows[0]
    # Column indices (0-based)
    try:
        col_mid     = header.index('Match ID')
        col_answer  = header.index('Their Answer')
        col_correct = header.index('Correct Answer')
        col_pts     = header.index('Points Awarded')
    except ValueError as e:
        print(f'  ⚠ Poll Responses header missing column: {e}')
        return

    ts = datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')
    scored_matches = 0

    for match in schedule:
        status  = str(match.get('Status', '')).strip()
        score_a = str(match.get('Score A', '')).strip()
        score_b = str(match.get('Score B', '')).strip()
        mid     = str(match.get('Match ID', '')).strip()

        if status != 'Completed' or not score_a or not score_b or not mid:
            continue

        info    = match_lookup.get(mid, {})
        team_a  = info.get('team_a') or match.get('Team A', '')
        team_b  = info.get('team_b') or match.get('Team B', '')
        correct = get_correct_answer(score_a, score_b, team_a, team_b)
        if not correct:
            print(f'  ⚠ Could not derive correct answer for {mid} (scores: {score_a}-{score_b})')
            continue

        # Find all response rows for this match (1-based row numbers in sheet)
        voted_players = set()
        rows_to_update = []   # (sheet_row_number, correct_answer, points)

        for i, row in enumerate(resp_rows[1:], start=2):   # row 2 onwards
            if len(row) <= max(col_mid, col_correct):
                continue
            if row[col_mid] != mid:
                continue
            # Only score if Correct Answer is blank (avoid re-scoring)
            if str(row[col_correct]).strip():
                voted_players.add(row[col_answer].replace(' wins', '').strip() if False else
                                  # just track the player name from a parallel col
                                  row[header.index('Player Name')] if 'Player Name' in header else '')
                # Still track who voted even if already scored
                if 'Player Name' in header:
                    voted_players.add(row[header.index('Player Name')])
                continue

            player_name = row[header.index('Player Name')] if 'Player Name' in header else ''
            their_ans   = str(row[col_answer]).strip()
            pts         = 3 if their_ans == correct else 0
            rows_to_update.append((i, correct, pts, player_name))
            voted_players.add(player_name)

        # Batch-update scored rows
        for (row_num, correct_ans, pts, _) in rows_to_update:
            try:
                resp_ws.update_cell(row_num, col_correct + 1, correct_ans)
                resp_ws.update_cell(row_num, col_pts + 1, pts)
            except Exception as e:
                print(f'  ⚠ Failed to update row {row_num}: {e}')

        # Add MISSED rows for players who never voted
        for player in PLAYERS_ALL:
            if player not in voted_players:
                match_name = f'{team_a} vs {team_b}'
                try:
                    resp_ws.append_row([mid, match_name, player, 'MISSED', correct, -2, ts])
                    print(f'  📋 MISSED: {player} → {mid} (−2 pts)')
                except Exception as e:
                    print(f'  ⚠ Failed to add MISSED row for {player}: {e}')

        if rows_to_update:
            print(f'  ✅ Scored {len(rows_to_update)} vote(s) for {mid} | Correct: {correct}')
        scored_matches += 1

    if scored_matches:
        update_leaderboard(gc)


def update_leaderboard(gc):
    """Re-derive leaderboard totals from Poll Responses and update Leaderboard tab."""
    if not gc:
        return
    try:
        sh      = gc.open_by_key(SHEET_ID)
        resp_ws = sh.worksheet('Poll Responses')
        lb_ws   = sh.worksheet('Leaderboard')
    except Exception as e:
        print(f'  ⚠ update_leaderboard: sheet open failed: {e}')
        return

    rows = resp_ws.get_all_records()
    totals = {p: {'total': 0, 'correct': 0, 'wrong': 0, 'missed': 0} for p in PLAYERS_ALL}

    for row in rows:
        player = str(row.get('Player Name', '')).strip()
        if player not in totals:
            continue
        pts       = int(row.get('Points Awarded') or 0)
        their_ans = str(row.get('Their Answer', '')).strip()
        totals[player]['total'] += pts
        if pts == 3:
            totals[player]['correct'] += 1
        elif their_ans == 'MISSED':
            totals[player]['missed'] += 1
        else:
            totals[player]['wrong'] += 1

    lb_rows = lb_ws.get_all_records()
    ts      = datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')

    for i, row in enumerate(lb_rows):
        player  = str(row.get('Player', '')).strip()
        if player not in totals:
            continue
        d       = totals[player]
        row_num = i + 2   # 1-based + header row
        try:
            lb_ws.update(f'D{row_num}:I{row_num}', [[
                d['total'], d['correct'], d['wrong'], d['missed'], '—', ts
            ]])
        except Exception as e:
            print(f'  ⚠ Failed to update leaderboard row for {player}: {e}')

    # Re-rank by total points
    lb_all = lb_ws.get_all_records()
    ranked = sorted(enumerate(lb_all, start=2), key=lambda x: -int(x[1].get('Total Points', 0) or 0))
    for rank, (row_num, _) in enumerate(ranked, start=1):
        try:
            lb_ws.update_cell(row_num, 1, rank)
        except Exception as e:
            print(f'  ⚠ Failed to update rank: {e}')

    print(f'  ✅ Leaderboard updated.')


# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
def main():
    if not TOKEN or not CHAT_ID:
        print('❌ TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set. Exiting.')
        return

    # Load match schedule
    if TRIAL_MODE:
        schedule_file = 'scripts/trial_matches.json'
    elif TEST_MODE:
        schedule_file = 'scripts/test_matches.json'
    else:
        schedule_file = 'scripts/matches.json'
    with open(schedule_file) as f:
        matches = json.load(f)

    # Build match_id → {team_a, team_b} lookup for answer resolution
    match_lookup = {m['id']: {'team_a': m['team_a'], 'team_b': m['team_b']} for m in matches}

    gc = connect_sheets()

    # ── Step 1: Load player ID mapping from sheet ───────────────────────────────
    player_ids = load_player_ids(gc)
    print(f'  👥 {len(player_ids)} player(s) mapped in sheet.')

    # ── Step 2: Process updates (new joins + poll answers) ──────────────────────
    collect_updates(gc, match_lookup, player_ids)

    # ── Step 3: Auto-score completed matches → update leaderboard ──────────────
    print('\n🏆 Checking for completed matches to score...')
    score_completed_matches(gc, match_lookup)

    # ── Step 4: Send scheduled polls / reminders ───────────────────────────────
    sent_log        = get_sent_log(gc)
    poll_msg_ids    = get_poll_message_ids(gc)   # {match_id: message_id} for reply-to
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

            poll_id    = ''
            message_id = ''

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
                result     = resp.get('result', {})
                poll_id    = result.get('poll', {}).get('id', '')
                message_id = str(result.get('message_id', ''))
                # Cache immediately so same-run reminders can use it
                if message_id:
                    poll_msg_ids[match['id']] = int(message_id)

            else:
                msg = build_reminder(match, notif_type)
                if msg:
                    payload = {
                        'chat_id':    CHAT_ID,
                        'text':       msg,
                        'parse_mode': 'Markdown',
                    }
                    # Reply to the original poll so players can tap to jump straight to it
                    reply_id = poll_msg_ids.get(match['id'])
                    if reply_id:
                        payload['reply_to_message_id'] = reply_id
                    tg('sendMessage', payload)

            log_sent(gc, match['id'], notif_type, poll_id, message_id, match['datetime_ist'])
            sent_count += 1

    if sent_count == 0:
        print('  ✅ Nothing to send right now.')
    else:
        print(f'\n  ✅ Sent {sent_count} notification(s).')


if __name__ == '__main__':
    main()
