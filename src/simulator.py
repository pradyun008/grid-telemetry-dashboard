"""Synthetic telemetry generator.

Each tick returns one sample with random values in [0, 50] for every
channel, plus a UTC timestamp string as the time-series index.
"""

import random
import time

from .channels import CHANNELS


class GridSimulator:
    def __init__(self, seed=None, hz=1.0):
        self.rng = random.Random(seed)
        self.seed = seed
        self.hz = hz
        self.period = 1.0 / hz

    def tick(self):
        """Return a sample dict: {t: Unix timestamp, <channel keys>: float in [0,50]}."""
        sample = {"t": time.time()}
        for c in CHANNELS:
            sample[c.key] = round(self.rng.uniform(0, 50), 2)
        return sample


if __name__ == "__main__":
    sim = GridSimulator(seed=42)
    for _ in range(10):
        print(sim.tick())
