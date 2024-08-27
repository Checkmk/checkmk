#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel

from cmk.messaging import Channel, Connection

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class SignalException(Exception):
    pass


def receive_messages(
    logger: logging.Logger,
    omd_root: Path,
    model: type[_ModelT],
    callback: Callable[[logging.Logger, Path], Callable[[object, object, object, _ModelT], None]],
    queue: str,
) -> None:
    try:
        with Connection("piggyback-hub", omd_root) as conn:
            channel: Channel[_ModelT] = conn.channel(model)
            channel.queue_declare(queue=queue, bindings=(queue,))
            on_message_callback = callback(logger, omd_root)

            logger.debug("Waiting for messages in queue %s", queue)

            while True:
                channel.consume(on_message_callback, queue=queue)
    except SignalException:
        logger.debug("Stopping receiving messages")
        return
    except Exception as e:
        logger.exception("Unhandled exception: %s.", e)
