"""
This file contains the Stats dataclass for tracking statistics.
"""
from dataclasses import dataclass, asdict

@dataclass
class Stats:
    """A dataclass to hold statistics."""
    captured_packets: int = 0
    sent_packets: int = 0
    dropped_packets: int = 0
    errors: int = 0
    captured_bytes: int = 0
    sent_bytes: int = 0
    dropped_bytes: int = 0

    def format(self) -> str:
        """Return a single-line summary string of the statistics."""
        parts = [f"{key}={value}" for key, value in asdict(self).items()]
        return "Stats: " + ", ".join(parts)
