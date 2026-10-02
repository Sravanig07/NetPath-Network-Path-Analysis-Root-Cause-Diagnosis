from __future__ import annotations

import asyncio
from fastapi import FastAPI, Response, status

app = FastAPI(title="Test Service C (Timeout & Rate Limit Simulator)")


@app.get("/health")
def health():
    return {"status": "ok", "service": "test-service-c"}


@app.get("/timeout")
async def timeout():
    # Deliberately sleep for 30 seconds to force client probe timeout
    await asyncio.sleep(30.0)
    return {"status": "late_response"}


@app.get("/rate-limit")
def rate_limit(response: Response):
    response.status_code = status.HTTP_429_TOO_MANY_REQUESTS
    response.headers["Retry-After"] = "60"
    return {
        "status": "error",
        "code": 429,
        "detail": "Too many requests. Rate limit quota exceeded."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
