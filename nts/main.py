import argparse
import logging
import time
import sys

from nts.logging_setup import setup_logging
from nts.stats import Stats
from nts.admin import is_admin
from nts.windivert_iface import WinDivertDriver, WinDivertError
from nts.windivert_ctypes import WinDivertCtypesDriver, WinDivertCtypesError
from nts.engine import PassthroughEngine

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
        "--mode",
        choices=["dry-run", "windivert-smoke", "passthrough", "ctypes-smoke"],
        default="dry-run",
        help="The operation mode.",
    )
    parser.add_argument(
        "--filter",
        default="outbound and tcp and ip",
        help="WinDivert filter string."
    )
    parser.add_argument(
        "--run-seconds",
        type=float,
        default=0, # Default to run indefinitely
        help="Duration in seconds for the operation to run. 0 for indefinite.",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=20,
        help="Maximum number of consecutive errors before stopping.",
    )
    parser.add_argument(
        "--max-packets",
        type=int,
        default=0,
        help="Maximum number of packets to capture before stopping. 0 for unlimited.",
    )
    parser.add_argument(
        "--diagnostic-packets",
        type=int,
        default=20,
        help="Number of initial packets to log with full diagnostics.",
    )

    args = parser.parse_args()

    try:
        setup_logging(args.log_level, args.log_dir)
    except Exception as e:
        logging.basicConfig()
        logging.critical(f"Failed to set up logging: {e}", exc_info=True)
        sys.exit(1)

    log = logging.getLogger(__name__)

    # Admin check for modes that require it
    if args.mode in ["windivert-smoke", "passthrough", "ctypes-smoke"] and not is_admin():
        log.error(f"The '{args.mode}' mode must be run as Administrator.")
        sys.exit(2)

    stats = Stats()

    if args.mode == "dry-run":
        log.info("Starting dry run mode. Press Ctrl+C to exit.")
        try:
            while True:
                log.info(stats.format())
                time.sleep(args.stats_interval)
        except KeyboardInterrupt:
            log.info("Ctrl+C received. Shutting down gracefully.")
            sys.exit(0)
        except Exception as e:
            log.critical(f"An unexpected error occurred during dry run: {e}", exc_info=True)
            sys.exit(1)

    elif args.mode == "windivert-smoke":
        log.info("Starting WinDivert smoke test.")
        try:
            with WinDivertDriver(logger=log) as driver:
                driver.open(args.filter)
                run_duration = args.run_seconds or 2.0
                log.info(f"WinDivert opened successfully. Running for {run_duration} seconds...")
                time.sleep(run_duration)
                log.info("WinDivert smoke test duration finished.")
            log.info("WinDivert smoke test succeeded.")
            sys.exit(0)
        except WinDivertError as e:
            log.critical(f"WinDivert smoke test failed: {e}", exc_info=log.level <= logging.DEBUG)
            sys.exit(1)
        except Exception as e:
            log.critical(f"An unexpected error occurred during the smoke test: {e}", exc_info=True)
            sys.exit(1)

    elif args.mode == "ctypes-smoke":
        log.info("Starting WinDivert ctypes smoke test.")
        try:
            with WinDivertCtypesDriver(logger=log) as driver:
                driver.open(args.filter)
                run_duration = args.run_seconds or 2.0
                log.info(f"WinDivert (ctypes) opened successfully. Running for {run_duration} seconds...")
                time.sleep(run_duration)
                log.info("WinDivert (ctypes) smoke test duration finished.")
            log.info("WinDivert (ctypes) smoke test succeeded.")
            sys.exit(0)
        except WinDivertCtypesError as e:
            log.critical(f"WinDivert (ctypes) smoke test failed: {e}", exc_info=log.level <= logging.DEBUG)
            sys.exit(1)
        except Exception as e:
            log.critical(f"An unexpected error occurred during the ctypes smoke test: {e}", exc_info=True)
            sys.exit(1)

    elif args.mode == "passthrough":
        log.info("Starting passthrough mode.")
        driver = WinDivertDriver(logger=log)
        engine = PassthroughEngine(
            driver=driver,
            filter_str=args.filter,
            stats=stats,
            stats_interval=args.stats_interval,
            logger=log,
        )
        engine.run(
            run_seconds=args.run_seconds,
            max_errors=args.max_errors,
            max_packets=args.max_packets,
            diagnostic_packets=args.diagnostic_packets
        )
        sys.exit(0)

    else:
        log.info("Application started. No operation specified.")

if __name__ == "__main__":
    main()
