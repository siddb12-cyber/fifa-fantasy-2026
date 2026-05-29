# MASTER STATE — FIFA Fantasy 2026
*Last updated: 2026-05-28*

---

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Avatar Creation | ⏳ PENDING | Awaiting 8 WhatsApp DP images from user |
| Phase 2 — Google Sheets Setup | ✅ READY (script) | `scripts/setup_sheets.py` built. Needs `google_credentials.json` to run |
| Phase 3 — WhatsApp Poll Automation | ✅ BUILT | `scripts/poll_scheduler.py`. Needs WhatsApp group name & football-data.org API key |
| Phase 4 — Dashboard (GitHub Pages) | ✅ BUILT (demo data) | `index.html`, `schedule.html`, `stats.html`, `match/template.html` |
| Phase 5 — Windows Task Scheduler | ✅ BUILT | `scripts/setup_scheduler.bat` — run as Admin |
| Phase 6 — Demo Mode | ✅ BUILT | Run `python dashboard_builder.py --demo` |

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

## Players & Assignments

| Pet Name | Full Name | Team | Jersey | Star Player | DP Filename |
|----------|-----------|------|--------|-------------|-------------|
| Budhya | Sidhant Budhkar | Portugal | #7 | Cristiano Ronaldo | Sidhant Budhkar (Budhya).jpg |
| Ambu | Kushal Ambulkar | Argentina | #10 | Lionel Messi | Kushal Ambulkar (Ambu).jpg |
| Vini | Vineet Nayak | England | #9 | Harry Kane | Vineet Nayak (Vini).jpg |
| Baby | Susmit Gulavani | Spain | #8 | Pedri | Susmit Gulavani (Baby).jpg |
| Abs | Abhishek Desai | Germany | #8 | Jamal Musiala | Abhishek Desai (Abs).jpg |
| Anna | Nishant Salian | France | #10 | Kylian Mbappé | Nishant Salian (Anna).jpg |
| Umaga | Umang Budhkar | Brazil | #10 | Vinicius Jr. | Umang Budhkar (Umaga).jpg |
| PR | Pranav Raut | Netherlands | #11 | Xavi Simons | Pranav Raut (PR).jpg |

---

## Pending Actions (User Must Do)

1. **Add Google credentials**: Place `google_credentials.json` at `C:/Users/siddh/Downloads/HK/FIFA/`
2. **Run Google Sheet setup**: `python scripts/setup_sheets.py`
3. **Set API key**: Edit `poll_scheduler.py` and `stats_fetcher.py` → set `FOOTBALL_KEY = "your_key"` (free from football-data.org)
4. **Set WhatsApp group name**: Edit `poll_scheduler.py` → set `WA_GROUP = "your group name"`
5. **Upload player DPs**: Place 8 WhatsApp DP images in `assets/avatars/` named: `sidd.jpg`, `kushal.jpg`, etc.
6. **Initialize GitHub repo**: Create `fifa-fantasy-2026` repo and push this folder
7. **Enable GitHub Pages**: Set source to `main` branch, `/ (root)` folder
8. **Register Task Scheduler**: Run `scripts/setup_scheduler.bat` as Administrator
9. **Run demo**: `python scripts/dashboard_builder.py --demo`

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

- GitHub Pages: `https://siddb12-cyber.github.io/fifa-fantasy-2026/` ✅ REPO EXISTS
- Google Sheet: `https://docs.google.com/spreadsheets/d/[SHEET_ID]` ← run setup_sheets.py to get ID
