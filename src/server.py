"""FastAPI app: serves the dashboard and pushes telemetry over SSE.

Endpoints:
  GET /          -> the dashboard page (web/index.html)
  GET /channels  -> JSON list of channel definitions (frontend builds charts from this)
  GET /stream    -> Server-Sent Events stream, one telemetry tick per second

Transport is SSE rather than WebSocket: the data is one-directional
(server -> browser) and low rate (1 Hz), which is exactly SSE's sweet
spot, and it needs no extra client library. See DECISIONS.md.
"""

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .channels import channels_as_dicts
from .simulator import GridSimulator

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Grid Telemetry Dashboard")
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/channels")
def channels():
    return channels_as_dicts()


@app.get("/stream")
async def stream(seed: int | None = None):
    """Server-Sent Events stream of telemetry, one sample per second.

    Each connection gets its own simulator. Pass ?seed=<int> for a
    reproducible stream.
    """
    sim = GridSimulator(seed=seed)

    async def event_generator():
        while True:
            sample = sim.tick()
            yield f"data: {json.dumps(sample)}\n\n"
            await asyncio.sleep(sim.period)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # disable proxy buffering if present
    }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )
