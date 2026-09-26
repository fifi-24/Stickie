# In-memory recent-message buffer for the group chat, so intent detection
# can look at a window of messages instead of one at a time. Good enough
# for tonight's single-group demo; a second group chat would need this
# keyed by group id (and probably a DB table) instead of one shared list.

_MAX_MESSAGES = 20
_messages: list[dict] = []


def record_message(sender: str, text: str) -> None:
    _messages.append({"sender": sender, "text": text})
    del _messages[: -_MAX_MESSAGES]


def recent_messages() -> list[dict]:
    return list(_messages)


def clear() -> None:
    _messages.clear()
