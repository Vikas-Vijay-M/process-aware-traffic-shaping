
import argparse
import logging
import time
import sys

from nts.logging_setup import setup_logging
from nts.stats import Stats

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="NTS Application")
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Set the logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )
    parser.add_argument(
        "--log-dir", default="./logs", help="Directory for log files."
    )
    parser.add_argument(
        "--stats-interval",
        type=float,
        default=1.0,
        help="Interval in seconds to log stats.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, run in a loop logging stats without any real processing.",
    )

    args = parser.parse_args()

    try:
        setup_logging(args.log_level, args.log_dir)
    except Exception as e:
        logging.basicConfig()
        logging.critical(f"Failed to set up logging: {e}", exc_info=True)
        sys.exit(1)


    stats = Stats()
    log = logging.getLogger(__name__)

    if args.dry_run:
        log.info("Starting dry run mode. Press Ctrl+C to exit.")
        try:
            while True:
                # In a real application, you would update stats here.
                # For dry-run, we just log the current (zero) stats.
                log.info(stats.format())
                time.sleep(args.stats_interval)
        except KeyboardInterrupt:
            log.info("Ctrl+C received. Shutting down gracefully.")
            sys.exit(0)
        except Exception as e:
            log.critical(f"An unexpected error occurred during dry run: {e}", exc_info=True)
            sys.exit(1)
    else:
        log.info("Application started. No operation specified (use --dry-run for a demo).")
        # In a real application, the main logic would go here.

if __name__ == "__main__":
    main()
