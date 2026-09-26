from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os

# Ensure the client is importable
from sendblue_client import send_message

app = FastAPI(title="Stickie API")

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
        f"💧 Stickie Proximity Alert: {req.user_a_name} and {req.user_b_name} are both at "
        f"{req.location_name} right now! Down for a quick 15-min coffee break?"
    )
    try:
        res = send_message(number=req.target_phone, text=text)
        return {"status": "success", "response": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate-concierge")
def simulate_concierge(req: ConciergeRequest):
    """
    Flow B: Solo Concierge Mode (Nancy's workflow).
    Texts the contact directly with 2-3 concrete slots so one reply finishes it.
    """
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
