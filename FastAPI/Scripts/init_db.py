# One-off script (not part of the running app): creates the schema, then
# inserts + queries one smoke-test row per table so we can prove it works.
# Run from FastAPI/: `python scripts/init_db.py`

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Contact, Interest, LastHangout, Plan, User, get_session, init_db


def main() -> None:
    init_db()
    print("Schema created.")

    with get_session() as session:
        user = User(name="Bhaumi (smoke test)", phone="+15550000001")
        session.add(user)
        session.flush()  # get user.id without committing yet

        contact = Contact(
            owner_user_id=user.id,
            name="Nancy (smoke test)",
            phone="+15550000002",
            cadence_days=7,
            last_met=date.today() - timedelta(days=10),
            notes="Likes coffee, met at HackGT 13.",
        )
        interest = Interest(user_id=user.id, tag="trivia")
        plan = Plan(status="proposed", venue="Jittery Joe's", time=datetime.now(timezone.utc))
        last_hangout = LastHangout(
            group_key=f"{user.phone},{contact.phone}",
            last_hangout_date=date.today() - timedelta(days=10),
        )

        session.add_all([contact, interest, plan, last_hangout])
        session.commit()

        print("Inserted one row into each table. Querying them back:")
        print(" users        ->", session.query(User).filter_by(id=user.id).one().name)
        print(" contacts     ->", session.query(Contact).filter_by(owner_user_id=user.id).one().name)
        print(" interests    ->", session.query(Interest).filter_by(user_id=user.id).one().tag)
        print(" plans        ->", session.query(Plan).filter_by(id=plan.id).one().venue)
        print(
            " last_hangout ->",
            session.query(LastHangout).filter_by(group_key=last_hangout.group_key).one().last_hangout_date,
        )


if __name__ == "__main__":
    main()
