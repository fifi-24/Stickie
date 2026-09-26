# Google Calendar freebusy client. First run opens a browser once for OAuth
# consent (needs GOOGLE_CLIENT_ID/SECRET in .env, from an OAuth client of
# type "Desktop app" in Google Cloud Console); after that a cached token in
# .google_token.json (repo root, gitignored) is reused with no browser step.

import datetime as dt
from pathlib import Path

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = Path(__file__).resolve().parents[3] / ".google_token.json"


def _get_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
                raise RuntimeError(
                    "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not set. Create an OAuth "
                    "client (Application type: Desktop app) in Google Cloud Console and "
                    "put both in .env."
                )
            client_config = {
                "installed": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())

    return creds


def _to_rfc3339(moment: dt.datetime) -> str:
    """Naive datetimes are assumed UTC; aware ones are converted to UTC.
    Either way, always produces a single valid 'Z'-suffixed timestamp —
    blindly appending "Z" to an aware datetime's isoformat() produces an
    invalid "+00:00Z" string, which is what broke this originally."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.timezone.utc)
    return moment.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def get_freebusy(calendar_id: str, time_min: dt.datetime, time_max: dt.datetime) -> list[dict]:
    """Returns the busy [{"start", "end"}, ...] blocks for one calendar in a window."""
    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)
    body = {
        "timeMin": _to_rfc3339(time_min),
        "timeMax": _to_rfc3339(time_max),
        "items": [{"id": calendar_id}],
    }
    result = service.freebusy().query(body=body).execute()
    return result["calendars"][calendar_id]["busy"]
