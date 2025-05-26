#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import FileHandler, Formatter, getLogger

import cmk.utils.log
import cmk.utils.paths

from cmk.trace.logs import add_span_log_handler

logger = getLogger("cmk.web")


def init_logging() -> None:
    handler = FileHandler(cmk.utils.paths.log_dir / "web.log", encoding="UTF-8")
    handler.setFormatter(Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s"))
    root = getLogger()
    del root.handlers[:]  # Remove all previously existing handlers
    root.addHandler(handler)
    add_span_log_handler()


def set_log_levels(log_levels: dict[str, int]) -> None:
    for name, level in _augmented_log_levels(log_levels).items():
        getLogger(name).setLevel(level)


# To see log entries from libraries and non-GUI code, reuse cmk.web's level.
def _augmented_log_levels(log_levels: dict[str, int]) -> dict[str, int]:
    root_level = log_levels.get("cmk.web")
    all_levels = {} if root_level is None else {"": root_level, "cmk": root_level}
    all_levels.update(log_levels)
    return all_levels
