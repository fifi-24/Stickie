# The real /nudge experience: one personal digest of everyone in your
# crew you're overdue to see, covering BOTH modes of Flow B --
#   - mutual: other people who are also real Stickie users (LastHangout)
#   - solo/concierge: your own one-sided Contact list, people who are
#     NOT on Stickie themselves (app/db.py's Contact table)
# texted back to the person who asked, with nothing sent to anyone else
# until they explicitly approve which items go out. Each item already
# carries a real suggested venue + time, not a bare "want to catch up?"

import datetime as dt

from app.availability import suggest_venue_and_time
from app.clients.sendblue import send_message
from app.config import DEMO_GROUP_NUMBERS
from app.db import Contact, Interest, LastHangout, User, get_session
from app.mutual_mode import DEFAULT_NUDGE_THRESHOLD_DAYS, _group_key
from app.reasoning import generate_nudge_message

# sender phone -> the digest items they were last texted, awaiting their
# approval reply. In-memory for tonight, same tradeoff as primitives.py's
# _pending: fine for a single demo process, lost on restart.
_pending_digests: dict[str, list[dict]] = {}


def _threshold_days_for(user: User | None) -> int:
    if user and user.nudge_threshold_days:
        return user.nudge_threshold_days
    return DEFAULT_NUDGE_THRESHOLD_DAYS


def _shared_activity(tags_a: set[str], tags_b: set[str]) -> str:
    shared = tags_a & tags_b
    if shared:
        return next(iter(shared))
    # No overlap on record -- fall back to either person's own interest,
    # then to a safe generic default. Never leave this empty: it's the
    # search term handed to Places.
    return next(iter(tags_a or tags_b), "coffee")


def _mutual_items(session, phone: str) -> list[dict]:
    me = session.query(User).filter_by(phone=phone).one_or_none()
    if me is None:
        return []
    threshold_days = _threshold_days_for(me)
    my_tags = {i.tag for i in session.query(Interest).filter_by(user_id=me.id).all()}
    today = dt.date.today()

    items: list[dict] = []
    for other_phone in DEMO_GROUP_NUMBERS:
        if other_phone == phone:
            continue
        key = _group_key(phone, other_phone)
        row = session.query(LastHangout).filter_by(group_key=key).one_or_none()
        if row is None:
            continue  # never hung out yet -- nothing to measure drift against
        days_since = (today - row.last_hangout_date).days
        if days_since < threshold_days or row.last_nudged_date == today:
            continue

        other = session.query(User).filter_by(phone=other_phone).one_or_none()
        other_name = (other.name if other else "") or other_phone
        other_tags = (
            {i.tag for i in session.query(Interest).filter_by(user_id=other.id).all()} if other else set()
        )
        activity = _shared_activity(my_tags, other_tags)
        plan = suggest_venue_and_time([phone, other_phone], activity, count=1)
        venue = plan["venue"]
        time_label = plan["times"][0] if plan["times"] else None

        items.append({
            "kind": "mutual",
            "key": key,
            "other_name": other_name,
            "other_phone": other_phone,
            "days_since": days_since,
            "venue": venue,
            "time_label": time_label,
            "message_to_other": generate_nudge_message(me.name or None, days_since, venue, time_label),
        })
    return items


def _solo_items(session, phone: str) -> list[dict]:
    me = session.query(User).filter_by(phone=phone).one_or_none()
    if me is None:
        return []
    today = dt.date.today()
    contacts = session.query(Contact).filter_by(owner_user_id=me.id).all()

    items: list[dict] = []
    for contact in contacts:
        days_since = (today - contact.last_met).days if contact.last_met else None
        if days_since is not None and days_since < contact.cadence_days:
            continue
        if contact.last_nudged_date == today:
            continue

        plan = suggest_venue_and_time([phone], "coffee", count=1)
        venue = plan["venue"]
        time_label = plan["times"][0] if plan["times"] else None

        who = me.name or "a friend"
        if days_since is None:
            opener = f"hi {contact.name}, this is {who}'s Stickie."
        else:
            opener = f"hi {contact.name}, this is {who}'s Stickie. it's been {days_since} days since you two caught up."
        message = (
            f"{opener} they'd love to grab {venue} on {time_label}, does that work?"
            if time_label
            else f"{opener} they'd love to grab {venue} sometime soon, does that work?"
        )

        items.append({
            "kind": "solo",
            "key": contact.id,
            "other_name": contact.name,
            "other_phone": contact.phone,
            "days_since": days_since,
            "venue": venue,
            "time_label": time_label,
            "message_to_other": message,
        })
    return items


def build_and_send_digest(phone: str) -> int:
    """The real /nudge handler: builds this person's crew digest (mutual +
    solo), texts it back to THEM ONLY, and holds it awaiting approval.
    Returns how many items were found."""
    with get_session() as session:
        items = _mutual_items(session, phone) + _solo_items(session, phone)

    if not items:
        send_message(phone, "you're all caught up with your crew, nobody's overdue right now")
        return 0

    _pending_digests[phone] = items

    lines = []
    for i, item in enumerate(items, start=1):
        gap = f"{item['days_since']} days" if item["days_since"] is not None else "a while"
        plan_bit = f"{item['venue']} on {item['time_label']}" if item["time_label"] else item["venue"]
        lines.append(f"{i}. {item['other_name']} - {gap} - suggested: {plan_bit}")

    text = (
        "here's who's overdue in your crew:\n"
        + "\n".join(lines)
        + '\nreply with a number to send that plan, a few separated by commas, '
        '"all" to send everything, or "no" to skip'
    )
    send_message(phone, text)
    return len(items)


def try_resolve_digest_approval(phone: str, reply_text: str | None) -> bool:
    """Returns True if `phone` had a pending digest and this reply was
    handled as an approval decision -- the webhook should stop processing
    this message further either way. Returns False (falls through to
    normal handling) if there's no pending digest, or the reply doesn't
    parse as a decision about it."""
    items = _pending_digests.get(phone)
    if not items:
        return False

    text = (reply_text or "").strip().lower()
    if text in ("no", "nah", "skip", "cancel"):
        del _pending_digests[phone]
        send_message(phone, "ok, skipped")
        return True

    if text in ("all", "yes", "send all", "send them all"):
        chosen = items
    else:
        chosen = []
        for part in text.replace(" and ", ",").split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(items):
                    chosen.append(items[idx])
        if not chosen:
            return False  # doesn't look like a reply to this digest at all

    sent = 0
    with get_session() as session:
        for item in chosen:
            # One bad number (unreachable/unverified) shouldn't 500 the
            # whole approval or block the rest of this person's batch.
            try:
                send_message(item["other_phone"], item["message_to_other"])
            except Exception as exc:
                print(f"Couldn't send nudge to {item['other_phone']}: {exc}")
                continue

            sent += 1
            if item["kind"] == "mutual":
                row = session.query(LastHangout).filter_by(group_key=item["key"]).one_or_none()
                if row is not None:
                    row.last_nudged_date = dt.date.today()
            else:
                contact = session.query(Contact).filter_by(id=item["key"]).one_or_none()
                if contact is not None:
                    contact.last_nudged_date = dt.date.today()
        session.commit()

    failed = len(chosen) - sent
    reply = f"sent {sent} nudge(s)" + (f", {failed} failed to send" if failed else "")
    send_message(phone, reply)
    del _pending_digests[phone]
    return True
