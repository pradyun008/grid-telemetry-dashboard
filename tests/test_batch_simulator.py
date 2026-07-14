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
    # Same seed => identical pool => identical output for identical call sequence.
    a = BatchGenerator(reporting_rate=5, refresh_interval=1.0, seed=42)
    b = BatchGenerator(reporting_rate=5, refresh_interval=1.0, seed=42)
    assert a.next_batch_csv() == b.next_batch_csv()


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
    # Request more points than the pool holds; values must wrap to the start.
    gen = BatchGenerator(reporting_rate=1, refresh_interval=1.0, seed=1)
    gen.POOL_SIZE  # sanity: constant exists
    first = _rows(gen.next_batch_csv())[0][1:]   # channel values of global row 0
    # Advance the cursor to exactly POOL_SIZE, so the next row wraps to row 0.
    gen.reported = BatchGenerator.POOL_SIZE
    wrapped = _rows(gen.next_batch_csv())[0][1:]
    assert wrapped == first
