#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import multiprocessing
import signal
import sys
from pathlib import Path
from typing import Callable, Generic, TypeVar

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
        model: type[_ModelT],
        callback: Callable[[Channel[_ModelT], DeliveryTag, _ModelT], None],
        queue: QueueName,
        message_ttl: int | None,
    ) -> None:
        super().__init__()
        self.logger = logger
        self.omd_root = omd_root
        self.model = model
        self.callback = callback
        self.queue = queue
        self.message_ttl = message_ttl
        self.task_name = f"receiving on queue '{self.queue.value}'"

    def run(self) -> None:
        self.logger.info("Starting: %s", self.task_name)
        signal.signal(
            signal.SIGTERM,
            make_log_and_exit(self.logger.debug, f"Stopping: {self.task_name}"),
        )
        try:
            with Connection(APP_NAME, self.omd_root) as conn:
                channel: Channel[_ModelT] = conn.channel(self.model)
                channel.queue_declare(queue=self.queue, message_ttl=self.message_ttl)

                self.logger.debug("Consuming: %s", self.task_name)
                channel.consume(self.queue, self.callback)

        except CMKConnectionError as exc:
            self.logger.error("Stopping: %s: %s", self.task_name, exc)
        except Exception as exc:
            self.logger.exception("Exception: %s: %s", self.task_name, exc)
            raise
