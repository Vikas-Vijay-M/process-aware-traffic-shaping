"""
This file contains the Stats dataclass for tracking statistics.
"""
from dataclasses import dataclass, asdict
import logging
import time


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
    send_invalid_param_errors: int = 0
    skipped_too_small_packets: int = 0

    def __post_init__(self):
        self._log = logging.getLogger(__name__)
        self.start_time = time.time()
        self.last_captured_packets = 0
        self.last_captured_bytes = 0
        self.last_sent_packets = 0
        self.last_sent_bytes = 0

    def calculate_and_log_rates(self, interval_seconds: float):
        """Calculates and logs the current packet and data rates."""
        
        current_captured_packets = self.captured_packets
        current_captured_bytes = self.captured_bytes
        current_sent_packets = self.sent_packets
        current_sent_bytes = self.sent_bytes

        # Packets per second
        capture_pps = (current_captured_packets - self.last_captured_packets) / interval_seconds
        send_pps = (current_sent_packets - self.last_sent_packets) / interval_seconds

        # Megabits per second
        capture_mbps = (current_captured_bytes - self.last_captured_bytes) * 8 / (1024 * 1024) / interval_seconds
        send_mbps = (current_sent_bytes - self.last_sent_bytes) * 8 / (1024 * 1024) / interval_seconds

        self._log.info(
            f"Rates: Capture={capture_pps:.2f} pps ({capture_mbps:.2f} Mbps), "
            f"Send={send_pps:.2f} pps ({send_mbps:.2f} Mbps)"
        )
        self._log.info(self.format())

        # Update last known values
        self.last_captured_packets = current_captured_packets
        self.last_captured_bytes = current_captured_bytes
        self.last_sent_packets = current_sent_packets
        self.last_sent_bytes = current_sent_bytes

    def format(self) -> str:
        """Return a single-line summary string of the statistics."""
        parts = [f"{key}={value}" for key, value in asdict(self).items() if key not in ['start_time', 'last_captured_packets', 'last_captured_bytes', 'last_sent_packets', 'last_sent_bytes']]
        return "Stats: " + ", ".join(parts)

    def print_final(self):
        """Prints the final summary of all statistics."""
        self._log.info("Final Statistics:")
        self._log.info(self.format())
        duration = time.time() - self.start_time
        if duration > 0:
            avg_capture_pps = self.captured_packets / duration
            avg_capture_mbps = self.captured_bytes * 8 / (1024 * 1024) / duration
            self._log.info(
                f"Average Capture Rate: {avg_capture_pps:.2f} pps ({avg_capture_mbps:.2f} Mbps) over {duration:.2f}s"
            )
