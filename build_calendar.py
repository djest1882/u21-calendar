#!/usr/bin/env python3
"""
Build an iCalendar (.ics) feed of U21 club games in English competitions.

Source: the Premier League's own match API (the same data that powers
premierleague.com/en/matches/u21). Competitions covered:

  PL2  Premier League 2                     (898)
  PDL  Professional Development League      (665)
  PLC  Premier League Cup                   (678)
  PLIC Premier League International Cup     (742)
  EFLT EFL Trophy - U21 sides' games only   (7)
  NLC  National League Cup - U21 sides only (1275)

Usage:  python build_calendar.py [output.ics] [--from-json file.json]
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API = "https://sdp-prem-prod.premier-league-prod.pulselive.com/api/v2/matches"
LONDON = ZoneInfo("Europe/London")
MATCH_LENGTH = timedelta(hours=2)

COMPETITIONS = {
    "898": "PL2",
    "665": "PDL",
    "678": "PLC",
    "742": "PLIC",
    "7": "EFL Trophy",
    "1275": "NL Cup",
}
# Competitions that also contain first-team-only games: keep only U21 games.
U21_ONLY = {"7", "1275"}
LEAGUES = {"898", "665"}

def season_start_year(today=None):
    today = today or datetime.now(LONDON).date()
    return today.year if today.month >= 7 else today.year - 1


def fetch_json(url, tries=4):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (u21-fixture-calendar)",
        "Accept": "application/json",
        "Origin": "https://www.premierleague.com",
        "Referer": "https://www.premierleague.com/",
    })
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def fetch_competition(comp_id, season):
    matches, nxt = [], None
    for _ in range(50):
        url = f"{API}?competition={comp_id}&season={season}&_limit=100"
        if nxt:
            url += f"&_next={nxt}"
        page = fetch_json(url)
        matches.extend(page.get("data") or [])
        nxt = (page.get("pagination") or {}).get("_next")
        if not nxt:
            break
    return matches


def is_u21_game(m):
    names = (m["homeTeam"]["name"] + " " + m["awayTeam"]["name"]).upper()
    return "U21" in names or "U23" in names


def keep(m):
    comp = str(m.get("competitionId"))
    if comp not in COMPETITIONS:
        return False
    if comp in U21_ONLY and not is_u21_game(m):
        return False
    return True


# ---------- iCalendar helpers ----------
def esc(text):
    return (str(text).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    """Fold lines to 75 octets as RFC 5545 requires."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out, chunk = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(chunk) + len(b) > (75 if not out else 74):
            out.append(chunk.decode("utf-8"))
            chunk = b""
        chunk += b
    out.append(chunk.decode("utf-8"))
    return "\r\n ".join(out)


def utc_stamp(dt):
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def score_text(m):
    h, a = m["homeTeam"].get("score"), m["awayTeam"].get("score")
    if h is None or a is None:
        return ""
    s = f"{h}-{a}"
    hp, ap = m.get("homePenaltyScore"), m.get("awayPenaltyScore")
    if hp is not None and ap is not None:
        s += f" ({hp}-{ap} pens)"
    return s


def build_event(m, now_stamp):
    comp_label = COMPETITIONS[str(m["competitionId"])]
    home, away = m["homeTeam"]["name"], m["awayTeam"]["name"]
    start = datetime.strptime(m["kickoff"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=LONDON)
    postponed = m.get("period") == "Postponed" or m.get("resultType") == "Postponed"
    finished = m.get("period") == "FullTime"

    summary = f"{home} v {away} ({comp_label})"
    if finished and score_text(m):
        summary = f"{home} {score_text(m)} {away} ({comp_label})"
    if postponed:
        summary = "POSTPONED: " + summary

    desc = [m.get("competition", comp_label)]
    if m.get("round") and m["round"].strip().lower() != "round":
        desc.append(f"Round: {m['round']}")
    elif m.get("matchWeek") and str(m["competitionId"]) in LEAGUES:
        desc.append(f"Matchweek {m['matchWeek']}")
    desc.append(f"Kick-off: {start.strftime('%a %d %b %Y, %H:%M')} UK time")
    if postponed:
        desc.append("This match has been postponed; a new date has not been confirmed.")
    desc.append(f"Match centre: https://www.premierleague.com/en/match/{m['matchId']}")

    lines = [
        "BEGIN:VEVENT",
        f"UID:u21-{m['matchId']}@premierleague-fixtures",
        f"DTSTAMP:{now_stamp}",
        f"DTSTART;TZID=Europe/London:{start.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/London:{(start + MATCH_LENGTH).strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{esc(summary)}",
        f"DESCRIPTION:{esc(chr(10).join(desc))}",
        f"CATEGORIES:{esc(comp_label)}",
        "TRANSP:TRANSPARENT",
        f"STATUS:{'TENTATIVE' if postponed else 'CONFIRMED'}",
    ]
    if m.get("ground"):
        lines.append(f"LOCATION:{esc(m['ground'])}")
    lines.append("END:VEVENT")
    return lines


VTIMEZONE = [
    "BEGIN:VTIMEZONE", "TZID:Europe/London", "X-LIC-LOCATION:Europe/London",
    "BEGIN:DAYLIGHT", "TZOFFSETFROM:+0000", "TZOFFSETTO:+0100", "TZNAME:BST",
    "DTSTART:19700329T010000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "END:DAYLIGHT",
    "BEGIN:STANDARD", "TZOFFSETFROM:+0100", "TZOFFSETTO:+0000", "TZNAME:GMT",
    "DTSTART:19701025T020000", "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", "END:STANDARD",
    "END:VTIMEZONE",
]


def build_calendar(matches):
    now_stamp = utc_stamp(datetime.now(timezone.utc))
    kept = sorted((m for m in matches if keep(m)), key=lambda m: m["kickoff"])
    seen, lines = set(), [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//U21 Fixtures//U21 club games//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:U21 Football",
        "X-WR-CALDESC:PL2\\, PDL\\, PL Cup\\, PL International Cup\\, EFL Trophy and "
        "National League Cup games involving U21 sides. "
        "Source: premierleague.com. Updated daily.",
        "X-WR-TIMEZONE:Europe/London",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
        *VTIMEZONE,
    ]
    for m in kept:
        if m["matchId"] in seen:
            continue
        seen.add(m["matchId"])
        lines += build_event(m, now_stamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n", len(seen)


def main():
    args = sys.argv[1:]
    out = "docs/u21-fixtures.ics"
    src = None
    if "--from-json" in args:
        i = args.index("--from-json")
        src = args[i + 1]
        del args[i:i + 2]
    if args:
        out = args[0]

    if src:
        with open(src, encoding="utf-8") as f:
            matches = json.load(f)
    else:
        season = season_start_year()
        matches = []
        for comp_id in COMPETITIONS:
            got = fetch_competition(comp_id, season)
            print(f"{COMPETITIONS[comp_id]:>11}: {len(got)} matches", file=sys.stderr)
            matches.extend(got)
        if len(matches) < 50:
            sys.exit("Too few matches returned - not overwriting the calendar.")

    ics, n = build_calendar(matches)
    import os
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(ics)
    print(f"Wrote {n} games to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
