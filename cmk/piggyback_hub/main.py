#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
import os
import signal
import sys
from dataclasses import dataclass
from itertools import cycle
from logging import getLogger
from logging.handlers import WatchedFileHandler
from pathlib import Path
from threading import Event

from cmk.ccc.daemon import daemonize, pid_file_lock

from cmk.messaging import QueueName
from cmk.piggyback_hub.config import PiggybackHubConfig, save_config_on_message
from cmk.piggyback_hub.payload import (
    PiggybackPayload,
    save_payload_on_message,
    SendingPayloadProcess,
)

from .config import CONFIG_QUEUE
from .utils import APP_NAME, ReceivingProcess

VERBOSITY_MAP = {
    0: logging.INFO,
    1: 15,
    2: logging.DEBUG,
}


@dataclass
class Arguments:
    foreground: bool
    debug: bool
    verbosity: int
    pid_file: str
    log_file: str
    omd_root: str


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
    parser.add_argument("omd_root", help="Site root path")

    args = parser.parse_args(argv[1:])
    return Arguments(
        foreground=args.foreground,
        verbosity=args.verbose,
        debug=args.debug,
        pid_file=args.pid_file,
        log_file=args.log_file,
        omd_root=args.omd_root,
    )


def _setup_logging(args: Arguments) -> logging.Logger:
    logger = getLogger("cmk.piggyback_hub")
    handler: logging.StreamHandler | WatchedFileHandler = (
        logging.StreamHandler(stream=sys.stderr)
        if args.foreground
        else WatchedFileHandler(Path(args.log_file))
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s"))
    logger.addHandler(handler)

    logger.setLevel(VERBOSITY_MAP[max(args.verbosity, 2)])

    return logger


def run_piggyback_hub(logger: logging.Logger, omd_root: Path) -> int:
    reload_config = Event()
    processes = (
        ReceivingProcess(
            logger,
            omd_root,
            PiggybackPayload,
            save_payload_on_message(logger, omd_root),
            QueueName("payload"),
            message_ttl=600,
        ),
        SendingPayloadProcess(logger, omd_root, reload_config),
        ReceivingProcess(
            logger,
            omd_root,
            PiggybackHubConfig,
            save_config_on_message(logger, omd_root, reload_config),
            CONFIG_QUEUE,
            message_ttl=None,
        ),
    )

    for p in processes:
        p.start()

    def terminate_all_processes() -> int:
        logger.info("Stopping: %s", APP_NAME)
        for p in processes:
            p.terminate()
        return 0

    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(terminate_all_processes()))

    # All processes should run forever. Die if either finishes.
    for proc in cycle(processes):
        proc.join(timeout=5)
        if not proc.is_alive():
            return terminate_all_processes()

    raise RuntimeError("Unreachable code reached")


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv

    args = _parse_arguments(argv)
    logger = _setup_logging(args)

    logger.info("Starting: %s", APP_NAME)

    if not args.foreground:
        daemonize()
        logger.info("Daemonized with PID %d.", os.getpid())

    try:
        with pid_file_lock(Path(args.pid_file)):
            return run_piggyback_hub(logger, Path(args.omd_root))
    except Exception as exc:
        if args.debug:
            raise
        logger.exception("Exception: %s: %s", APP_NAME, exc)
        return 1
