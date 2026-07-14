# Grid Telemetry Dashboard — System Summary

Real-time dashboard streaming synthetic telemetry across 4 channels. Python
(FastAPI) backend, vanilla JS + uPlot frontend. Data is currently random
values in `[0, 50]`, but the pipeline shape is real (push source → transport →
live browser charts).

Run: `python run.py` from this dir → opens http://127.0.0.1:8000. Deps:
`fastapi`, `uvicorn[standard]` (see `requirements.txt`). Python 3.9+.

## Layout

```
grid-telemetry-dashboard/
├── run.py                  # entry point; launches uvicorn on 127.0.0.1:8000, opens browser
├── src/
│   ├── channels.py         # Channel dataclass + CHANNELS list — single source of truth
│   ├── simulator.py        # GridSimulator: one random sample per tick (live/SSE mode)
│   ├── batch_simulator.py  # BatchGenerator: a whole CSV of rows at once (batch mode)
│   └── server.py           # FastAPI app: all endpoints
├── web/
│   ├── index.html          # entire frontend (HTML + CSS + JS in one file)
│   └── vendor/             # uPlot, bundled for offline use
└── data/batches/           # runtime CSV scratch (gitignored, ephemeral)
```

Docs: `README.md` (user-facing), `DECISIONS.md` (design rationale, referenced
as D8/D9 etc. in code comments), `LOG.md` (work log), `RESTRICTIONS.md`
(batch-mode numeric limits — enforced in both server and frontend).

**Before changing batch mode, read `RESTRICTIONS.md` and `LOG.md`.**

## Channels (`src/channels.py`)

`CHANNELS` is the single source of truth. Frozen `Channel` dataclass:
`key, label, unit, nominal, hard_low, hard_high, precision`. Currently 4
generic channels, all nominal 25.0, range 0–50. Backend and frontend both
derive from this (frontend fetches it via `/channels`). Edit this list to
add/rename channels — everything downstream adapts.

## Two data modes

**Live mode (SSE, default):** `GridSimulator.tick()` emits one sample
`{t: unix_ts, channel_1: ..., ...}` per second. Served over
`GET /stream` as Server-Sent Events. Each connection gets its own simulator;
`?seed=<int>` for reproducibility. One-directional + low-rate, so SSE over
WebSocket (see DECISIONS D-transport).

**Batch mode (CSV polling):** `BatchGenerator.next_batch_csv()` builds a whole
CSV in memory (header `t,channel_1..4` + rows emitted as they come due each
refresh; per-CSV count varies batch-to-batch, averaging reporting × refresh with
a max of ceil(reporting × refresh) used for window sizing). Server writes files to `data/batches/batch_XXXXX.csv`, keeps only
the last `BATCH_RETENTION = 3`. Client polls for the newest file. See DECISIONS D8.

## Endpoints (`src/server.py`)

| Method | Path             | Purpose                                                        |
|--------|------------------|----------------------------------------------------------------|
| GET    | `/`              | dashboard page (`web/index.html`)                              |
| GET    | `/channels`      | JSON channel defs; frontend builds charts from this            |
| GET    | `/stream`        | SSE telemetry, 1 sample/sec (live mode). `?seed=<int>`         |
| POST   | `/batch/start`   | `?points=&refresh=&reporting=&seed=`; writes batch 0, then one every `refresh`s via bg task. Validates: reporting 1–1000, refresh ≥ max(0.25, 1/reporting) and ≤ 3600, points ≥ ceil(reporting×refresh) and ≤ 10000 |
| POST   | `/batch/stop`    | cancels bg loop, deletes `data/batches/`                       |
| GET    | `/batch/latest`  | newest CSV via FileResponse; seq in `X-Batch-Seq` header       |

Batch mode uses a single global `batch_state = {"task", "seq"}` — local
single-user tool, no per-connection isolation (unlike `/stream`).

## Frontend (`web/index.html`, single file)

- Fetches `/channels`, builds one uPlot panel per channel.
- **Live mode:** consumes `/stream` SSE, pushes 1 pt/sec, `WINDOW = 10` pts.
- **Batch mode:** `startBatch(points, refresh, reporting)` calls `/batch/start?points=&refresh=&reporting=`, then `pollBatch()` on a
  timer every `refresh` seconds. Dedupes via `X-Batch-Seq` vs `lastBatchSeq` (skips
  re-render if unchanged). `parseCsv()` = naive `split("\n")`/`split(",")`.
  `WINDOW = points`. `batchDividerPlugin()` draws a vertical divider at each
  CSV boundary (tracked in `batchStarts[]`).

## Viewing the raw data

- Live JSON: `curl http://127.0.0.1:8000/stream`, or DevTools → Network →
  `stream` → EventStream tab.
- Batch CSV: `curl -i http://127.0.0.1:8000/batch/latest` (the `-i` shows
  `X-Batch-Seq`), or `cat data/batches/batch_*.csv`, or DevTools → Network →
  `batch/latest` responses.

## Gotchas / notes

- `data/batches/` is gitignored and ephemeral: only last 3 files kept, and
  `/batch/stop` (+ `/batch/start`) wipe the whole dir. No durable record of
  sent CSVs unless you raise `BATCH_RETENTION` or archive elsewhere.
- To plug in a real data source: replace `GridSimulator.tick()` (and/or
  `BatchGenerator`) — just return the same `{t, channel_*}` shape.
- To change history shown: `WINDOW` in `index.html`. To change value range:
  `rng.uniform(0, 50)` in the simulators + `scales.y.range` in `index.html`.
