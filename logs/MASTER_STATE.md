# MASTER STATE — FIFA Fantasy 2026
*Last updated: 2026-05-29 (Session 4)*

---

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Avatar Creation | ✅ DONE | Gemini-generated cartoon avatars live on dashboard |
| Phase 2 — Google Sheets Setup | ✅ DONE | Main sheet ID: 18SfYYXYaGxvh-2bZIq_h4dOXfS7YtD5c49nW454MY2o. All 6 tabs + 104 matches populated. |
| Phase 3 — Telegram Poll Bot | ✅ LIVE | `scripts/poll_bot.py` on GitHub Actions. Group: "FIFA World Cup Fantasy". Sheet-based player ID mapping. |
| Phase 4 — Dashboard (GitHub Pages) | ✅ LIVE v3 | Unified aurora UI, Golden Glove + Playmaker added, country refs removed. https://siddb12-cyber.github.io/fifa-fantasy-2026/ |
| Phase 5 — Windows Task Scheduler | ⏭️ SKIPPED | Replaced by GitHub Actions (runs 24/7, no local machine needed) |
| Phase 6 — Demo Mode | ✅ LIVE | Portugal 2-1 Argentina demo match live on GitHub Pages |

---

## Files Created This Session

```
FIFA World Cup Fantasy Game/
├── index.html                          ← Leaderboard (dark stadium UI)
├── schedule.html                       ← 104-match schedule with filters
├── stats.html                          ← Player & team stats hub
├── match/
│   └── template.html                   ← Match preview/report template
├── assets/
│   ├── avatars/                        ← Empty — waiting for DPs
│   └── animations/                     ← Empty — waiting for DPs
├── scripts/
│   ├── setup_sheets.py                 ← Creates Google Sheet with 6 tabs + 104 matches
│   ├── poll_scheduler.py               ← WhatsApp poll automation (Selenium)
│   ├── sheets_updater.py               ← Records poll responses to Google Sheets
│   ├── stats_fetcher.py                ← Fetches live stats from football-data.org
│   ├── dashboard_builder.py            ← Rebuilds HTML from Sheets data + git push
│   ├── setup_scheduler.bat             ← Registers Windows Task Scheduler jobs
│   ├── install_deps.bat                ← pip install requirements
│   └── requirements.txt
└── logs/
    ├── MASTER_STATE.md                 ← This file
    └── session_2026-05-28.md           ← Session log
```

---

## Players

| Pet Name | Full Name | DP Filename |
|----------|-----------|-------------|
| Budhya | Sidhant Budhkar | Sidhant (Budhya).jpeg |
| Ambu   | Kushal Ambulkar | Kushal (Ambu).jpeg |
| Vini   | Vineet Nayak    | Vineet (Vini).jpeg |
| Baby   | Susmit Gulavani | Susmit (Baby).jpeg |
| Abs    | Abhishek Desai  | Abhishek (Abs).jpeg |
| Anna   | Nishant Salian  | Nishant (Anna).jpeg |
| Umaga  | Umang Budhkar   | Umang (Umaga).jpeg |
| PR     | Pranav Raut     | Pranav (PR).jpeg |

*Team/country/jersey removed from player model — Session 4.*

---

## Pending Actions (Before June 12)

1. **🎨 REGENERATE CARTOON AVATARS** → Run `scripts/run_avatars.bat` — replaces old photos with OpenCV cartoon cards
2. **👥 ADD 7 PLAYERS TO TELEGRAM GROUP** → Share invite link → they join → open "Player IDs" sheet → fill Pet Name column for each
3. **🚀 GO LIVE ON JUNE 12** → GitHub Actions → Poll Scheduler → Run workflow → set `TEST_MODE = false`, `FORCE_SEND = false`

### ✅ Completed Actions
- google_credentials.json placed at `C:/Users/siddh/Downloads/HK/FIFA/`
- All 8 player DPs uploaded and avatars generated (16 PNG files)
- GitHub repo created, all files pushed, GitHub Pages live
- Telegram bot (@fifafantasycircle_bot) working in "FIFA World Cup Fantasy" group
- Google Sheets main sheet set up (ID: 18SfYYXYaGxvh-2bZIq_h4dOXfS7YtD5c49nW454MY2o) — 104 matches, all tabs
- Poll answer collection via getUpdates — votes auto-recorded to Poll Responses sheet
- Sheet-based player ID mapping — new members auto-logged, Sidhant maps pet names manually
- matches.json (104 matches) generated for production mode
- GitHub Secrets set: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_JSON, FOOTBALL_API_KEY

---

## Key Config Values

| Variable | File | Current Value |
|----------|------|---------------|
| `FOOTBALL_KEY` | poll_scheduler.py, stats_fetcher.py | ← SET THIS |
| `WA_GROUP` | poll_scheduler.py | "FIFA Fantasy 2026 🏆" (update if different) |
| `CHROME_PROFILE` | poll_scheduler.py | `C:\Users\siddh\AppData\Local\Google\Chrome\User Data\Profile 6` |
| `CREDS_PATH` | all scripts | `C:\Users\siddh\Downloads\HK\FIFA\google_credentials.json` |

---

## Polls Status

No polls posted yet. Tournament starts 12 Jun 2026.

---

## Leaderboard Status

All 8 players seeded at 0 points. No matches played yet.

---

## Dashboard URLs

- GitHub Pages: `https://siddb12-cyber.github.io/fifa-fantasy-2026/` ✅ LIVE (enable Pages in repo settings)
- Google Sheet: `https://docs.google.com/spreadsheets/d/[SHEET_ID]` ← free Drive space then run setup_sheets.py
