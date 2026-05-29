# football-data.org API Reference — FIFA Fantasy 2026

## Key Details
- Auth Header: `X-Auth-Token: <your_token>`
- Base URL: `https://api.football-data.org/v4/`
- FIFA World Cup: Competition Code = `WC`, Competition ID = `2000`

## Key Endpoints
```
GET /v4/competitions/WC/matches              # all WC matches
GET /v4/competitions/WC/matches?status=IN_PLAY  # live now
GET /v4/competitions/WC/matches?matchday=1   # specific matchday
GET /v4/competitions/WC/scorers              # top scorers
GET /v4/competitions/WC/standings            # group standings
GET /v4/competitions/WC/teams               # all teams
GET /v4/matches/{id}                         # single match detail
```

## Match Status Values
SCHEDULED | TIMED | IN_PLAY | PAUSED | EXTRA_TIME | PENALTY_SHOOTOUT
| FINISHED | SUSPENDED | POSTPONED | CANCELLED | AWARDED

## Match Stage Values
GROUP_STAGE | LAST_64 | LAST_32 | LAST_16 | QUARTER_FINALS
| SEMI_FINALS | THIRD_PLACE | FINAL

## Match Group Values
GROUP_A | GROUP_B | GROUP_C | GROUP_D | GROUP_E | GROUP_F
| GROUP_G | GROUP_H | GROUP_I | GROUP_J | GROUP_K | GROUP_L

## Goal Types
REGULAR | OWN | PENALTY

## Card Types
YELLOW | YELLOW_RED | RED

## Response Headers
X-RequestsAvailable  → remaining requests before rate limit
X-RequestCounter-Reset → seconds until request counter resets

## Rate Limits (Free Tier)
~10 requests/minute

## Useful Filter Params
?status=IN_PLAY          # only live matches
?dateFrom=2026-06-11&dateTo=2026-06-12   # date range
?stage=GROUP_STAGE       # filter by stage
