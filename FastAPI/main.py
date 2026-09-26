import json
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load root .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Stickie Inbound Service")

@app.get("/")
def health_check():
    return {"status": "ok", "app": "Stickie"}

@app.post("/webhook/sendblue")
async def sendblue_webhook(request: Request):
    """
    Receives inbound SMS/iMessage payloads from Sendblue.
    """
    try:
        payload = await request.json()
    except Exception:
        # Fallback if body is empty or non-JSON
        body_bytes = await request.body()
        print(f"⚠️ Non-JSON inbound payload received: {body_bytes.decode('utf-8', errors='ignore')}")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Invalid JSON"})

    # Pretty-print raw inbound payload in console
    print("\n" + "=" * 50)
    print("📥 INBOUND SENDBLUE PAYLOAD RECEIVED:")
    print(json.dumps(payload, indent=2))
    print("=" * 50 + "\n")

    # Extract common Sendblue webhook fields
    sender = payload.get("from_number") or payload.get("number")
    content = payload.get("content")
    is_outbound = payload.get("is_outbound", False)

    # Ignore echo events if Sendblue sends outbound delivery receipts to the same hook
    if is_outbound:
        print(f"ℹ️ Outbound status update for message to {payload.get('to_number')}: {payload.get('status')}")
        return {"status": "acknowledged", "type": "outbound_receipt"}

    print(f"💬 Message from {sender}: \"{content}\"")

    # Send 200 OK immediately so Sendblue doesn't retry
    return {"status": "received", "from": sender, "preview": content}