# The real onboarding flow: text a phone number a magic link -> they land
# on the site already "logged in" as themselves (no password) -> set
# name + interests -> connect Google Calendar. Everything here writes to
# the real database; nothing is mocked.

from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.clients.google_oauth_web import exchange_code_for_token, get_authorization_url
from app.clients.sendblue import send_message
from app.config import FRONTEND_BASE_URL
from app.db import Interest, OnboardingToken, User, get_session
from app.phone import normalize_phone

router = APIRouter()

TOKEN_VALID_MINUTES = 30


class StartRequest(BaseModel):
    phone: str


@router.post("/onboard/start")
def onboard_start(body: StartRequest) -> dict:
    """Texts `phone` a 4-digit verification code. Called from the site's
    own login screen (name + phone entered together) -- this is the
    front door every new user goes through. Real numeric-code
    verification, not a magic link: nothing here depends on the phone's
    own browser being able to reach our tunnel URL, which a link would."""
    phone = normalize_phone(body.phone)
    code = f"{secrets.randbelow(10000):04d}"
    with get_session() as session:
        session.add(OnboardingToken(token=code, phone=phone))
        session.commit()

    try:
        send_message(phone, f"Your Stickie verification code is {code}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not text that number") from exc
    return {"status": "sent"}


@router.get("/onboard/verify")
def onboard_verify(token: str) -> dict:
    """Magic-link verification -- still used by /website and any texted
    link (see app/commands.py's handle_website_command), which creates
    its own long random token separately from the numeric-code flow
    above. Returns the phone the token was issued for, or 401 if it's
    missing/used/expired."""
    with get_session() as session:
        row = session.query(OnboardingToken).filter_by(token=token).one_or_none()
        if row is None or row.used:
            raise HTTPException(status_code=401, detail="Invalid or already-used link")
        if datetime.now(timezone.utc) - row.created_at.replace(tzinfo=timezone.utc) > timedelta(
            minutes=TOKEN_VALID_MINUTES
        ):
            raise HTTPException(status_code=401, detail="This link has expired")

        row.used = True
        session.commit()
        return {"phone": row.phone}


class VerifyCodeRequest(BaseModel):
    phone: str
    name: str
    code: str


@router.post("/onboard/verify-code")
def onboard_verify_code(body: VerifyCodeRequest) -> dict:
    """The real signup step: checks the 4-digit code texted by
    /onboard/start, and on success upserts the User row with the name
    entered on the same screen -- one step instead of the old
    verify-then-separately-save-name flow, matching a name+phone
    collected together up front."""
    phone = normalize_phone(body.phone)
    with get_session() as session:
        row = (
            session.query(OnboardingToken)
            .filter_by(phone=phone, token=body.code, used=False)
            .order_by(OnboardingToken.created_at.desc())
            .first()
        )
        if row is None:
            raise HTTPException(status_code=401, detail="Wrong code")
        if datetime.now(timezone.utc) - row.created_at.replace(tzinfo=timezone.utc) > timedelta(
            minutes=TOKEN_VALID_MINUTES
        ):
            raise HTTPException(status_code=401, detail="This code has expired")

        row.used = True

        user = session.query(User).filter_by(phone=phone).one_or_none()
        if user is None:
            user = User(name=body.name, phone=phone)
            session.add(user)
        else:
            user.name = body.name
        session.commit()

        return {"phone": phone}


@router.get("/users/status")
def user_status(phone: str) -> dict:
    """The site calls this to decide whether to show onboarding or the
    real dashboard for a given (already-verified) phone number."""
    phone = normalize_phone(phone)
    with get_session() as session:
        user = session.query(User).filter_by(phone=phone).one_or_none()
        if user is None:
            return {"exists": False}
        interests = [i.tag for i in session.query(Interest).filter_by(user_id=user.id).all()]
        return {
            "exists": True,
            "name": user.name,
            "interests": interests,
            "has_calendar": bool(user.google_token),
            "nudge_threshold_days": user.nudge_threshold_days,
        }


class SettingsRequest(BaseModel):
    phone: str
    nudge_threshold_days: int


@router.post("/users/settings")
def update_settings(body: SettingsRequest) -> dict:
    """Persists the real, per-user override for how many days without
    seeing someone before /nudge calls it overdue -- what the dashboard's
    'Review' dropdown actually controls now, instead of just local state
    that reset on refresh."""
    phone = normalize_phone(body.phone)
    with get_session() as session:
        user = session.query(User).filter_by(phone=phone).one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="No user with that phone")
        user.nudge_threshold_days = body.nudge_threshold_days
        session.commit()
        return {"status": "saved"}


class CompleteRequest(BaseModel):
    phone: str
    name: str
    interests: list[str] = []


@router.post("/onboard/complete")
def onboard_complete(body: CompleteRequest) -> dict:
    """Real write: upserts the User row and replaces their interest tags."""
    phone = normalize_phone(body.phone)
    with get_session() as session:
        user = session.query(User).filter_by(phone=phone).one_or_none()
        if user is None:
            user = User(name=body.name, phone=phone)
            session.add(user)
            session.flush()
        else:
            user.name = body.name
            session.query(Interest).filter_by(user_id=user.id).delete()

        for tag in body.interests:
            session.add(Interest(user_id=user.id, tag=tag))

        session.commit()
        return {"user_id": user.id}


@router.get("/oauth/google/start")
def oauth_google_start(phone: str) -> RedirectResponse:
    """'Connect Google Calendar' button hits this; it redirects to Google's
    real consent screen. `phone` rides through as `state` so the callback
    knows whose account to attach the token to."""
    return RedirectResponse(get_authorization_url(state=phone))


@router.get("/oauth/google/callback")
def oauth_google_callback(code: str, state: str) -> RedirectResponse:
    """Google redirects back here after consent. `state` is the phone
    number we sent in oauth_google_start. Stores the real credentials on
    that user's row -- this is what makes their own calendar usable
    later, instead of only Bhaumi's. Sends them straight back into the
    site with their phone as an explicit ?phone= param -- not relying on
    stickie_phone already being in this tab's localStorage, since that
    can't be guaranteed (different tab, cleared storage, etc). The
    site's own status check then sees has_calendar=true and shows the
    real dashboard immediately, instead of leaving them on a dead-end
    "close this tab" page or bouncing them back into onboarding."""
    token_json = exchange_code_for_token(code, state)

    with get_session() as session:
        user = session.query(User).filter_by(phone=state).one_or_none()
        if user is None:
            user = User(name="", phone=state)
            session.add(user)
            session.flush()
        user.google_token = token_json
        session.commit()

    return RedirectResponse(f"{FRONTEND_BASE_URL}/?phone={state}")
