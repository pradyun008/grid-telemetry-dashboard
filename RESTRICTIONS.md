# RESTRICTIONS

Numeric limits and rules enforced in CSV batch mode. Enforced in BOTH
`src/server.py` (`/batch/start`) and `web/index.html` (client-side), which
must stay in sync. Rationale lives in DECISIONS.md D9.

## The three batch-mode fields

| Field | Rule | Why |
|-------|------|-----|
| Reporting rate (pts/s) | integer, `1 <= reporting <= 1000` | Bounds how fast the pool is walked and how big a CSV can get. Integer per D9. |
| Refresh interval (s) | `refresh >= 1/reporting` AND `refresh >= 0.25` AND `refresh <= 3600` | Can't pull faster than data is produced (else empty CSVs); 0.25s hard floor prevents polling storms when 1/reporting is tiny. |
| Points on screen | integer, `ceil(reporting*refresh) <= points <= 10000` | The window must hold at least one whole CSV; 10000 is the display/row ceiling. |

## Derived consequence — implicit CSV cap

Because `points >= ceil(reporting * refresh)` and `points <= 10000`, a single
CSV can never exceed 10000 rows. Any combination where
`ceil(reporting * refresh) > 10000` (e.g. reporting=1000, refresh=30 = 30000
rows) is rejected outright — no legal `points` value exists for it. This is
what bounds CSV size now that "rows per CSV" is no longer a direct input.

## Behavioral rules (not numeric bounds)

- Data is pre-generated into a fixed pool of `BatchGenerator.POOL_SIZE`
  (10000) value-rows and **loops** when exhausted: values wrap to the start,
  timestamps keep climbing (`t0 + index/reporting`).
- CSV row counts may **wobble** when the refresh interval isn't a clean
  multiple of the point spacing (e.g. reporting=3, refresh=0.5 -> 1,2,1,2).
  The long-run reporting rate stays exact.
