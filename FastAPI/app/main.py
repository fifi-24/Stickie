# Entry point for the backend. Run with: uvicorn app.main:app --reload
# Right now it only proves the server boots — Tasks 4/5/etc. hang more onto `app`.

from fastapi import FastAPI

app = FastAPI(title="Stickie Backend")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
