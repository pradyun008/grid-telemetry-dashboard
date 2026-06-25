# Grid Telemetry Dashboard

A real-time dashboard that streams live data across four channels, updating once per second. Built with Python (FastAPI) on the backend and vanilla JS + uPlot in the browser.

Data is synthetic for now — random values in the 0–50 range — but the pipeline is the real shape: a push-based source → SSE stream → live browser charts.

---

## Run it locally

You need **Python 3.9+**. From this folder:

```bash
# 1. (recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. start the server
python run.py
```

Then open **http://127.0.0.1:8000** in your browser. Stop with **Ctrl+C**.

> No internet needed — the charting library is bundled locally.

---

## What you'll see

Four panels (Channel 1–4), each showing:

- **Live value** (large) and its **deviation from nominal (Δ)**
- A **line chart** of the last 10 seconds of data, updating every second
- A dashed **nominal baseline** at 25.0 for reference

The UTC clock in the header updates live. X-axis labels show the current minute (`10:17`) when it changes, and seconds (`:30`, `:45`) in between.

---

## Inspect the raw data

To see the raw JSON ticks as they arrive:

**Browser DevTools (easiest):**
1. Open the dashboard
2. Press `Cmd+Option+I` (Mac) or `F12` (Windows)
3. Network tab → reload the page → click `stream` → **EventStream** tab

**curl:**
```bash
curl http://127.0.0.1:8000/stream
```

**Channel definitions:**
```
http://127.0.0.1:8000/channels
```

---

## Project layout

```
grid-telemetry-dashboard/
├── run.py              # entry point: python run.py
├── requirements.txt
├── src/
│   ├── channels.py     # channel definitions (single source of truth)
│   ├── simulator.py    # generates random telemetry ticks
│   └── server.py       # FastAPI: serves the page + /stream (SSE, 1 Hz)
└── web/
    ├── index.html      # the dashboard (vanilla JS + uPlot)
    └── vendor/         # uPlot, bundled for offline use
```

---

## Customising

- **Add/rename channels** → edit `src/channels.py`
- **Plug in a real data source** → replace `GridSimulator.tick()` in `src/simulator.py` — just return `{"t": <unix timestamp>, "channel_1": ..., ...}`
- **Change how much history is shown** → `WINDOW` constant in `web/index.html`
- **Change the data range** → update `rng.uniform(0, 50)` in `simulator.py` and `scales.y.range` in `web/index.html`

See `DECISIONS.md` for the reasoning behind each design choice.
