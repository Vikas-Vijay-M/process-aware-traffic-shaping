"""
This file contains the logging setup for the application.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_level: str, log_dir: str):
    """
    Set up logging to console and a rotating file.

    Args:
        log_level (str): The logging level.
        log_dir (str): The directory to store log files.
    """
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            logging.error(f"Error creating log directory {log_dir}: {e}")
            raise

    log_file = os.path.join(log_dir, "nts.log")

    # Set up the root logger
    logger = logging.getLogger()
    try:
        logger.setLevel(log_level.upper())
    except ValueError:
        logging.warning(f"Invalid log level '{log_level}'. Defaulting to INFO.")
        logger.setLevel(logging.INFO)
        log_level = "INFO"


    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # Rotating file handler
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        try:
            rfh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
            rfh.setFormatter(formatter)
            logger.addHandler(rfh)
        except (OSError, IOError) as e:
            logging.error(f"Could not open log file {log_file}: {e}")
            # Continue with console logging

    logging.info(f"Logging initialized with level {log_level} to directory {log_dir}")

