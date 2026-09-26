# Entry point for the backend. Run with: uvicorn app.main:app --reload
# Owns the /health check, the single SendBlue webhook every flow's
# messages arrive through (group chat + every 1:1 thread), and two
# manual demo-trigger endpoints for flows C and B-solo (not wired to any
# real detection yet — these just prove the send path works on demand).

import json

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.clients.sendblue import send_message
from app.commands import try_handle_command
from app.conversation import record_message, recent_messages
from app.crew_digest import try_resolve_digest_approval
from app.crew_routes import router as crew_router
from app.mutual_mode import run_mutual_mode_check
from app.onboarding import router as onboarding_router
from app.planning import post_proposal_to_group, record_time_pick
from app.primitives import get_pending_options, resolve_pending_reply
from app.reasoning import NEEDS_CLARIFICATION_PREFIX, detect_plan_intent

app = FastAPI(title="Stickie Backend")

# The frontend (Vite, port 5173) calls this API from the browser -
# without CORS enabled, every fetch from it would be silently blocked.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(onboarding_router)
app.include_router(crew_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "Stickie"}


@app.post("/webhook/sendblue")
async def sendblue_webhook(request: Request):
    """Receives every inbound SendBlue event: real messages, reactions, and
    delivery/read receipts for messages we sent. Delivery receipts are
    acknowledged and ignored; real inbound messages are checked against any
    pending "propose_options_and_await_reply" record (see app/primitives.py)."""
    try:
        payload = await request.json()
    except Exception:
        body_bytes = await request.body()
        print(f"Non-JSON inbound payload received: {body_bytes.decode('utf-8', errors='ignore')}")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Invalid JSON"})

    print("\n" + "=" * 50)
    print("INBOUND SENDBLUE PAYLOAD:")
    print(json.dumps(payload, indent=2))
    print("=" * 50 + "\n")

    sender = payload.get("from_number") or payload.get("number")
    content = payload.get("content")
    is_outbound = payload.get("is_outbound", False)

    if is_outbound:
        print(f"Outbound status update for message to {payload.get('to_number')}: {payload.get('status')}")
        return {"status": "acknowledged", "type": "outbound_receipt"}

    print(f"Message from {sender}: \"{content}\"")

    # Manual slash-commands (e.g. /website, /plan pickleball) always take
    # priority over passive detection -- if this was one, we're done.
    if try_handle_command(sender, content):
        print(f"COMMAND HANDLED for {sender}")
        return {"status": "command_handled", "from": sender}

    # If this sender has a pending /nudge digest awaiting their approval,
    # a reply like "1", "all", or "no" belongs to that decision, not to
    # anything else -- check it before Flow A's own pending-reply logic
    # so the two can never be mixed up.
    if try_resolve_digest_approval(sender, content):
        print(f"DIGEST APPROVAL HANDLED for {sender}")
        return {"status": "digest_approval_handled", "from": sender}

    # If this reply matches one of the active plan's private time-pick
    # options, tally it — record_time_pick() no-ops harmlessly if there's
    # no active plan or this isn't a real match (e.g. an unrelated message).
    resolution = resolve_pending_reply(sender, content)
    if resolution is not None:
        print(f"Resolved pending reply for {sender} -> {resolution}")
        if resolution.startswith(NEEDS_CLARIFICATION_PREFIX):
            # A real attempt to answer, just too ambiguous to resolve on
            # its own (e.g. "another time works better" with no hint
            # which) -- ask a real follow-up instead of the plan just
            # silently stalling forever, which is what used to happen.
            options = get_pending_options(sender) or []
            if options:
                choices = " or ".join(options) if len(options) <= 2 else ", ".join(options)
                send_message(sender, f"sorry, which did you mean -- {choices}? lmk and i'll lock it in")
        else:
            record_time_pick(sender, resolution)

    # Flow A: feed every group message into the recent-message window,
    # check whether a plan is forming (step 1), and if so, build + send
    # the real proposal (steps 2-3). post_proposal_to_group() clears the
    # conversation buffer so this doesn't fire again for the same plan.
    record_message(sender, content or "")
    plan = detect_plan_intent(recent_messages())
    if plan is not None:
        print(f"PLAN DETECTED: {plan}")
        result = post_proposal_to_group(plan["activity"])
        print(f"PROPOSAL SENT: {result}")

    return {"status": "received", "from": sender, "preview": content}


@app.post("/api/simulate-mutual-check")
def simulate_mutual_check(force: bool = True) -> dict:
    """Flow B mutual mode: real drift-nudge check on demand. `force=true`
    (the default, for demoing/testing live) ignores real dates and nudges
    every mutual pair regardless; `force=false` runs the actual
    NUDGE_THRESHOLD/last_nudged_date logic against real LastHangout rows."""
    nudged = run_mutual_mode_check(force=force)
    return {"nudged_pairs": nudged}


# --- Sophie's manual demo triggers (flows C and B-solo) ---
# Not wired to any real detection logic yet (Flow C needs the proximity
# toggle + distance check, Flow B-solo needs the contacts/rolodex + due
# check) — these just prove the send path fires on a button press.


class ProximityRequest(BaseModel):
    user_a_name: str
    user_b_name: str
    target_phone: str
    location_name: str


class ConciergeRequest(BaseModel):
    power_user_name: str
    contact_name: str
    target_phone: str
    intent: str


@app.post("/api/simulate-proximity")
def simulate_proximity(req: ProximityRequest):
    """Flow C: Spontaneous Proximity Spark."""
    text = (
        f"Stickie Proximity Alert: {req.user_a_name} and {req.user_b_name} are both at "
        f"{req.location_name} right now! Down for a quick 15-min coffee break?"
    )
    try:
        res = send_message(number=req.target_phone, text=text)
        return {"status": "success", "response": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulate-concierge")
def simulate_concierge(req: ConciergeRequest):
    """Flow B: Solo Concierge Mode (Nancy's workflow). Texts the contact
    directly with 2-3 concrete slots so one reply finishes it."""
    text = (
        f"Hi {req.contact_name}, this is {req.power_user_name}'s Stickie! They'd love to "
        f"{req.intent.lower()}. Based on their calendar, does Tue at 3:00 PM or "
        f"Wed at 5:00 PM work for you?"
    )
    try:
        res = send_message(number=req.target_phone, text=text)
        return {"status": "success", "response": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
