import ctypes
import logging
import os
from typing import Optional


class WinDivertCtypesError(Exception):
    """Custom exception for WinDivert ctypes related errors."""
    pass


# Ensure local ./windivert directory is on PATH before importing pydivert's DLL
_here = os.path.dirname(__file__)
_root = os.path.abspath(os.path.join(_here, ".."))
_windivert_dir = os.path.join(_root, "windivert")
if os.path.isdir(_windivert_dir):
    current_path = os.environ.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    if _windivert_dir not in path_parts:
        os.environ["PATH"] = _windivert_dir + os.pathsep + current_path

import pydivert.windivert_dll as _wdll
from pydivert.windivert_dll.structs import WinDivertAddress


def _require_windivert_func(name: str):
    """Fetch a WinDivert* symbol from pydivert.windivert_dll or raise a clear error."""
    try:
        return getattr(_wdll, name)
    except AttributeError as exc:  # pragma: no cover - defensive
        available = [n for n in dir(_wdll) if "WinDivert" in n]
        raise WinDivertCtypesError(
            f"pydivert.windivert_dll is missing symbol '{name}'. "
            f"Available WinDivert* symbols: {available}"
        ) from exc


# Bind the known-good function objects from pydivert.
WinDivertOpen = _require_windivert_func("WinDivertOpen")
WinDivertRecv = _require_windivert_func("WinDivertRecv")
WinDivertSend = _require_windivert_func("WinDivertSend")
WinDivertClose = _require_windivert_func("WinDivertClose")
WinDivertHelperCalcChecksums = _require_windivert_func("WinDivertHelperCalcChecksums")


class WinDivertCtypesDriver:
    """Thin wrapper around pydivert's WinDivert DLL bindings."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self._log = logger or logging.getLogger(__name__)
        self._handle = None

    def open(self, filter_str: str, priority: int = 0, flags: int = 0) -> None:
        """
        Opens the WinDivert driver with the specified filter.

        Args:
            filter_str: The packet filter string.
            priority: The priority of the handle.
            flags: Flags for the handle.
        """
        if self._handle:
            self._log.warning("WinDivert handle is already open.")
            return

        self._log.info(f"Opening WinDivert handle with filter: '{filter_str}'")

        # Layer is always 0 (Network) for now
        WINDIVERT_LAYER_NETWORK = 0

        # Convert filter string to bytes for c_char_p
        filter_bytes = filter_str.encode('utf-8')

        handle = WinDivertOpen(filter_bytes, WINDIVERT_LAYER_NETWORK, priority, flags)

        # WinDivertOpen returns INVALID_HANDLE_VALUE (-1) on error
        if handle is None or handle == ctypes.c_void_p(-1).value:
            error_code = ctypes.get_last_error()
            self._log.error(f"WinDivertOpen failed with error code: {error_code}")
            raise WinDivertCtypesError(f"Failed to open WinDivert handle. WinAPI Error: {error_code}")
        
        self._handle = handle
        self._log.info(f"WinDivert handle opened successfully: {self._handle}")

    def recv(self, bufsize: int = 0xFFFF) -> tuple[bytes, WinDivertAddress]:
        if not self._handle:
            raise WinDivertCtypesError("WinDivert handle is not open. Call open() first.")

        packet_buffer = ctypes.create_string_buffer(bufsize)
        addr = WinDivertAddress()
        read_len = ctypes.c_uint(0)

        ok = WinDivertRecv(
            self._handle,
            packet_buffer,
            bufsize,
            ctypes.byref(addr),
            ctypes.byref(read_len),
        )

        if not ok:
            err = ctypes.get_last_error()
            raise WinDivertCtypesError(f"WinDivertRecv failed, GetLastError={err}")

        length = read_len.value
        if length <= 0 or length > bufsize:
            raise WinDivertCtypesError(
                f"WinDivertRecv returned invalid length: {length} (bufsize={bufsize})"
            )

        packet_bytes = packet_buffer.raw[:length]
        return packet_bytes, addr

    def send(self, packet: bytes, addr: WinDivertAddress) -> None:
        if not self._handle:
            raise WinDivertCtypesError("WinDivert handle is not open. Call open() first.")

        packet_len = len(packet)
        packet_buffer = ctypes.create_string_buffer(packet, packet_len)

        # Recalculate checksums in-place
        WinDivertHelperCalcChecksums(packet_buffer, packet_len, 0)

        write_len = ctypes.c_uint(0)
        ok = WinDivertSend(
            self._handle,
            packet_buffer,
            packet_len,
            ctypes.byref(addr),
            ctypes.byref(write_len),
        )

        if not ok:
            err = ctypes.get_last_error()
            raise WinDivertCtypesError(f"WinDivertSend failed, GetLastError={err}")

    def close(self) -> None:
        """Closes the WinDivert driver."""
        if not self._handle:
            self._log.debug("No WinDivert handle to close.")
            return

        self._log.debug(f"Closing WinDivert handle: {self._handle}")
        
        if not WinDivertClose(self._handle):
            error_code = ctypes.get_last_error()
            self._log.error(f"WinDivertClose failed for handle {self._handle} with error code: {error_code}")
        else:
            self._log.info(f"WinDivert handle {self._handle} closed successfully.")
        
        self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
