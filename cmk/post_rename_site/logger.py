#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from logging import Formatter, getLogger, StreamHandler

import cmk.utils.log as log

logger = getLogger("cmk.post_rename_site")


def setup_logging(*, verbose: int) -> None:
    handler = StreamHandler(stream=sys.stdout)
    handler.setFormatter(Formatter("%(message)s"))
    del log.logger.handlers[:]  # Remove all previously existing handlers
    log.logger.addHandler(handler)

    log.logger.setLevel(log.verbosity_to_log_level(verbose))
    logger.setLevel(log.logger.level)

    # TODO: Fix this cruel hack caused by our funny mix of GUI + console
    # stuff. Currently, we just move the console handler to the top, so
    # both worlds are happy. We really, really need to split business logic
    # from presentation code... :-/
    if log.logger.handlers:
        console_handler = log.logger.handlers[0]
        del log.logger.handlers[:]
        getLogger().addHandler(console_handler)
