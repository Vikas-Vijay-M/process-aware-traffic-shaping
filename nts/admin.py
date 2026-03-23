import ctypes
import os

def is_admin():
    """
    Checks if the current user has administrator privileges.

    Returns:
        bool: True if the user is an admin, False otherwise.
    """
    try:
        return os.getuid() == 0
    except AttributeError:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
