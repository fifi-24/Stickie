# Stickie

The glue of the friend group — an AI agent that lives in your group chat (and 1:1 threads) over real iMessage, plans events, sparks spontaneous hangouts, discovers new ideas, and keeps friendships from drifting.

Built for HackGT 13, targeting Meta's "Bringing People Closer Together with AI" track.

## Repo layout

- `FastAPI/` — the backend service: the Muse Spark agent, SendBlue (iMessage) integration, Google Calendar/Places, and the database. Owned by Bhaumi (with Sophie's SendBlue client under `FastAPI/Scripts/`).
- `Frontend/` — the web control panel: onboarding, proximity toggle, plan/RSVP status, rolodex view. Owned by Sophie.

## Backend setup

```bash
cd FastAPI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` at the repo root and fill in real keys there — never in `.env.example`, and never commit `.env`.

Run the API:

```bash
uvicorn app.main:app --reload
```

Then check `http://127.0.0.1:8000/health`.

## Frontend setup

See `Frontend/README.md` (Sophie's scope).
