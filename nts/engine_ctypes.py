import argparse
import logging
import time
from threading import Event

from .stats import Stats
from .windivert_ctypes import WinDivertCtypesDriver, WinDivertCtypesError

class CtypesPassthroughEngine:
    def __init__(self, args: argparse.Namespace, stop_event: Event):
        self.args = args
        self.stop_event = stop_event
        self.stats = Stats()
        self._log = logging.getLogger(__name__)
        self.driver = WinDivertCtypesDriver(logger=self._log)
        self.consecutive_errors = 0

    def run(self):
        self._log.info("Starting Ctypes Passthrough Engine...")
        try:
            with self.driver as driver:
                driver.open(self.args.filter)
                self._main_loop()
        except WinDivertCtypesError as e:
            self._log.critical(f"Failed to initialize WinDivert: {e}", exc_info=True)
        except Exception:
            self._log.critical("An unexpected error occurred in the engine.", exc_info=True)
        finally:
            self._log.info("Ctypes Passthrough Engine stopped.")
            self.stats.print_final()

    def _main_loop(self):
        start_time = time.time()
        last_stats_time = start_time
        packets_logged = 0

        while not self.stop_event.is_set():
            if self.args.run_seconds and (time.time() - start_time) > self.args.run_seconds:
                self._log.info(f"Run time of {self.args.run_seconds} seconds finished.")
                break

            try:
                packet, addr = self.driver.recv(self.args.bufsize)
                recv_len = len(packet)
                self.stats.captured_packets += 1
                self.stats.captured_bytes += recv_len

                if packets_logged < 5 and recv_len > 0:
                    self._log.debug(
                        f"Recv len={recv_len}, first_byte={packet[0]:#04x}"
                    )
                    packets_logged += 1

                self.driver.send(packet, addr)
                self.stats.sent_packets += 1
                self.stats.sent_bytes += recv_len
                
                self.consecutive_errors = 0

            except WinDivertCtypesError as e:
                self._log.error(f"Packet capture/send error: {e}")
                self.stats.errors += 1
                self.consecutive_errors += 1
                if self.consecutive_errors >= self.args.max_errors:
                    self._log.critical(f"Exceeded max consecutive errors ({self.args.max_errors}). Stopping.")
                    break
                continue

            current_time = time.time()
            if current_time - last_stats_time >= self.args.stats_interval:
                self.stats.calculate_and_log_rates(self.args.stats_interval)
                last_stats_time = current_time

    def stop(self):
        self._log.info("Stopping Ctypes Passthrough Engine...")
        self.stop_event.set()
