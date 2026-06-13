# FIFA Fantasy 2026 — Claude Code Instructions

## Project Identity
- **Name:** FIFA World Cup Fantasy Game 2026
- **GitHub Pages:** `https://siddb12-cyber.github.io/fifa-fantasy-2026/`
- **Google Sheet:** ID in `GOOGLE_SHEET_ID` GitHub Secret — sheet name "FIFA World Cup 2026"
- **Google Account:** siddb12@gmail.com
- **Telegram Group:** "FIFA World Cup Fantasy" | Bot: @fifafantasycircle_bot
- **Credentials file (local):** `C:/Users/siddh/Downloads/HK/FIFA/google_credentials.json`

## Stack
- **Language:** Python 3.11
- **Automation:** GitHub Actions (no local scheduler — runs 24/7 serverless)
- **Storage:** Google Sheets (gspread + google-auth)
- **Notifications:** Telegram Bot API (poll_bot.py)
- **Frontend:** Static HTML/CSS/JS on GitHub Pages (no framework, no build step)
- **Stats source:** football-data.org free tier (FOOTBALL_API_KEY secret)

## Repo Layout
```
scripts/
  poll_bot.py          # Core: sends Telegram polls + reminders + auto-scores
  sheets_updater.py    # Manual/CLI: record responses, recalc leaderboard
  dashboard_builder.py # Reads Sheets → writes index.html, stats.html, match/{id}.html
  stats_fetcher.py     # Reads football-data.org → writes Sheet Player/Team Stats tabs
  reset_tournament.py  # One-shot: clear trial data (run with --execute, else --dry-run)
  matches.json         # 104-match production schedule
  trial_matches.json   # 8-match trial schedule (used during testing)
  test_matches.json    # Small test schedule
.github/workflows/
  poll_scheduler.yml   # Every 30 min → poll_bot.py
  stats_updater.yml    # Every 2h → stats_fetcher.py → dashboard_builder.py → git push
assets/avatars/        # Player profile pics + generated PNGs
assets/animations/     # Celebration GIFs per player
match/template.html    # Template for per-match preview/report pages
logs/
  MASTER_STATE.md      # Phase status, history
  session_*.md         # Per-session logs
  memory.md (root)     # Working memory updated mid-session
```

## Google Sheets Tabs
| Tab | Purpose |
|-----|---------|
| Leaderboard | Ranks + points per player |
| Poll Responses | Every vote: Match ID, Player, Answer, Points |
| Full Schedule | 104 matches with Status, Score A/B |
| Sent Log | Deduplication log for poll_bot.py |
| Bot Config | Telegram update_offset persistence |
| Player IDs | Telegram user_id → Pet Name mapping |
| Match Log | Manual match result log |
| Player Stats | From stats_fetcher.py |
| Team Stats | From stats_fetcher.py |
| Bonus Polls | Google Form responses (new — NOT yet used by any script) |

## Players
| Pet Name | Full Name |
|----------|-----------|
| Budhya | Sidhant Budhkar (owner) |
| Ambu | Kushal Ambulkar |
| Vini | Vineet Nayak |
| Baby | Susmit Gulavani |
| Abs | Abhishek Desai |
| Anna | Nishant Salian |
| Umaga | Umang Budhkar |
| PR | Pranav Raut |
| Ash | Ashish (last name TBD) — **DO NOT modify PLAYERS_META or avatar integration** |

## Scoring Rules
- Correct prediction: **+3 pts**
- Wrong prediction: **0 pts**
- Missed/no vote: **−2 pts**

## Key Env Vars / GitHub Secrets
| Name | Used by |
|------|---------|
| TELEGRAM_TOKEN | poll_bot.py |
| TELEGRAM_CHAT_ID | poll_bot.py |
| GOOGLE_SHEET_ID | poll_bot.py, dashboard_builder.py, stats_fetcher.py |
| GOOGLE_CREDENTIALS_JSON | all scripts (base64-encoded service account JSON) |
| FOOTBALL_API_KEY | stats_fetcher.py |
| GITHUB_TOKEN | stats_updater.yml git push |

## poll_bot.py Modes
| Env Var | Default | Effect |
|---------|---------|--------|
| TRIAL_MODE=true | true (hardcoded in workflow) | Uses trial_matches.json |
| TEST_MODE=false | false | Logs 'TEST' or 'PROD' to Sheets |
| FORCE_SEND=true | false | Bypasses timing window |
| FORCE_MATCH=M007 | '' | Targets specific match for force-send |

## Notification Schedule (per match)
- Poll sent **24h before kickoff**
- Reminder at **6h, 3h, 90min before**
- Poll closed **60min before kickoff**
- Window tolerance: ±90 min (covers 3 GitHub Actions cron cycles)

## Standing Deferrals — DO NOT TOUCH
- **Ash player integration:** avatar + PLAYERS_META not finalized
- **Telegram deprecation:** planned but not started — do not touch poll_bot.py, Telegram workflows, or secrets
- **Bonus Polls tab:** new Google Form tab added 2026-06-13, not yet wired to any script

## Behavior Rules
- Be autonomous; only ask when a credential is missing or an action is irreversible.
- Write code that runs on Windows (PowerShell-safe paths).
- Prefer free tools and globally accessible APIs (no geo-restricted services).
- Update `memory.md` and `PROJECT_STATE.md` after completing major work.
- After any file changes intended for GitHub Pages, the user must commit + push (or trigger stats_updater.yml).
- dashboard_builder.py reads directly from Google Sheets — always rebuild dashboard after Sheet changes.
- Sandbox cannot reach `oauth2.googleapis.com` — Sheet-mutating scripts must run locally or via GitHub Actions workflow_dispatch.

## Session Protocol
- Read `logs/MASTER_STATE.md` and `memory.md` at the start of every session.
- Write a session log to `logs/session_YYYY-MM-DD.md` at session end.
- Never ask the user to repeat prior context — use session logs.
