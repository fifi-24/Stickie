# Manual commands anyone can text Stickie directly instead of waiting for
# passive detection. Checked FIRST in the webhook (app/main.py), before
# anything else -- a recognized command short-circuits normal processing.

import datetime as dt
import re
import secrets

from app.clients.sendblue import send_message
from app.config import DEMO_GROUP_NUMBERS, FRONTEND_BASE_URL
from app.crew_digest import build_and_send_digest
from app.db import Contact, OnboardingToken, User, get_session
from app.mutual_mode import record_hangout
from app.phone import normalize_phone
from app.planning import post_proposal_to_group

COMMAND_PATTERN = re.compile(r"^/(\w+)\s*(.*)$", re.DOTALL)


def _safe_send(phone: str, text: str) -> None:
    """A delivery hiccup (unverified number, transient SendBlue error)
    replying to a manual command shouldn't 500 the whole webhook --
    matches the best-effort pattern already used elsewhere in this app
    (_add_to_everyones_calendar, crew_digest._send_items)."""
    try:
        send_message(phone, text)
    except Exception as exc:
        print(f"Couldn't text {phone}: {exc}")


def handle_website_command(sender: str) -> None:
    """/website -- texts back a link that drops the sender straight into
    the real dashboard if they're already onboarded. Reuses the exact
    same magic-link mechanism as first-time onboarding: for an
    already-onboarded phone, the site's own status check just skips
    onboarding entirely and shows the dashboard -- no separate "logged
    in" link type needed."""
    token = secrets.token_urlsafe(24)
    with get_session() as session:
        session.add(OnboardingToken(token=token, phone=sender))
        session.commit()
    link = f"{FRONTEND_BASE_URL}/onboard?token={token}"
    send_message(sender, f"Here's your Stickie link: {link}")


def handle_plan_command(sender: str, activity: str) -> None:
    """/plan <activity> -- skips passive "did 2 people affirm" detection
    and starts a real group proposal immediately, e.g. "/plan pickleball".
    Runs the exact same propose -> collect -> confirm pipeline as the
    passively-detected path."""
    activity = activity.strip()
    if not activity:
        send_message(sender, "Tell me what you want to plan, like: /plan pickleball")
        return
    result = post_proposal_to_group(activity)
    print(f"MANUAL /plan by {sender}: {result}")


def handle_join_command(sender: str) -> None:
    """/join -- lets anyone (e.g. a judge trying the demo live) add
    themselves into the group Flow A plans for, on the spot, with no
    restart and no env-var edit. Also doubles as this number's real
    SendBlue "verified contact" text -- the free tier requires a
    recipient to message us first before we can message them, which
    texting this command already satisfies.

    Mutates DEMO_GROUP_NUMBERS in place (append, never reassign) so
    every other module's own `from app.config import DEMO_GROUP_NUMBERS`
    reference -- planning.py, crew_digest.py, mutual_mode.py -- keeps
    pointing at the same list object and sees the new member too."""
    phone = normalize_phone(sender)
    already_in = phone in DEMO_GROUP_NUMBERS
    if not already_in:
        DEMO_GROUP_NUMBERS.append(phone)
    text = (
        "You're already in the crew!"
        if already_in
        else "You're in! Next time this group plans something, you'll get a private "
        "heads-up to pick a time too. Text /website any time for a link to your "
        "own dashboard (calendar connect is optional)."
    )
    _safe_send(phone, text)


def handle_met_command(sender: str, name: str) -> None:
    """/met <name> -- manually log a real hangout without waiting on a
    Flow A plan to finalize. If <name> matches one of the sender's own
    solo Contacts, updates that Contact.last_met -- the exact field the
    Crew tab and /nudge digest already read for days_since/overdue, so
    this feeds the real logic with no other changes needed. If <name>
    instead matches another real Stickie user, reuses record_hangout()
    (app/mutual_mode.py) -- the same call planning.py already makes
    when a Flow A plan finalizes via RSVP, so a manual /met and a real
    confirmed plan update the drift clock identically."""
    name = name.strip()
    if not name:
        _safe_send(sender, "Who'd you meet? Try: /met Nancy")
        return

    other_phone = None
    other_name = None
    name_pattern = f"%{name}%"
    with get_session() as session:
        owner = session.query(User).filter_by(phone=sender).one_or_none()
        contact = (
            session.query(Contact)
            .filter(Contact.owner_user_id == owner.id, Contact.name.ilike(name_pattern))
            .first()
            if owner
            else None
        )
        if contact is not None:
            contact.last_met = dt.date.today()
            session.commit()
            _safe_send(sender, f"Got it -- logged that you just met up with {contact.name}.")
            return

        other = (
            session.query(User)
            .filter(User.phone.in_(DEMO_GROUP_NUMBERS), User.name.ilike(name_pattern))
            .first()
        )
        if other is not None and other.phone != sender:
            other_phone, other_name = other.phone, other.name

    if other_phone:
        record_hangout([sender, other_phone])
        _safe_send(sender, f"Got it -- logged that you and {other_name} just hung out.")
        return

    _safe_send(sender, f"Couldn't find anyone named '{name}' in your crew or contacts.")


def handle_nudge_command(sender: str) -> None:
    """/nudge -- builds and texts back a personal digest of everyone
    overdue in your crew (mutual friends + your own solo contacts), each
    with a real suggested plan. Nothing goes to anyone else until you
    reply approving specific items (see app/crew_digest.py)."""
    build_and_send_digest(sender)


def try_handle_command(sender: str, content: str | None) -> bool:
    """Returns True if `content` was a recognized command and has already
    been fully handled -- the webhook should stop processing this message
    any further when this returns True."""
    if not content:
        return False
    match = COMMAND_PATTERN.match(content.strip())
    if not match:
        return False

    command, rest = match.group(1).lower(), match.group(2)
    if command == "website":
        handle_website_command(sender)
        return True
    if command == "plan":
        handle_plan_command(sender, rest)
        return True
    if command == "nudge":
        handle_nudge_command(sender)
        return True
    if command == "join":
        handle_join_command(sender)
        return True
    if command == "met":
        handle_met_command(sender, rest)
        return True
    return False
