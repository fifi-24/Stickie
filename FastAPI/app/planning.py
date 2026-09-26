# Flow A, steps 2-5, corrected order: privately ask everyone's availability
# FIRST, only confirm a real date/time in the group once everyone's
# answered, and hand out a one-tap calendar link since we can't write
# directly to three different people's calendars (only one OAuth token
# exists tonight).

import datetime as dt
import json
from urllib.parse import urlencode

from app.clients.google_calendar import get_freebusy
from app.clients.places import search_places
from app.clients.sendblue import send_group_message
from app.config import DEMO_GROUP_NUMBERS
from app.conversation import clear as clear_conversation
from app.db import Plan, get_session
from app.primitives import propose_options_and_await_reply

# Demo location: Georgia Tech / downtown Atlanta, since that's where the
# group actually is tonight. Swap for real per-user locations later.
DEMO_LAT = 33.7756
DEMO_LNG = -84.3963

# Tonight's single-group simplification: one plan collecting answers at a
# time. _active_plan_id tracks which Plan row; _active_plan_times maps
# each time label ("Sunday 3:00PM") back to the real datetime it means,
# so a finalized plan can be turned into a real calendar link.
_active_plan_id: int | None = None
_active_plan_times: dict[str, dt.datetime] = {}
_active_plan_activity: str = ""


def _candidate_times(count: int = 2) -> list[tuple[str, dt.datetime]]:
    """A couple of open-looking (label, datetime) slots over the next few
    days, based on Bhaumi's own calendar (the only one connected tonight)."""
    now = dt.datetime.now(dt.timezone.utc)
    busy = get_freebusy("primary", now, now + dt.timedelta(days=5))
    busy_ranges = [
        (dt.datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
         dt.datetime.fromisoformat(b["end"].replace("Z", "+00:00")))
        for b in busy
    ]

    candidates: list[tuple[str, dt.datetime]] = []
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for day_offset in range(1, 6):
        for hour in (15, 18):  # 3pm, 6pm
            slot_start = today + dt.timedelta(days=day_offset, hours=hour)
            slot_end = slot_start + dt.timedelta(hours=1)
            overlaps = any(b_start < slot_end and slot_start < b_end for b_start, b_end in busy_ranges)
            if not overlaps:
                candidates.append((slot_start.strftime("%A %-I:%M%p"), slot_start))
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


def record_time_pick(sender: str, resolved_time: str) -> None:
    """Called from the webhook once resolve_pending_reply() has already
    matched a reply to one of the active plan's time-option labels.
    Tallies the pick; once every group member has answered, finalizes the
    plan (majority vote, ties go to the earlier time) and sends the real
    confirmation to the group with a calendar link — this is the step
    that was missing before."""
    global _active_plan_id, _active_plan_times, _active_plan_activity

    if _active_plan_id is None or resolved_time not in _active_plan_times:
        return

    with get_session() as session:
        row = session.query(Plan).filter_by(id=_active_plan_id).one_or_none()
        if row is None or row.status != "collecting":
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

        link = _gcal_link(_active_plan_activity, row.venue, winning_time)
        print(f"PLAN CONFIRMED: {_active_plan_activity} at {row.venue}, {winning_label} (votes: {counts})")
        send_group_message(
            DEMO_GROUP_NUMBERS,
            f"It's settled! {_active_plan_activity} at {row.venue}, {winning_label}. "
            f"Add it to your calendar: {link}",
        )

    _active_plan_id = None
    _active_plan_times = {}
    _active_plan_activity = ""
