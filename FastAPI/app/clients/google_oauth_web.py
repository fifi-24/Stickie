# Per-user Google Calendar connect, via a real browser OAuth redirect —
# different from google_calendar.py, which is the one-time local-server
# flow for Bhaumi's own calendar only. Each user's own credentials JSON
# gets stored in users.google_token, keyed by their phone number, so
# Flow A can eventually check everyone's real calendar, not just one.
#
# Uses the same GOOGLE_CLIENT_ID/SECRET (Desktop-app type) as
# google_calendar.py. Desktop-type clients accept any http://localhost
# redirect URI without extra registration, which is why this works with
# zero additional Google Cloud Console setup — but only when whoever is
# completing the OAuth screen does it from a browser that can actually
# reach that localhost address (i.e., on this machine).

import json

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.clients.google_calendar import _to_rfc3339
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
REDIRECT_URI = "http://localhost:8000/oauth/google/callback"


def _flow() -> Flow:
    client_config = {
        "installed": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)


def get_authorization_url(state: str) -> str:
    """state carries the phone number through the redirect round-trip, so
    the callback knows whose account this is."""
    flow = _flow()
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state)
    return auth_url


def exchange_code_for_token(code: str) -> str:
    """Returns the credentials as a JSON string, ready to store in users.google_token."""
    flow = _flow()
    flow.fetch_token(code=code)
    return flow.credentials.to_json()


def get_freebusy_for_user(token_json: str, time_min, time_max) -> list[dict]:
    """Same shape as google_calendar.get_freebusy(), but for a specific
    user's own stored token instead of Bhaumi's global one."""
    creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
    service = build("calendar", "v3", credentials=creds)
    body = {
        "timeMin": _to_rfc3339(time_min),
        "timeMax": _to_rfc3339(time_max),
        "items": [{"id": "primary"}],
    }
    result = service.freebusy().query(body=body).execute()
    return result["calendars"]["primary"]["busy"]
