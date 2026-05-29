# MASTER STATE — FIFA Fantasy 2026
*Last updated: 2026-05-29 (Session 4)*

---

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Avatar Creation | ⚠️ RUN NEEDED | Old (non-cartoon) PNGs exist. Run `scripts/run_avatars.bat` to regenerate with OpenCV cartoon effect |
| Phase 2 — Google Sheets Setup | ⚠️ RUN NEEDED | setup_sheets.py fixed (Sheets API fallback, no Drive API required). Run it now. |
| Phase 3 — WhatsApp Poll Automation | ✅ BUILT | `scripts/poll_scheduler.py`. Needs football-data.org API key. Group: "FIFA 26 Test Group" |
| Phase 4 — Dashboard (GitHub Pages) | ✅ LIVE v3 | Unified aurora UI, Golden Glove + Playmaker added, country refs removed. https://siddb12-cyber.github.io/fifa-fantasy-2026/ |
| Phase 5 — Windows Task Scheduler | ✅ BUILT | `scripts/setup_scheduler.bat` — run as Admin after Sheets setup |
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

## Pending Actions (User Must Do)

1. **🎨 REGENERATE CARTOON AVATARS** → Run `scripts/run_avatars.bat` (double-click) — replaces old photos with OpenCV cartoon cards
2. **📊 SET UP GOOGLE SHEETS** → Run `python scripts/setup_sheets.py` — fixed 403 error (now uses Sheets API fallback, no Drive API needed)
3. **🔑 Set football-data.org API key** → Register free at football-data.org → edit `poll_scheduler.py` + `stats_fetcher.py` → set `FOOTBALL_KEY = "your_key"`
4. **🌐 Enable GitHub Pages** → github.com/siddb12-cyber/fifa-fantasy-2026 → Settings → Pages → Source: main / root → Save
5. **📤 Push redesigned dashboard** → Run `scripts/push_dashboard.bat` to push all v2 redesigns to GitHub Pages
6. **⚙️ Register Task Scheduler** → Run `scripts/setup_scheduler.bat` as Administrator (after Sheets setup)
7. **💬 Update WhatsApp group** → When real group created, edit `poll_scheduler.py` → `WA_GROUP = "real group name"`

### ✅ Completed Actions
- google_credentials.json placed at `C:/Users/siddh/Downloads/HK/FIFA/`
- All 8 player DPs uploaded to `C:/Users/siddh/Downloads/HK/FIFA/assets/avatars/`
- GitHub repo created and all files pushed to `main` branch
- All Python dependencies installed
- Avatars generated (16 PNG files)
- Demo dashboard built and deployed

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
