# THE Muse Spark seam. Every place that needs to understand messy human
# text calls interpret() — tonight it's a plain keyword heuristic (no
# network call, $0 cost, works fully offline). Tomorrow, once MODEL_API_KEY
# is live, replace the body of interpret() with a call to
# app.clients.muse_spark.ask_muse_spark, prompting it to pick the option
# the reply matches (or name a counter-proposal). Nothing outside this
# file needs to change — every caller already just does:
#     interpret(reply_text, options) -> str

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
