"""Telemetry channel definitions.

This is the single source of truth for what the grid is reporting. The
simulator, the SSE server, and the dashboard frontend all read from here
(the frontend fetches it over /channels), so the four channels and their
nominal values are defined exactly once.

To change which channels exist, edit this list. Everything downstream
adapts automatically.
"""

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Channel:
    key: str
    label: str
    unit: str
    nominal: float
    hard_low: float
    hard_high: float
    precision: int


# Four channels of a transmission-bus telemetry point.
# Chosen to span very different scales of "operationally significant change":
#   - frequency barely moves but tiny moves matter enormously
#   - power factor is a bounded ratio
#   - voltage drifts on a slow band
#   - active power swings widely with load
CHANNELS = [
    Channel(key="channel_1", label="Channel 1", unit="", nominal=25.0, hard_low=0.0, hard_high=50.0, precision=2),
    Channel(key="channel_2", label="Channel 2", unit="", nominal=25.0, hard_low=0.0, hard_high=50.0, precision=2),
    Channel(key="channel_3", label="Channel 3", unit="", nominal=25.0, hard_low=0.0, hard_high=50.0, precision=2),
    Channel(key="channel_4", label="Channel 4", unit="", nominal=25.0, hard_low=0.0, hard_high=50.0, precision=2),
]


def channels_as_dicts():
    """Serializable form for the /channels endpoint."""
    return [asdict(c) for c in CHANNELS]
