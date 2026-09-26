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
# Separate "Web application" type OAuth client for the per-user browser
# redirect flow (app/clients/google_oauth_web.py) -- the Desktop-type
# client above only supports http://localhost redirects, which break
# the moment a real user completes this on their own phone instead of
# this machine. Falls back to the Desktop client's creds so nothing
# crashes before these are set, but the redirect will still fail on a
# real device until a real Web-application client is created and its
# redirect URI (WEBHOOK_BASE_URL + /oauth/google/callback) is registered.
GOOGLE_WEB_CLIENT_ID = os.environ.get("GOOGLE_WEB_CLIENT_ID") or GOOGLE_CLIENT_ID
GOOGLE_WEB_CLIENT_SECRET = os.environ.get("GOOGLE_WEB_CLIENT_SECRET") or GOOGLE_CLIENT_SECRET

WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")
# Where the onboarding magic-link text should point. Set this to whatever
# publicly reaches the frontend (e.g. a second tunnel) if you want the
# texted link to open on someone else's phone; defaults to localhost,
# which only works when opened on this machine.
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173")

MY_PHONE_NUMBER = os.environ.get("MY_PHONE_NUMBER", "")
# Comma-separated real, pre-verified demo numbers, e.g. "+19033063505,+1..."
# Falls back to just MY_PHONE_NUMBER (a 1-person "group") if not set.
DEMO_GROUP_NUMBERS = [
    n.strip() for n in os.environ.get("DEMO_GROUP_NUMBERS", MY_PHONE_NUMBER).split(",") if n.strip()
]
