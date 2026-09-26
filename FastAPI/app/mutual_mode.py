# Flow B, mutual mode ("crossover nudge"): when two people who are BOTH
# real Stickie users haven't hung out in a while, privately nudge both of
# them to reconnect -- with a real suggested venue+time already attached,
# not just "want to catch up?" Different from Contact/solo mode (app/db.py's
# Contact table, one-sided -- a power user's own rolodex of people who
# aren't on Stickie themselves); this is pairwise, between two mutual
# accounts, driven entirely by real date math against LastHangout.

import datetime as dt
from itertools import combinations

from app.availability import suggest_venue_and_time
from app.clients.sendblue import send_message
from app.config import DEMO_GROUP_NUMBERS
from app.db import Interest, LastHangout, User, get_session
from app.reasoning import generate_nudge_message

# Placeholder cadence for tonight -- every real user should eventually set
# their own review cadence (the "Weekly/Bi-weekly/Monthly" field already
# in the dashboard's settings UI isn't persisted to a real column yet;
# this is the same constant for every pair until that's wired up).
NUDGE_THRESHOLD = dt.timedelta(days=14)


def _group_key(phone_a: str, phone_b: str) -> str:
    return ",".join(sorted((phone_a, phone_b)))


def record_hangout(phones: list[str], on: dt.date | None = None) -> None:
    """Call this whenever a plan actually finalizes (see
    planning.py:record_time_pick) -- marks every pair among `phones` as
    having just hung out, resetting their drift clock and clearing any
    earlier nudge for that gap."""
    on = on or dt.date.today()
    with get_session() as session:
        for a, b in combinations(sorted(phones), 2):
            key = _group_key(a, b)
            row = session.query(LastHangout).filter_by(group_key=key).one_or_none()
            if row is None:
                session.add(LastHangout(group_key=key, last_hangout_date=on, last_nudged_date=None))
            else:
                row.last_hangout_date = on
                row.last_nudged_date = None
        session.commit()


def _user_info(session, phone: str) -> tuple[str, set[str]]:
    user = session.query(User).filter_by(phone=phone).one_or_none()
    if user is None:
        return "", set()
    tags = {i.tag for i in session.query(Interest).filter_by(user_id=user.id).all()}
    return user.name or "", tags


def _shared_activity(tags_a: set[str], tags_b: set[str]) -> str:
    shared = tags_a & tags_b
    if shared:
        return next(iter(shared))
    # No overlap on record -- fall back to either person's own interest,
    # then to a safe generic default. Never leave this empty: it's the
    # search term handed to Places.
    return next(iter(tags_a or tags_b), "coffee")


def run_mutual_mode_check(force: bool = False) -> list[str]:
    """The real check: for every mutual pair in the demo group, nudge them
    if it's been NUDGE_THRESHOLD or longer since LastHangout and they
    haven't already been nudged for this same gap. Each nudge carries a
    real suggested venue + time (checked against just that pair's own
    calendars), not a bare "want to catch up?" Returns the group_keys that
    got nudged.

    `force=True` is a demo-only override: skips the real threshold/date
    check entirely and nudges every pair regardless, so this can be
    triggered live in front of people instead of waiting two weeks or
    hand-editing the database to test it."""
    nudged: list[str] = []
    today = dt.date.today()

    with get_session() as session:
        for a, b in combinations(sorted(DEMO_GROUP_NUMBERS), 2):
            key = _group_key(a, b)
            row = session.query(LastHangout).filter_by(group_key=key).one_or_none()
            days_since = (today - row.last_hangout_date).days if row else None

            if not force:
                if row is None:
                    continue  # never hung out yet -- nothing to measure drift against
                if days_since < NUDGE_THRESHOLD.days:
                    continue
                if row.last_nudged_date == today:
                    continue  # already nudged for this exact gap

            name_a, tags_a = _user_info(session, a)
            name_b, tags_b = _user_info(session, b)
            activity = _shared_activity(tags_a, tags_b)

            plan = suggest_venue_and_time([a, b], activity, count=1)
            venue = plan["venue"]
            time_label = plan["times"][0] if plan["times"] else None

            send_message(a, generate_nudge_message(name_b, days_since, venue, time_label))
            send_message(b, generate_nudge_message(name_a, days_since, venue, time_label))
            nudged.append(key)

            if row is None:
                session.add(LastHangout(
                    group_key=key,
                    last_hangout_date=today - NUDGE_THRESHOLD,
                    last_nudged_date=today,
                ))
            else:
                row.last_nudged_date = today

        session.commit()

    return nudged
