# Entry point for the backend. Run with: uvicorn app.main:app --reload
# Owns the /health check and the single SendBlue webhook every flow's
# messages arrive through (group chat + every 1:1 thread).

import json

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.primitives import resolve_pending_reply

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

    resolution = resolve_pending_reply(sender, content)
    if resolution is not None:
        print(f"Resolved pending reply for {sender} -> {resolution}")

    return {"status": "received", "from": sender, "preview": content}
