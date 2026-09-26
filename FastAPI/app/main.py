# Entry point for the backend. Run with: uvicorn app.main:app --reload
# Owns the /health check and the single SendBlue webhook every flow's
# messages arrive through (group chat + every 1:1 thread).

import json

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.conversation import record_message, recent_messages
from app.planning import post_proposal_to_group, record_rsvp
from app.primitives import resolve_pending_reply
from app.reasoning import detect_plan_intent

app = FastAPI(title="Stickie Backend")


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

    # Both of these key off the sender's phone number independently, so we
    # run both rather than treat them as either/or: resolve_pending_reply
    # is for the private-RSVP fallback's time-pick question, record_rsvp is
    # for a plain yes/no in the group thread. A "yes" typed in the group
    # will show up as an "unrecognized reply" against the private time
    # question (harmless noise) AND get correctly recorded as an RSVP.
    resolution = resolve_pending_reply(sender, content)
    if resolution is not None:
        print(f"Resolved pending reply for {sender} -> {resolution}")

    if record_rsvp(sender, content or ""):
        print(f"RSVP recorded for {sender}")

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
