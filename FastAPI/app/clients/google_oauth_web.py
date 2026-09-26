# Per-user Google Calendar connect, via a real browser OAuth redirect —
# different from google_calendar.py, which is the one-time local-server
# flow for Bhaumi's own calendar only. Each user's own credentials JSON
# gets stored in users.google_token, keyed by their phone number, so
# Flow A can eventually check everyone's real calendar, not just one.
#
# Uses GOOGLE_WEB_CLIENT_ID/SECRET, a separate "Web application" type
# OAuth client, NOT the Desktop-app client google_calendar.py uses.
# Desktop-type clients only accept http://localhost redirects, which
# only resolve correctly when whoever completes the OAuth screen is on
# this same machine -- on a real user's own phone, "localhost" means
# their phone, so the redirect fails with ERR_CONNECTION_FAILED. A Web
# application client's redirect URI must be the backend's actual public
# address instead, registered up front in Google Cloud Console.

import json

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.clients.google_calendar import _to_rfc3339
from app.config import GOOGLE_WEB_CLIENT_ID, GOOGLE_WEB_CLIENT_SECRET, WEBHOOK_BASE_URL

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
REDIRECT_URI = f"{WEBHOOK_BASE_URL}/oauth/google/callback"

# get_authorization_url() and exchange_code_for_token() run as two separate
# HTTP requests, so a fresh Flow() in each would auto-generate a different
# random PKCE code_verifier for each -- the exchange would then send a
# verifier that doesn't match the code_challenge Google already saw,
# and every real token exchange fails with invalid_grant. Persisting the
# verifier here (keyed by state/phone) and reusing it on the callback
# side is what actually makes the round trip verify.
_code_verifiers: dict[str, str] = {}


def _flow(code_verifier: str | None = None) -> Flow:
    client_config = {
        "web": {
            "client_id": GOOGLE_WEB_CLIENT_ID,
            "client_secret": GOOGLE_WEB_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI, code_verifier=code_verifier
    )


def get_authorization_url(state: str) -> str:
    """state carries the phone number through the redirect round-trip, so
    the callback knows whose account this is."""
    flow = _flow()
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state)
    _code_verifiers[state] = flow.code_verifier
    return auth_url


def exchange_code_for_token(code: str, state: str) -> str:
    """Returns the credentials as a JSON string, ready to store in users.google_token."""
    flow = _flow(code_verifier=_code_verifiers.pop(state, None))
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
