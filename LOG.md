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

---

## 2026-07-03 — Design CSV batch mode (alternate feed)

**Goal.** Design a second, alternate data-feed mode alongside the existing
live 1 Hz SSE stream: synthetic data delivered as CSV batches on a
schedule, with the dashboard window advancing in whole-batch increments
rather than one point at a time.

**Steps.**
1. Brainstormed requirements via clarifying Q&A: mode is a toggle on the
   same dashboard page (not a separate route); switching modes fully
   resets chart state; rows-per-CSV and feed-interval are independently
   configurable; window size is derived as `2 * rows_per_csv` (current
   batch + previous one, matching the user's "minute window, 30s batches"
   example); row timestamps within a batch are spread evenly across the
   feed interval so a batch's time span always matches its arrival
   cadence.
2. Researched how real grid telemetry systems move data, to decide the
   transport mechanism honestly rather than guessing: high-rate PMU/SCADA
   telemetry streams continuously (IEEE C37.118 over TCP/UDP); AMI smart
   meter interval data is commonly moved as literal batch CSV/XML file
   exports consumed by MDMS on a schedule. See search results cited in
   the design spec commit.
3. Decided batch mode should simulate the latter pattern faithfully: the
   server writes real `.csv` files to disk and the browser polls and
   fetches the file over plain HTTP, rather than pushing CSV-shaped text
   over a persistent SSE connection (considered and rejected — see
   DECISIONS.md D8 alternatives).
4. Wrote the full design as `DECISIONS.md` D8 (originally drafted as a
   standalone spec file, then folded into `DECISIONS.md` to match this
   project's existing convention of recording decisions there rather than
   in a separate `docs/` tree).

**Inputs / environment.** No code written yet — this was a design-only
session.

**Results.** Design agreed and recorded as D8. No implementation yet.

**Rationale.** See D8 in full for the "why" behind each choice (transport,
window derivation, prefetching, global vs. per-session state).

**Dead ends.**
- First draft of the spec was written to `docs/superpowers/specs/` as a
  standalone markdown file — this project doesn't have a `docs/` folder
  convention and records decisions in `DECISIONS.md` instead, so the
  content was folded into D8 there and the `docs/` folder removed.
- First transport proposal was JSON wrapping a CSV string sent over SSE;
  rejected once we realized it wasn't a literal file. Second proposal was
  raw multi-line CSV text over SSE (technically valid per the SSE spec's
  multi-line `data:` framing) — still rejected in favor of an actual file
  + HTTP fetch, since batch mode is meant to simulate real file-based
  ingestion, not a stream carrying file-shaped content.

**Next.** Write an implementation plan for D8 and build
`src/batch_simulator.py`, the `/batch/*` endpoints in `src/server.py`, and
the mode toggle + polling logic in `web/index.html`.

---

## 2026-07-13 — Batch mode: three independent knobs + pre-generated data

**Goal.** Split CSV batch mode's two coupled inputs (rows-per-CSV, feed
interval; window hard-derived as 2×rows) into three independent fields —
points on screen, refresh interval, reporting rate — and switch from
on-the-spot generation to a pre-generated looping pool.

**Steps.**
1. Rewrote `BatchGenerator` (`src/batch_simulator.py`): pre-generates a fixed
   pool of 10000 random value-rows, walks it at the reporting rate assigning
   timestamps at report time, loops on exhaustion. Each `next_batch_csv()`
   emits the points that came due in one refresh (point-spacing model).
2. Reworked `/batch/start` to take `points`, `refresh`, `reporting` and
   validate every restriction (see RESTRICTIONS.md).
3. Updated `web/index.html`: three fields, window sized directly from points,
   client-side validation mirroring the server.
4. Added `RESTRICTIONS.md`; pointed `CLAUDE.md` at it and `LOG.md`.
5. Added pytest suite (`tests/`) covering pool determinism, constant vs
   wobbling batch sizes, timestamp spacing, pool looping, and all
   server-side validation branches.

**Inputs / environment.** Python 3.11, FastAPI, pytest 8.3.4, httpx 0.28.1.

**Results.** `python -m pytest -v` green (13 tests). Manual browser checks:
constant and wobbling batch sizes confirmed via DevTools; all invalid combos
blocked with inline errors before any request.

**Rationale.** See DECISIONS.md D9 in full. Headline: separate production
(reporting rate), delivery (refresh interval), and display (points) so each
is reasoned about independently; pre-generated pool keeps the underlying
dataset stable while reporting rate only changes walk speed.

**Dead ends.**
- Considered forcing equal-size CSVs by constraining refresh to multiples of
  the point spacing — rejected (re-couples refresh to reporting, rejects
  typed values). Allowed the wobble instead.
