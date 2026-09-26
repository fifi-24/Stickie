# THE Muse Spark seam. Every place that needs to understand messy human
# text calls one of these three functions. Each now calls the real
# Muse Spark API (app/clients/muse_spark.py) first, and falls back to
# the original plain-keyword heuristic (kept, renamed _heuristic) if
# the real call fails or returns something unparseable for any reason
# -- a live demo should never go down because of one bad model response
# or a network hiccup, so every real call is wrapped defensively.

import json
import re

from app.clients.muse_spark import ask_muse_spark

# Flow A, step 1: detect a plan forming in a chat transcript.
# Matches the interest-tag vocabulary from onboarding, so a detected
# activity lines up with what search_places() is given later.
ACTIVITY_TAGS = [
    "trivia", "coffee", "hiking", "live music", "board games", "brunch",
    "movies", "sports", "karaoke", "pickleball", "study session", "food truck",
]

_AFFIRMATIONS = (
    "omg yes", "let's go", "lets go", "i'm down", "im down", "sounds good",
    "count me in", "yeah", "yes", "sure", "down",
)


def _detect_plan_intent_heuristic(messages: list[dict]) -> dict | None:
    for i, msg in enumerate(messages):
        text = msg["text"].lower()
        activity = next((tag for tag in ACTIVITY_TAGS if tag in text), None)
        if not activity:
            continue

        proposer = msg["sender"]
        affirmers: list[str] = []
        for later in messages[i + 1:]:
            if later["sender"] == proposer or later["sender"] in affirmers:
                continue
            if any(word in later["text"].lower() for word in _AFFIRMATIONS):
                affirmers.append(later["sender"])

        if affirmers:
            return {"activity": activity, "proposer": proposer, "affirmers": affirmers}

    return None


def _extract_json(text: str) -> dict | None:
    """Model replies sometimes wrap JSON in a markdown code fence or add
    a sentence around it -- pull out the first {...} block rather than
    requiring the whole reply to be bare JSON."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def detect_plan_intent(messages: list[dict]) -> dict | None:
    """messages: [{"sender": phone, "text": str}, ...] oldest first.
    Returns {"activity": tag, "proposer": phone, "affirmers": [phone, ...]}
    the moment someone mentions an activity and at least one *other*
    person affirms afterward — or None if no plan is forming yet."""
    if not messages:
        return None

    numbered = "\n".join(f"{i+1}. [{m['sender']}] {m['text']}" for i, m in enumerate(messages))
    known_senders = sorted({m["sender"] for m in messages})
    prompt = (
        "Here is a group chat transcript, oldest first. Each line shows the "
        "sender's phone number in brackets.\n\n"
        f"{numbered}\n\n"
        f"Known senders: {', '.join(known_senders)}\n\n"
        "Decide whether a real hangout plan is forming: someone proposes an "
        "activity (directly or indirectly) and at least one OTHER person "
        "affirms it afterward (agreement, enthusiasm, or a reaction implying "
        "'let's do this' -- not just replying on-topic). Sarcasm, joking, or "
        "explicitly declining does not count as affirming.\n\n"
        "Reply with ONLY a JSON object, no other text:\n"
        '{"plan_detected": true or false, "activity": "a couple words '
        'naming the activity, or null", "proposer": "the exact phone number '
        'who proposed it, or null", "affirmers": ["exact phone numbers who '
        'affirmed, only from the known senders list"]}'
    )
    try:
        raw = ask_muse_spark(prompt, max_output_tokens=1100)
        parsed = _extract_json(raw)
        if not parsed or not parsed.get("plan_detected"):
            return None
        activity = parsed.get("activity")
        proposer = parsed.get("proposer")
        affirmers = [a for a in parsed.get("affirmers", []) if a in known_senders]
        if not activity or proposer not in known_senders or not affirmers:
            return None
        return {"activity": activity, "proposer": proposer, "affirmers": affirmers}
    except Exception as exc:
        print(f"Muse Spark call failed in detect_plan_intent, falling back to heuristic: {exc}")
        return _detect_plan_intent_heuristic(messages)


# Flow A's private-RSVP fallback / Flow B's solo mode: resolve a free-text
# reply against a fixed set of options.

# Strong signals first (unambiguous), weak ones ("one", "two" as bare
# number-words) last — otherwise "the second one" would match index 1's
# weak word "one" before ever checking index 2's strong word "second".
_STRONG_ORDINALS = {1: ("1st", "first"), 2: ("2nd", "second"), 3: ("3rd", "third"), 4: ("4th", "fourth")}
_WEAK_ORDINALS = {1: ("one",), 2: ("two",), 3: ("three",), 4: ("four",)}

_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _extract_day_time(text: str) -> tuple[str | None, int | None, str | None]:
    """Pulls a weekday name and an hour+am/pm out of loose text, so "monday
    3pm" matches an option labelled "Monday 3:00PM" -- an exact substring
    match fails on that pair since the punctuation/leading-zero formatting
    differs, which is exactly what silently dropped a real changed-pick
    reply (it fell through to "unrecognized" and got ignored)."""
    day = next((d for d in _WEEKDAYS if d in text), None)
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)
    if not match:
        return day, None, None
    return day, int(match.group(1)), match.group(3)


def _interpret_heuristic(reply_text: str, options: list[str]) -> str:
    text = reply_text.lower()

    for i, option in enumerate(options, start=1):
        if str(i) in text or option.lower() in text or any(w in text for w in _STRONG_ORDINALS.get(i, ())):
            return option

    reply_day, reply_hour, reply_ampm = _extract_day_time(text)
    if reply_hour is not None:
        for option in options:
            opt_day, opt_hour, opt_ampm = _extract_day_time(option.lower())
            if reply_hour == opt_hour and reply_ampm == opt_ampm and (
                reply_day is None or opt_day is None or reply_day == opt_day
            ):
                return option

    for i, option in enumerate(options, start=1):
        if any(w in text for w in _WEAK_ORDINALS.get(i, ())):
            return option

    if len(options) == 1:
        if any(word in text for word in ("yes", "yeah", "yep", "sounds good", "works")):
            return options[0]
        if any(word in text for word in ("no", "nah", "can't", "cant")):
            return "declined"

    return f"unrecognized reply: {reply_text!r}"


NEEDS_CLARIFICATION_PREFIX = "needs_clarification: "


def interpret(reply_text: str, options: list[str]) -> str:
    """Resolves a free-text reply against a fixed set of options -- e.g.
    "eh thursday's rough, can we push to next week instead" against
    ["Monday 3:00PM", "Thursday 6:00PM"], which the old keyword-only
    heuristic could never parse (no exact substring, no ordinal, no
    recognizable day+time in the reply itself).

    Three-way classification, not just matched/unmatched: a reply that IS
    trying to answer this question but is too vague to resolve (e.g. bare
    "another time works better" with no hint which) returns a
    NEEDS_CLARIFICATION_PREFIX-tagged string so the webhook can text back
    a follow-up instead of silently stalling the plan forever -- which is
    exactly what used to happen. A reply that's unrelated to this question
    entirely (a side comment, declining outright) still returns the plain
    "unrecognized reply: ..." string and is silently ignored, same as
    before -- the plan shouldn't get a clarifying text for every off-topic
    message in the thread."""
    numbered = "\n".join(f"{i}. {opt}" for i, opt in enumerate(options, start=1))
    prompt = (
        f'Someone was privately asked to pick one of these options:\n{numbered}\n\n'
        f'Their reply was: "{reply_text}"\n\n'
        "Decide exactly one of three things:\n"
        '1. MATCHED -- their reply clearly picks one specific option, even '
        'phrased indirectly (e.g. preferring "the later one", or rejecting '
        'the other option by name so only one is left).\n'
        '2. AMBIGUOUS -- their reply is clearly trying to answer this '
        'question (a counter-proposal, a preference, a bare "yeah"/"no") '
        'but it is not possible to tell which specific option they mean, '
        'or they are asking for a different time not on the list at all.\n'
        '3. UNRELATED -- their reply has nothing to do with this question: '
        'a side comment, a question about something else, small talk, or a '
        "flat decline of the whole thing (not picking between the options, "
        "just not interested).\n\n"
        "Reply with ONLY a JSON object, no other text:\n"
        '{"status": "MATCHED" or "AMBIGUOUS" or "UNRELATED", '
        '"option": "exact option text copied verbatim from the list above, '
        'only if status is MATCHED, else null"}'
    )
    try:
        raw = ask_muse_spark(prompt, max_output_tokens=1100)
        parsed = _extract_json(raw)
        if not parsed:
            raise ValueError(f"unparseable interpret() response: {raw!r}")

        status = parsed.get("status")
        if status == "MATCHED":
            option = parsed.get("option")
            for opt in options:
                if option == opt:
                    return opt
            raise ValueError(f"MATCHED but option didn't match list: {option!r}")
        if status == "AMBIGUOUS":
            return f"{NEEDS_CLARIFICATION_PREFIX}{reply_text!r}"
        if status == "UNRELATED":
            return f"unrecognized reply: {reply_text!r}"
        raise ValueError(f"unexpected status in interpret() response: {parsed!r}")
    except Exception as exc:
        print(f"Muse Spark call failed in interpret, falling back to heuristic: {exc}")
        return _interpret_heuristic(reply_text, options)


def _generate_nudge_message_heuristic(
    other_name: str | None, days_since: int | None, venue: str | None, time_label: str | None
) -> str:
    who = other_name or "your friend"
    if days_since is None:
        opener = f"hey! you and {who} haven't hung out through Stickie yet."
    else:
        opener = f"hey, it's been {days_since} days since you and {who} hung out."

    if venue and time_label:
        return f"{opener} want to grab {venue} on {time_label}? let me know if that works"
    return f"{opener} want to find a time to catch up?"


# Flow B mutual mode: the drift-nudge message sent to two friends once
# it's been a while since they last hung out.
def generate_nudge_message(
    other_name: str | None, days_since: int | None, venue: str | None, time_label: str | None
) -> str:
    who = other_name or "your friend"
    gap = "haven't hung out through Stickie yet" if days_since is None else f"haven't hung out in {days_since} days"
    plan_bit = f" Suggested plan: {venue} on {time_label}." if venue and time_label else ""
    prompt = (
        f"Write ONE short text message (under 220 characters) nudging someone "
        f"to reconnect with their friend {who}, who they {gap}.{plan_bit} "
        "Sound like a real person texting a friend, not an app notification: "
        "casual, warm, a little playful is fine. No emojis, no hashtags, no "
        "markdown, no em dashes (use a comma or period instead). Reply with "
        "ONLY the message text, nothing else."
    )
    try:
        raw = ask_muse_spark(prompt, max_output_tokens=1100).strip().strip('"')
        if not raw or len(raw) > 320:
            raise ValueError(f"empty or too-long nudge message: {raw!r}")
        return raw
    except Exception as exc:
        print(f"Muse Spark call failed in generate_nudge_message, falling back to heuristic: {exc}")
        return _generate_nudge_message_heuristic(other_name, days_since, venue, time_label)
