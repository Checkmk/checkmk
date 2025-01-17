#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import logging
import multiprocessing
import signal
import sys
import time
from collections.abc import Callable
from pathlib import Path
from ssl import SSLCertVerificationError
from typing import Generic, TypeVar

from pydantic import BaseModel

from cmk.messaging import AppName, Channel, CMKConnectionError, Connection, DeliveryTag, QueueName

APP_NAME = AppName("piggyback-hub")

_ModelT = TypeVar("_ModelT", bound=BaseModel)


def make_log_and_exit(log: Callable[[str], None], message: str) -> Callable[[object, object], None]:
    def log_and_exit(signum: object, frame: object) -> None:
        log(message)
        sys.exit(0)

    return log_and_exit


class ReceivingProcess(multiprocessing.Process, Generic[_ModelT]):
    def __init__(
        self,
        logger: logging.Logger,
        omd_root: Path,
        site: str,
        model: type[_ModelT],
        callback: Callable[[Channel[_ModelT], DeliveryTag, _ModelT], None],
        crash_report_callback: Callable[[], str],
        queue: QueueName,
        message_ttl: int | None,
    ) -> None:
        super().__init__()
        self.logger = logger
        self.omd_root = omd_root
        self.site = site
        self.model = model
        self.callback = callback
        self.crash_report_callback = crash_report_callback
        self.queue = queue
        self.message_ttl = message_ttl
        self.task_name = f"receiving on queue '{self.queue.value}'"

    def run(self) -> None:
        self.logger.info("Starting: %s", self.task_name)
        signal.signal(
            signal.SIGTERM,
            make_log_and_exit(self.logger.info, f"Terminating: {self.task_name}"),
        )
        try:
            while True:
                with make_connection(self.omd_root, self.site, self.logger, self.task_name) as conn:
                    try:
                        channel: Channel[_ModelT] = conn.channel(self.model)
                        channel.queue_declare(queue=self.queue, message_ttl=self.message_ttl)

                        self.logger.debug("Consuming: %s", self.task_name)
                        channel.consume(self.queue, self.callback)
                    except CMKConnectionError as exc:
                        self.logger.info(
                            "Interrupted by failed connection: %s: %s", self.task_name, exc
                        )
        except CMKConnectionError as exc:
            self.logger.error("Reconnecting failed: %s: %s", self.task_name, exc)
        except Exception as exc:
            self.logger.exception("Exception: %s: %s", self.task_name, exc)
            crash_report_msg = self.crash_report_callback()
            self.logger.error(crash_report_msg)
            raise


def make_connection(
    omd_root: Path, omd_site: str, logger: logging.Logger, task_name: str
) -> Connection:
    retry_during_presumed_broker_restart = itertools.repeat(3, 20)
    retry_forever = itertools.repeat(60)

    for interval in itertools.chain(retry_during_presumed_broker_restart, retry_forever):
        try:
            # Note: We re-read the certificates here.
            return Connection(APP_NAME, omd_root, omd_site)
        except (
            # Certs could have changed
            SSLCertVerificationError,
            # and/or broker is restarting
            CMKConnectionError,
        ) as exc:
            logger.info("Connection failed (will retry): %s: %s", task_name, exc)
            # Retry.
            time.sleep(interval)

    raise RuntimeError("Unreachable code reached")
