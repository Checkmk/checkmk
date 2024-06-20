#!/bin/bash
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from logging import getLogger
from logging.handlers import WatchedFileHandler
from pathlib import Path
from types import FrameType

from cmk.utils.daemon import daemonize, pid_file_lock

VERBOSITY_MAP = {
    0: logging.INFO,
    1: 15,
    2: logging.DEBUG,
}


class SignalException(Exception):
    pass


@dataclass
class Arguments:
    foreground: bool
    debug: bool
    verbosity: int
    pid_file: str
    log_file: str


def _parse_arguments(argv: list[str]) -> Arguments:
    parser = argparse.ArgumentParser(description="Piggyback Hub daemon")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Enable verbose output, twice for more details",
    )
    parser.add_argument(
        "-g",
        "--foreground",
        action="store_true",
        help="Run in the foreground instead of daemonizing",
    )
    parser.add_argument("--debug", action="store_true", help="Let Python exceptions come through")
    parser.add_argument("pid_file", help="Path to the PID file")
    parser.add_argument("log_file", help="Path to the log file")

    args = parser.parse_args(argv[1:])
    return Arguments(
        foreground=args.foreground,
        verbosity=args.verbose,
        debug=args.debug,
        pid_file=args.pid_file,
        log_file=args.log_file,
    )


def _setup_logging(args: Arguments) -> logging.Logger:
    logger = getLogger("cmk.piggyback_hub")
    handler: logging.StreamHandler | WatchedFileHandler = (
        logging.StreamHandler(stream=sys.stderr)
        if args.foreground
        else WatchedFileHandler(Path(args.log_file))
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s] %(message)s"))
    logger.addHandler(handler)

    logger.setLevel(VERBOSITY_MAP.get(args.verbosity, logging.INFO))

    return logger


def signal_handler(_signum: int, _stack_frame: FrameType | None) -> None:
    raise SignalException()


def _register_signal_handler() -> None:
    signal.signal(signal.SIGTERM, signal_handler)


# a dummy daemon for now
def run_piggyback_hub():
    while True:
        time.sleep(5)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv

    args = _parse_arguments(argv)
    logger = _setup_logging(args)

    logger.info("Starting Piggyback Hub daemon.")

    try:
        _register_signal_handler()
    except Exception as e:
        if args.debug:
            raise
        logger.exception("Unhandled exception: %s.", e)
        return 1

    if not args.foreground:
        daemonize()
        logger.info("Daemonized with PID %d.", os.getpid())

    try:
        with pid_file_lock(Path(args.pid_file)):
            run_piggyback_hub()
    except SignalException:
        logger.info("Stopping Piggyback Hub daemon.")
    except Exception as e:
        if args.debug:
            raise
        logger.exception("Unhandled exception: %s.", e)
        return 1

    logger.info("Shuting down.")
    return 0
