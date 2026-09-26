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
    calendar connected, plus Bhaumi's own global calendar as a fallback --
    a slot only counts as open if it's free for everyone asked about, not
    just whoever happens to be the one this backend runs as."""
    def _parse(blocks: list[dict]) -> list[tuple[dt.datetime, dt.datetime]]:
        return [
            (dt.datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
             dt.datetime.fromisoformat(b["end"].replace("Z", "+00:00")))
            for b in blocks
        ]

    ranges = _parse(get_freebusy("primary", time_min, time_max))

    with get_session() as session:
        users = session.query(User).filter(User.phone.in_(phones)).all()
        for user in users:
            if not user.google_token:
                continue
            try:
                ranges.extend(_parse(get_freebusy_for_user(user.google_token, time_min, time_max)))
            except Exception as exc:
                print(f"Couldn't read {user.phone}'s calendar, skipping their availability: {exc}")

    return ranges


def candidate_times(phones: list[str], count: int = 2) -> list[tuple[str, dt.datetime]]:
    """A couple of open-looking (label, datetime) slots over the next few
    days, checked against every one of `phones`'s own real calendar.

    Bug that was here before: "3pm"/"6pm" were computed against a UTC-based
    day-start, so they were actually 3pm/6pm UTC — 11am/2pm Eastern, not
    3pm/6pm Eastern. Now built in DEMO_TZ (the demo's real local zone) and
    only converted to UTC at the boundary (busy-block comparison, and the
    datetime this function hands back for storage/calendar links) — a
    proper UTC instant converts correctly to whatever zone a recipient's
    own device/calendar is set to, which is what "device timing" means."""
    now_local = dt.datetime.now(DEMO_TZ)
    now_utc = now_local.astimezone(dt.timezone.utc)
    busy_ranges = busy_ranges_for(phones, now_utc, now_utc + dt.timedelta(days=5))

    candidates: list[tuple[str, dt.datetime]] = []
    today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    for day_offset in range(1, 6):
        for hour in (15, 18):  # 3pm, 6pm, Eastern
            slot_start_local = today_local + dt.timedelta(days=day_offset, hours=hour)
            slot_start_utc = slot_start_local.astimezone(dt.timezone.utc)
            slot_end_utc = slot_start_utc + dt.timedelta(hours=1)
            overlaps = any(b_start < slot_end_utc and slot_start_utc < b_end for b_start, b_end in busy_ranges)
            if not overlaps:
                candidates.append((slot_start_local.strftime("%A %-I:%M%p"), slot_start_utc))
            if len(candidates) >= count:
                return candidates
    return candidates


def suggest_venue_and_time(phones: list[str], activity: str, count: int = 2) -> dict:
    """Real venue + real candidate times for `activity`, checked against
    exactly the calendars of `phones` (not necessarily the whole group --
    mutual mode only wants the two people actually being nudged)."""
    places = search_places(activity, DEMO_LAT, DEMO_LNG)
    venue = places[0]["name"] if places else activity.title()
    times = candidate_times(phones, count=count)
    return {"venue": venue, "times": [label for label, _ in times], "time_values": [v for _, v in times]}
