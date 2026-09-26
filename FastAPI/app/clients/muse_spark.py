# The real Muse Spark client -- raw HTTP against the exact request shape
# confirmed from dev.meta.ai's own docs (Build with Muse Spark -> "At a
# glance" + its curl example): the OpenAI Responses API surface
# (POST {base}/responses, body has "input"/"output_text"), NOT Anthropic's
# Messages API -- the dashboard's "Configure Claude Code" tab is just one
# of several supported agent-CLI integrations, not the API's native shape.
# Using plain requests (already a dependency everywhere else in this app)
# instead of installing an SDK avoids any risk of a version mismatch
# between an SDK's method surface and this documented contract.

import requests

from app.config import MODEL_API_BASE_URL, MODEL_API_KEY, MUSE_SPARK_MODEL


def ask_muse_spark(prompt: str, max_output_tokens: int = 700) -> str:
    """Sends one prompt, returns the model's plain text reply. Every
    caller in app/reasoning.py asks for a specific, narrow output shape
    in its own prompt -- this function stays a thin, generic wrapper so
    the actual instructions live next to what's calling them.

    reasoning.effort defaults to "high" on Meta's side, which burned 458
    of 475 output tokens on invisible reasoning for a five-word answer
    in testing -- real cost/latency for no benefit on the narrow
    classification/extraction tasks this app actually needs. "low" is
    plenty for those."""
    response = requests.post(
        f"{MODEL_API_BASE_URL}/responses",
        headers={
            "Authorization": f"Bearer {MODEL_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MUSE_SPARK_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
            "reasoning": {"effort": "low"},
            "max_output_tokens": max_output_tokens,
            "stream": False,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    # Prefer the SDK-style convenience field if Meta's response includes
    # it; otherwise walk the raw "output" items for the first real
    # message's text block. Written defensively since this is the first
    # real call ever made against this endpoint -- adjusted live once we
    # see the actual response shape.
    if data.get("output_text"):
        return data["output_text"]

    for item in data.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") in ("output_text", "text"):
                    return block.get("text", "")

    return ""
