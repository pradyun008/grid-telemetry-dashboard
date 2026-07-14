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
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .batch_simulator import BatchGenerator
from .channels import channels_as_dicts
from .simulator import GridSimulator

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
BATCH_DIR = Path(__file__).resolve().parent.parent / "data" / "batches"
BATCH_RETENTION = 3

app = FastAPI(title="Grid Telemetry Dashboard")
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

# Global batch-mode state. This is a local single-user tool (see DECISIONS.md
# D8), so a single active batch session is sufficient -- no per-connection
# isolation like /stream has.
batch_state = {"task": None, "seq": -1}


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


def _write_batch(gen):
    """Write the next batch to disk, prune old files, advance seq."""
    batch_state["seq"] += 1
    path = BATCH_DIR / f"batch_{batch_state['seq']:05d}.csv"
    path.write_text(gen.next_batch_csv())

    files = sorted(BATCH_DIR.glob("batch_*.csv"))
    for stale in files[:-BATCH_RETENTION]:
        stale.unlink()


async def _batch_loop(gen):
    while True:
        await asyncio.sleep(gen.feed_interval_seconds)
        _write_batch(gen)


@app.post("/batch/start")
async def batch_start(rows: int, interval: float, seed: int | None = None):
    """(Re)start CSV batch mode: write batch 0 immediately, then one new
    batch every `interval` seconds via a background task. See DECISIONS.md D8.
    """
    if rows < 1 or rows > 10_000:
        raise HTTPException(400, "rows must be between 1 and 10000")
    if interval <= 0 or interval > 3600:
        raise HTTPException(400, "interval must be between 0 and 3600 seconds")

    if batch_state["task"] is not None:
        batch_state["task"].cancel()

    shutil.rmtree(BATCH_DIR, ignore_errors=True)
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    batch_state["seq"] = -1

    gen = BatchGenerator(rows_per_csv=rows, feed_interval_seconds=interval, seed=seed)
    _write_batch(gen)
    batch_state["task"] = asyncio.create_task(_batch_loop(gen))
    return {"seq": batch_state["seq"]}


@app.post("/batch/stop")
async def batch_stop():
    """Stop the background batch loop and clear scratch batch files."""
    if batch_state["task"] is not None:
        batch_state["task"].cancel()
        batch_state["task"] = None
    shutil.rmtree(BATCH_DIR, ignore_errors=True)
    batch_state["seq"] = -1
    return {"stopped": True}


@app.get("/batch/latest")
async def batch_latest():
    """Return the most recent batch's CSV file, with its sequence number
    in X-Batch-Seq so the client can tell whether it's actually new.
    """
    if batch_state["seq"] < 0:
        raise HTTPException(404, "no batch available -- call /batch/start first")
    path = BATCH_DIR / f"batch_{batch_state['seq']:05d}.csv"
    return FileResponse(
        path,
        media_type="text/csv",
        headers={"X-Batch-Seq": str(batch_state["seq"])},
    )
