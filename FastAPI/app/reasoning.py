# THE Muse Spark seam. Every place that needs to understand messy human
# text calls one of these two functions — tonight both are plain keyword
# heuristics (no network call, $0 cost, works fully offline). Tomorrow,
# once MODEL_API_KEY is live, replace each function's body with a real
# Muse Spark call. Nothing outside this file needs to change.


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


def interpret(reply_text: str, options: list[str]) -> str:
    text = reply_text.lower()

    for i, option in enumerate(options, start=1):
        if str(i) in text or option.lower() in text or any(w in text for w in _STRONG_ORDINALS.get(i, ())):
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
