import os
from dotenv import load_dotenv
from sendblue_client import send_message
from pathlib import Path
from dotenv import load_dotenv

# Points to /stickie/.env regardless of where you run the script from
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

load_dotenv()

target_number = os.getenv("MY_PHONE_NUMBER")

if not target_number:
    print("❌ Error: Set MY_PHONE_NUMBER in your .env file.")
    exit(1)

print(f"🚀 Sending test message to {target_number}...")

try:
    res = send_message(
        number=target_number,
        text="👋 Hey! This is Stickie testing live out of our hackathon repo."
    )
    print("✅ Message successfully queued/sent!")
    print("Response payload:", res)
except Exception as e:
    print(f"❌ Failed to send message: {e}")