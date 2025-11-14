#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""TimeoutManager tests

These test cases are intended to be run in the site context.

To avoid pytest collection errors, neither the module nor the functions are prefixed with "test_".
"""

import logging
import sys
import time

from cmk.gui.exceptions import RequestTimeout
from cmk.gui.utils.timeout_manager import TimeoutManager

logger = logging.getLogger(__name__)


def timeout_manager_disable() -> int:
    tm = TimeoutManager()
    tm.enable_timeout(1)
    tm.disable_timeout()
    try:
        time.sleep(1)
    except TimeoutError as excp:
        logger.exception("Timeout raised while TimeoutManager was disabled!", exc_info=excp)
        return 1
    else:
        return 0


def timeout_manager_raises_timeout() -> int:
    tm = TimeoutManager()
    tm.enable_timeout(1)
    try:
        time.sleep(2)
    except RequestTimeout:
        return 0
    else:
        logger.exception("No timeout raised while TimeoutManager was enabled!")
        return 1


if __name__ == "__main__":
    if len(sys.argv) == 2:
        test_name = sys.argv[1]
        if test_name == "disable":
            sys.exit(timeout_manager_disable())
        if test_name == "raises_timeout":
            sys.exit(timeout_manager_raises_timeout())
        logger.error('Test "%s" is unknown!', test_name)
        sys.exit(2)
    else:
        logger.error("No test specified!")
        sys.exit(3)
