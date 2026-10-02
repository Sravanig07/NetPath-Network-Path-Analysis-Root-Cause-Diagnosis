from __future__ import annotations

import asyncio
import random
import time
from fastapi import FastAPI, Query

app = FastAPI(title="Test Service A (Latency Simulator)")


@app.get("/health")
def health():
    return {"status": "ok", "service": "test-service-a", "time": time.time()}


@app.get("/slow")
async def slow_response(delay: float = Query(2.0, ge=0.1, le=15.0)):
    await asyncio.sleep(delay)
    return {
        "status": "ok",
        "service": "test-service-a",
        "simulated_delay_seconds": delay,
        "message": f"Responded after deliberate delay of {delay}s"
    }


@app.get("/random-latency")
async def random_latency():
    delay = random.uniform(0.1, 1.5)
    await asyncio.sleep(delay)
    return {
        "status": "ok",
        "service": "test-service-a",
        "simulated_delay_seconds": round(delay, 3)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
