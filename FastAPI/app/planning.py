# Flow A, steps 2-5: turn a detected plan (app/reasoning.py) into a real
# venue + time proposal, post it to the group, persist it, track RSVPs,
# and privately follow up with everyone too.

import datetime as dt
import json

from app.clients.google_calendar import get_freebusy
from app.clients.places import search_places
from app.clients.sendblue import send_group_message
from app.config import DEMO_GROUP_NUMBERS
from app.conversation import clear as clear_conversation
from app.db import Plan, get_session
from app.primitives import propose_options_and_await_reply
from app.reasoning import interpret

# Demo location: Georgia Tech / downtown Atlanta, since that's where the
# group actually is tonight. Swap for real per-user locations later.
DEMO_LAT = 33.7756
DEMO_LNG = -84.3963

# The plan currently awaiting RSVPs in the group thread, if any. Tonight's
# single-group simplification: one active plan at a time, same as the
# conversation buffer in app/conversation.py.
_active_plan_id: int | None = None


def _candidate_times(count: int = 2) -> list[tuple[str, dt.datetime]]:
    """A couple of open-looking (label, datetime) slots over the next few
    days, based on Bhaumi's own calendar (the only one connected tonight —
    see post_proposal_to_group's private-RSVP fallback for everyone else)."""
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


def post_proposal_to_group(activity: str) -> dict:
    """Steps 3-5: build the proposal (step 2), send it to the real group,
    persist it as a Plan row, remember it as the active plan so replies get
    tracked as RSVPs (step 4), clear the conversation buffer so it doesn't
    get re-proposed, and privately DM every member too (step 5) — tonight's
    calendar is only connected for one person, so *everyone* gets the same
    private fallback ask rather than trying to detect who lacks access."""
    global _active_plan_id

    plan = propose_plan(activity)
    times_str = " or ".join(plan["times"]) if plan["times"] else "a time this week"
    message = f"Ok I got you - {plan['venue']} for {activity}? {times_str} both look open, lmk what works!"
    send_group_message(DEMO_GROUP_NUMBERS, message)

    with get_session() as session:
        row = Plan(
            status="proposed",
            venue=plan["venue"],
            time=plan["time_values"][0] if plan["time_values"] else None,
            rsvps="{}",
        )
        session.add(row)
        session.commit()
        _active_plan_id = row.id

    clear_conversation()

    # Private-RSVP fallback: DM each member individually with the same
    # options, using the already-tested shared primitive. A full natural
    # sentence (via `message=`) instead of the generic numbered-list
    # fallback, so it reads like a person, not a bot form.
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


def record_rsvp(sender: str, text: str) -> bool:
    """Step 4: if a plan is currently awaiting RSVPs, resolve this reply
    against yes/no and store it. Returns True if this message was consumed
    as an RSVP (so the webhook knows not to treat it as anything else)."""
    if _active_plan_id is None or not text:
        return False

    answer = interpret(text, ["yes", "no"])
    if answer not in ("yes", "no", "declined"):
        return False
    answer = "no" if answer == "declined" else answer

    with get_session() as session:
        row = session.query(Plan).filter_by(id=_active_plan_id).one_or_none()
        if row is None:
            return False
        rsvps = json.loads(row.rsvps or "{}")
        rsvps[sender] = answer
        row.rsvps = json.dumps(rsvps)
        session.commit()

    return True
