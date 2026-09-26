# Loads .env (repo root) once and exposes every setting other modules need
# as a plain constant. Nothing else in the app should call os.environ directly.

import os
from pathlib import Path

from dotenv import load_dotenv

# .env lives at the repo root (one level above FastAPI/), matching .env.example
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./stickie.db")

MODEL_API_KEY = os.environ.get("MODEL_API_KEY", "")
MUSE_SPARK_MODEL = os.environ.get("MUSE_SPARK_MODEL", "muse-spark-1.3")
MODEL_API_BASE_URL = "https://api.meta.ai/v1"

SENDBLUE_API_KEY = os.environ.get("SENDBLUE_API_KEY", "")
SENDBLUE_API_SECRET = os.environ.get("SENDBLUE_API_SECRET", "")
SENDBLUE_BASE_URL = os.environ.get("SENDBLUE_BASE_URL", "https://api.sendblue.co/api")
SENDBLUE_FROM_NUMBER = os.environ.get("SENDBLUE_FROM_NUMBER", "")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")

WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")

MY_PHONE_NUMBER = os.environ.get("MY_PHONE_NUMBER", "")
# Comma-separated real, pre-verified demo numbers, e.g. "+19033063505,+1..."
# Falls back to just MY_PHONE_NUMBER (a 1-person "group") if not set.
DEMO_GROUP_NUMBERS = [
    n.strip() for n in os.environ.get("DEMO_GROUP_NUMBERS", MY_PHONE_NUMBER).split(",") if n.strip()
]
