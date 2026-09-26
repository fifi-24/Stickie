# Every phone number in this app needs to compare equal to itself
# regardless of how it was typed -- a user onboarding via a website form
# might type "9033063505", "(903) 306-3505", or "+19033063505" for the
# same real number. Before this existed, a mismatch here silently created
# a second, separate User row under the "wrong" format, which looked to
# that person like the site had forgotten them and looped them back
# through onboarding from scratch. SendBlue's own webhook payloads always
# arrive already in "+1XXXXXXXXXX" form, so this mostly matters for
# whatever a person types into the "your phone number" field by hand.


def normalize_phone(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if raw.strip().startswith("+"):
        return f"+{digits}"
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}" if digits else raw.strip()
