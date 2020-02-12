#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is an unsorted collection of functions which are needed in
Check_MK modules and/or cmk.base modules code."""

import signal
from types import FrameType  # pylint: disable=unused-import
from typing import NoReturn, Optional  # pylint: disable=unused-import

from cmk.utils.exceptions import MKTerminate
# TODO: Cleanup all imports of cmk.base.utils.* and purge these intermediate imports
from cmk.utils.type_defs import HostName, HostAddress, ServiceName, MetricName, CheckPluginName  # noqa: F401 # pylint: disable=unused-import

# TODO: Try to find a better place for them.


def worst_service_state(*states):
    # type: (int) -> int
    """Aggregates several monitoring states to the worst state"""
    if 2 in states:
        return 2
    return max(states)


#.
#   .--Ctrl-C--------------------------------------------------------------.
#   |                     ____ _        _        ____                      |
#   |                    / ___| |_ _ __| |      / ___|                     |
#   |                   | |   | __| '__| |_____| |                         |
#   |                   | |___| |_| |  | |_____| |___                      |
#   |                    \____|\__|_|  |_|      \____|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Handling of Ctrl-C                                                  |
#   '----------------------------------------------------------------------'


# register SIGINT handler for consistent CTRL+C handling
def _handle_keepalive_interrupt(signum, frame):
    # type: (int, Optional[FrameType]) -> NoReturn
    raise MKTerminate()


def register_sigint_handler():
    # type: () -> None
    signal.signal(signal.SIGINT, _handle_keepalive_interrupt)
