from __future__ import annotations

import random
from fastapi import FastAPI, HTTPException, Query, status

app = FastAPI(title="Test Service B (Error Simulator)")


@app.get("/health")
def health():
    return {"status": "ok", "service": "test-service-b"}


@app.get("/error")
def simulate_error(code: int = Query(500, description="HTTP status code to trigger")):
    if code == 500:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Simulated Internal Server Error in backend database query")
    elif code == 502:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Simulated Bad Gateway from upstream service")
    elif code == 503:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Simulated Service Unavailable - Capacity Exhausted")
    elif code == 504:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Simulated Gateway Timeout from upstream dependency")
    elif code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulated 404 Resource Not Found")
    else:
        raise HTTPException(status_code=code, detail=f"Simulated error code {code}")


@app.get("/flaky")
def flaky():
    if random.random() < 0.5:
        raise HTTPException(status_code=503, detail="Simulated intermittent flaky outage")
    return {"status": "ok", "service": "test-service-b", "message": "Flaky call succeeded"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
