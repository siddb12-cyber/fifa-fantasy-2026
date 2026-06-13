# FIFA 2026 Predictor League — Reset & Dashboard Automation — Working Memory

_Last updated: 2026-06-13_

> **See also:** [CLAUDE.md](CLAUDE.md) (project conventions + standing deferrals) | [PROJECT_STATE.md](PROJECT_STATE.md) (current phase + file status)

## Critical Rules (governing this whole effort)
1. Maintain this memory.md, update after every completed task.
2. Never read the entire repo / never recursive full scans.
3. Never read large files completely — chunks of ≤100-200 lines.
4. Never inspect multiple large files simultaneously.
5. No package installs unless required.
6. No destructive actions without explicit approval.
7. Minimal context usage; show progress after every step.
8. Avoid loading generated/asset/build/log/.git/node_modules content unless needed.
9. If context gets high: stop, update this file, give a continuation prompt.

## Standing Deferrals (DO NOT touch)
- **Ash**: full name TBD later. Do NOT modify `PLAYERS_META`, leaderboard player mappings, or avatar integration. Avatar files already exist (`assets/avatars/Ashish (Ash).jpeg`, `ash_avatar.png`, untracked).
- **Telegram**: deprecation planned but NOT started. Do not touch `poll_bot.py`, Telegram workflows, or Telegram secrets.
- **poll_scheduler.yml**: future role = Sheet processing → leaderboard recalc → dashboard rebuild → deploy. Not implemented yet.

## Active Scope: "Option B Reset" (full tournament reset prep, go-live 2026-06-12)
**Sheet — remove**: poll responses, trial predictions, trial results, trial points; **reset**: leaderboard scores + ranks.
**Sheet — preserve**: structure, formulas, tabs, fixtures (Full Schedule), player master data.
**Dashboard — remove**: generated trial stats, prediction summaries, leaderboard output, trial match pages.
**Dashboard — rebuild**: only AFTER approval.

## Phase 1 — Discovery (COMPLETE)
Findings below. Output delivered to user in chat in the required format. **APPROVED by user 2026-06-11.** Proceeding to Phase 2 planning.

### Sheet tabs (live spreadsheet "FIFA World Cup 2026", ID in GOOGLE_SHEET_ID secret)
- Leaderboard, Poll Responses, Full Schedule, Sent Log, Player IDs, Bot Config, Match Log, Player Stats, Team Stats
- "Test Schedule" exists only in `setup_test_sheet.py` — likely a SEPARATE test spreadsheet, not the live one. Needs confirmation, low priority.

### Dashboard generation chain
- `scripts/dashboard_builder.py` → builds `index.html` (leaderboard), `stats.html` (player/team stats), `match/{id}.html` from `match/template.html`. Reads Leaderboard, Poll Responses, Full Schedule. Has `PLAYERS_META` (DO NOT TOUCH).
- `scripts/sheets_updater.py` → `recalc` mode aggregates Poll Responses → writes Leaderboard cols F:K, re-ranks col A.
- `scripts/stats_fetcher.py` → writes Team Stats / Player Stats / Full Schedule from football-data.org.
- `.github/workflows/stats_updater.yml` (every 2h) runs stats_fetcher → dashboard_builder → git push. Confirmed-working git push pattern.

### Known modified/untracked files (git status, not re-verified this session)
- Modified: index.html, match/M001.html, match/M002.html, scripts/poll_bot.py (Telegram, deferred), scripts/trial_matches.json, stats.html
- Untracked: FIFA_2026_Schedule.ics, assets/avatars/* (Ash), scripts/generate_calendar.py, scripts/poll_trigger.gs, stray dir `"...FIFA World Cup Fantasy Game/"` (uninvestigated)

### Open questions — RESOLVED 2026-06-11 (user answers)
- M001/M002 trial match pages → **Delete both (git rm match/M001.html match/M002.html)**.
- "Sent Log" / "Bot Config" tabs → **Clear contents, keep structure/header** (Telegram code/workflows still untouched — deferral still applies to code, not to this data clear).
- "Player Stats" / "Team Stats" tabs → **Clear contents, keep header**; let `stats_fetcher.py` (via `stats_updater.yml`, every 2h) repopulate naturally.
- Sandbox cannot reach `oauth2.googleapis.com` (403) → reset script must be run by the user locally (or via GitHub Actions `workflow_dispatch`), not from this sandbox.

## Phase 2 — Status
- **CREATED** `scripts/reset_tournament.py` (on disk, ready to run): clears Poll Responses, Match Log, Sent Log, Bot Config, Player Stats, Team Stats (header row preserved on each); shells out to `sheets_updater.py recalc` to rebuild a clean zeroed Leaderboard; shells out to `dashboard_builder.py` to regenerate index.html/stats.html; removes match/M001.html and match/M002.html. Defaults to `--dry-run` (no writes) — requires `--execute` flag. Does NOT auto git add/commit/push — prints suggested git commands for user to review.
- Script itself was NOT executed by the user — see below for what the user did instead.
- Caveat flagged to user: "Bot Config" may hold persistent poll-bot config (not just trial-run state) — user should eyeball that tab (or run `--dry-run` first, which lists exactly what would be cleared) before running with --execute. Telegram code itself remains untouched per deferral.

## Phase 3 — Manual Reset Completed by User (2026-06-12)
- User has manually cleared the trial-run entries directly in the Google Sheet (bypassing `reset_tournament.py`).
- User has manually populated the Sheet with responses, points, and scores for **Matches 1–4** (real tournament data, not trial data).
- This means: Sheet-side reset is effectively DONE via manual edits, not via the script. `reset_tournament.py` remains on disk, unused — keep for reference but do not assume Sheet state matches what it would produce.
- NOT YET VERIFIED FROM THIS SESSION: current state of Leaderboard ranks/scores, whether dashboard (index.html/stats.html/match pages) has been regenerated to reflect M1–M4 results, whether M001.html/M002.html (trial match pages) were deleted, status of Sent Log/Bot Config/Player Stats/Team Stats tabs.

## Phase 4 — New Tab Added by User (2026-06-13)
- User has added a new tab called **"Bonus Polls"** to the Google Sheet, which syncs data from a Google Form shared with their friends group.
- NOT YET INTEGRATED: no script (dashboard_builder.py, sheets_updater.py, etc.) currently reads/uses this tab — purely informational for now. Do not assume any automation references it until told otherwise.

## Next step
Awaiting user instructions on what to do next — likely candidates: (1) verify Sheet state (Leaderboard, tabs) matches manual edits, (2) regenerate dashboard (index.html/stats.html/match pages) to reflect M1–M4 results via `dashboard_builder.py`, (3) confirm whether M001/M002 trial pages still need deletion, (4) git commit/push updated dashboard, (5) decide how/whether "Bonus Polls" tab feeds into leaderboard or dashboard. Do not act until user gives direction — current instruction was only to update this memory file.
