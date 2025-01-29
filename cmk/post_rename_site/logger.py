#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from logging import Formatter, getLogger, StreamHandler

from cmk.utils import log

logger = getLogger("cmk.post_rename_site")


# TODO: Fix this cruel hack caused by our funny mix of GUI + console stuff.
def setup_logging(*, verbose: int) -> None:
    log.logger.setLevel(log.verbosity_to_log_level(verbose))
    logger.setLevel(log.logger.level)
    handler = StreamHandler(sys.stdout)
    handler.setFormatter(Formatter("%(message)s"))
    getLogger().addHandler(handler)
