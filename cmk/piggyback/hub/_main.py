#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
import signal
import sys
from collections.abc import Callable
from dataclasses import dataclass
from itertools import cycle
from logging import getLogger
from logging.handlers import WatchedFileHandler
from multiprocessing import Event as make_event
from multiprocessing.synchronize import Event
from pathlib import Path

from cmk.ccc.daemon import daemonize, pid_file_lock

from cmk.messaging import Channel, DeliveryTag, QueueName, set_logging_level

from ._config import CONFIG_QUEUE, ConfigType, PiggybackHubConfig, save_config
from ._payload import (
    PiggybackPayload,
    save_payload_on_message,
    send_messages_oneshot,
    SendingPayloadProcess,
)
from ._utils import APP_NAME, ReceivingProcess


@dataclass
class Arguments:
    foreground: bool
    debug: bool
    log_level: int
    pid_file: str
    log_file: str
    omd_root: str
    omd_site: str


def handle_received_config(
    logger: logging.Logger, omd_root: Path, omd_site: str, reload_config: Event
) -> Callable[[Channel[PiggybackHubConfig], DeliveryTag, PiggybackHubConfig], None]:
    def _on_message(
        channel: Channel[PiggybackHubConfig],
        delivery_tag: DeliveryTag,
        received: PiggybackHubConfig,
    ) -> None:
        logger.debug("New configuration received (type: %s)", received.type.name)

        match received.type:
            case ConfigType.ONESHOT:
                send_messages_oneshot(logger, omd_root, omd_site, received.locations)
            case ConfigType.PERSISTED:
                save_config(omd_root, received)
                reload_config.set()

        channel.acknowledge(delivery_tag)

    return _on_message


def _parse_arguments(argv: list[str]) -> Arguments:
    parser = argparse.ArgumentParser(description="Piggyback Hub daemon")
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default="NOTSET",
        choices=["CRITICAL", "FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        help="Override the configured logging level",
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
    parser.add_argument("omd_site", help="Site name")

    args = parser.parse_args(argv[1:])
    return Arguments(
        foreground=args.foreground,
        debug=args.debug,
        log_level=logging.getLevelNamesMapping()[args.log_level],
        pid_file=args.pid_file,
        log_file=args.log_file,
        omd_root=args.omd_root,
        omd_site=args.omd_site,
    )


def _setup_logging(args: Arguments) -> logging.Logger:
    logger = getLogger(__name__)
    handler: logging.StreamHandler | WatchedFileHandler = (
        logging.StreamHandler(stream=sys.stderr)
        if args.foreground
        else WatchedFileHandler(Path(args.log_file))
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(process)d] %(message)s"))
    logger.addHandler(handler)

    logger.setLevel(args.log_level)
    set_logging_level(args.log_level)

    return logger


def run_piggyback_hub(
    logger: logging.Logger, omd_root: Path, omd_site: str, crash_report_callback: Callable[[], str]
) -> int:
    reload_config = make_event()
    processes = (
        ReceivingProcess(
            logger,
            omd_root,
            omd_site,
            PiggybackPayload,
            save_payload_on_message(logger, omd_root),
            crash_report_callback,
            QueueName("payload"),
            message_ttl=600,
        ),
        SendingPayloadProcess(logger, omd_root, reload_config, crash_report_callback),
        ReceivingProcess(
            logger,
            omd_root,
            omd_site,
            PiggybackHubConfig,
            handle_received_config(logger, omd_root, omd_site, reload_config),
            crash_report_callback,
            CONFIG_QUEUE,
            message_ttl=None,
        ),
    )

    for p in processes:
        p.start()

    def terminate_all_processes(reason: str) -> int:
        logger.info("Stopping: %s (%s)", APP_NAME.value, reason)
        for p in processes:
            p.terminate()
        return 0

    signal.signal(
        signal.SIGTERM, lambda signum, frame: sys.exit(terminate_all_processes("received SIGTERM"))
    )

    # All processes should run forever. Die if either finishes.
    for proc in cycle(processes):
        proc.join(timeout=5)
        if not proc.is_alive():
            assert isinstance(proc, ReceivingProcess | SendingPayloadProcess)  # mypy :-/
            return terminate_all_processes(f"{proc.task_name} died")

    raise RuntimeError("Unreachable code reached")


def main(crash_report_callback: Callable[[], str], argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv

    if crash_report_callback is None:

        def dummy_crash_report():
            return "No crash report created"

        crash_report_callback = dummy_crash_report

    args = _parse_arguments(argv)
    logger = _setup_logging(args)
    omd_root = Path(args.omd_root)

    logger.info("Starting: %s", APP_NAME.value)

    if not args.foreground:
        daemonize()
        logger.info("Daemonized.")

    try:
        with pid_file_lock(Path(args.pid_file)):
            return run_piggyback_hub(logger, omd_root, args.omd_site, crash_report_callback)
    except Exception as exc:
        if args.debug:
            raise
        logger.exception("Exception: %s: %s", APP_NAME.value, exc)
        crash_report_msg = crash_report_callback()
        logger.error(crash_report_msg)
        return 1
