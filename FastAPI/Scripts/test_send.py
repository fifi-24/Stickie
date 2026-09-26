# One-off script: sends yourself one real test iMessage via SendBlue.
# Run from FastAPI/: python Scripts/test_send.py

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.sendblue import send_message
from app.config import SENDBLUE_FROM_NUMBER  # noqa: F401 (imported for parity/debugging)

target_number = os.getenv("MY_PHONE_NUMBER")

if not target_number:
    print("Error: Set MY_PHONE_NUMBER in your .env file.")
    sys.exit(1)

print(f"Sending test message to {target_number}...")

try:
    res = send_message(
        number=target_number,
        text="Hey! This is Stickie testing live out of our hackathon repo.",
    )
    print("Message successfully queued/sent!")
    print("Response payload:", res)
except Exception as e:
    print(f"Failed to send message: {e}")
