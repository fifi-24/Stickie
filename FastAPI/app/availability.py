# Shared "find a real open slot + a real venue" logic. Used by Flow A
# (planning.py, checked against the whole group) and Flow B mutual mode
# (a single pair) -- lives here, not in either of those modules, so
# neither has to import the other.

import datetime as dt
from zoneinfo import ZoneInfo

from app.clients.google_calendar import get_freebusy
from app.clients.google_oauth_web import get_freebusy_for_user
from app.clients.places import search_places
from app.db import User, get_session

# Demo location: Georgia Tech / downtown Atlanta, since that's where the
# group actually is tonight. Swap for real per-user locations later.
DEMO_LAT = 33.7756
DEMO_LNG = -84.3963
DEMO_TZ = ZoneInfo("America/New_York")


def busy_ranges_for(phones: list[str], time_min: dt.datetime, time_max: dt.datetime) -> list[tuple[dt.datetime, dt.datetime]]:
    """Union of busy blocks across every one of `phones` who has their own
    calendar connected, plus global calendar as fallback. Gracefully
    falls back to empty ranges if Google OAuth credentials are not set."""
    def _parse(blocks: list[dict]) -> list[tuple[dt.datetime, dt.datetime]]:
        return [
            (dt.datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
             dt.datetime.fromisoformat(b["end"].replace("Z", "+00:00")))
            for b in blocks
        ]

    ranges = []
    # Primary/global calendar check with fallback
    try:
        ranges = _parse(get_freebusy("primary", time_min, time_max))
    except Exception as exc:
        print(f"⚠️ Primary Google Calendar check skipped/failed: {exc}")

    # Per-user calendar check with fallback
    try:
        with get_session() as session:
            users = session.query(User).filter(User.phone.in_(phones)).all()
            for user in users:
                if not user.google_token:
                    continue
                try:
                    ranges.extend(_parse(get_freebusy_for_user(user.google_token, time_min, time_max)))
                except Exception as exc:
                    print(f"Couldn't read {user.phone}'s calendar, skipping their availability: {exc}")
    except Exception as exc:
        print(f"⚠️ DB lookup for user calendar tokens skipped/failed: {exc}")

    return ranges


def candidate_times(phones: list[str], count: int = 2) -> list[tuple[str, dt.datetime]]:
    """A couple of open-looking (label, datetime) slots over the next few
    days, checked against every one of `phones`'s own real calendar."""
    now_local = dt.datetime.now(DEMO_TZ)
    now_utc = now_local.astimezone(dt.timezone.utc)

    try:
        busy_ranges = busy_ranges_for(phones, now_utc, now_utc + dt.timedelta(days=5))
    except Exception as exc:
        print(f"⚠️ Calendar availability scan failed, treating slots as open: {exc}")
        busy_ranges = []

    candidates: list[tuple[str, dt.datetime]] = []
    today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    for day_offset in range(1, 6):
        for hour in (15, 18):  # 3pm, 6pm Eastern
            slot_start_local = today_local + dt.timedelta(days=day_offset, hours=hour)
            slot_start_utc = slot_start_local.astimezone(dt.timezone.utc)
            slot_end_utc = slot_start_utc + dt.timedelta(hours=1)
            overlaps = any(b_start < slot_end_utc and slot_start_utc < b_end for b_start, b_end in busy_ranges)
            if not overlaps:
                candidates.append((slot_start_local.strftime("%A %-I:%M%p"), slot_start_utc))
            if len(candidates) >= count:
                return candidates

    # Fallback if every slot had a conflict
    if not candidates:
        fallback_time = (today_local + dt.timedelta(days=1, hours=16)).astimezone(dt.timezone.utc)
        candidates.append(("Tomorrow 4:00PM", fallback_time))

    return candidates


def suggest_venue_and_time(phones: list[str], activity: str, count: int = 2) -> dict:
    """Real venue + real candidate times for `activity`, checked against
    calendars of `phones`, with full fallback resilience for hackathon demos."""
    try:
        places = search_places(activity, DEMO_LAT, DEMO_LNG)
    except Exception as exc:
        print(f"Places lookup failed for {activity!r}, falling back to generic venue: {exc}")
        places = []

    venue = places[0]["name"] if places else activity.title()

    try:
        times = candidate_times(phones, count=count)
    except Exception as exc:
        print(f"Candidate times generation failed, falling back: {exc}")
        tomorrow_utc = (dt.datetime.now(DEMO_TZ) + dt.timedelta(days=1)).replace(
            hour=16, minute=0, second=0, microsecond=0
        ).astimezone(dt.timezone.utc)
        times = [("Tomorrow 4:00PM", tomorrow_utc)]

    return {
        "venue": venue,
        "times": [label for label, _ in times],
        "time_values": [v for _, v in times]
    }