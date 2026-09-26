# Flow A, steps 2-5, corrected order: privately ask everyone's availability
# FIRST, only confirm a real date/time in the group once everyone's
# answered, and hand out a one-tap calendar link since we can't write
# directly to three different people's calendars (only one OAuth token
# exists tonight).

import datetime as dt
import json
import threading
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from app.clients.google_calendar import get_freebusy
from app.clients.google_oauth_web import create_event_for_user, get_freebusy_for_user
from app.clients.places import search_places
from app.clients.sendblue import send_group_message
from app.config import DEMO_GROUP_NUMBERS
from app.conversation import clear as clear_conversation
from app.db import Plan, User, get_session
from app.primitives import propose_options_and_await_reply

# record_time_pick() does a read-modify-write on row.rsvps (load the JSON
# blob, add one pick, save the whole blob back) -- two replies landing on
# separate request threads within the same instant can both read the
# pre-update blob, and whichever commits last silently overwrites the
# other's pick, permanently under-counting the plan. This lock makes that
# critical section run one request at a time.
_rsvp_lock = threading.Lock()

# How long after a plan starts collecting that a reply can still change an
# already-recorded pick (or land as a first pick at all).
ALTERATION_WINDOW = dt.timedelta(hours=24)

# Demo location: Georgia Tech / downtown Atlanta, since that's where the
# group actually is tonight. Swap for real per-user locations later.
DEMO_LAT = 33.7756
DEMO_LNG = -84.3963
DEMO_TZ = ZoneInfo("America/New_York")

# Tonight's single-group simplification: one plan collecting answers at a
# time. _active_plan_id tracks which Plan row; _active_plan_times maps
# each time label ("Sunday 3:00PM") back to the real datetime it means,
# so a finalized plan can be turned into a real calendar link.
_active_plan_id: int | None = None
_active_plan_times: dict[str, dt.datetime] = {}
_active_plan_activity: str = ""


def _all_busy_ranges(time_min: dt.datetime, time_max: dt.datetime) -> list[tuple[dt.datetime, dt.datetime]]:
    """Union of busy blocks across every participant who has their own
    calendar connected, plus Bhaumi's own global calendar as a fallback --
    a slot only counts as open if it's free for everyone, not just
    whoever happens to be the one this backend runs as."""
    def _parse(blocks: list[dict]) -> list[tuple[dt.datetime, dt.datetime]]:
        return [
            (dt.datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
             dt.datetime.fromisoformat(b["end"].replace("Z", "+00:00")))
            for b in blocks
        ]

    ranges = _parse(get_freebusy("primary", time_min, time_max))

    with get_session() as session:
        users = session.query(User).filter(User.phone.in_(DEMO_GROUP_NUMBERS)).all()
        for user in users:
            if not user.google_token:
                continue
            try:
                ranges.extend(_parse(get_freebusy_for_user(user.google_token, time_min, time_max)))
            except Exception as exc:
                print(f"Couldn't read {user.phone}'s calendar, skipping their availability: {exc}")

    return ranges


def _candidate_times(count: int = 2) -> list[tuple[str, dt.datetime]]:
    """A couple of open-looking (label, datetime) slots over the next few
    days, checked against every connected participant's own real
    calendar (see _all_busy_ranges) -- not just Bhaumi's.

    Bug that was here before: "3pm"/"6pm" were computed against a UTC-based
    day-start, so they were actually 3pm/6pm UTC — 11am/2pm Eastern, not
    3pm/6pm Eastern. Now built in DEMO_TZ (the demo's real local zone) and
    only converted to UTC at the boundary (busy-block comparison, and the
    datetime this function hands back for storage/calendar links) — a
    proper UTC instant converts correctly to whatever zone a recipient's
    own device/calendar is set to, which is what "device timing" means."""
    now_local = dt.datetime.now(DEMO_TZ)
    now_utc = now_local.astimezone(dt.timezone.utc)
    busy_ranges = _all_busy_ranges(now_utc, now_utc + dt.timedelta(days=5))

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


def propose_plan(activity: str) -> dict:
    """Step 2: find a real venue + real candidate times for a detected activity."""
    places = search_places(activity, DEMO_LAT, DEMO_LNG)
    venue = places[0]["name"] if places else activity.title()
    times = _candidate_times()
    return {"venue": venue, "times": [label for label, _ in times], "time_values": [dt_ for _, dt_ in times]}


def _gcal_link(activity: str, venue: str, start: dt.datetime) -> str:
    """A one-tap 'add to your calendar' link — works for anyone with a
    Google account, no OAuth from us required. This is how we get the
    event onto three different people's calendars without three tokens."""
    end = start + dt.timedelta(hours=1)
    fmt = "%Y%m%dT%H%M%SZ"
    params = {
        "action": "TEMPLATE",
        "text": f"{activity.title()} - {venue}",
        "dates": f"{start.strftime(fmt)}/{end.strftime(fmt)}",
        "location": venue,
        "details": "Planned by Stickie",
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


def post_proposal_to_group(activity: str) -> dict:
    """Step 3 (corrected order): tell the group we're on it (no specific
    time yet — nothing's decided), persist a Plan row in 'collecting'
    status, clear the conversation buffer, then privately ask every
    member's availability. Nothing gets confirmed in the group until
    everyone's answered — see record_time_pick()."""
    global _active_plan_id, _active_plan_times, _active_plan_activity

    plan = propose_plan(activity)
    send_group_message(
        DEMO_GROUP_NUMBERS,
        f"Ok {activity} at {plan['venue']}! Checking what time works for everyone, one sec.",
    )

    with get_session() as session:
        row = Plan(status="collecting", venue=plan["venue"], time=None, rsvps="{}")
        session.add(row)
        session.commit()
        _active_plan_id = row.id
        _active_plan_times = dict(zip(plan["times"], plan["time_values"]))
        _active_plan_activity = activity

    clear_conversation()

    times = plan["times"]
    if len(times) >= 2:
        private_text = f"hey! group's talking {activity} - does {times[0]} or {times[1]} work better for you?"
    elif times:
        private_text = f"hey! group's talking {activity} - does {times[0]} work for you?"
    else:
        private_text = f"hey! group's talking {activity} - what's good for you this week?"

    for number in DEMO_GROUP_NUMBERS:
        propose_options_and_await_reply(number, times, message=private_text)

    return plan


def _add_to_everyones_calendar(activity: str, venue: str, start: dt.datetime) -> None:
    """Inserts the finalized plan directly onto every connected
    participant's own calendar. Best-effort per person -- one person's
    token being stale/revoked shouldn't stop everyone else from getting
    it, and the group message's gcal link stays as a manual fallback."""
    end = start + dt.timedelta(hours=1)
    with get_session() as session:
        users = session.query(User).filter(User.phone.in_(DEMO_GROUP_NUMBERS)).all()
        for user in users:
            if not user.google_token:
                continue
            try:
                create_event_for_user(user.google_token, f"{activity.title()} - {venue}", venue, start, end)
            except Exception as exc:
                print(f"Couldn't auto-add to {user.phone}'s calendar (they may need to reconnect): {exc}")


def record_time_pick(sender: str, resolved_time: str) -> None:
    """Called from the webhook once resolve_pending_reply() has already
    matched a reply to one of the active plan's time-option labels.
    Tallies the pick (a changed pick overwrites the same person's earlier
    one, since picks is keyed by phone); once every group member has
    answered, finalizes the plan (majority vote, ties go to the earlier
    time), adds it straight to everyone's own calendar, and sends the
    real confirmation to the group."""
    global _active_plan_id, _active_plan_times, _active_plan_activity

    if _active_plan_id is None or resolved_time not in _active_plan_times:
        return

    # record_time_pick() is a read-modify-write on the same JSON blob
    # (row.rsvps): load it, change one key, save the whole thing back.
    # Two replies arriving on overlapping request threads could both read
    # the same starting blob and then each save their own version, with
    # whichever commits last silently discarding the other's pick. This
    # lock forces that whole read-modify-write to happen one at a time.
    with _rsvp_lock, get_session() as session:
        row = session.query(Plan).filter_by(id=_active_plan_id).one_or_none()
        if row is None or row.status != "collecting":
            return
        if dt.datetime.now(dt.timezone.utc) - row.created_at > ALTERATION_WINDOW:
            print(f"Ignoring pick from {sender}: past the 24h alteration window for this plan")
            return

        picks = json.loads(row.rsvps or "{}")
        picks[sender] = resolved_time
        row.rsvps = json.dumps(picks)
        session.commit()
        print(f"Time pick recorded for {sender}: {resolved_time} ({len(picks)}/{len(DEMO_GROUP_NUMBERS)} in)")

        if len(picks) < len(DEMO_GROUP_NUMBERS):
            return  # still waiting on someone

        counts: dict[str, int] = {}
        for pick in picks.values():
            counts[pick] = counts.get(pick, 0) + 1
        winning_label = max(counts, key=lambda label: counts[label])
        winning_time = _active_plan_times[winning_label]

        row.status = "confirmed"
        row.time = winning_time
        session.commit()

        activity, venue = _active_plan_activity, row.venue

    _add_to_everyones_calendar(activity, venue, winning_time)

    link = _gcal_link(activity, venue, winning_time)
    print(f"PLAN CONFIRMED: {activity} at {venue}, {winning_label} (votes: {counts})")
    send_group_message(
        DEMO_GROUP_NUMBERS,
        f"It's settled! {activity} at {venue}, {winning_label}. "
        f"Added it to your calendar already -- here's the link too just in case: {link}",
    )

    _active_plan_id = None
    _active_plan_times = {}
    _active_plan_activity = ""
