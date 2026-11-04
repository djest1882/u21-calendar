# U21 Football — calendar feed

A subscribable calendar of every game involving U21 sides in:

| Code | Competition |
|---|---|
| PL2 | Premier League 2 |
| PDL | Professional Development League |
| PLC | Premier League Cup |
| PLIC | Premier League International Cup |
| EFL Trophy | EFL Trophy (only ties involving a U21 side) |
| NL Cup | National League Cup (only ties involving a U21 side) |

## How it works

`build_calendar.py` pulls fixtures from the Premier League's own match data (the source behind premierleague.com/en/matches/u21) and writes `docs/u21-fixtures.ics`. A GitHub Action re-runs it every 6 hours and commits the file only when a fixture changes, so date moves, kick-off changes, postponements and new cup draws flow through automatically. Each match keeps the same ID, so your calendar app updates the existing event rather than adding a duplicate.

- Finished games show the score in the title, e.g. `Bristol Rovers 2-2 (2-4 pens) Chelsea U21 (EFL Trophy)`.
- Postponed games are titled `POSTPONED:` until a new date is set.
- Events are marked "free" so they don't block your diary.

## Subscribe

Use the raw file link: `https://raw.githubusercontent.com/<you>/<repo>/main/docs/u21-fixtures.ics`

- **Google Calendar** (computer): Other calendars → **+** → **From URL** → paste the link.
- **Apple Calendar**: File → **New Calendar Subscription** → paste the link → set refresh to every hour.
- **iPhone**: Settings → Calendar → Accounts → Add Account → Other → **Add Subscribed Calendar**.
- **Outlook**: Add calendar → **Subscribe from web**.

Google Calendar refreshes subscribed calendars on its own schedule (typically every 12–24 hours); Apple and Outlook refresh more often.

## Run it manually

Actions tab → **Update U21 calendar** → **Run workflow**.
