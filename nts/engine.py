import logging
import time
import binascii
from nts.windivert_iface import WinDivertDriver, WinDivertError
from nts.stats import Stats

class PassthroughEngine:
    """
    An engine that captures packets and reinjects them immediately.
    """

    def __init__(
        self,
        driver: WinDivertDriver,
        filter_str: str,
        stats: Stats,
        stats_interval: float,
        logger: logging.Logger,
    ):
        self._driver = driver
        self._filter = filter_str
        self._stats = stats
        self._stats_interval = stats_interval
        self._log = logger

    def run(self, run_seconds: float = 0, max_errors: int = 20, max_packets: int = 0, diagnostic_packets: int = 20) -> None:
        """
        Runs the passthrough engine.

        Args:
            run_seconds: The duration to run in seconds. If 0, runs indefinitely.
            max_errors: The maximum number of consecutive errors before stopping.
            max_packets: The maximum number of packets to capture before stopping.
            diagnostic_packets: Number of initial packets to log with full diagnostics.
        """
        start_time = time.time()
        last_stats_time = start_time
        error_count = 0
        last_packets = 0
        last_bytes = 0

        try:
            self._driver.open(self._filter)
            self._log.info("Passthrough engine started.")

            while True:
                # Check for exit conditions
                if run_seconds > 0 and (time.time() - start_time) > run_seconds:
                    self._log.info(f"Run time of {run_seconds} seconds exceeded.")
                    break
                if max_packets > 0 and self._stats.captured_packets >= max_packets:
                    self._log.info(f"Captured {self._stats.captured_packets} packets, exceeding max of {max_packets}.")
                    break

                try:
                    packet = self._driver.recv(timeout=1)
                    if packet:
                        # Safely get raw bytes and length
                        raw_bytes = None
                        packet_len = 0
                        if hasattr(packet, 'raw'):
                            if isinstance(packet.raw, memoryview):
                                packet_len = packet.raw.nbytes
                                raw_bytes = packet.raw.tobytes()
                            elif isinstance(packet.raw, (bytes, bytearray)):
                                packet_len = len(packet.raw)
                                raw_bytes = bytes(packet.raw)

                        self._stats.captured_packets += 1
                        self._stats.captured_bytes += packet_len

                        # Diagnostic logging for the first N packets
                        if self._stats.captured_packets <= diagnostic_packets:
                            self._log.info(f"--- Packet #{self._stats.captured_packets} Diagnostics ---")
                            self._log.info(f"  - Type: {type(packet)}")
                            if hasattr(packet, 'raw'):
                                self._log.info(f"  - Raw Type: {type(packet.raw)}")
                                if isinstance(packet.raw, memoryview):
                                    self._log.info(f"  - Raw memoryview: nbytes={packet.raw.nbytes}, format='{packet.raw.format}', itemsize={packet.raw.itemsize}")
                                else:
                                    self._log.info(f"  - Raw len: {len(packet.raw)}")
                            
                            if raw_bytes:
                                self._log.info(f"  - Raw Hex (first 64 bytes): {binascii.hexlify(raw_bytes[:64]).decode()}")

                            if hasattr(packet, 'src_addr'):
                                self._log.info(f"  - Src Addr: {packet.src_addr}")
                            if hasattr(packet, 'dst_addr'):
                                self._log.info(f"  - Dst Addr: {packet.dst_addr}")
                            
                            if hasattr(packet, 'tcp'):
                                if hasattr(packet.tcp, 'src_port'):
                                    self._log.info(f"  - TCP Src Port: {packet.tcp.src_port}")
                                if hasattr(packet.tcp, 'dst_port'):
                                    self._log.info(f"  - TCP Dst Port: {packet.tcp.dst_port}")
                            self._log.info("-------------------------")


                        self._driver.send(packet, self._stats)
                        self._stats.sent_packets += 1
                        self._stats.sent_bytes += packet_len
                        error_count = 0  # Reset on success
                    else:
                        # No packet received, this is normal with a timeout.
                        time.sleep(0.001)
                        continue

                except WinDivertError as e:
                    # Check for the specific "incorrect parameter" error on send
                    if isinstance(e.__cause__, OSError) and e.__cause__.winerror == 87:
                        self._stats.send_invalid_param_errors += 1
                        self._stats.dropped_packets += 1
                        if 'packet_len' in locals():
                            self._stats.dropped_bytes += packet_len

                        if self._stats.send_invalid_param_errors % 100 == 1:
                            self._log.warning(
                                "Got 'incorrect parameter' error on send, likely a checksum issue. Dropping packet. "
                                f"({self._stats.send_invalid_param_errors} total so far)"
                            )
                        continue # Treat as skippable

                    # Handle other, potentially more severe errors
                    error_count += 1
                    if error_count <= 3:
                        self._log.exception("A recoverable error occurred in the main loop (full traceback):")
                    else:
                        self._log.debug("A recoverable error occurred in the main loop.", exc_info=True)
                    
                    if error_count > max_errors:
                        self._log.critical(f"Exceeded max consecutive errors ({max_errors}). Stopping.")
                        raise SystemExit(1) from e
                    continue

                # Log stats periodically
                current_time = time.time()
                if current_time - last_stats_time >= self._stats_interval:
                    interval = current_time - last_stats_time
                    
                    packets_since_last = self._stats.captured_packets - last_packets
                    bytes_since_last = self._stats.captured_bytes - last_bytes
                    
                    pps = packets_since_last / interval if interval > 0 else 0
                    mbps = (bytes_since_last * 8) / (interval * 1_000_000) if interval > 0 else 0

                    self._log.info(f"{self._stats.format()} | {pps:.2f} pps, {mbps:.2f} Mbps")

                    last_stats_time = current_time
                    last_packets = self._stats.captured_packets
                    last_bytes = self._stats.captured_bytes

        except KeyboardInterrupt:
            self._log.info("Ctrl+C received. Shutting down passthrough engine.")
        except Exception as e:
            self._log.critical(f"An unhandled exception occurred in the engine: {e}", exc_info=True)
        finally:
            self._driver.close()
            self._log.info("Passthrough engine stopped.")
