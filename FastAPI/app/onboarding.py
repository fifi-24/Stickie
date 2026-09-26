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

router = APIRouter()

TOKEN_VALID_MINUTES = 30


class StartRequest(BaseModel):
    phone: str


@router.post("/onboard/start")
def onboard_start(body: StartRequest) -> dict:
    """Texts `phone` a one-time link to the onboarding page. Called from
    the site's own 'enter your number' screen — this is the front door
    every new user goes through."""
    token = secrets.token_urlsafe(24)
    with get_session() as session:
        session.add(OnboardingToken(token=token, phone=body.phone))
        session.commit()

    link = f"{FRONTEND_BASE_URL}/onboard?token={token}"
    send_message(body.phone, f"Welcome to Stickie! Tap to set up your account: {link}")
    return {"status": "sent"}


@router.get("/onboard/verify")
def onboard_verify(token: str) -> dict:
    """The onboarding page calls this once, on load, with the token from
    the link's query string. Returns the phone number the token was
    issued for, or 401 if it's missing/used/expired."""
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


@router.get("/users/status")
def user_status(phone: str) -> dict:
    """The site calls this to decide whether to show onboarding or the
    real dashboard for a given (already-verified) phone number."""
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
        }


class CompleteRequest(BaseModel):
    phone: str
    name: str
    interests: list[str] = []


@router.post("/onboard/complete")
def onboard_complete(body: CompleteRequest) -> dict:
    """Real write: upserts the User row and replaces their interest tags."""
    with get_session() as session:
        user = session.query(User).filter_by(phone=body.phone).one_or_none()
        if user is None:
            user = User(name=body.name, phone=body.phone)
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
    site (same tab, same phone/browser that started onboarding, so
    stickie_phone is already in its localStorage) instead of leaving them
    on a dead-end "close this tab" page -- the site's own status check
    now sees has_calendar=true and shows the real dashboard immediately."""
    token_json = exchange_code_for_token(code, state)

    with get_session() as session:
        user = session.query(User).filter_by(phone=state).one_or_none()
        if user is None:
            user = User(name="", phone=state)
            session.add(user)
            session.flush()
        user.google_token = token_json
        session.commit()

    return RedirectResponse(FRONTEND_BASE_URL)
