#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from logging import Logger
from pathlib import Path
from typing import Literal, TypedDict

from cmk.ccc import store

from .event_context import EnrichedEventContext
from .notification_result import NotificationContext, NotificationResult


class NotificationForward(TypedDict):
    forward: Literal[True]
    context: EnrichedEventContext


class NotificationViaPlugin(TypedDict):
    plugin: str
    context: NotificationContext


def create_spool_file(
    logger_: Logger,
    spool_dir: Path,
    data: NotificationForward | NotificationResult | NotificationViaPlugin,
) -> None:
    spool_dir.mkdir(parents=True, exist_ok=True)
    file_path = spool_dir / str(uuid.uuid4())
    logger_.info("Creating spoolfile: %s", file_path)
    store.save_object_to_file(file_path, data, pprint_value=True)
