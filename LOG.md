# PROJECT LOG — Grid Telemetry Dashboard

Append-only. Write entries contemporaneously, not from memory. One log per
project. Record dead ends and rationale, not just successes.

Entry template (copy for each new entry):

```
## YYYY-MM-DD — <short title>
**Goal.** What this session was trying to achieve.
**Steps.** What was actually done, in order.
**Inputs / environment.** Versions, seeds, config, machine.
**Results.** What happened + pointers to output files.
**Rationale.** Why the choices were made.
**Dead ends.** What was tried and abandoned, and why.
```

---

## 2026-06-24 — Scaffold project + build synthetic data pipeline
**Goal.** Stand up the project structure and a runnable end-to-end pipeline
(synthetic source → push transport → live dashboard) that a mentor can run
with one command. Implementation was gated on design clarity until now.

**Steps.**
1. Created folder structure: `src/` (Python package), `web/` (static
   frontend + vendored libs), top-level `run.py`.
2. Defined the four channels as the single source of truth in
   `src/channels.py` (frequency, voltage, active power, power factor).
3. Built `src/simulator.py`: mean-reverting (OU-style) dynamics + gaussian
   noise + slow drift + occasional decaying transient events. Seedable.
4. Built `src/server.py` (FastAPI): `/` serves the dashboard, `/channels`
   exposes channel defs, `/stream` is a 1 Hz SSE telemetry stream.
5. Built `web/index.html`: fetches `/channels`, subscribes to `/stream`,
   renders one uPlot chart per channel with tight auto-ranging against a
   dashed nominal baseline and a live deviation (Δ) readout.
6. Vendored uPlot v1.6.32 into `web/vendor/` so it runs with no internet.
7. Wrote `requirements.txt` (pinned), `.gitignore`, `README.md`,
   `DECISIONS.md`, and seeded this log.

**Inputs / environment.** Python 3 (system); FastAPI 0.115.6;
uvicorn[standard] 0.34.0; uPlot 1.6.32 (vendored). Simulator default
tick rate 1 Hz. Reproducibility seed example: `42`.

**Results.** End-to-end smoke test passed:
- `python -m src.simulator` → valid seeded ticks near nominal.
- `GET /channels` → 4 channel definitions (JSON).
- `GET /` → dashboard HTML.
- `GET /static/vendor/uPlot.iife.min.js` → HTTP 200 (vendoring works).
- `GET /stream` → JSON ticks at ~1.0 s spacing (1 Hz confirmed).
Output files: `src/channels.py`, `src/simulator.py`, `src/server.py`,
`run.py`, `web/index.html`, `web/vendor/*`.

**Rationale.** Recorded in full in `DECISIONS.md` (D1–D7). Headlines:
SSE over WebSocket (one-directional, low rate); uPlot + vanilla JS (small,
no build, offline); tight auto-range against nominal (visibility is an
axis-scaling problem); 5-min sliding window (bounds memory/latency).

**Dead ends.** None this session — the open decisions from scoping (data
source, channels, library, transport, window) were resolved as logged in
DECISIONS.md rather than discovered through failure.

**Next.** Open the dashboard and watch for a few minutes; sanity-check that
transients are visible and the Δ readouts read correctly. Then decide
whether any channel's dynamics need retuning, and whether to point the
simulator interface at a real/recorded source.

---

## 2026-06-24 — Simplify simulator, channels, and dashboard UI

**Goal.** Strip the project down to a bare-bones state: simple random data,
generic channel names, tighter UI, and a more sensible retention window.

**Steps.**
1. Replaced the OU physics model in `src/simulator.py` with `random.uniform(0, 50)`
   per channel per tick. Removed all PARAMS, event logic, and drift. Timestamp
   reverted to `time.time()` (Unix float) so uPlot x-axis works correctly.
2. Renamed channels from domain names (`frequency`, `voltage`, etc.) to
   `channel_1`–`channel_4` with generic labels in `src/channels.py`.
3. Removed `warn_low` / `warn_high` fields from the `Channel` dataclass and
   all four channel definitions.
4. Fixed y-axis ranging in `web/index.html`: replaced the tight nominal-centric
   `makeRange()` function with a fixed `[0, 50]` range to match the new data.
5. Changed retention window from 300 points (5 min) to 10 points (10 sec).
6. Replaced x-axis time format (which was showing full date + time) with a
   custom `values` function: shows `HH:MM` only when the minute changes,
   `:SS` otherwise. Reduced tick spacing from 64 → 30 px for a denser grid.
7. Bolded and brightened the UTC clock in the header (`#clock` element).

**Inputs / environment.** Same stack as session 1. No new dependencies.

**Results.** Dashboard renders correctly with line charts spanning 0–50,
10-second sliding window, and cleaner x-axis labels. Raw SSE ticks confirmed
via browser DevTools EventStream tab.

**Rationale.** The physics simulator was appropriate for a domain-accurate
prototype but added complexity that obscured the pipeline. Simplifying to
random values makes it easier to reason about what the system is doing.
See updated decisions D2, D5, D6.

**Dead ends.**
- Initially changed `t` to a `"%H:%M:%S"` string — broke uPlot which needs
  a numeric Unix timestamp. Reverted to `time.time()`.
- `makeRange()` with nominal-centric logic produced near-flat charts (y-axis
  locked to ~25±0.02) because the nominal reference line anchored dataMin.
  Replaced with fixed `[0, 50]`.
