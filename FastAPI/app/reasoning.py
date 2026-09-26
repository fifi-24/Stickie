# THE Muse Spark seam. Every place that needs to understand messy human
# text calls one of these two functions — tonight both are plain keyword
# heuristics (no network call, $0 cost, works fully offline). Tomorrow,
# once MODEL_API_KEY is live, replace each function's body with a real
# Muse Spark call. Nothing outside this file needs to change.

import re


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


def detect_plan_intent(messages: list[dict]) -> dict | None:
    """messages: [{"sender": phone, "text": str}, ...] oldest first.
    Returns {"activity": tag, "proposer": phone, "affirmers": [phone, ...]}
    the moment someone mentions an activity and at least one *other* person
    affirms afterward — or None if no plan is forming yet.
    Tomorrow: replace the body with a Muse Spark call over the same window,
    asking it to return this same shape."""
    for i, msg in enumerate(messages):
        text = msg["text"].lower()
        activity = next((tag for tag in ACTIVITY_TAGS if tag in text), None)
        if not activity:
            continue

        proposer = msg["sender"]
        affirmers: list[str] = []
        for later in messages[i + 1 :]:
            if later["sender"] == proposer or later["sender"] in affirmers:
                continue
            if any(word in later["text"].lower() for word in _AFFIRMATIONS):
                affirmers.append(later["sender"])

        if affirmers:
            return {"activity": activity, "proposer": proposer, "affirmers": affirmers}

    return None


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


def interpret(reply_text: str, options: list[str]) -> str:
    text = reply_text.lower()

    for i, option in enumerate(options, start=1):
        if str(i) in text or option.lower() in text or any(w in text for w in _STRONG_ORDINALS.get(i, ())):
            return option

    # Free-form day/time phrasing ("monday 3pm", "changed my mind, sat 6")
    # -- matches on meaning (same weekday + same hour/am-pm) rather than
    # requiring the option's exact "Monday 3:00PM" formatting verbatim.
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

    # Plain yes/no when there's only one option on the table
    if len(options) == 1:
        if any(word in text for word in ("yes", "yeah", "yep", "sounds good", "works")):
            return options[0]
        if any(word in text for word in ("no", "nah", "can't", "cant")):
            return "declined"

    return f"unrecognized reply: {reply_text!r}"


# Flow B mutual mode: the drift-nudge message sent to two friends once
# it's been a while since they last hung out. Tomorrow: replace the body
# with a real Muse Spark call, asking it for a short, natural nudge that
# can reference their shared interests/last activity -- the plain
# template below has no way to do that.
def generate_nudge_message(days_since: int | None) -> str:
    if days_since is None:
        return "hey! you two haven't grabbed anything through Stickie yet -- want to find a time?"
    return f"hey! it's been {days_since} days since you two hung out -- want to find a time to catch up?"
