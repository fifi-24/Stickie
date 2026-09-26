# The shared primitive reused by Flow A's private-RSVP fallback and every
# bit of Flow B's solo/concierge outreach: send ONE message with every
# option up front, remember we're waiting on a reply, and resolve it via
# interpret() (see app/reasoning.py) when the webhook sees a reply.

from dataclasses import dataclass

from app.clients.sendblue import send_message
from app.reasoning import interpret

# In-memory for tonight — fine for a single demo process. Move to a DB
# table if this needs to survive a restart before a reply comes back.
_pending: dict[str, "PendingReply"] = {}


@dataclass
class PendingReply:
    phone: str
    options: list[str]
    resolved: str | None = None


def propose_options_and_await_reply(phone: str, options: list[str], intro: str = "") -> None:
    """Sends ONE message containing every option up front — never an open
    'when are you free?' that forces a back-and-forth."""
    lines = "\n".join(f"{i}. {option}" for i, option in enumerate(options, start=1))
    message = f"{intro}\n{lines}".strip() if intro else lines
    send_message(phone, message)
    _pending[phone] = PendingReply(phone=phone, options=options)


def resolve_pending_reply(phone: str, reply_text: str | None) -> str | None:
    """Called from the webhook (app/main.py) on every inbound message.
    Returns the resolved option, or None if nothing was pending for this number."""
    pending = _pending.get(phone)
    if pending is None or reply_text is None:
        return None
    pending.resolved = interpret(reply_text, pending.options)
    return pending.resolved
