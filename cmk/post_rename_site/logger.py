#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import getLogger

import cmk.utils.log as log

logger = getLogger("cmk.post_rename_site")


def setup_logging(*, verbose: bool) -> None:
    level = log.verbosity_to_log_level(verbose)

    log.setup_console_logging()
    log.logger.setLevel(level)

    logger.setLevel(level)

    # TODO: Fix this cruel hack caused by our funny mix of GUI + console
    # stuff. Currently, we just move the console handler to the top, so
    # both worlds are happy. We really, really need to split business logic
    # from presentation code... :-/
    if log.logger.handlers:
        console_handler = log.logger.handlers[0]
        del log.logger.handlers[:]
        getLogger().addHandler(console_handler)
