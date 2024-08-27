#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from logging import getLogger
from logging.handlers import WatchedFileHandler
from pathlib import Path
from types import FrameType

from pydantic import BaseModel

from cmk.utils.daemon import daemonize, pid_file_lock
from cmk.utils.hostaddress import HostName

from cmk.messaging import Channel, Connection
from cmk.piggyback import (
    get_piggyback_raw_data,
    load_last_distribution_time,
    PiggybackMessage,
    PiggybackMetaData,
    store_last_distribution_time,
    store_piggyback_raw_data,
)
from cmk.piggyback_hub.config import config_path, PiggybackConfig, save_config, Target
from cmk.piggyback_hub.utils import receive_messages, SignalException

VERBOSITY_MAP = {
    0: logging.INFO,
    1: 15,
    2: logging.DEBUG,
}


SENDING_PAUSE = 60  # [s]


@dataclass
class Arguments:
    foreground: bool
    debug: bool
    verbosity: int
    pid_file: str
    log_file: str
    omd_root: str


class PiggybackPayload(BaseModel):
    source_host: str
    target_host: str
    last_update: int
    last_contact: int | None
    sections: Sequence[bytes]


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
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s] %(message)s"))
    logger.addHandler(handler)

    logger.setLevel(VERBOSITY_MAP.get(args.verbosity, logging.INFO))

    return logger


def signal_handler(_signum: int, _stack_frame: FrameType | None) -> None:
    raise SignalException()


def _register_signal_handler() -> None:
    signal.signal(signal.SIGTERM, signal_handler)


def _save_payload(
    logger: logging.Logger,
    omd_root: Path,
) -> Callable[[object, object, object, PiggybackPayload], None]:
    def _on_message(
        _channel: object, _delivery: object, _properties: object, received: PiggybackPayload
    ) -> None:
        logger.debug(
            "Received payload for piggybacked host '%s' from source host '%s'",
            received.target_host,
            received.source_host,
        )
        store_piggyback_raw_data(
            source_hostname=HostName(received.source_host),
            piggybacked_raw_data={HostName(received.target_host): received.sections},
            timestamp=received.last_update,
            omd_root=omd_root,
            status_file_timestamp=received.last_contact,
        )

    return _on_message


def _load_piggyback_targets(
    piggyback_hub_config_path: Path, current_site_id: str
) -> Sequence[Target]:
    if not piggyback_hub_config_path.exists():
        return []
    with open(piggyback_hub_config_path, "r") as f:
        piggyback_hub_config: Sequence[Mapping[str, str]] = json.load(f)

    targets = []
    for config in piggyback_hub_config:
        match config:
            case {"host_name": target_host_name, "site_id": target_site_id}:
                if target_site_id != current_site_id:
                    targets.append(
                        Target(host_name=HostName(target_host_name), site_id=target_site_id)
                    )
            case other:
                raise ValueError(f"Invalid piggyback_hub configuration: {other}")
    return targets


def _is_message_already_distributed(meta: PiggybackMetaData, omd_root: Path) -> bool:
    if (
        distribution_time := load_last_distribution_time(meta.source, meta.piggybacked, omd_root)
    ) is None:
        return False

    return distribution_time >= meta.last_update


def _get_piggyback_raw_data_to_send(
    target_host: HostName, omd_root: Path
) -> Sequence[PiggybackMessage]:
    return [
        data
        for data in get_piggyback_raw_data(target_host, omd_root)
        if not _is_message_already_distributed(data.meta, omd_root)
    ]


def _send_message(
    channel: Channel,
    piggyback_message: PiggybackMessage,
    target_site_id: str,
    omd_root: Path,
    routing: str,
) -> None:
    channel.publish_for_site(
        target_site_id,
        PiggybackPayload(
            source_host=piggyback_message.meta.source,
            target_host=piggyback_message.meta.piggybacked,
            last_update=piggyback_message.meta.last_update,
            last_contact=piggyback_message.meta.last_contact,
            sections=[piggyback_message.raw_data],
        ),
        routing=routing,
    )
    store_last_distribution_time(
        piggyback_message.meta.source,
        piggyback_message.meta.piggybacked,
        piggyback_message.meta.last_update,
        omd_root,
    )


def _send_messages(logger: logging.Logger, omd_root: Path) -> None:
    try:
        with Connection("piggyback-hub", omd_root) as conn:
            channel = conn.channel(PiggybackPayload)

            while True:
                targets = _load_piggyback_targets(config_path(omd_root), omd_root.name)
                for target in targets:
                    for piggyback_message in _get_piggyback_raw_data_to_send(
                        target.host_name, omd_root
                    ):
                        logger.debug(
                            "Sending payload for piggybacked host '%s' from source host '%s' to site '%s'",
                            piggyback_message.meta.piggybacked,
                            piggyback_message.meta.source,
                            target.site_id,
                        )
                        _send_message(
                            channel, piggyback_message, target.site_id, omd_root, "payload"
                        )

                time.sleep(SENDING_PAUSE)
    except SignalException:
        logger.debug("Stopping distributing messages")
        return
    except Exception as e:
        logger.exception("Unhandled exception: %s.", e)


def run_piggyback_hub(logger: logging.Logger, omd_root: Path) -> None:
    # TODO: remove this loop when rabbitmq available in site
    while True:
        time.sleep(5)

    receiving_thread = threading.Thread(
        target=receive_messages,
        args=(logger, omd_root, PiggybackPayload, _save_payload, "payload"),
    )
    sending_thread = threading.Thread(target=_send_messages, args=(logger, omd_root))
    receive_config_thread = threading.Thread(
        target=receive_messages, args=(logger, omd_root, PiggybackConfig, save_config, "config")
    )

    receiving_thread.start()
    sending_thread.start()
    receive_config_thread.start()
    receiving_thread.join()
    sending_thread.join()
    receive_config_thread.join()


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
            run_piggyback_hub(logger, Path(args.omd_root))
    except SignalException:
        logger.info("Stopping Piggyback Hub daemon.")
    except Exception as e:
        if args.debug:
            raise
        logger.exception("Unhandled exception: %s.", e)
        return 1

    logger.info("Shutting down.")
    return 0
