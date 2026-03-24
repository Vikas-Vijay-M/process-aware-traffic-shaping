import logging
import sys
from typing import Optional

class WinDivertError(Exception):
    """Custom exception for WinDivert related errors."""
    pass

class WinDivertDriver:
    """A wrapper for the WinDivert library."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self._log = logger or logging.getLogger(__name__)
        self._handle = None
        self._send_mode = None

    def open(self, filter_str: str) -> None:
        """
        Opens the WinDivert driver with the specified filter.

        Args:
            filter_str: The packet filter string.

        Raises:
            WinDivertError: If there is an issue opening the driver.
        """
        if self._handle:
            self._log.warning("WinDivert handle is already open.")
            return

        try:
            # Lazy import to allow the app to run without pydivert for other modes.
            import pydivert
        except ImportError as e:
            self._log.critical("The 'pydivert' package is not installed. Please install it to use WinDivert.", exc_info=True)
            raise WinDivertError("pydivert package not found") from e

        try:
            self._log.info(f"Constructing WinDivert handle with filter: '{filter_str}'")
            self._handle = pydivert.WinDivert(filter_str)

            # Ensure the handle is actually opened.
            if hasattr(self._handle, 'open') and callable(getattr(self._handle, 'open')):
                self._log.debug("Calling self._handle.open()")
                self._handle.open()
            else:
                self._log.debug("pydivert handle does not have a callable .open() method; assuming constructor opens it.")

            # Sanity check if the handle reports its state.
            if hasattr(self._handle, 'is_open') and not self._handle.is_open:
                raise WinDivertError("pydivert handle was not open after initialization. Check library version or driver status.")
            elif hasattr(self._handle, 'is_open'):
                self._log.debug(f"pydivert handle is_open: {self._handle.is_open}")

            self._log.info("WinDivert handle is ready.")

        except Exception as e:
            # pydivert can raise various exceptions for driver/DLL issues.
            self._log.critical(
                "Failed to open WinDivert. Ensure WinDivert drivers are installed and accessible.",
                exc_info=True
            )
            raise WinDivertError("Failed to open WinDivert driver") from e

    def close(self) -> None:
        """Closes the WinDivert driver."""
        if self._handle:
            if hasattr(self._handle, 'close') and callable(getattr(self._handle, 'close')):
                try:
                    self._log.debug("Calling self._handle.close()")
                    self._handle.close()
                    self._log.info("WinDivert handle closed successfully.")
                except Exception as e:
                    self._log.error("An error occurred while closing the WinDivert handle.", exc_info=True)
            else:
                self._log.debug("Handle does not have a callable .close() method.")
        self._handle = None

    def recv(self, timeout: int = 1) -> object | None:
        """
        Receives a packet from the WinDivert handle.

        Args:
            timeout: The timeout in milliseconds for the receive operation.

        Returns:
            The received packet object, or None if no packet is received.
        """
        if not self._handle:
            self._log.error("Cannot receive, WinDivert handle is not open.")
            return None
        try:
            # pydivert's recv takes a timeout in milliseconds
            packet = self._handle.recv(timeout)
            if packet:
                if not hasattr(self, '_recv_logged_type'):
                    self._log.info(f"--- pydivert Packet Diagnostics (first packet) ---")
                    self._log.info(f"Packet type: {type(packet)}")
                    if hasattr(packet, "raw"):
                        self._log.info(f"Packet raw length: {len(packet.raw)}")
                    if hasattr(packet, "wd_addr"):
                        self._log.info(f"Packet wd_addr type: {type(packet.wd_addr)}")
                    
                    packet_dir = [
                        k for k in dir(packet) if "raw" in k or "addr" in k or "checksum" in k or 
                        "ip" in k or "tcp" in k or "udp" in k or "recalc" in k or "calc" in k
                    ]
                    self._log.info(f"Packet attributes: {packet_dir}")

                    handle_dir = [
                        k for k in dir(self._handle) if "send" in k or "recv" in k or "open" in k or
                        "close" in k or "helper" in k or "checksum" in k
                    ]
                    self._log.info(f"Handle attributes: {handle_dir}")
                    self._log.info(f"-------------------------------------------------")
                    self._recv_logged_type = True
                return packet
            return None
        except Exception as e:
            self._log.debug("An error occurred during recv.", exc_info=True)
            raise WinDivertError("Failed to receive packet") from e

    def send(self, packet: object, stats) -> None:
        """
        Sends a packet through the WinDivert handle using only pydivert.Packet.
        """
        if not self._handle:
            self._log.error("Cannot send, WinDivert handle is not open.")
            return

        # 1. Sanity check packet size
        raw_len = 0
        if hasattr(packet, 'raw') and isinstance(packet.raw, (bytes, bytearray, memoryview)):
            if isinstance(packet.raw, memoryview):
                raw_len = packet.raw.nbytes
            else:
                raw_len = len(packet.raw)
        
        if raw_len < 20:
            stats.skipped_too_small_packets += 1
            return

        # 2. Handle memoryview by rebuilding the packet
        original_packet = packet
        if isinstance(packet.raw, memoryview):
            try:
                import pydivert.packet
                raw_bytes = bytes(packet.raw)
                packet = pydivert.packet.Packet(raw_bytes, packet.wd_addr)
                self._log.debug("Rebuilt packet from memoryview.")
            except Exception as e:
                self._log.debug(f"Failed to rebuild packet from memoryview: {e}", exc_info=True)
                packet = original_packet # Fallback to original

        # 3. Always recalculate checksums
        if hasattr(packet, 'recalculate_checksums') and callable(packet.recalculate_checksums):
            if not hasattr(self, '_checksum_log_sent'):
                self._log.debug("Calling packet.recalculate_checksums() before sending.")
                self._checksum_log_sent = True
            packet.recalculate_checksums()
        
        # 4. Send the packet object
        try:
            self._handle.send(packet)
        except Exception as e:
            self._log.debug("An error occurred during send.", exc_info=True)
            raise WinDivertError("Failed to send packet") from e

    def __enter__(self):
        # The open call is not here because the filter is needed.
        # The user of the context manager should call open() explicitly.
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
