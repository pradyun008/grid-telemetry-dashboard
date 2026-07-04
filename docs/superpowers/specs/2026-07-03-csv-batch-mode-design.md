# CSV Batch Mode — Design

Date: 2026-07-03

## Summary

Add a second data-feed mode to the dashboard, alternate to the existing live
1 Hz SSE stream: a **CSV batch mode** that simulates the way real grid
telemetry sometimes arrives — not as a continuous stream, but as discrete
CSV files delivered on a schedule (the way AMI/MDMS meter-data pipelines
batch-export interval reads, as opposed to how PMU/SCADA telemetry streams
continuously over protocols like IEEE C37.118). The user toggles between
the two modes on the same dashboard page.

## Motivation

The current dashboard (`README.md`, `DECISIONS.md` D1–D7) only supports a
push-based, point-at-a-time feed. We want to demonstrate the other common
real-world telemetry delivery pattern: whole batches of rows delivered
periodically, where the visualization window advances in discrete chunks
rather than one point at a time.

## Configuration model

Two independently configurable knobs, set by the user in the UI before
starting batch mode:

- **rows_per_csv** — number of data rows in each CSV batch (default 30)
- **feed_interval_seconds** — how often a new CSV batch arrives (default 30)

These are independent: a batch can contain any number of rows regardless of
how often batches arrive. Row timestamps within a batch are spaced evenly
across the interval: `spacing = feed_interval_seconds / rows_per_csv`. This
keeps each CSV's internal time span exactly matching its arrival cadence,
with no overlaps or gaps between batches.

**Window size is derived, not configured directly**: the dashboard always
shows exactly the current batch plus the previous one, i.e.
`window_points = 2 * rows_per_csv`. When a new batch arrives, the oldest
batch's worth of points is dropped in one shot — the window advances in
whole-batch increments, not a rolling one-point-at-a-time shift.

Columns are fixed at the existing 4 channels (`channel_1`–`channel_4`) plus
timestamp, matching `src/channels.py` — no new channel configuration for
this feature.

## Backend

### `src/batch_simulator.py` (new)

A `BatchGenerator` class that, given `rows_per_csv`, `feed_interval_seconds`,
and an optional seed, produces one batch: `rows_per_csv` samples per
channel (same random generation approach as `GridSimulator`), with
timestamps spaced `feed_interval_seconds / rows_per_csv` apart starting
from "now." Serializes the batch to actual CSV text via Python's `csv`
module (header row: `t,channel_1,channel_2,channel_3,channel_4`).

### Disk storage

Batches are written to `data/batches/batch_%05d.csv` (sequence-numbered,
zero-padded). This directory is created at runtime and added to
`.gitignore` — it's scratch output, not checked in. Retention: after
writing a new batch, delete any files beyond the last 3, so disk usage
stays bounded during long-running sessions.

### Server endpoints (`src/server.py`)

Global (single active session) state — this is a local single-user tool,
so no per-connection isolation is needed for batch mode, unlike `/stream`.

- `POST /batch/start?rows=<int>&interval=<float>&seed=<int|None>`
  (Re)initializes batch state: cancels any existing background task,
  clears `data/batches/`, resets the sequence counter, generates and
  writes batch 0 immediately, then starts an asyncio background task.

  The background task loop, after the initial batch:
  1. Sleep until the current batch's `feed_interval_seconds` has elapsed
     since it was written.
  2. Generate and write the next batch immediately after — this ordering
     means batch-building happens right after the previous send, using
     the entire interval as slack, so generation cost (negligible for
     realistic row counts) never delays delivery.

- `POST /batch/stop`
  Cancels the background task and clears `data/batches/`. Called when the
  user switches back to live mode, or restarts batch mode with new
  settings (via a fresh `/batch/start` call, which also stops any prior
  session first).

- `GET /batch/latest`
  Returns the current latest batch file as `text/csv` (`FileResponse`),
  with a `X-Batch-Seq` response header carrying the sequence number so the
  client can detect whether this is actually a new batch or the same one
  as last poll.

## Frontend (`web/index.html`)

### Mode toggle

A toggle in the header: **Live (1 Hz)** / **Batch (CSV)**. Switching modes
fully resets dashboard state:
- Disconnects the current data source (closes the `EventSource` for live
  mode, or stops the polling `setInterval`/`setTimeout` for batch mode).
- Clears `xs`/`ys` arrays.
- Rebuilds panels/charts for the newly selected mode.

### Batch mode controls

Two number inputs — **rows per CSV** (default 30, validated 1–10,000) and
**feed interval (s)** (default 30, validated 1–3600) — plus a **Start**
button. Clicking Start:
1. Validates inputs client-side.
2. Calls `POST /batch/start?rows=...&interval=...`.
3. Begins polling `GET /batch/latest` every `interval` seconds.

### Polling and rendering

Each poll:
1. Read `X-Batch-Seq`. If unchanged since the last poll, skip entirely
   (guards against duplicate rendering from timing jitter between the
   client's poll cadence and the server's write cadence).
2. If new, parse the CSV response body into rows.
3. Append all rows' points to `xs`/`ys` in one operation.
4. Trim from the front of `xs`/`ys` so total length caps at exactly
   `2 * rows_per_csv` — this drops the entire oldest batch in one step
   once a third batch's worth would otherwise accumulate.
5. Call `plot.setData(...)` once for the whole updated window (a single
   batch redraw, not per-point animation) — this is what makes the window
   visibly advance in whole-batch increments rather than sliding smoothly.

Footer/window label text updates to reflect the current `2 * rows` window
size and batch-mode framing (vs. the live mode's "last N sec" text).

## Error handling

- Client-side validation rejects out-of-range `rows`/`interval` before
  calling `/batch/start` — no server-side round trip needed to catch
  obviously bad input.
- If a poll's `fetch` fails (e.g. server restarted), the status indicator
  shows the existing "reconnecting" styling reused from live mode; the
  client simply retries on the next scheduled poll — no special backoff
  or recovery logic.

## Testing

The project has no automated test suite (`DECISIONS.md`). Verification
will be manual, the same way the existing live dashboard is verified:
run the app, toggle into batch mode with a couple of different
rows/interval combinations, and confirm in the browser that the window
advances in discrete two-batch chunks — old data disappearing all at once
on batch arrival, not trickling out point by point.

## Out of scope

- Multi-user/session isolation for batch mode (global server state is
  fine for this local single-user tool).
- Configurable window size independent of `2 * rows_per_csv`.
- Persisting/inspecting historical batch files beyond the retention window.
- Automated tests (matches the existing project's lack of a test suite).
