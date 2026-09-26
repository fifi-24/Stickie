# Flow A, steps 2-3: turn a detected plan (app/reasoning.py) into a real
# venue + time proposal and post it to the group.

import datetime as dt

from app.clients.google_calendar import get_freebusy
from app.clients.places import search_places
from app.clients.sendblue import send_group_message
from app.config import DEMO_GROUP_NUMBERS
from app.conversation import clear as clear_conversation

# Demo location: Georgia Tech / downtown Atlanta, since that's where the
# group actually is tonight. Swap for real per-user locations later.
DEMO_LAT = 33.7756
DEMO_LNG = -84.3963


def _candidate_times(count: int = 2) -> list[str]:
    """A couple of open-looking slots over the next few days, based on
    Bhaumi's own calendar (the only one connected tonight — everyone else
    goes through the private-RSVP fallback instead of real freebusy)."""
    now = dt.datetime.now(dt.timezone.utc)
    busy = get_freebusy("primary", now, now + dt.timedelta(days=5))
    busy_ranges = [
        (dt.datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
         dt.datetime.fromisoformat(b["end"].replace("Z", "+00:00")))
        for b in busy
    ]

    candidates = []
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for day_offset in range(1, 6):
        for hour in (15, 18):  # 3pm, 6pm
            slot_start = today + dt.timedelta(days=day_offset, hours=hour)
            slot_end = slot_start + dt.timedelta(hours=1)
            overlaps = any(b_start < slot_end and slot_start < b_end for b_start, b_end in busy_ranges)
            if not overlaps:
                candidates.append(slot_start.strftime("%A %-I:%M%p"))
            if len(candidates) >= count:
                return candidates
    return candidates


def propose_plan(activity: str) -> dict:
    """Step 2: find a real venue + real candidate times for a detected activity."""
    places = search_places(activity, DEMO_LAT, DEMO_LNG)
    venue = places[0]["name"] if places else activity.title()
    return {"venue": venue, "times": _candidate_times()}


def post_proposal_to_group(activity: str) -> dict:
    """Step 3: build the proposal (step 2), send it to the real group, and
    clear the conversation buffer so this same plan doesn't get proposed
    again on the next affirming message that comes in."""
    plan = propose_plan(activity)
    times_str = " or ".join(plan["times"]) if plan["times"] else "a time this week"
    message = f"Heard you all want to do {activity}! How about {plan['venue']}, {times_str}?"
    send_group_message(DEMO_GROUP_NUMBERS, message)
    clear_conversation()
    return plan
