#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import threading
from pathlib import Path
from typing import Callable, Generic, TypeVar

from pydantic import BaseModel

from cmk.messaging import Channel, Connection

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class SignalException(Exception):
    pass


class ReceivingThread(threading.Thread, Generic[_ModelT]):
    def __init__(
        self,
        logger: logging.Logger,
        omd_root: Path,
        model: type[_ModelT],
        callback: Callable[[Channel[_ModelT], _ModelT], None],
        queue: str,
    ) -> None:
        super().__init__()
        self.logger = logger
        self.omd_root = omd_root
        self.model = model
        self.callback = callback
        self.queue = queue

    def run(self) -> None:
        try:
            with Connection("piggyback-hub", self.omd_root) as conn:
                channel: Channel[_ModelT] = conn.channel(self.model)
                channel.queue_declare(queue=self.queue, bindings=(self.queue,))

                self.logger.debug("Waiting for messages in queue %s", self.queue)

                while True:
                    channel.consume(self.callback, queue=self.queue)
        except SignalException:
            self.logger.debug("Stopping receiving messages")
            return
        except Exception as e:
            self.logger.exception("Unhandled exception: %s.", e)
