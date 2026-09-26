import os
import requests
from typing import List, Optional
from dotenv import load_dotenv
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

load_dotenv()

BASE_URL = os.getenv("SENDBLUE_BASE_URL", "https://api.sendblue.co/api")
API_KEY = os.getenv("SENDBLUE_API_KEY")
API_SECRET = os.getenv("SENDBLUE_API_SECRET")
FROM_NUMBER = os.getenv("SENDBLUE_FROM_NUMBER")

HEADERS = {
    "sb-api-key-id": API_KEY,
    "sb-api-secret-key": API_SECRET,
    "Content-Type": "application/json"
}

def send_message(number: str, text: str, media_url: Optional[str] = None) -> dict:
    """Send a direct 1-on-1 iMessage/SMS via Sendblue."""
    url = f"{BASE_URL}/send-message"
    payload = {
        "number": number,
        "content": text
    }
    if FROM_NUMBER:
        payload["from_number"] = FROM_NUMBER
    if media_url:
        payload["media_url"] = media_url

    response = requests.post(url, json=payload, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def send_group_message(numbers: List[str], text: str, group_id: Optional[str] = None) -> dict:
    """Send a group message to multiple numbers via Sendblue."""
    url = f"{BASE_URL}/send-group-message"
    payload = {
        "numbers": numbers,
        "content": text
    }
    if FROM_NUMBER:
        payload["from_number"] = FROM_NUMBER
    if group_id:
        payload["group_id"] = group_id

    response = requests.post(url, json=payload, headers=HEADERS)
    response.raise_for_status()
    return response.json()