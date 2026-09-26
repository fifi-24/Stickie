# Sends real iMessages (SMS/RCS fallback automatic) via the SendBlue REST
# API. Moved here from Scripts/sendblue_client.py so every API client lives
# in one place; behavior is unchanged from Sophie's original.

from typing import List, Optional

import requests

from app.config import SENDBLUE_API_KEY, SENDBLUE_API_SECRET, SENDBLUE_BASE_URL, SENDBLUE_FROM_NUMBER

HEADERS = {
    "sb-api-key-id": SENDBLUE_API_KEY,
    "sb-api-secret-key": SENDBLUE_API_SECRET,
    "Content-Type": "application/json",
}


def send_message(number: str, text: str, media_url: Optional[str] = None) -> dict:
    """Send a direct 1-on-1 iMessage/SMS via Sendblue."""
    url = f"{SENDBLUE_BASE_URL}/send-message"
    payload = {"number": number, "content": text}
    if SENDBLUE_FROM_NUMBER:
        payload["from_number"] = SENDBLUE_FROM_NUMBER
    if media_url:
        payload["media_url"] = media_url

    response = requests.post(url, json=payload, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def send_group_message(numbers: List[str], text: str, group_id: Optional[str] = None) -> dict:
    """Send a group message to multiple numbers via Sendblue."""
    url = f"{SENDBLUE_BASE_URL}/send-group-message"
    payload = {"numbers": numbers, "content": text}
    if SENDBLUE_FROM_NUMBER:
        payload["from_number"] = SENDBLUE_FROM_NUMBER
    if group_id:
        payload["group_id"] = group_id

    response = requests.post(url, json=payload, headers=HEADERS)
    response.raise_for_status()
    return response.json()
