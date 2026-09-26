# The 5 tables the whole app shares: users, contacts, interests, plans,
# last_hangout. SQLite for now (DATABASE_URL in .env) — swapping to a hosted
# Postgres (e.g. Supabase) later is a one-line change, nothing here moves.

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    """A real Stickie account — a friend-group member or a solo-mode power user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    interests: Mapped[list["Interest"]] = relationship(back_populates="user")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="owner")


class Contact(Base):
    """One entry in a power user's one-sided rolodex (solo/concierge mode, Flow B)."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32))
    cadence_days: Mapped[int] = mapped_column(Integer, default=30)
    last_met: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    owner: Mapped["User"] = relationship(back_populates="contacts")


class Interest(Base):
    """One interest tag for a user, captured at onboarding (Flow A / Flow D)."""

    __tablename__ = "interests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tag: Mapped[str] = mapped_column(String(60))

    user: Mapped["User"] = relationship(back_populates="interests")


class Plan(Base):
    """A proposed or confirmed hangout (Flow A / solo mode's confirmed meetup)."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="proposed")  # proposed | confirmed | cancelled
    venue: Mapped[str] = mapped_column(String(200), default="")
    time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rsvps: Mapped[str] = mapped_column(Text, default="{}")  # small JSON blob: {"+15551234567": "yes"}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class LastHangout(Base):
    """Last-seen timestamp per pair/group, for mutual-mode drift detection (Flow B)."""

    __tablename__ = "last_hangout"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_key: Mapped[str] = mapped_column(String(200), unique=True)  # e.g. sorted "phoneA,phoneB"
    last_hangout_date: Mapped[date] = mapped_column(Date)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
