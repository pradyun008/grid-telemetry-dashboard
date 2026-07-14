"""Synthetic telemetry generator for CSV batch mode.

Unlike GridSimulator (one point pushed per tick), BatchGenerator walks
through a pre-generated pool of random value-rows at a fixed reporting rate
and emits, on each refresh, the rows whose report time came due during that
interval. See DECISIONS.md D9 and RESTRICTIONS.md.
"""

import csv
import io
import math
import random
import time

from .channels import CHANNELS


class BatchGenerator:
    POOL_SIZE = 10_000  # fixed pre-generated pool of value-rows; loops when exhausted

    def __init__(self, reporting_rate, refresh_interval, seed=None):
        self.reporting_rate = reporting_rate            # int points/sec
        self.refresh_interval = refresh_interval        # float seconds
        self.rng = random.Random(seed)
        self.dt = 1.0 / reporting_rate                  # seconds between points
        # Deterministic starting time when seeded for reproducibility; current time otherwise
        self.t0 = time.time()
        self.reported = 0                               # points reported so far
        self.batch_index = 0                            # 0-based refresh counter
        # Pre-generate the pool up front: channel values only, no timestamps.
        self.pool = [
            [round(self.rng.uniform(0, 50), 2) for _ in CHANNELS]
            for _ in range(self.POOL_SIZE)
        ]

    def next_batch_csv(self):
        """Return one batch's rows as CSV text, advancing the cursor.

        The number of points that should exist after refresh n (0-based) is
        floor((n + 1) * refresh_interval * reporting_rate); this batch carries
        that total minus everything already reported. The 1e-9 epsilon guards
        against float undershoot (e.g. 0.1 * 10 landing at 0.9999999999).
        """
        elapsed = (self.batch_index + 1) * self.refresh_interval
        total_due = math.floor(elapsed * self.reporting_rate + 1e-9)
        n_rows = total_due - self.reported

        buf = io.StringIO()
        fieldnames = ["t"] + [c.key for c in CHANNELS]
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for j in range(self.reported, self.reported + n_rows):
            values = self.pool[j % self.POOL_SIZE]
            row = {"t": round(self.t0 + j * self.dt, 3)}
            for c, v in zip(CHANNELS, values):
                row[c.key] = v
            writer.writerow(row)

        self.reported += n_rows
        self.batch_index += 1
        return buf.getvalue()
