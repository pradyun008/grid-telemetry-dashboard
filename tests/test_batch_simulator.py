import math

from src.batch_simulator import BatchGenerator
from src.channels import CHANNELS


def _rows(csv_text):
    """Return data rows (list of lists) from CSV text, excluding the header."""
    lines = [ln for ln in csv_text.strip().split("\n") if ln]
    return [ln.split(",") for ln in lines[1:]]


def test_header_matches_channels():
    gen = BatchGenerator(reporting_rate=2, refresh_interval=0.5, seed=1)
    header = gen.next_batch_csv().strip().split("\n")[0]
    assert header == "t," + ",".join(c.key for c in CHANNELS)


def test_pool_is_pregenerated_and_seeded():
    # Same seed => identical pool => identical channel values. Timestamps are
    # wall-clock (t0 = time.time()) and differ between instances, so compare
    # only the channel columns, not the full CSV text.
    a = BatchGenerator(reporting_rate=5, refresh_interval=1.0, seed=42)
    b = BatchGenerator(reporting_rate=5, refresh_interval=1.0, seed=42)
    va = [r[1:] for r in _rows(a.next_batch_csv())]
    vb = [r[1:] for r in _rows(b.next_batch_csv())]
    assert va == vb


def test_constant_batch_size():
    # reporting=2 => points 0.5s apart; refresh=0.5 => exactly 1 point per batch.
    gen = BatchGenerator(reporting_rate=2, refresh_interval=0.5, seed=1)
    counts = [len(_rows(gen.next_batch_csv())) for _ in range(4)]
    assert counts == [1, 1, 1, 1]


def test_wobbling_batch_size():
    # reporting=3 => points ~0.333s apart; refresh=0.5 => counts alternate 1,2,1,2.
    gen = BatchGenerator(reporting_rate=3, refresh_interval=0.5, seed=1)
    counts = [len(_rows(gen.next_batch_csv())) for _ in range(4)]
    assert counts == [1, 2, 1, 2]


def test_timestamps_spaced_by_reporting_rate():
    gen = BatchGenerator(reporting_rate=4, refresh_interval=1.0, seed=1)
    rows = _rows(gen.next_batch_csv())          # 4 rows in the first second
    ts = [float(r[0]) for r in rows]
    diffs = [round(ts[i + 1] - ts[i], 3) for i in range(len(ts) - 1)]
    assert all(d == 0.25 for d in diffs)         # 1/4 s apart


def test_pool_loops_when_exhausted():
    # Walk the generator forward naturally until the pool wraps. reporting=1000,
    # refresh=1.0 => 1000 rows per batch; after 10 batches (10000 rows) the pool
    # is exhausted, so batch 11's first row (global index 10000) must wrap to the
    # same channel values as global row 0. No manual state poking — this drives
    # the real code path with a consistent cursor and batch_index.
    gen = BatchGenerator(reporting_rate=1000, refresh_interval=1.0, seed=1)
    row0_values = _rows(gen.next_batch_csv())[0][1:]   # global row 0
    for _ in range(9):
        gen.next_batch_csv()                            # batches 1..9 -> reported=10000
    wrap_first = _rows(gen.next_batch_csv())[0][1:]     # global row 10000
    assert wrap_first == row0_values
