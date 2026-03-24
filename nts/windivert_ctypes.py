import ctypes
import logging
import os
from typing import Optional

class WinDivertCtypesError(Exception):
    """Custom exception for WinDivert ctypes related errors."""
    pass

class WinDivertCtypesDriver:
    """
    A ctypes-based wrapper for the WinDivert library.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self._log = logger or logging.getLogger(__name__)
        self._handle = None
        self._windivert_dll = None
        self._load_dll()

    def _load_dll(self):
        """Loads the WinDivert.dll library."""
        local_path = os.path.join(os.getcwd(), "windivert", "WinDivert.dll")
        if os.path.exists(local_path):
            self._log.debug(f"Found WinDivert.dll at local path: {local_path}")
            try:
                self._windivert_dll = ctypes.WinDLL(local_path)
                self._log.info("Successfully loaded WinDivert.dll from local path.")
                return
            except OSError as e:
                self._log.error(f"Failed to load WinDivert.dll from {local_path}", exc_info=True)
                raise WinDivertCtypesError(f"Failed to load local WinDivert.dll: {e}") from e

        self._log.debug("Local WinDivert.dll not found, trying system PATH.")
        try:
            self._windivert_dll = ctypes.WinDLL("WinDivert.dll")
            self._log.info("Successfully loaded WinDivert.dll from system PATH.")
        except OSError as e:
            self._log.critical("WinDivert.dll not found in local './windivert/' directory or in system PATH.")
            raise WinDivertCtypesError(
                "WinDivert.dll not found. Please download the latest WinDivert-x64.zip, "
                "create a './windivert' directory, and place WinDivert.dll and WinDivert64.sys inside."
            ) from e

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

        # Define function prototype for WinDivertOpen
        # HANDLE WinDivertOpen(const char *filter, WINDIVERT_LAYER layer, int16_t priority, uint64_t flags);
        try:
            WinDivertOpen = self._windivert_dll.WinDivertOpen
            WinDivertOpen.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_short, ctypes.c_ulonglong]
            WinDivertOpen.restype = ctypes.c_void_p
        except AttributeError as e:
            raise WinDivertCtypesError("Invalid WinDivert.dll: WinDivertOpen function not found.") from e

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

    def close(self) -> None:
        """Closes the WinDivert driver."""
        if not self._handle:
            self._log.debug("No WinDivert handle to close.")
            return

        self._log.debug(f"Closing WinDivert handle: {self._handle}")
        
        # Define function prototype for WinDivertClose
        # BOOL WinDivertClose(HANDLE handle);
        try:
            WinDivertClose = self._windivert_dll.WinDivertClose
            WinDivertClose.argtypes = [ctypes.c_void_p]
            WinDivertClose.restype = ctypes.c_bool
        except AttributeError as e:
            raise WinDivertCtypesError("Invalid WinDivert.dll: WinDivertClose function not found.") from e

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
