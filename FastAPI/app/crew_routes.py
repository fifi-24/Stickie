# Real backend for the dashboard's Crew tab: list your actual crew
# (mutual Stickie friends + your own one-sided solo contacts), add/edit
# a contact, and nudge one person directly with a single click -- no
# more of the old mock's fake "Concierge nudge dispatched" banner that
# never sent anything.

import datetime as dt

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.crew_digest import list_crew, send_one_now
from app.db import Contact, User, get_session
from app.phone import normalize_phone

router = APIRouter()


@router.get("/crew")
def get_crew(phone: str) -> dict:
    return list_crew(normalize_phone(phone))


class AddContactRequest(BaseModel):
    owner_phone: str
    name: str
    phone: str
    cadence_days: int = 30


@router.post("/contacts")
def add_contact(body: AddContactRequest) -> dict:
    owner_phone = normalize_phone(body.owner_phone)
    with get_session() as session:
        owner = session.query(User).filter_by(phone=owner_phone).one_or_none()
        if owner is None:
            raise HTTPException(status_code=404, detail="No user with that phone")
        contact = Contact(
            owner_user_id=owner.id,
            name=body.name,
            phone=normalize_phone(body.phone),
            cadence_days=body.cadence_days,
        )
        session.add(contact)
        session.commit()
        return {"id": contact.id}


class UpdateContactRequest(BaseModel):
    cadence_days: int


@router.patch("/contacts/{contact_id}")
def update_contact(contact_id: int, body: UpdateContactRequest) -> dict:
    """Real per-contact cadence editing -- each solo contact can have its
    own overdue threshold, unlike mutual friends, which currently share
    one setting (see User.nudge_threshold_days)."""
    with get_session() as session:
        contact = session.query(Contact).filter_by(id=contact_id).one_or_none()
        if contact is None:
            raise HTTPException(status_code=404, detail="No such contact")
        contact.cadence_days = body.cadence_days
        session.commit()
        return {"status": "saved"}


class NudgeOneRequest(BaseModel):
    phone: str
    kind: str  # "mutual" | "solo"
    key: str | int  # a phone string for "mutual", a Contact id for "solo"


@router.post("/api/nudge-one")
def nudge_one(body: NudgeOneRequest) -> dict:
    """A direct nudge-one-person click from the Crew tab -- sends
    immediately, no approval round-trip, since clicking this button IS
    the explicit approval."""
    ok = send_one_now(normalize_phone(body.phone), body.kind, str(body.key))
    if not ok:
        raise HTTPException(status_code=400, detail="Could not send that nudge")
    return {"status": "sent"}


class SeedDemoRequest(BaseModel):
    phone: str


_DEMO_CONTACTS = [
    {"name": "Nancy Park", "phone": "+15555550101", "cadence_days": 30, "days_ago": 45},
    {"name": "Marcus Lee", "phone": "+15555550102", "cadence_days": 14, "days_ago": 25},
    {"name": "Priya Patel", "phone": "+15555550103", "cadence_days": 30, "days_ago": 10},
]


@router.post("/api/seed-demo-contacts")
def seed_demo_contacts(body: SeedDemoRequest) -> dict:
    """Demo/testing convenience, not a real user-facing feature: adds a
    few realistic fake solo contacts with varied last_met dates, so the
    Crew tab and /nudge digest have something real to show without
    waiting on an actual month to pass. Safe to call more than once --
    skips names that already exist for this owner. Their phone numbers
    are fake, so an actual nudge send to them will fail gracefully
    (reported as "failed to send") -- the UI/digest text itself is real
    either way."""
    owner_phone = normalize_phone(body.phone)
    with get_session() as session:
        owner = session.query(User).filter_by(phone=owner_phone).one_or_none()
        if owner is None:
            raise HTTPException(status_code=404, detail="No user with that phone")
        added = []
        for c in _DEMO_CONTACTS:
            existing = session.query(Contact).filter_by(owner_user_id=owner.id, name=c["name"]).one_or_none()
            if existing:
                continue
            session.add(Contact(
                owner_user_id=owner.id,
                name=c["name"],
                phone=c["phone"],
                cadence_days=c["cadence_days"],
                last_met=dt.date.today() - dt.timedelta(days=c["days_ago"]),
            ))
            added.append(c["name"])
        session.commit()
    return {"added": added}
