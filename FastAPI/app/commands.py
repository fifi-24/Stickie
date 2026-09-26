# Manual commands anyone can text Stickie directly instead of waiting for
# passive detection. Checked FIRST in the webhook (app/main.py), before
# anything else -- a recognized command short-circuits normal processing.

import re
import secrets

from app.clients.sendblue import send_message
from app.config import FRONTEND_BASE_URL
from app.db import OnboardingToken, get_session
from app.mutual_mode import run_mutual_mode_check
from app.planning import post_proposal_to_group

COMMAND_PATTERN = re.compile(r"^/(\w+)\s*(.*)$", re.DOTALL)


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


def handle_nudge_command(sender: str) -> None:
    """/nudge -- manually runs the Flow B mutual-mode drift check right
    now (force=True: nudges every mutual pair regardless of real dates,
    same as the demo endpoint) instead of waiting on real elapsed time."""
    nudged = run_mutual_mode_check(force=True)
    send_message(sender, f"Nudged {len(nudged)} pair(s)." if nudged else "Nobody to nudge yet.")


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
    return False
