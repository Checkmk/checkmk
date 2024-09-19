#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Callable, Generic, TypeVar

from pydantic import BaseModel

from cmk.messaging import Channel, Connection

from .config import PiggybackConfig

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
                channel.consume(self.callback, queue=self.queue)

        except SignalException:
            self.logger.debug("Stopping receiving messages")
            return
        except Exception as e:
            self.logger.exception("Unhandled exception: %s.", e)


def distribute(configs: Mapping[str, PiggybackConfig], omd_root: Path) -> None:
    # TODO: remove the return statement and uncomment the code below after fix the flaky integration test
    return
    # for site_id, config in configs.items():
    #     with Connection("piggyback-hub", omd_root) as conn:
    #         channel = conn.channel(PiggybackConfig)
    #         channel.publish_for_site(site_id, config, routing="config")
